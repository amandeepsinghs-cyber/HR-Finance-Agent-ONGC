"""Semantic Router for Yukti AI.
Embeds user queries via Vertex AI text-embedding-004 and matches against
precomputed embeddings for 89 certified queries in certified/library.yaml.
Routes above threshold to run_certified_query(id, params) with parameter extraction.
Routes below threshold to live NL->SQL generation.
Logs every routing decision per turn.
"""

import json
import logging
import math
from pathlib import Path
import re
import time
from typing import Any, Dict, List, Optional, Tuple
from google import genai

from app.config import GCP_PROJECT, VERTEX_LOCATION
from app.semantic.entities import get_entities
from app.semantic.normalize import fiscal_years_for_sql, resolve_fy
from app.tools.certified_query import get_certified_entry, list_certified_queries

logger = logging.getLogger("yukti.router")

CERTIFIED_DIR = Path(__file__).resolve().parent.parent / "certified"
EMBEDDINGS_PATH = CERTIFIED_DIR / "embeddings.json"

ROUTING_THRESHOLD = 0.60

# Remap refusal templates to authorized enterprise data templates for leadership
REFUSAL_TO_DATA_MAP = {
    "D4": "C6",  # Loss-making fields & capex
    "D5": "C1",  # Delhi 5-year stay
    "D2": "C1",  # Draft transfer list -> stay tenure
    "M4": "C6",  # Loss-making fields
}

# Work-centre / field names and fiscal-year phrases are resolved by the single entity
# dictionary and the FY resolver (B1.2 / B1.3, decision D-30); no local maps here.


def _cosine_similarity(v1: List[float], v2: List[float]) -> float:
    dot = sum(a * b for a, b in zip(v1, v2))
    norm1 = math.sqrt(sum(a * a for a in v1))
    norm2 = math.sqrt(sum(b * b for b in v2))
    return dot / (norm1 * norm2) if (norm1 and norm2) else 0.0


