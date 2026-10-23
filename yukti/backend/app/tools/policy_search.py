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
                        # P0.7 (BUG-31, D-35): "illustrative" unless the CSV marks the row "real"
                        "provenance": "real" if (row.get("provenance") or "").strip() == "real" else "illustrative",
                    })
        from pathlib import Path
        import json
        fin_corpus = Path(__file__).resolve().parents[3] / "financial_build" / "data" / "financial_notes_corpus.jsonl"
        if fin_corpus.exists():
            with open(fin_corpus, "r", encoding="utf-8") as f:
                for line in f:
                    if not line.strip():
                        continue
                    c = json.loads(line)
                    items.append({
                        "doc_id": f"ONGC Annual Report ({c.get('fiscal_year', 'FY17–FY26')})",
                        "clause_ref": c.get("note_ref", "Schedule III"),
                        "clause_title": c.get("title", ""),
                        "clause_text": c.get("content", ""),
                        "maps_to_question_ids": ",".join(c.get("causal_tags", [])),
                        "source_basis": c.get("yahoo_finance_equivalent", "Schedule III P&L"),
                        "provenance": "illustrative",  # P0.7: generated financial_build notes, not AR text
                    })
        self._local_index = items
        return items

    def search_local(self, query: str, top_k: int = 3) -> List[Dict[str, Any]]:
        """Performs keyword and semantic matching on local rulebooks clause index."""
        items = self._load_local_csv()
        if not items:
            return []

        import re
        q_lower = query.lower()
        q_terms = [t for t in re.findall(r"[a-z0-9]+", q_lower) if len(t) > 2 and t not in ("how", "many", "are", "there", "what", "the", "about", "policy", "rules", "rule", "one", "year", "for", "and", "can", "you", "tell")]
        scored = []

        # High-precision topic boost rules so specific leave/HR/finance inquiries hit their exact clause first
        topic_boosts = [
            (["casual leave", "cl ", "casual leaves"], "leave rules", "2a.0", 25),
            (["special casual", "scl", "blood donation", "sports leave"], "leave rules", "2b.0", 25),
            (["earned leave", "el ", "300 days", "encash"], "leave rules", "3.0", 20),
            (["encash", "superannuation encashment", "leave encashment"], "leave rules", "4.0", 22),
            (["half pay leave", "hpl"], "leave rules", "5.0", 25),
            (["commuted leave", "medical leave", "sick leave"], "leave rules", "5a.0", 25),
            (["study leave"], "leave rules", "6.0", 25),
            (["maternity", "adoption leave", "miscarriage"], "leave rules", "6a.0", 25),
            (["paternity"], "leave rules", "6b.0", 25),
            (["child care", "ccl"], "leave rules", "6c.0", 25),
            (["extraordinary leave", "eol", "leave without pay"], "leave rules", "8.0", 25),
            (["quarantine", "disability leave", "sabbatical"], "leave rules", "8a.0", 25),
            (["compensatory off", "comp off", "comp-off", "14-day", "14 days on", "offshore duty"], "leave rules", "10.0", 25),
            (["cafeteria", "35%", "mining allowance", "offshore allowance", "hardship"], "hr manual", "7.0", 25),
            (["hra", "house rent", "leased accommodation", "cla", "self lease"], "hr manual", "8.0", 25),
            (["ta/da", "travel entitlement", "daily allowance", "hotel", "transfer grant", "air travel"], "hr manual", "9.0", 25),
            (["furniture", "laptop", "mobile", "house building", "hba", "car advance", "conveyance advance"], "hr manual", "10.0", 25),
            (["probation", "confirmation"], "hr manual", "3.0", 20),
            (["resignation", "notice period"], "hr manual", "6.0", 22),
            (["prbs", "pension", "annuity", "nps"], "prbs", "", 18),
            (["opd", "medical reimbursement", "hospitalization", "asha kiran", "post-retirement medical"], "post-retirement medical", "", 18),
            (["bdp", "delegated power", "financial power", "sanction limit", "procurement limit"], "bdp summary", "", 18),
        ]

        for item in items:
            doc_l = item["doc_id"].lower()
            ref_l = item["clause_ref"].lower()
            title_l = item.get("clause_title", "").lower()
            text_l = item.get("clause_text", "").lower()
            haystack = f"{doc_l} {ref_l} {title_l} {text_l}"
            score = 0
            for term in q_terms:
                if term in title_l:
                    score += 4
                elif term in haystack:
                    score += 1

            for phrases, target_doc, target_ref, boost in topic_boosts:
                if any(p in q_lower for p in phrases):
                    if target_doc in doc_l and (not target_ref or target_ref in ref_l):
                        score += boost

            # Domain boosts
            if ("transfer" in q_lower or "stay" in q_lower or "tenure" in q_lower or "rotation" in q_lower) and "jrtp" in doc_l:
                score += 6
            if ("superannuation" in q_lower or "retirement" in q_lower) and "clause 7" in ref_l and "jrtp" in doc_l:
                score += 6
            if ("promotion" in q_lower or "dpc" in q_lower) and "promotion" in doc_l:
                score += 6
            if "leave" in q_lower and "leave" in doc_l:
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
                "highlight": item["clause_text"][:320] + ("..." if len(item["clause_text"]) > 320 else ""),
                "score": score,
                "provenance": item.get("provenance", "illustrative"),  # P0.7
            })
        return results

    def search(self, query: str, top_k: int = 3, persona: str = "CMD") -> Dict[str, Any]:
        """Queries curated local ONGC rulebooks index first for exact statutory clauses, enriched by Vertex AI Search."""
        t0 = time.perf_counter()
        local_clauses = self.search_local(query, top_k=top_k)
        if local_clauses and local_clauses[0].get("score", 0) >= 4:
            elapsed_ms = round((time.perf_counter() - t0) * 1000, 2)
            return {
                "status": "success",
                "source": "local_rulebooks_index",
                "query": query,
                "latency_ms": elapsed_ms,
                "clauses": local_clauses,
                "primary_clause": local_clauses[0],
            }

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
                prov_match = self.search_local(f"{doc_id} {clause_ref}", top_k=1)
                clauses.append({
                    "doc_id": h_doc,
                    "doc_title": full_title,
                    "clause_ref": clause_ref,
                    "text": text,
                    "highlight": text[:300] + ("..." if len(text) > 300 else ""),
                    # P0.7: same provenance as the matching index row; unknown -> illustrative
                    "provenance": prov_match[0].get("provenance", "illustrative") if prov_match else "illustrative",
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
        from app.config import YUKTI_RESULT_CACHE
        from app.tool_cache import get_tool_cache
        if YUKTI_RESULT_CACHE:
            get_tool_cache().set_policy(query, persona, out)
        return out

    async def search_async(self, query: str, top_k: int = 3, persona: str = "CMD") -> Dict[str, Any]:
        """Non-blocking async wrapper for policy search (H1.1)."""
        import asyncio
        return await asyncio.to_thread(self.search, query=query, top_k=top_k, persona=persona)
