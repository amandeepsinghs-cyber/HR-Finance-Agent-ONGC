"""Vertex AI Policy Search and Rulebooks RAG Engine for Yukti AI.
Queries Vertex AI Search engine 'hrfin-doc-search-engine' (location: global)
and falls back to rulebooks_clause_index.csv and hrfin_docs.silver_chunks.
"""

import csv
import logging
import os
import time
from typing import Any, Dict, List, Optional
from google.cloud import discoveryengine_v1 as discoveryengine

from app.config import (
    GCP_PROJECT,
    RULEBOOKS_CSV_PATH,
    VERTEX_SEARCH_ENGINE,
    VERTEX_SEARCH_LOCATION,
)

logger = logging.getLogger("yukti.tools.policy_search")


DOC_HUMAN_TITLES = {
    "JRTP": "Job Rotation and Transfer Policy",
    "DOC-RB-JRTP-SCAN": "Job Rotation and Transfer Policy",
    "DOC-RB-JRTP-PDF": "Job Rotation and Transfer Policy",
    "DOC-RB-JRTP-DOCX": "Job Rotation and Transfer Policy",
    "BDP": "Book of Delegated Powers",
    "BDP summary": "Book of Delegated Powers",
    "Leave Rules": "ONGC Leave Rules",
    "R&P/Promotion": "Modified Recruitment & Promotion Regulations",
    "HR Manual": "ONGC Corporate HR Manual",
    "PRBS": "Post-Retirement Benefit Scheme",
    "Post-retirement medical": "Post-Retirement Medical Scheme",
    "CDA Rules": "Conduct, Discipline and Appeal Rules",
    "Whistle Blower Policy": "Whistle Blower Policy",
}


def get_human_doc_title(doc_id: str) -> str:
    clean = doc_id.strip()
    return DOC_HUMAN_TITLES.get(clean, DOC_HUMAN_TITLES.get(clean.upper(), clean))


