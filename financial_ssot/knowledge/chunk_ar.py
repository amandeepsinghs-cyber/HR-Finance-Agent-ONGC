"""P1.8 Part B: deterministic chunker for the real ONGC Annual Report text (SPEC-01 §8.1).

Input: the `pdftotext -layout` text of the ARs (non-`_flow` files), one form feed per PDF page.
Output: `financial_ssot/out/doc_chunks_ar.jsonl` (no embeddings) and
`financial_ssot/out/doc_chunks_summary.csv`.

Rules (packet P1.8 Part B):
- `source_page` = 1-based physical PDF page = count of `\\f` before the text + 1 (SPEC-01 §4.1).
- Chunks never cross a page boundary; 300-600 tokens (whitespace tokens x 1.3), 60-token overlap.
- Section from `sections.yaml` (running titles + body headings, carried forward across pages).
- `note_no` inside the notes block; `line_codes` from `dim_financial_line.ar_labels` (when the CSV
  exists) and keyword tags; `entities` from a small dictionary.
- Chunks with < 40 tokens or > 60 % numeric tokens are dropped; exact duplicate texts within one
  AR are dropped.

No LLM, no network, no BigQuery. Every chunk is verbatim AR text (whitespace collapsed).

Run from the app root:  python -m financial_ssot.knowledge.chunk_ar
"""
from __future__ import annotations

import argparse
import collections
import csv
import hashlib
import json
import math
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Iterable, Optional

PKG_DIR = Path(__file__).resolve().parent            # financial_ssot/knowledge
SSOT_DIR = PKG_DIR.parent                             # financial_ssot
APP_ROOT = SSOT_DIR.parent
TEXT_DIR = APP_ROOT / "knowledge" / "public_sources" / "grounding_data" / "text"
OUT_DIR = SSOT_DIR / "out"
DIM_CSV = SSOT_DIR / "dim_financial_line.csv"
SECTIONS_YAML = PKG_DIR / "sections.yaml"

# Packet req. 1: FY17, FY18 (English), FY19, FY22-FY26, non-`_flow` text.
AR_FILES = {
    "FY17": "ONGC_AR_FY2016-17.txt",
    "FY18": "ONGC_AR_FY2017-18.txt",
    "FY19": "ONGC_AR_FY2018-19.txt",
    "FY22": "ONGC_AR_FY2021-22.txt",
    "FY23": "ONGC_AR_FY2022-23.txt",
    "FY24": "ONGC_AR_FY2023-24.txt",
    "FY25": "ONGC_AR_FY2024-25.txt",
    "FY26": "ONGC_AR_FY2025-26.txt",
}

TOKEN_FACTOR = 1.3
MAX_TOKENS = 600
MIN_TOKENS_WINDOW = 300
OVERLAP_TOKENS = 60
MIN_CHUNK_TOKENS = 40
MAX_NUMERIC_SHARE = 0.60
EMITTED_SECTIONS = ("mdna", "directors_report", "notes", "brsr", "cmd_letter", "ten_year", "other")
CHUNKER_VERSION = "P1.8-chunk_ar-2"

_APOS = str.maketrans({"\u2019": "'", "\u2018": "'", "\u00b4": "'", "`": "'"})
_SEG_SPLIT = re.compile(r"\s{3,}")
_FOLIO = re.compile(r"\d{1,3}")
_BOILERPLATE = re.compile(
    r"(integrated annual report|annual report)\s*\d{4}\s*-\s*\d{2,4}|exploring hidden depths|achieving glorious heights|"
    r"uni.?ied\. digital\. sustainable\.?|overview|lead & change|\d{1,3}",
    re.I,
)
_NUMERIC_TOKEN = re.compile(r"^[^A-Za-z]*\d[^A-Za-z]*$")


def est_tokens(n_words: int) -> float:
    return n_words * TOKEN_FACTOR


# ----------------------------------------------------------------------------------------------
# Config
# ----------------------------------------------------------------------------------------------
@dataclass
class Rule:
    section: str
    regex: re.Pattern
    scope: str = "any"  # any | running_title | running_title_or_fs


@dataclass
class Config:
    rules: list
    toc_min_sections: int
    note_regex: re.Pattern
    keywords: dict
    entities: dict
    dim_labels: list = field(default_factory=list)  # [(line_code, compiled regex)]
    max_carry: dict = field(default_factory=dict)   # section -> max pages carried after last match