class SemanticRouter:
    """Matches user turns to certified query templates or directs to live NL->SQL."""

    def __init__(
        self,
        project_id: str = GCP_PROJECT,
        location: str = VERTEX_LOCATION,
        threshold: float = ROUTING_THRESHOLD,
    ):
        self.project_id = project_id
        self.location = location
        self.threshold = threshold
        self._client: Optional[genai.Client] = None
        self.embeddings: Dict[str, List[float]] = {}
        self.load_precomputed_embeddings()

    @property
    def client(self) -> genai.Client:
        if self._client is None:
            self._client = genai.Client(
                vertexai=True,
                project=self.project_id,
                location=self.location,
            )
        return self._client

    def load_precomputed_embeddings(self) -> None:
        if EMBEDDINGS_PATH.exists():
            try:
                with open(EMBEDDINGS_PATH, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    self.embeddings = data.get("embeddings", {})
                logger.info(f"Loaded {len(self.embeddings)} precomputed certified query embeddings.")
            except Exception as e:
                logger.warning(f"Could not load precomputed embeddings: {e}")
        else:
            logger.warning(f"Embeddings file not found at {EMBEDDINGS_PATH}")

    def embed_query(self, text: str) -> Optional[List[float]]:
        """Embeds a single query turn with Vertex AI text-embedding-004."""
        try:
            res = self.client.models.embed_content(
                model="text-embedding-004",
                contents=[text],
            )
            if res.embeddings and len(res.embeddings) > 0:
                return res.embeddings[0].values
        except Exception as e:
            logger.warning(f"Embedding API error: {e}")
        return None

    def _keyword_overlap(self, query: str, entry: Dict[str, Any]) -> float:
        """Calculates lexical keyword overlap ratio."""
        q_lower = query.lower()
        keywords = entry.get("intent_keywords", [])
        if not keywords:
            return 0.0
        matches = sum(1 for kw in keywords if kw.lower() in q_lower)
        return matches / len(keywords)

    def extract_turn_parameters(
        self,
        query: str,
        entry: Dict[str, Any],
        prev_params: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Extracts parameters from turn text, dimension lookups, and session context."""
        # Extract turn parameters from text, or fill with entry defaults
        extracted = dict(prev_params or {})
        q_lower = query.lower()
        param_defs = entry.get("params", {})
        for p_k, p_meta in param_defs.items():
            if p_k not in extracted and isinstance(p_meta, dict) and p_meta.get("default") is not None:
                extracted[p_k] = p_meta["default"]

        # 1. Resolve Work Centre
        ents = get_entities()
        if "wc_id" in param_defs:
            wc = ents.resolve_wc(q_lower)
            if wc:
                extracted["wc_id"] = wc

        # 2. Resolve Fiscal Year
        if "fiscal_year" in param_defs:
            fy = resolve_fy(q_lower, available=fiscal_years_for_sql(entry.get("parameterized_sql", "")) or None)
            if fy and fy.get("fy"):
                extracted["fiscal_year"] = fy["fy"]

        # 3. Resolve Minimum Stay Duration (months or years)
        if "min_stay_days" in param_defs:
            yr_match = re.search(r"\b(\d+)\s*(?:years?|yrs?|saal)\b", q_lower)
            mo_match = re.search(r"\b(\d+)\s*(?:months?|mahine)\b", q_lower)
            if mo_match:
                extracted["min_stay_days"] = int(mo_match.group(1))
            elif yr_match:
                extracted["min_stay_days"] = int(yr_match.group(1)) * 12

        # 4. Resolve Executive Grade Threshold
        if "min_grade" in param_defs:
            grade_match = re.search(r"\b(e[1-9])\b", q_lower)
            if grade_match:
                extracted["min_grade"] = grade_match.group(1).upper()

        # 5. Resolve Field
        if "field_id" in param_defs:
            fld = ents.resolve_field(q_lower)
            if fld:
                extracted["field_id"] = fld

        return extracted

    def route(
        self,
        query: str,
        session_id: Optional[str] = None,
        persona: str = "CMD",
        active_query_state: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Decides whether to route the turn to a certified query or live NL->SQL.

        Returns:
            dict with 'route': ('certified' | 'live_nl_sql'),
                      'query_id': matched certified query ID or None,
                      'score': confidence score,
                      'extracted_params': resolved parameters,
                      'entry': certified entry dict or None.
        """
        t0 = time.perf_counter()

        # Check for contextual follow-up on active certified query
        if active_query_state and active_query_state.get("certified_id"):
            active_id = active_query_state["certified_id"]
            active_entry = get_certified_entry(active_id)
            if active_entry:
                # Check if turn is an entity shift (e.g. "what about Mumbai?", "only E5 and above")
                new_params = self.extract_turn_parameters(
                    query, active_entry, prev_params=active_query_state.get("params")
                )
                if new_params != active_query_state.get("params") and len(query.split()) < 10:
                    elapsed = round((time.perf_counter() - t0) * 1000, 1)
                    logger.info(f"Route: certified (follow-up modify state) | ID: {active_id} | Time: {elapsed}ms")
                    return {
                        "route": "certified",
                        "query_id": active_id,
                        "score": 0.95,
                        "is_followup_modification": True,
                        "extracted_params": new_params,
                        "entry": active_entry,
                        "elapsed_ms": elapsed,
                    }

        # Embed user query
        query_vec = self.embed_query(query)

        best_id = None
        best_score = -1.0
        best_entry = None

        all_queries = list_certified_queries()
        for entry in all_queries:
            qid = entry["id"]
            ref_vec = self.embeddings.get(qid)
            lex_sim = self._keyword_overlap(query, entry)
            if query_vec and ref_vec:
                sem_sim = _cosine_similarity(query_vec, ref_vec)
                # Hybrid score: primary semantic similarity with keyword reinforcement
                hybrid_score = max(sem_sim, 0.75 * sem_sim + 0.25 * lex_sim)
            else:
                cq = (entry.get("canonical_question") or "").strip().lower()
                ql = query.strip().lower()
                if cq and (ql == cq or (len(ql) >= 20 and ql in cq)):
                    hybrid_score = 0.92
                else:
                    hybrid_score = lex_sim

            if hybrid_score > best_score:
                best_score = hybrid_score
                best_id = qid
                best_entry = entry

        elapsed = round((time.perf_counter() - t0) * 1000, 1)

        # Remap refusal templates to authorized enterprise data templates for leadership personas
        if persona.upper() == "CMD" and best_id in REFUSAL_TO_DATA_MAP:
            remapped_id = REFUSAL_TO_DATA_MAP[best_id]
            remapped_entry = get_certified_entry(remapped_id)
            if remapped_entry:
                logger.info(f"Remapping refusal template {best_id} to enterprise data template {remapped_id} for CMD")
                best_id = remapped_id
                best_entry = remapped_entry

        # Topic-level guards so specific leave/policy queries never false-match unrelated certified entries (e.g. P5 study leave)
        q_low_guard = query.lower()
        if best_id == "P5" and "study" not in q_low_guard:
            best_score = 0.0
        elif best_id == "P4" and not any(w in q_low_guard for w in ["earned", "encash", "retire", "superannuat"]):
            best_score = 0.0
        elif best_id == "E1" and not any(w in q_low_guard for w in ["balance", "my leave"]):
            best_score = 0.0
        elif any(w in q_low_guard for w in ["casual leave", "maternity leave", "paternity leave", "child care leave", "special casual", "commuted leave", "quarantine leave", "sabbatical", "compensatory off"]):
            best_score = 0.0

        # Evaluate threshold
        if best_score >= self.threshold and best_entry:
            extracted_params = self.extract_turn_parameters(query, best_entry)
            logger.info(
                f"Route: certified | Query ID: {best_id} | Score: {best_score:.3f} >= {self.threshold} | Time: {elapsed}ms"
            )
            return {
                "route": "certified",
                "query_id": best_id,
                "score": round(best_score, 3),
                "is_followup_modification": False,
                "extracted_params": extracted_params,
                "entry": best_entry,
                "elapsed_ms": elapsed,
            }
        else:
            logger.info(
                f"Route: live_nl_sql | Top Match: {best_id} | Score: {best_score:.3f} < {self.threshold} | Time: {elapsed}ms"
            )
            return {
                "route": "live_nl_sql",
                "query_id": None,
                "top_match_id": best_id,
                "score": round(best_score, 3),
                "extracted_params": {},
                "entry": None,
                "elapsed_ms": elapsed,
            }


_GLOBAL_ROUTER: Optional[SemanticRouter] = None


def get_semantic_router() -> SemanticRouter:
    """Singleton getter for SemanticRouter."""
    global _GLOBAL_ROUTER
    if _GLOBAL_ROUTER is None:
        _GLOBAL_ROUTER = SemanticRouter()
    return _GLOBAL_ROUTER