class PolicySearchEngine:
    """Handles semantic retrieval of official ONGC policies, rulebooks, and clauses."""

    def __init__(
        self,
        project_id: str = GCP_PROJECT,
        location: str = VERTEX_SEARCH_LOCATION,
        engine_id: str = VERTEX_SEARCH_ENGINE,
    ):
        self.project_id = project_id
        self.location = location
        self.engine_id = engine_id
        self._search_client: Optional[discoveryengine.SearchServiceClient] = None
        self._local_index: Optional[List[Dict[str, Any]]] = None

    @property
    def client(self) -> discoveryengine.SearchServiceClient:
        if self._search_client is None:
            self._search_client = discoveryengine.SearchServiceClient()
        return self._search_client

    def _load_local_csv(self) -> List[Dict[str, Any]]:
        if self._local_index is not None:
            return self._local_index
        items = []
        if RULEBOOKS_CSV_PATH.exists():
            with open(RULEBOOKS_CSV_PATH, "r", encoding="utf-8") as f:
                reader = csv.DictReader(f)
                for row in reader:
                    items.append({
                        "doc_id": row.get("doc_id", "ONGC Rulebook"),
                        "clause_ref": row.get("clause_ref", ""),
                        "clause_title": row.get("clause_title", ""),
                        "clause_text": row.get("clause_text", ""),
                        "maps_to_question_ids": row.get("maps_to_question_ids", ""),
                        "source_basis": row.get("source_basis", ""),
                    })
        self._local_index = items
        return items

    def search_local(self, query: str, top_k: int = 3) -> List[Dict[str, Any]]:
        """Performs keyword and semantic matching on local rulebooks clause index."""
        items = self._load_local_csv()
        if not items:
            return []

        q_terms = [t.lower() for t in query.split() if len(t) > 2]
        scored = []

        for item in items:
            haystack = f"{item['doc_id']} {item['clause_ref']} {item['clause_title']} {item['clause_text']}".lower()
            score = 0
            for term in q_terms:
                if term in haystack:
                    score += 1

            # Domain boosts
            q_lower = query.lower()
            if ("transfer" in q_lower or "stay" in q_lower or "tenure" in q_lower) and "JRTP" in item["doc_id"]:
                score += 4
            if "superannuation" in q_lower or "retirement" in q_lower:
                if "clause 7" in item["clause_ref"].lower():
                    score += 5
            if "promotion" in q_lower or "dpc" in q_lower:
                if "promotion" in item["doc_id"].lower():
                    score += 4
            if "leave" in q_lower and "leave" in item["doc_id"].lower():
                score += 4

            if score > 0:
                scored.append((score, item))

        scored.sort(key=lambda x: x[0], reverse=True)
        results = []
        for score, item in scored[:top_k]:
            h_doc = get_human_doc_title(item["doc_id"])
            c_title = item.get("clause_title", "")
            full_title = f"{h_doc} — {item['clause_ref']}: {c_title}" if c_title else f"{h_doc} — {item['clause_ref']}"
            results.append({
                "doc_id": h_doc,
                "doc_title": full_title,
                "clause_ref": item["clause_ref"],
                "text": item["clause_text"],
                "highlight": item["clause_text"][:300] + ("..." if len(item["clause_text"]) > 300 else ""),
                "score": score,
            })
        return results

    def search(self, query: str, top_k: int = 3, persona: str = "CMD") -> Dict[str, Any]:
        """Queries Vertex AI Search engine, falling back to local rulebooks index."""
        t0 = time.perf_counter()
        from app.config import YUKTI_RESULT_CACHE
        from app.tool_cache import get_tool_cache
        tool_cache = get_tool_cache()

        if YUKTI_RESULT_CACHE:
            cached = tool_cache.get_policy(query, persona=persona)
            if cached:
                cached_copy = dict(cached)
                cached_copy["from_cache"] = True
                cached_copy["latency_ms"] = round((time.perf_counter() - t0) * 1000, 2)
                return cached_copy

        source = "vertex_ai_search"
        clauses: List[Dict[str, Any]] = []

        try:
            serving_config = (
                f"projects/{self.project_id}/locations/{self.location}/collections/default_collection/"
                f"engines/{self.engine_id}/servingConfigs/default_config"
            )
            request = discoveryengine.SearchRequest(
                serving_config=serving_config,
                query=query,
                page_size=top_k,
            )
            response = self.client.search(request)
            for res in response.results:
                doc = res.document
                struct = getattr(doc, "struct_data", {}) or {}
                clause_ref = struct.get("clause_ref", "Clause Reference")
                doc_title = struct.get("heading", struct.get("title", "ONGC Policy"))
                doc_id = struct.get("doc_id", "JRTP")
                text = struct.get("text", struct.get("snippet", ""))

                if not text:
                    # Enrich from local if empty
                    local_match = self.search_local(f"{doc_id} {clause_ref}", top_k=1)
                    if local_match:
                        text = local_match[0]["text"]

                h_doc = get_human_doc_title(doc_id)
                full_title = f"{h_doc} — {clause_ref}: {doc_title}" if doc_title else f"{h_doc} — {clause_ref}"
                clauses.append({
                    "doc_id": h_doc,
                    "doc_title": full_title,
                    "clause_ref": clause_ref,
                    "text": text,
                    "highlight": text[:300] + ("..." if len(text) > 300 else ""),
                })
        except Exception as e:
            logger.warning(f"Vertex AI Search failed ({e}); falling back to local rulebooks index.")
            source = "local_rulebooks_index"
            clauses = self.search_local(query, top_k=top_k)

        elapsed_ms = round((time.perf_counter() - t0) * 1000, 2)
        primary_clause = clauses[0] if clauses else None

        out = {
            "status": "success",
            "source": source,
            "query": query,
            "latency_ms": elapsed_ms,
            "clauses": clauses,
            "primary_clause": primary_clause,
        }
        if YUKTI_RESULT_CACHE:
            tool_cache.set_policy(query, persona, out)
        return out