def load_sections(path: Path = SECTIONS_YAML) -> dict:
    """sections.yaml is JSON-compatible YAML (flow style, full-line `#` comments), so PyYAML is
    optional: the financial_ssot project does not depend on it."""
    text = path.read_text(encoding="utf-8")
    try:
        import yaml  # type: ignore
        return yaml.safe_load(text)
    except ImportError:
        return json.loads("\n".join(l for l in text.splitlines() if not l.lstrip().startswith("#")))


def load_config(sections_yaml: Path = SECTIONS_YAML, dim_csv: Path = DIM_CSV) -> Config:
    raw = load_sections(sections_yaml)
    rules = []
    for r in raw["rules"]:
        for p in r["patterns"]:
            rules.append(Rule(r["section"], re.compile(p, re.I), r.get("scope", "any")))
    cfg = Config(
        rules=rules,
        toc_min_sections=int(raw.get("toc_min_sections", 3)),
        note_regex=re.compile(raw["note_regex"]),
        keywords={k: re.compile(v, re.I) for k, v in (raw.get("keywords") or {}).items()},
        entities={k: re.compile(v, re.I) for k, v in (raw.get("entities") or {}).items()},
        max_carry={k: int(v) for k, v in (raw.get("max_carry_pages") or {}).items()},
    )
    cfg.dim_labels = load_dim_labels(dim_csv)
    return cfg


def load_dim_labels(dim_csv: Path) -> list:
    """`dim_financial_line.ar_labels` → [(line_code, regex)]; empty when the CSV is absent (req. 5)."""
    if not dim_csv.exists():
        return []
    out = []
    with dim_csv.open(encoding="utf-8") as fh:
        for row in csv.DictReader(fh):
            code = (row.get("line_code") or "").strip()
            raw = (row.get("ar_labels") or "").strip()
            if not code or not raw:
                continue
            if raw.startswith("["):
                try:
                    labels = json.loads(raw)
                except json.JSONDecodeError:
                    labels = [raw]
            else:
                labels = re.split(r"[|;]", raw)
            for lab in labels:
                lab = " ".join(str(lab).translate(_APOS).split())
                # Generic one-word labels ("Total", "Others") would tag everything.
                if len(lab) < 8 or len(lab.split()) < 2:
                    continue
                out.append((code, re.compile(r"\b" + re.escape(lab).replace(r"\ ", r"\s+") + r"\b", re.I)))
    return out


# ----------------------------------------------------------------------------------------------
# Page layout helpers
# ----------------------------------------------------------------------------------------------
def norm_seg(s: str) -> str:
    return " ".join(s.translate(_APOS).split())


def segments(line: str) -> list:
    return [norm_seg(s) for s in _SEG_SPLIT.split(line.strip()) if s.strip()]


def split_pages(text: str) -> list:
    """Split on form feed. Page i (0-based) is PDF page i+1. A trailing empty page after the last
    form feed is dropped."""
    pages = text.split("\f")
    if pages and not pages[-1].strip():
        pages = pages[:-1]
    return pages


def find_gutter(lines: list) -> Optional[int]:
    """Column position of a two-column gutter, or None. A gutter is a run of >= 2 character
    columns in the middle 30-70 % of the page that almost no line occupies, while many lines have
    text on both sides."""
    text_lines = [l.rstrip() for l in lines if l.strip()]
    if len(text_lines) < 8:
        return None
    width = max(len(l) for l in text_lines)
    if width < 60:
        return None
    n = len(text_lines)
    lo, hi = int(width * 0.30), int(width * 0.70)
    occ = [0] * (width + 1)
    for l in text_lines:
        for x in range(lo, min(hi + 2, len(l))):
            if l[x] != " ":
                occ[x] += 1
    limit = max(1, int(0.04 * n))
    best, best_score = None, 0
    x = lo
    while x <= hi:
        if occ[x] <= limit:
            start = x
            while x <= hi and occ[x] <= limit:
                x += 1
            if x - start >= 2:
                mid = (start + x) // 2
                both = sum(1 for l in text_lines if l[:mid].strip() and l[mid:].strip())
                if both >= max(5, int(0.25 * n)) and both > best_score:
                    best, best_score = mid, both
        else:
            x += 1
    return best


