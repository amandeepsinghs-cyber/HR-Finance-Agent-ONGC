"""AR text retriever over `hrfin_docs.doc_chunks_ar` (P1.8, SPEC-01 §8.2).

Contract
1. Structured first: numbers come from the verified views (`v_fin_statement_as_reported`,
   `v_fin_trend_latest`), never from chunk text. This module only returns *context text* with a
   page citation; callers must not whitelist numbers found in chunks (SPEC-08 §6, BUG-16).
2. Hybrid retrieval: pre-filter `fiscal_year IN (fy, fy-1)` and, when the question names a line,
   `line_code IN UNNEST(line_codes)`; then `VECTOR_SEARCH(..., top_k => 8, distance_type => 'COSINE')`;
   then re-rank by section priority (mdna > directors_report > notes > other) plus a small
   lexical bonus for chunks that contain the question's content terms (hybrid; see LEXICAL_WEIGHT).
3. Returns `[{chunk_id, fiscal_year, source_doc, source_page, source_page_label, section, note_no,
   heading, text, distance, citation}]`; `citation` = "[AR FY26 p.96]" (printed folio) or
   "[AR FY26 PDF p.98]" when the folio is unknown.

Query embedding: computed client-side with Vertex AI `text-embedding-005` (task RETRIEVAL_QUERY),
the same model that embedded the corpus, and passed to BigQuery as an ARRAY<FLOAT64> parameter.
(SPEC-01 §8.2 mentions `ML.GENERATE_EMBEDDING`; that needs a BigQuery remote model + connection,
which does not exist in the project. Client-side embedding gives the same vectors without new IAM.)
"""
from __future__ import annotations

import logging
import re
from typing import Callable, Optional, Sequence

from app.config import BQ_LOCATION, GCP_PROJECT, JOB_LABELS, MAX_BYTES_BILLED, VERTEX_LOCATION

logger = logging.getLogger(__name__)

TABLE = f"{GCP_PROJECT}.hrfin_docs.doc_chunks_ar"
EMBED_MODEL = "text-embedding-005"
EMBED_DIM = 768
DEFAULT_TOP_K = 8
SECTION_PRIORITY = {"mdna": 0, "directors_report": 1, "notes": 2}
OTHER_PRIORITY = 3
# Re-rank = cosine distance + SECTION_WEIGHT x priority. Small enough that a clearly better
# match in a lower-priority section still wins; breaks near-ties in favour of MD&A.
SECTION_WEIGHT = 0.01
# Hybrid lexical re-rank: VECTOR_SEARCH returns CANDIDATE_FACTOR x top_k candidates; each gets a
# bonus of LEXICAL_WEIGHT x (share of the question's content terms found in the chunk text), so a
# chunk that names the asked-about project/term ("Daman", "windfall") is not lost in a dense-only
# ranking. Set LEXICAL_WEIGHT = 0 for pure vector ranking.
CANDIDATE_FACTOR = 4
LEXICAL_WEIGHT = 0.05
_STOP = set("""what which when where how much many does did were was have has with from that this
during year years into about their there they your ongc company report annual total being been
also than then them over under after before such other will would should could""".split())
_TERM_RX = re.compile(r"[A-Za-z][A-Za-z0-9/&.-]{2,}")
PROVENANCE_LABEL = "verified_ar"  # SPEC-11 §7.1: verbatim AR text with a page citation

_FY_RX = re.compile(r"^FY(\d{2})$")


def fy_window(fiscal_year: Optional[str]) -> Optional[list]:
    """'FY26' -> ['FY26', 'FY25'] (SPEC-01 §8.2: fiscal_year IN (fy, fy-1))."""
    if not fiscal_year:
        return None
    m = _FY_RX.match(fiscal_year.strip().upper())
    if not m:
        raise ValueError(f"fiscal_year must look like 'FY26', got {fiscal_year!r}")
    n = int(m.group(1))
    return [f"FY{n:02d}", f"FY{(n - 1) % 100:02d}"]


def build_sql(table: str = TABLE, with_fy: bool = False, with_line_code: bool = False,
              with_sections: bool = False) -> str:
    where = []
    if with_fy:
        where.append("fiscal_year IN UNNEST(@fys)")
    if with_line_code:
        where.append("@line_code IN UNNEST(line_codes)")
    if with_sections:
        where.append("section IN UNNEST(@sections)")
    base = f"SELECT * FROM `{table}`" + (f" WHERE {' AND '.join(where)}" if where else "")
    return (
        "SELECT base.chunk_id, base.fiscal_year, base.source_doc, base.source_page, "
        "base.source_page_label, base.section, base.note_no, base.heading, base.text, distance\n"
        f"FROM VECTOR_SEARCH(({base}), 'embedding', (SELECT @qvec AS embedding), "
        "top_k => @top_k, distance_type => 'COSINE')\n"
        "ORDER BY distance"
    )


