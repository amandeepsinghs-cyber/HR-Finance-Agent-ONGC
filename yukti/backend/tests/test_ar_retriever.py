"""P1.8: unit tests for app.knowledge.ar_retriever with a mocked BigQuery client (offline)."""
from __future__ import annotations

import os
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.knowledge import ar_retriever as ar  # noqa: E402


class _Job:
    def __init__(self, rows):
        self._rows = rows

    def result(self):
        return [_Row(r) for r in self._rows]


class _Row(dict):
    def items(self):  # bigquery.Row exposes .items()
        return super().items()


class FakeBQ:
    def __init__(self, rows):
        self.rows = rows
        self.calls = []

    def query(self, sql, job_config=None):
        self.calls.append((sql, job_config))
        return _Job(self.rows)


def _rows():
    return [
        {"chunk_id": "AR_FY26_p0300_c01", "fiscal_year": "FY26", "source_doc": "ONGC_AR_FY2025-26.pdf",
         "source_page": 300, "source_page_label": None, "section": "other", "note_no": None,
         "heading": "x", "text": "t1", "distance": 0.200},
        {"chunk_id": "AR_FY26_p0098_c01", "fiscal_year": "FY26", "source_doc": "ONGC_AR_FY2025-26.pdf",
         "source_page": 98, "source_page_label": "96", "section": "directors_report", "note_no": None,
         "heading": "Board's Report", "text": "accreted 44.01 MMTOE", "distance": 0.205},
        {"chunk_id": "AR_FY26_p0240_c02", "fiscal_year": "FY26", "source_doc": "ONGC_AR_FY2025-26.pdf",
         "source_page": 240, "source_page_label": "238", "section": "mdna", "note_no": None,
         "heading": "MD&A", "text": "t3", "distance": 0.30},
    ]


def _params(job_config):
    return {p.name: p for p in job_config.query_parameters}


def test_fy_window():
    assert ar.fy_window("FY26") == ["FY26", "FY25"]
    assert ar.fy_window("fy17") == ["FY17", "FY16"]
    assert ar.fy_window(None) is None
    with pytest.raises(ValueError):
        ar.fy_window("2026")


def test_sql_prefilters_and_vector_search():
    sql = ar.build_sql("p.hrfin_docs.doc_chunks_ar", with_fy=True, with_line_code=True)
    assert "VECTOR_SEARCH((SELECT * FROM `p.hrfin_docs.doc_chunks_ar` WHERE fiscal_year IN UNNEST(@fys) AND @line_code IN UNNEST(line_codes))" in sql
    assert "'embedding'" in sql and "distance_type => 'COSINE'" in sql and "top_k => @top_k" in sql
    assert "WHERE" not in ar.build_sql("t")


def test_retrieve_passes_params_reranks_and_cites():
    bq = FakeBQ(_rows())
    r = ar.ARRetriever(bq_client=bq, embed_fn=lambda q: [0.1] * 768, table="p.d.t")
    out = r.retrieve("What 2P reserves?", fiscal_year="FY26", line_code="KW.DEPLETION")
    sql, cfg = bq.calls[0]
    p = _params(cfg)
    assert p["fys"].values == ["FY26", "FY25"]
    assert p["line_code"].value == "KW.DEPLETION"
    assert p["top_k"].value == 8 * ar.CANDIDATE_FACTOR
    assert len(p["qvec"].values) == 768
    assert cfg.maximum_bytes_billed and cfg.labels
    # section re-rank: directors_report (0.205 + 0.01) beats other (0.200 + 0.03)
    assert [o["chunk_id"] for o in out] == ["AR_FY26_p0098_c01", "AR_FY26_p0300_c01", "AR_FY26_p0240_c02"]
    assert out[0]["citation"] == "[AR FY26 p.96]"
    assert out[1]["citation"] == "[AR FY26 PDF p.300]"
    assert all(o["provenance_label"] == "verified_ar" for o in out)
    assert {"chunk_id", "source_doc", "source_page_label", "section", "heading", "text", "distance"} <= set(out[0])


def test_lexical_bonus_and_top_k_cut():
    rows = _rows()
    rows[2]["text"] = "planned monetization of Daman Upside Development Project in Q3"
    rows[2]["distance"] = 0.22
    bq = FakeBQ(rows)
    r = ar.ARRetriever(bq_client=bq, embed_fn=lambda q: [0.1] * 768)
    q = "When will the Daman Upside Development Project be monetised?"
    assert ar.query_terms(q) == {"daman", "upside", "development", "project", "monetised"}
    out = r.retrieve(q, top_k=1)
    # mdna: 0.22 + 0 - 0.05 * 4/5 = 0.18 beats directors_report 0.205 + 0.01 = 0.215
    assert [o["chunk_id"] for o in out] == ["AR_FY26_p0240_c02"]
    assert _params(bq.calls[0][1])["top_k"].value == ar.CANDIDATE_FACTOR


def test_untagged_line_code_filter_is_skipped_and_logged(caplog):
    # G4 C2: line_codes holds only KW.* tags today; a dim code such as PL.REV_OPS must not turn the
    # pre-filter into "match nothing".
    bq = FakeBQ(_rows())
    r = ar.ARRetriever(bq_client=bq, embed_fn=lambda q: [0.1] * 768)
    with caplog.at_level("INFO", logger=ar.logger.name):
        out = r.retrieve("revenue from operations", fiscal_year="FY26", line_code="PL.REV_OPS")
    sql, cfg = bq.calls[0]
    assert "line_codes" not in sql and "line_code" not in _params(cfg)
    assert "fiscal_year IN UNNEST(@fys)" in sql
    assert out, "results must not be emptied by an untagged line_code"
    assert any("PL.REV_OPS" in m and "skipped" in m for m in caplog.messages)
    assert ar.usable_line_code("KW.ROYALTY") == "KW.ROYALTY"
    assert ar.usable_line_code(None) is None


def test_no_filters_when_not_given():
    bq = FakeBQ([])
    r = ar.ARRetriever(bq_client=bq, embed_fn=lambda q: [0.0] * 768)
    assert r.retrieve("royalty") == []
    sql, cfg = bq.calls[0]
    assert "WHERE" not in sql and "fys" not in _params(cfg)


def test_empty_question_and_bad_dims():
    bq = FakeBQ([])
    assert ar.ARRetriever(bq_client=bq, embed_fn=lambda q: [0.0] * 768).retrieve("  ") == []
    assert not bq.calls
    with pytest.raises(ValueError):
        ar.ARRetriever(bq_client=bq, embed_fn=lambda q: [0.0] * 10).retrieve("royalty")


@pytest.mark.skipif(os.getenv("YUKTI_LIVE_BQ") != "1", reason="live BigQuery test (set YUKTI_LIVE_BQ=1, ADC)")
def test_live_fy26_reserve_accretion():
    out = ar.ARRetriever().retrieve("How much 2P reserves did ONGC accrete during the year and what was the reserve replacement ratio?",
                                    fiscal_year="FY26")
    assert out and any(o["fiscal_year"] == "FY26" and o["source_page"] == 98 for o in out[:5])