def decolumn(lines: list) -> list:
    """Return the page lines in reading order: the left column, then the right column."""
    gx = find_gutter(lines)
    if gx is None:
        return [l for l in lines]
    left, right = [], []
    for l in lines:
        cut = gx
        if 0 < cut < len(l) and l[cut - 1] != " " and l[cut] != " ":
            # A line crosses the gutter: cut at the nearest space instead of mid-word.
            for d in range(1, 16):
                if cut - d > 0 and l[cut - d] == " ":
                    cut -= d
                    break
                if cut + d >= len(l) or l[cut + d] == " ":
                    cut = min(cut + d, len(l))
                    break
            else:
                # No space nearby: keep the line whole in the left column (never split a word).
                cut = len(l)
        left.append(l[:cut])
        right.append(l[cut:])
    return left + right


# ----------------------------------------------------------------------------------------------
# Section tagging
# ----------------------------------------------------------------------------------------------
class Tagger:
    def __init__(self, cfg: Config):
        self.cfg = cfg

    def match(self, seg: str, where: str, in_fs: bool) -> Optional[tuple]:
        """(section, heading) for a segment, or None. `where` = 'running' | 'body'."""
        if not seg or len(seg) > 110:
            return None
        for r in self.cfg.rules:
            if r.scope == "running_title" and where != "running":
                continue
            if r.scope == "running_title_or_fs" and where != "running" and not in_fs:
                continue
            if r.regex.fullmatch(seg):
                return r.section, seg
        return None

    def line_matches(self, line: str, where: str, in_fs: bool) -> list:
        out = []
        for seg in segments(line):
            m = self.match(seg, where, in_fs)
            if m:
                out.append(m)
        return out


def fs_kind(heading: str) -> str:
    h = heading.lower()
    return "consolidated" if "consolidated" in h else "standalone"


@dataclass
class State:
    section: Optional[str] = None     # internal section (may be 'fs')
    heading: Optional[str] = None
    notes_seen: bool = False
    kind: Optional[str] = None        # standalone | consolidated, inside the FS block
    note_no: Optional[str] = None
    page: int = 0                     # current PDF page (set by the caller)
    last_page: int = 0                # page of the last heading/running-title match

    def emitted(self) -> str:
        if self.section is None:
            return "other"
        if self.section == "fs":
            return "notes" if self.notes_seen else "other"
        return self.section

    def in_fs(self) -> bool:
        return self.section in ("fs", "notes")

    def expire(self, max_carry: dict) -> None:
        """Short sections (e.g. the 10-yr table) stop carrying forward `max_carry[section]` pages
        after their last match, so following pages without headings fall back to the default
        instead of inheriting them (AR FY22 PDF p.25-57 were tagged ten_year in chunker v1)."""
        lim = max_carry.get(self.section) if self.section else None
        if lim is not None and self.page - self.last_page > lim:
            self.section, self.heading = None, None
            self.notes_seen, self.kind, self.note_no = False, None, None

    def apply(self, section: str, heading: str) -> None:
        self.last_page = self.page
        if section == "fs":
            k = fs_kind(heading)
            if not self.in_fs() or (self.kind and k != self.kind):
                self.notes_seen = False
                self.note_no = None
            self.kind = k
            if self.section != "notes":
                self.section = "fs"
            self.heading = heading
            return
        if section == "notes":
            if "consolidated" in heading.lower() or "standalone" in heading.lower():
                k = fs_kind(heading)
                if self.kind and k != self.kind:
                    self.note_no = None
                self.kind = k
            self.notes_seen = True
            self.section = "notes"
            self.heading = heading
            return
        self.section, self.heading = section, heading
        self.notes_seen, self.kind, self.note_no = False, None, None


# ----------------------------------------------------------------------------------------------
# Document processing
# ----------------------------------------------------------------------------------------------
@dataclass
class PageInfo:
    fiscal_year: str
    source_page: int
    source_page_label: Optional[str]
    section: str
    tagged: bool          # section came from a matched heading/running title (not the default)
    is_toc: bool
    n_words: int


def page_label(raw_lines: list, pdf_page: int, prev_offset: Optional[int]) -> tuple:
    """Printed folio from the first/last 3 non-empty lines; returns (label, offset)."""
    nonempty = [l for l in raw_lines if l.strip()]
    if not nonempty:
        return None, prev_offset
    cands = []
    for l in list(reversed(nonempty[-3:])) + nonempty[:3]:
        for s in segments(l):
            for tok in (s.split() if len(s.split()) <= 6 else []):
                if _FOLIO.fullmatch(tok) and 1 <= int(tok) <= pdf_page:
                    cands.append(int(tok))
    if not cands:
        return None, prev_offset
    if prev_offset is not None:
        for c in cands:
            if abs((pdf_page - c) - prev_offset) <= 1:
                return str(c), pdf_page - c
    for c in cands:
        if 0 <= pdf_page - c <= 40:
            return str(c), pdf_page - c
    return None, prev_offset


