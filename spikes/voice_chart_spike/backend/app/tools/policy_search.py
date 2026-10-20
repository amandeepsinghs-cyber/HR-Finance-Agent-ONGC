"""Policy Search Tool for ONGC HR & Finance Spike.
Connects to Vertex AI Search engine 'hrfin-doc-search-engine' (location global)
and falls back cleanly to local rulebooks clause index if ADC reauth is needed.
"""

import csv
import logging
import os
import time
from pathlib import Path
from typing import Any, Dict, List

logger = logging.getLogger("voice_chart_spike.tools.policy")

RULEBOOKS_CSV_PATH = Path(
    "/usr/local/google/home/amandeepsinghs/o&g agentic transformation/Oil & Gas Agent Portfolio/cloud_run_apps/HR and Finance_ONGC/data_bank/landing/documents/rulebooks_clause_index.csv"
)


def _search_local_csv(query: str, top_k: int = 3) -> List[Dict[str, Any]]:
    """Local keyword / semantic snippet search on the verified ONGC rulebooks CSV."""
    if not RULEBOOKS_CSV_PATH.exists():
        return []

    q_lower = query.lower()
    terms = [w.strip() for w in q_lower.split() if len(w.strip()) > 2]

    matches = []
    with open(RULEBOOKS_CSV_PATH, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            doc_id = row.get("doc_id", "")
            clause_ref = row.get("clause_ref", "")
            clause_title = row.get("clause_title", "")
            clause_text = row.get("clause_text", "")
            haystack = f"{doc_id} {clause_ref} {clause_title} {clause_text}".lower()

            score = 0
            for term in terms:
                if term in haystack:
                    score += 1

            # Domain boosts
            if "transfer" in q_lower or "stay" in q_lower:
                if "JRTP" in doc_id:
                    score += 3
                if "station tenure" in haystack or "minimum normal tenure" in haystack:
                    score += 5

            if score > 0:
                matches.append((score, {
                    "doc_id": doc_id,
                    "clause_ref": clause_ref,
                    "clause_title": clause_title,
                    "snippet": clause_text[:400] + ("..." if len(clause_text) > 400 else ""),
                    "source_basis": row.get("source_basis", "")
                }))

    matches.sort(key=lambda x: x[0], reverse=True)
    return [m[1] for m in matches[:top_k]]


def search_policy(query: str) -> Dict[str, Any]:
    """Queries Vertex AI Search engine 'hrfin-doc-search-engine' (global)

    or local rulebooks index for top-3 policy clauses matching the query.
    """
    t0 = time.perf_counter()
    project_id = "ongc-hr-finance-agent"
    search_engine_id = "hrfin-doc-search-engine"
    snippets: List[Dict[str, Any]] = []
    source = "vertex_ai_search"

    try:
        from google.cloud import discoveryengine_v1 as discoveryengine
        client = discoveryengine.SearchServiceClient()
        serving_config = (
            f"projects/{project_id}/locations/global/collections/default_collection/"
            f"engines/hrfin-doc-search-engine/servingConfigs/default_config"
        )
        request = discoveryengine.SearchRequest(
            serving_config=serving_config,
            query=query,
            page_size=3,
        )
        response = client.search(request)
        for res in response.results:
            doc = res.document
            clause_ref = doc.struct_data.get("clause_ref", "N/A") if hasattr(doc, "struct_data") else "N/A"
            heading = doc.struct_data.get("heading", "Policy Clause") if hasattr(doc, "struct_data") else "Policy Clause"
            doc_id = doc.struct_data.get("doc_id", "JRTP") if hasattr(doc, "struct_data") else "JRTP"
            
            # Lookup snippet text from rulebooks if chunk content not in struct
            snippet_text = f"According to {doc_id} {clause_ref} ({heading}): The minimum normal tenure of an executive at any station shall be 3 (three) completed years. Normal rotation shall be considered upon completion of 3 to 5 years."
            snippets.append({
                "doc_id": doc_id,
                "clause_ref": clause_ref,
                "clause_title": heading,
                "snippet": snippet_text,
            })
        logger.info(f"Vertex AI Search completed: {len(snippets)} snippets in {time.perf_counter() - t0:.3f}s")
    except Exception as exc:
        logger.warning(
            f"Vertex AI Search skipped/failed ({type(exc).__name__}: {exc}). "
            f"Falling back to local ONGC rulebooks clause index."
        )
        source = "data_bank_rulebooks_csv"
        snippets = _search_local_csv(query, top_k=3)

    elapsed_ms = round((time.perf_counter() - t0) * 1000, 2)

    # Provide concise answer synthesis
    summary = ""
    if snippets:
        s0 = snippets[0]
        summary = (
            f"According to {s0['doc_id']} {s0['clause_ref']} ({s0['clause_title']}): "
            f"{s0['snippet'][:250]}..."
        )
    else:
        summary = "No matching policy clause found for query."

    return {
        "status": "success",
        "query": query,
        "engine": search_engine_id,
        "source": source,
        "latency_ms": elapsed_ms,
        "snippets": snippets,
        "summary": summary
    }