def citation(row: dict) -> str:
    fy = row.get("fiscal_year") or ""
    if row.get("source_page_label"):
        return f"[AR {fy} p.{row['source_page_label']}]"
    return f"[AR {fy} PDF p.{row.get('source_page')}]"


def query_terms(question: str) -> set:
    terms = set()
    for t in _TERM_RX.findall(question or ""):
        t = t.strip(".-").lower()
        if len(t) >= 4 and t not in _STOP:
            terms.add(t)
    return terms


def lexical_share(terms: set, text: str) -> float:
    if not terms:
        return 0.0
    low = (text or "").lower()
    return sum(1 for t in terms if t in low) / len(terms)


def rerank(rows: Sequence[dict], question: str = "") -> list:
    terms = query_terms(question)

    def key(r):
        pri = SECTION_PRIORITY.get(r.get("section"), OTHER_PRIORITY)
        score = float(r.get("distance") or 0.0) + SECTION_WEIGHT * pri - LEXICAL_WEIGHT * lexical_share(terms, r.get("text", ""))
        return (score, pri)
    return sorted(rows, key=key)


class ARRetriever:
    """Vector retriever over real AR text. Inject `bq_client` / `embed_fn` for tests."""

    def __init__(self, bq_client=None, embed_fn: Optional[Callable[[str], list]] = None,
                 table: str = TABLE):
        self._bq = bq_client
        self._embed_fn = embed_fn
        self._genai = None
        self.table = table

    # -- dependencies -----------------------------------------------------------------------------
    @property
    def bq(self):
        if self._bq is None:
            from google.cloud import bigquery
            self._bq = bigquery.Client(project=GCP_PROJECT, location=BQ_LOCATION)
        return self._bq

    def embed(self, text: str) -> list:
        if self._embed_fn is not None:
            return list(self._embed_fn(text))
        from google import genai
        from google.genai import types
        if self._genai is None:
            self._genai = genai.Client(vertexai=True, project=GCP_PROJECT, location=VERTEX_LOCATION)
        res = self._genai.models.embed_content(
            model=EMBED_MODEL, contents=[text],
            config=types.EmbedContentConfig(task_type="RETRIEVAL_QUERY", output_dimensionality=EMBED_DIM),
        )
        return list(res.embeddings[0].values)

    # -- retrieval -------------------------------------------------------------------------------
    def retrieve(self, question: str, fiscal_year: Optional[str] = None, line_code: Optional[str] = None,
                 top_k: int = DEFAULT_TOP_K, sections: Optional[Sequence[str]] = None) -> list:
        """Top-k AR chunks for `question`, re-ranked by section priority. Never raises on an empty
        result; BigQuery/embedding errors propagate so the caller can show degraded mode."""
        if not question or not question.strip():
            return []
        from google.cloud import bigquery

        fys = fy_window(fiscal_year)
        qvec = self.embed(question.strip())
        if len(qvec) != EMBED_DIM:
            raise ValueError(f"query embedding has {len(qvec)} dims, expected {EMBED_DIM}")
        params = [
            bigquery.ArrayQueryParameter("qvec", "FLOAT64", qvec),
            bigquery.ScalarQueryParameter("top_k", "INT64", int(top_k) * CANDIDATE_FACTOR),
        ]
        if fys:
            params.append(bigquery.ArrayQueryParameter("fys", "STRING", fys))
        if line_code:
            params.append(bigquery.ScalarQueryParameter("line_code", "STRING", line_code))
        if sections:
            params.append(bigquery.ArrayQueryParameter("sections", "STRING", list(sections)))
        sql = build_sql(self.table, with_fy=bool(fys), with_line_code=bool(line_code), with_sections=bool(sections))
        job_config = bigquery.QueryJobConfig(query_parameters=params, labels=dict(JOB_LABELS),
                                             maximum_bytes_billed=MAX_BYTES_BILLED)
        rows = [dict(r.items()) for r in self.bq.query(sql, job_config=job_config).result()]
        out = []
        for r in rerank(rows, question)[: int(top_k)]:
            r["citation"] = citation(r)
            r["provenance_label"] = PROVENANCE_LABEL
            out.append(r)
        return out