def is_furniture(line: str, tagger: Tagger, in_fs: bool) -> bool:
    """Header/footer line made only of folios, running titles and boilerplate."""
    segs = segments(line)
    if not segs:
        return False
    for s in segs:
        if _BOILERPLATE.fullmatch(s) or tagger.match(s, "running", in_fs):
            continue
        if all(_FOLIO.fullmatch(t) or _BOILERPLATE.fullmatch(t) for t in s.split()):
            continue
        if re.fullmatch(r"(\d{1,3}\s+)?[A-Za-z' &]+?(\s+\d{1,3})?", s) and tagger.match(
            re.sub(r"^\d{1,3}\s+|\s+\d{1,3}$", "", s), "running", in_fs
        ):
            continue
        return False
    return True


_SEG_POS = re.compile(r"\S(?:\S| {1,2}(?=\S))*")


def strip_side_tabs(lines: list, tagger: Tagger) -> list:
    """Blank out the vertical chapter tabs printed in the right margin (FY25/FY26 odd pages:
    "Overview / Annexures to the Board's Report / Standalone Financial Statements / ..." stacked
    at one column, ~147 of 180). SPEC-01 §4.2 rule 6 treats this margin text as noise.
    A tab stack = >= 2 running-title (or "Overview") segments on different lines that start at
    the same column (+-2) in the right 45 % of the page. Body text is never removed."""
    nonblank = [l.rstrip() for l in lines if l.strip()]
    if not nonblank:
        return lines
    width = max(len(l) for l in nonblank)
    cands = []  # (line_idx, start, end, section_or_overview)
    for i, l in enumerate(lines):
        for m in _SEG_POS.finditer(l):
            if m.start() < 0.55 * width:
                continue
            seg = norm_seg(m.group())
            hit = tagger.match(seg, "running", True)
            if hit:
                cands.append((i, m.start(), m.end(), hit[0]))
            elif seg.lower() == "overview":
                cands.append((i, m.start(), m.end(), "overview"))
    kill = set()
    for i, st, en, sec in cands:
        group = [c for c in cands if abs(c[1] - st) <= 2]
        if len({c[0] for c in group}) >= 2:
            kill.add((i, st, en))
    if not kill:
        return lines
    out = [list(l) for l in lines]
    for i, st, en in kill:
        for x in range(st, en):
            out[i][x] = " "
    return ["".join(l) for l in out]


def _strip_folio(seg: str) -> str:
    return re.sub(r"^\d{1,3}\s+|\s+\d{1,3}$", "", seg)


def _join_hyphens(words: list) -> list:
    """Join a line-end hyphenation ("Income-" + "tax" -> "Income-tax"); the hyphen is kept and a
    joined word is never joined again (table fragments such as "continu-" "discon-" stay apart)."""
    out, joined = [], []
    for w in words:
        if (out and not joined[-1] and out[-1][0].endswith("-") and len(out[-1][0]) > 2
                and out[-1][0][-2].isalpha() and w[0][:1].islower()):
            prev_w, prev_s = out[-1]
            out[-1] = (prev_w + w[0], prev_s)
            joined[-1] = True
        else:
            out.append(w)
            joined.append(False)
    return out


