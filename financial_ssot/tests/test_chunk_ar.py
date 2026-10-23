"""Offline tests for the P1.8 AR text chunker (packet P1.8 Part B acceptance criteria).

No network, no BigQuery, no LLM. Runs the chunker over the real AR text files in
knowledge/public_sources/grounding_data/text (skipped if the files are absent).
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

import pytest

APP_ROOT = Path(__file__).resolve().parents[2]
if str(APP_ROOT) not in sys.path:
    sys.path.insert(0, str(APP_ROOT))

from financial_ssot.knowledge import chunk_ar as ca  # noqa: E402

pytestmark = pytest.mark.skipif(
    not all((ca.TEXT_DIR / f).exists() for f in ca.AR_FILES.values()),
    reason="AR text files not present",
)


@pytest.fixture(scope="module")
def corpus():
    cfg = ca.load_config()
    out = {}
    for fy, fname in ca.AR_FILES.items():
        text = (ca.TEXT_DIR / fname).read_text(encoding="utf-8")
        chunks, pages, stats = ca.process_document(fy, text, cfg, fname.replace(".txt", ".pdf"))
        out[fy] = {"text": text, "pages": pages, "chunks": chunks, "stats": stats}
    return out


def _all_chunks(corpus):
    return [c for d in corpus.values() for c in d["chunks"]]


# --- unit tests on synthetic layout --------------------------------------------------------------
def test_windows_respect_token_bounds_and_overlap():
    for n in (31, 200, 300, 461, 462, 700, 1234, 3000):
        w = ca.windows(n)
        assert w[0][0] == 0 and w[-1][1] == n
        for (s, e) in w:
            assert (e - s) * ca.TOKEN_FACTOR <= ca.MAX_TOKENS + 1
            if len(w) > 1:
                assert (e - s) * ca.TOKEN_FACTOR >= ca.MIN_TOKENS_WINDOW
        for (s1, e1), (s2, e2) in zip(w, w[1:]):
            assert e1 - s2 == round(ca.OVERLAP_TOKENS / ca.TOKEN_FACTOR)


def test_decolumn_reads_left_column_first():
    left = [f"left words line {i} alpha beta gamma" for i in range(12)]
    right = [f"right words line {i} delta epsilon" for i in range(12)]
    lines = [f"{l:<60}      {r}" for l, r in zip(left, right)]
    out = [x.strip() for x in ca.decolumn(lines) if x.strip()]
    assert out[:12] == left and out[12:] == right


def test_section_state_fs_then_notes():
    cfg = ca.load_config()
    t = ca.Tagger(cfg)
    st = ca.State()
    st.apply(*t.match("Standalone Financial Statements", "running", False))
    assert st.emitted() == "other"
    st.apply(*t.match("Notes to the Standalone Financial Statements for the year ended March 31, 2026", "body", True))
    assert st.emitted() == "notes"
    st.apply(*t.match("Standalone Financial Statements", "running", True))
    assert st.emitted() == "notes"  # running title on later notes pages keeps notes
    assert t.match("as detailed in the Board's Report.", "body", False) is None  # prose is not a heading


# --- acceptance criteria on the real corpus --------------------------------------------------------
def test_every_chunk_has_source_page_and_one_page(corpus):
    for fy, d in corpus.items():
        pages = ca.split_pages(d["text"])
        for c in d["chunks"]:
            assert isinstance(c["source_page"], int) and 1 <= c["source_page"] <= len(pages)
            assert c["chunk_id"].startswith(f"AR_{fy}_p{c['source_page']:04d}_c")
            # 0 chunks span two pages: every word of the chunk is on its own PDF page.
            page_words = set(" ".join(pages[c["source_page"] - 1].split()).split())
            words = c["text"].split()
            missing = [w for w in words if w not in page_words and not _hyphen_join(w, page_words)]
            assert not missing, (c["chunk_id"], missing[:10])


def _hyphen_join(word, page_words):
    """A line-end hyphenation join ("Income-" + "tax") is the only rewrite the chunker makes."""
    for i, ch in enumerate(word):
        if ch == "-" and word[: i + 1] in page_words and word[i + 1:] in page_words:
            return True
    return False


def test_chunk_size_and_filters(corpus):
    for c in _all_chunks(corpus):
        n = len(c["text"].split())
        assert n * ca.TOKEN_FACTOR >= ca.MIN_CHUNK_TOKENS
        assert n * ca.TOKEN_FACTOR <= ca.MAX_TOKENS + 1
        assert ca.numeric_share(c["text"].split()) <= ca.MAX_NUMERIC_SHARE
        assert c["section"] in ca.EMITTED_SECTIONS
        assert re.fullmatch(r"[0-9a-f]{64}", c["text_sha256"])


def test_chunk_ids_unique(corpus):
    ids = [c["chunk_id"] for c in _all_chunks(corpus)]
    assert len(ids) == len(set(ids))


def test_fy26_reserve_accretion_page(corpus):
    hits = [c for c in corpus["FY26"]["chunks"] if "accreted 44.01 MMTOE" in c["text"]]
    assert hits, "no chunk with the FY26 2P accretion sentence"
    assert all(c["source_page"] == 98 for c in hits)
    assert any(c["section"] in ("directors_report", "mdna") for c in hits)
    assert hits[0]["source_page_label"] == "96"


def test_each_fy_has_mdna_and_notes(corpus):
    for fy, d in corpus.items():
        secs = {c["section"] for c in d["chunks"]}
        assert "mdna" in secs, fy
        assert "notes" in secs, fy


def test_section_tagging_coverage(corpus):
    # Stop-and-ask trigger in the packet: sections.yaml must tag >= 80 % of pages.
    for fy, d in corpus.items():
        pages = d["pages"]
        assert sum(p.tagged for p in pages) / len(pages) >= 0.80, fy


def test_known_page_labels(corpus):
    # SPEC-01 §4.1: FY24 standalone P&L = PDF p.247, printed p.245; FY26 10-yr table PDF p.23 = printed p.21.
    lab24 = {p.source_page: p.source_page_label for p in corpus["FY24"]["pages"]}
    lab26 = {p.source_page: p.source_page_label for p in corpus["FY26"]["pages"]}
    assert lab24[247] == "245"
    assert lab26[23] == "21"


def test_note_numbers_inside_notes(corpus):
    notes = [c for c in _all_chunks(corpus) if c["section"] == "notes"]
    with_no = [c for c in notes if c["note_no"]]
    assert len(with_no) / max(1, len(notes)) >= 0.5
    assert all(c["note_no"] is None for c in _all_chunks(corpus) if c["section"] != "notes")


def test_keyword_line_codes(corpus):
    roy = [c for c in _all_chunks(corpus) if "KW.ROYALTY" in c["line_codes"]]
    assert roy and all(re.search(r"royalt", c["text"], re.I) for c in roy)