def windows(n: int) -> list:
    """[(start, end)] word windows for a page of n words: <= 600 tokens each, >= 300 tokens when
    the page is split, 60-token overlap. A page too short for two 300-token windows is one chunk."""
    max_w = int(MAX_TOKENS / TOKEN_FACTOR)              # 461
    ov_w = round(OVERLAP_TOKENS / TOKEN_FACTOR)          # 46
    min_w = math.ceil(MIN_TOKENS_WINDOW / TOKEN_FACTOR)  # 231
    if n <= max_w and n < 2 * min_w - ov_w:
        return [(0, n)]
    # As many windows as possible while every window stays >= 300 tokens (finer retrieval
    # granularity), and at least enough that none exceeds 600 tokens.
    k = max(math.ceil((n - ov_w) / (max_w - ov_w)), (n - ov_w) // (min_w - ov_w), 1)
    size = math.ceil((n + (k - 1) * ov_w) / k)
    stride = size - ov_w
    out = []
    for i in range(k):
        s = i * stride
        e = min(n, s + size) if i < k - 1 else n
        out.append((s, e))
    return out


def numeric_share(words: list) -> float:
    if not words:
        return 1.0
    return sum(1 for w in words if _NUMERIC_TOKEN.match(w)) / len(words)


def tag_codes(text: str, cfg: Config) -> list:
    codes = []
    for code, rx in cfg.dim_labels:
        if code not in codes and rx.search(text):
            codes.append(code)
    for kw, rx in cfg.keywords.items():
        if rx.search(text):
            codes.append(f"KW.{kw}")
    return codes


def tag_entities(text: str, cfg: Config) -> list:
    return [k for k, rx in cfg.entities.items() if rx.search(text)]


def process_document(fy: str, text: str, cfg: Config, source_doc: str) -> tuple:
    """Returns (chunks, pages, stats)."""
    tagger = Tagger(cfg)
    st = State()
    prev_offset = None
    chunks, pages = [], []
    stats = collections.Counter()
    seen_sha = set()
    for pidx, page in enumerate(split_pages(text)):
        pdf_page = pidx + 1
        st.page = pdf_page
        st.expire(cfg.max_carry)
        raw_lines = strip_side_tabs(page.split("\n"), tagger)
        label, prev_offset = page_label(raw_lines, pdf_page, prev_offset)

        # 1) Running title: first/last 3 non-empty lines (nav bars with >= 2 sections ignored).
        nonempty_idx = [i for i, l in enumerate(raw_lines) if l.strip()]
        edge_idx = sorted(set(nonempty_idx[:3] + nonempty_idx[-3:]))
        running = None
        furniture = set()
        for i in edge_idx:
            ms = []
            for s in segments(raw_lines[i]):
                m = tagger.match(s, "running", st.in_fs()) or tagger.match(_strip_folio(s), "running", st.in_fs())
                if m:
                    ms.append(m)
            segs_i = segments(raw_lines[i])
            if len(ms) >= 2 or (ms and any(x.lower() == "overview" for x in segs_i)):
                furniture.add(i)     # chapter navigation bar (FY25: "Overview  Standalone FS  Consolidated FS")
                continue
            if ms and is_furniture(raw_lines[i], tagger, st.in_fs()):
                furniture.add(i)
                if running is None or i in nonempty_idx[-3:]:
                    running = ms[0]
            elif is_furniture(raw_lines[i], tagger, st.in_fs()):
                furniture.add(i)

        # 2) TOC detection on all body segments.
        body_secs = set()
        for i, l in enumerate(raw_lines):
            if i in furniture:
                continue
            for m in tagger.line_matches(l, "body", True):
                body_secs.add(m[0])
        is_toc = len(body_secs) >= cfg.toc_min_sections
        tagged = False

        page_state_running = None
        if running and not is_toc:
            # Running title labels the whole page; notes headings on FS pages still flip notes_seen.
            st.apply(*running)
            tagged = True
            page_state_running = running

        body_lines = [l for i, l in enumerate(raw_lines) if i not in furniture]
        ordered = decolumn(body_lines)

        # Per-word state.
        words = []  # (word, (section_emitted, heading, note_no))
        toc_state = ("other", "Contents", None)
        for line in ordered:
            if not line.strip():
                continue
            if not is_toc:
                for sec, head in tagger.line_matches(line, "body", st.in_fs()):
                    if page_state_running and sec not in ("notes",):
                        continue  # running title is authoritative for this page
                    if page_state_running and sec == "notes" and not st.in_fs():
                        continue
                    st.apply(sec, head)
                    tagged = True
                if st.section == "notes" or (st.section == "fs" and st.notes_seen):
                    m = cfg.note_regex.match(line)
                    if m and 1 <= int(m.group(1)) <= 60:
                        st.note_no = m.group(1)
            snap = toc_state if is_toc else (st.emitted(), st.heading, st.note_no if st.emitted() == "notes" else None)
            for w in line.split():
                words.append((w, snap))
        # A page is "tagged" when its section derives from a matched heading (on this page or
        # carried forward), not from the front-matter default.
        tagged = st.section is not None and not is_toc
        words = _join_hyphens(words)

        pages.append(PageInfo(fy, pdf_page, label, "other" if is_toc else st.emitted(),
                              tagged and not is_toc, is_toc, len(words)))

        for ci, (s, e) in enumerate(windows(len(words)), start=1):
            ws = words[s:e]
            toks = [w for w, _ in ws]
            stats["windows"] += 1
            if est_tokens(len(toks)) < MIN_CHUNK_TOKENS:
                stats["drop_short"] += 1
                continue
            if numeric_share(toks) > MAX_NUMERIC_SHARE:
                stats["drop_numeric"] += 1
                continue
            secs = collections.Counter(sn[0] for _, sn in ws)
            section = secs.most_common(1)[0][0]
            first = next(sn for _, sn in ws if sn[0] == section)
            note_no = first[2] or next((sn[2] for _, sn in ws if sn[0] == section and sn[2]), None)
            body = " ".join(toks)
            sha = hashlib.sha256(body.encode("utf-8")).hexdigest()
            if sha in seen_sha:
                stats["drop_duplicate"] += 1
                continue
            seen_sha.add(sha)
            chunks.append({
                "chunk_id": f"AR_{fy}_p{pdf_page:04d}_c{ci:02d}",
                "fiscal_year": fy,
                "source_doc": source_doc,
                "source_page": pdf_page,
                "source_page_label": label,
                "section": section,
                "note_no": note_no,
                "heading": first[1],
                "text": body,
                "token_estimate": round(est_tokens(len(toks))),
                "line_codes": tag_codes(body, cfg),
                "entities": tag_entities(body, cfg),
                "text_sha256": sha,
                "chunker_version": CHUNKER_VERSION,
            })
    stats["chunks"] = len(chunks)
    return chunks, pages, stats


def section_ranges(pages: Iterable[PageInfo]) -> dict:
    """section -> 'a-b;c-d' contiguous PDF page ranges."""
    by = collections.defaultdict(list)
    for p in pages:
        by[p.section].append(p.source_page)
    out = {}
    for sec, nums in by.items():
        nums.sort()
        ranges, start, prev = [], nums[0], nums[0]
        for n in nums[1:]:
            if n != prev + 1:
                ranges.append((start, prev))
                start = n
            prev = n
        ranges.append((start, prev))
        out[sec] = ";".join(f"{a}-{b}" if a != b else f"{a}" for a, b in ranges)
    return out


def run(text_dir: Path = TEXT_DIR, out_dir: Path = OUT_DIR, fys: Optional[list] = None) -> dict:
    cfg = load_config()
    out_dir.mkdir(parents=True, exist_ok=True)
    summary_rows, all_stats = [], {}
    total = 0
    with (out_dir / "doc_chunks_ar.jsonl").open("w", encoding="utf-8") as fh:
        for fy, fname in AR_FILES.items():
            if fys and fy not in fys:
                continue
            text = (text_dir / fname).read_text(encoding="utf-8")
            chunks, pages, stats = process_document(fy, text, cfg, fname.replace(".txt", ".pdf"))
            for c in chunks:
                fh.write(json.dumps(c, ensure_ascii=False) + "\n")
            total += len(chunks)
            by_sec = collections.Counter(c["section"] for c in chunks)
            ranges = section_ranges(pages)
            row = {
                "fiscal_year": fy,
                "source_doc": fname.replace(".txt", ".pdf"),
                "pages": len(pages),
                "pages_tagged_pct": round(100 * sum(p.tagged for p in pages) / max(1, len(pages)), 1),
                "pages_with_label_pct": round(100 * sum(p.source_page_label is not None for p in pages) / max(1, len(pages)), 1),
                "chunks": len(chunks),
                "dropped_short": stats["drop_short"],
                "dropped_numeric": stats["drop_numeric"],
                "dropped_duplicate": stats["drop_duplicate"],
            }
            for sec in EMITTED_SECTIONS:
                row[f"chunks_{sec}"] = by_sec.get(sec, 0)
            for sec in EMITTED_SECTIONS:
                row[f"pages_{sec}"] = ranges.get(sec, "")
            summary_rows.append(row)
            all_stats[fy] = row
    with (out_dir / "doc_chunks_summary.csv").open("w", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=list(summary_rows[0].keys()))
        w.writeheader()
        w.writerows(summary_rows)
    all_stats["_total_chunks"] = total
    return all_stats


def main(argv: Optional[list] = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--fy", action="append", help="limit to FY (repeatable), e.g. --fy FY26")
    args = ap.parse_args(argv)
    stats = run(fys=args.fy)
    print(f"total chunks: {stats['_total_chunks']}")
    print((OUT_DIR / "doc_chunks_summary.csv").read_text(encoding="utf-8"))
    return 0


if __name__ == "__main__":
    sys.exit(main())
