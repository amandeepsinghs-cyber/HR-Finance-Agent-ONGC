"""Deterministic NSE XBRL parser (P1.4): Reg-33 annual results, FY18-FY21, FY23-FY24.

SPEC-01 §3 (rank 4), §4.4, §5.3, §6 V10.  Packet: docs/delegation/packets/v3/P1.4_xbrl_parser.md

Rules (all deterministic, ``lxml.etree`` only; no regex over XML):

1. ``fiscal_year`` / ``scope`` come from the file name
   (``NSE_XBRL_ONGC_FY2020-21_Standalone__*.xml`` -> ``FY21``, ``standalone``).
2. Facts are the children of ``xbrli:xbrl`` in the ``in-bse-fin`` namespace
   (matched by prefix, because the URI changes 2018-03-31 -> 2020-03-31).
3. ``period_type`` comes from the ``contextRef`` **name**, not the context's
   declared dates: ``Four...D`` = ``annual`` (12 months to FY-end), ``One...D`` =
   ``quarter`` (Q4), ``...I`` = ``instant`` (as at FY-end; balance sheet); cash-flow
   facts are always ``annual`` (Reg-33 CF is annual-only; FY21 files it under ``OneD``).  The
   names are used because the filings' context elements are unreliable: the
   FY18-FY21 files declare no ``FourD``/``OneD`` context at all, and the FY23/FY24
   files declare ``FourD`` with a 3-month period (``2024-01-01..2024-03-31``)
   although its values are full-year (FY24 Revenue FourD 1,384,021.3 ₹ mn = AR).
   The declared dates are kept in ``context_period_declared`` for audit.
   Any other context name raises ``ValueError`` (packet stop-and-ask trigger).
4. Dimensional contexts (``FourReportableSegmentRevenue01D``,
   ``OneOperatingExpenses03D`` ...) get ``segment_member`` = the text of the
   ``DescriptionOf*`` fact that carries the same ``contextRef`` (e.g.
   ``Offshore``); if none exists, the explicit-member QName, else the context id.
5. Numeric facts (those with ``unitRef``) go to :func:`parse`; text facts to
   :func:`parse_text_facts`.  ``INR`` money: ``value_inr_cr = value_inr / 1e7``,
   ``value_inr_mn = value_inr / 1e6`` and ``precision_inr_cr = 10**(-decimals)/1e7``
   (``decimals="-7"`` -> 1.0 ₹ cr).  Non-INR units (EPS, ratios, shares) keep
   ``value_inr_*`` / ``precision_inr_cr`` = None.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

from lxml import etree

EXTRACTOR_VERSION = "xbrl/1.0.0"
APP_ROOT = Path(__file__).resolve().parents[2]
XBRL_DIR = APP_ROOT / "knowledge" / "public_sources" / "grounding_data" / "xbrl"
TAG_MAP = Path(__file__).resolve().parent / "xbrl_tag_map.csv"
TEN_YEAR = APP_ROOT / "financial_ssot" / "out" / "ten_year_raw.parquet"

NS_XBRLI = "http://www.xbrl.org/2003/instance"
NS_XBRLDI = "http://xbrl.org/2006/xbrldi"
FIN_PREFIX = "in-bse-fin"
TOLERANCE_INR_CR = 0.5  # V10: XBRL is rounded to ₹1 cr
CF_CCE_TAG = "CashAndCashEquivalentsCashFlowStatement"  # tag map: CF.CCE_* (split OPEN/CLOSE in code)
CF_CCE_CHANGE_TAG = "IncreaseDecreaseInCashAndCashEquivalents"
# Point-in-time balances that the filings put on duration (One...D) contexts.
INSTANT_TAGS = {"SegmentAssets"}
RESTATED_REVIEW_PCT = 1.0  # restated Δ above this % of the 10-yr value -> P1.6 review list

# Documented reasons for V10 differences (fiscal_year, xbrl_tag or "*") -> text.
# Sources: MANIFEST_v3_acquisition.md §3, SPEC-01 §6 regression fixtures.
EXPLANATIONS: dict[tuple[str, str], str] = {
    ("FY19", "*"): ("restated: 10-yr FY19 column marked '*' in AR FY22/FY24/FY26; XBRL = as-reported "
                    "own-year AR FY19 (PAT 267,157.89 ₹ mn, MANIFEST_v3 §3)"),
    ("FY20", "*"): ("restated: 10-yr FY20 column marked '*'; XBRL = as-reported (PAT 134,445.4 ₹ mn vs "
                    "134,637 restated, MANIFEST_v3 §3)"),
    ("FY23", "*"): ("restated: 10-yr FY23 column marked '*' in AR FY24/FY26; XBRL = as-reported "
                    "(PAT 388,288.7 vs 400,965 ₹ mn, MANIFEST_v3 §3)"),
    ("FY24", "Income"): ("reclassification not marked '*': AR FY25 restated FY24 Other income 10,778.19 -> "
                         "10,735.52 ₹ cr (Δ 42.67 cr; SPEC-01 §6 V07 fixture); AR FY24 10-yr = XBRL. "
                         "Conflict candidate for O"),
}


def explain(fiscal_year: str, tag: str, status: str) -> str | None:
    if status == "pass":
        return None
    return EXPLANATIONS.get((fiscal_year, tag)) or EXPLANATIONS.get((fiscal_year, "*")) or (
        "10-yr column marked '*' (restated)" if status == "restated" else "unexplained")

_FILE_RE = re.compile(r"NSE_XBRL_ONGC_FY(\d{4})-(\d{2})_(Standalone|Consolidated)__")
_CTX_RE = re.compile(r"^(One|Four)([A-Za-z]*?)(\d{2})?([DI])$")
_CF_PREFIXES = (
    "CashFlows", "CashAndCashEquivalentsCashFlowStatement", "Adjustments", "Proceeds", "Payments",
    "PurchaseOf", "Repayments", "InterestPaid", "InterestReceived", "DividendsPaid", "DividendsReceived",
    "IncomeTaxesPaid", "OtherInflows", "OtherCash", "OtherAdjustments", "EffectOfExchange",
    "IncreaseDecreaseInCash", "CashAdvances", "CashPayment", "CashReceipts",
)


# --------------------------------------------------------------------------- helpers
def file_meta(path: str | Path) -> dict:
    """``FY2020-21`` -> ``FY21``; ``Standalone`` -> ``standalone``."""
    name = Path(path).name
    m = _FILE_RE.search(name)
    if not m:
        raise ValueError(f"unexpected XBRL file name: {name}")
    return {
        "fiscal_year": f"FY{m.group(2)}",
        "fy_text": f"FY{m.group(1)}-{m.group(2)}",
        "period_end": f"20{m.group(2)}-03-31",
        "scope": m.group(3).lower(),
        "source_doc": name,
    }


def context_info(context_ref: str) -> dict:
    """Classify a context id by its NSE naming convention (rule 3)."""
    m = _CTX_RE.match(context_ref)
    if not m:
        raise ValueError(f"unknown XBRL context naming: {context_ref!r} (stop-and-ask)")
    span, axis, _num, kind = m.groups()
    if kind == "I":
        period_type = "instant"
    else:
        period_type = "annual" if span == "Four" else "quarter"
    return {"period_type": period_type, "dimensional": bool(axis), "axis_group": axis or None}


def _fin_ns(root) -> str:
    ns = root.nsmap.get(FIN_PREFIX)
    if not ns:
        raise ValueError(f"namespace prefix {FIN_PREFIX!r} not declared (stop-and-ask)")
    return ns


def _contexts(root) -> dict[str, dict]:
    out = {}
    for c in root.iter(f"{{{NS_XBRLI}}}context"):
        period = c.find(f"{{{NS_XBRLI}}}period")
        dates = [e.text for e in period] if period is not None else []
        member = c.find(f".//{{{NS_XBRLDI}}}explicitMember")
        out[c.get("id")] = {
            "dates": "..".join(d for d in dates if d),
            "member": member.text.strip() if member is not None and member.text else None,
        }
    return out


def _facts(root):
    ns = _fin_ns(root)
    for el in root:
        if not isinstance(el.tag, str):
            continue
        q = etree.QName(el)
        if q.namespace == ns and el.get("contextRef"):
            yield el, q.localname


def _member_descriptions(root) -> dict[str, str]:
    """contextRef -> text of the ``DescriptionOf*`` fact on that dimensional context."""
    out: dict[str, str] = {}
    for el, tag in _facts(root):
        ctx = el.get("contextRef")
        if tag.startswith("DescriptionOf") and context_info(ctx)["dimensional"] and el.text:
            out.setdefault(ctx, el.text.strip())
    return out


def statement_guess(tag: str, ctx: dict) -> str:
    if ctx["axis_group"] and "Segment" in ctx["axis_group"] or tag.startswith(("Segment", "NetSegment", "UnAllocable", "OtherUnallocable", "InterSegment")):
        return "segment"
    if ctx["period_type"] == "instant":
        return "balance_sheet"
    if tag.startswith(_CF_PREFIXES):
        return "cash_flow"
    return "pnl"


def _precision(decimals: str | None) -> float | None:
    if decimals is None or decimals == "INF":
        return 0.0 if decimals == "INF" else None
    return 10 ** (-int(decimals)) / 1e7


def load_tag_map(path: Path = TAG_MAP) -> dict[str, dict]:
    with path.open(encoding="utf-8") as fh:
        return {r["xbrl_tag"]: r for r in csv.DictReader(fh)}


# --------------------------------------------------------------------------- parse
def parse(path: str | Path, extracted_at: str | None = None, tag_map: dict | None = None,
          source_name: str | None = None) -> list[dict]:
    """Numeric facts of one XBRL file as bronze rows (+ packet §5.1 fields).

    ``source_name`` overrides the file name used for FY/scope (test fixtures)."""
    path = Path(path)
    meta = file_meta(source_name or path)
    tag_map = load_tag_map() if tag_map is None else tag_map
    stamp = extracted_at or datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    root = etree.parse(str(path)).getroot()
    ctx_decl = _contexts(root)
    descr = _member_descriptions(root)
    rows: list[dict] = []
    seen: dict[tuple[str, str], float] = {}
    for el, tag in _facts(root):
        unit = el.get("unitRef")
        if unit is None:
            continue  # text fact -> parse_text_facts
        ctx_ref = el.get("contextRef")
        ci = context_info(ctx_ref)
        raw = (el.text or "").strip()
        value = float(raw)
        decimals = el.get("decimals")
        is_inr = unit == "INR"
        decl = ctx_decl.get(ctx_ref)
        notes = []
        if decl is None:
            notes.append("context_not_declared_in_file")
        elif ci["period_type"] == "annual" and decl["dates"] and not decl["dates"].startswith(f"20{int(meta['fiscal_year'][2:]) - 1:02d}-04-01"):
            notes.append(f"context_period_mislabelled:{decl['dates']}")
        stmt = statement_guess(tag, ci)
        period_type = ci["period_type"]
        if stmt == "cash_flow" and period_type == "quarter":
            # Reg-33 cash flow is annual-only; the FY21 filings put the full-year CF under OneD
            # (FY21 standalone CFO 27,665.11 ₹ cr), FY23/FY24 under FourD.
            period_type = "annual"
            notes.append("cf_annual_filed_under_OneD")
        if tag in INSTANT_TAGS and period_type != "instant":
            period_type = "instant"  # e.g. SegmentAssets filed on OneD / OneReportableSegmentAssetsNND
            notes.append("point_in_time_tag_on_duration_context")
        key = (tag, ctx_ref)
        if key in seen:
            notes.append("duplicate_fact" + ("" if seen[key] == value else f"_conflict:{seen[key]}"))
        seen[key] = value
        member = None
        if ci["dimensional"]:
            # instant segment facts (...Liabilities01I) carry their description on the ...01D twin
            member = (descr.get(ctx_ref) or descr.get(ctx_ref[:-1] + "D")
                      or (decl or {}).get("member") or ctx_ref)
        line = el.sourceline
        eid = hashlib.sha1(f"{meta['source_doc']}|{tag}|{ctx_ref}|{line}".encode()).hexdigest()[:16]
        mapped = tag_map.get(tag, {})
        line_code = mapped.get("proposed_line_code") or None
        if tag == CF_CCE_TAG:
            # Filed twice per context: 1st = C&CE at beginning, 2nd = at end of period
            # (FY24 standalone 2nd = 34.55 ₹ cr = AR FY24 CF closing 345.48 ₹ mn, SPEC-01 V04).
            nth = sum(1 for r in rows if r["xbrl_tag"] == tag and r["context_ref"] == ctx_ref)
            line_code = "CF.CCE_OPEN" if nth == 0 else "CF.CCE_CLOSE"
            notes = [n for n in notes if not n.startswith("duplicate_fact")]
            notes.append("cf_cce_opening" if nth == 0 else "cf_cce_closing")
        if line_code == "PL.PAT" and meta["scope"] == "consolidated":
            notes.append("includes_nci")  # total PAT; owners' share = ProfitOrLossAttributableToOwnersOfParent
        rows.append({
            # bronze schema (SPEC-01 §5.3, P1.2 column order)
            "extract_id": eid,
            "source_system": "xbrl",
            "source_doc": meta["source_doc"],
            "source_page": None,
            "source_page_label": None,
            "source_text_line": line,
            "raw_label": tag,
            "raw_value_text": raw,
            "parsed_value": value,
            "unit": unit,
            "column_header": ctx_ref,
            "scope": meta["scope"],
            "statement_guess": stmt,
            "extractor_version": EXTRACTOR_VERSION,
            "extracted_at": stamp,
            "report_vintage": f"XBRL_{meta['fy_text']}",
            "fiscal_year": meta["fiscal_year"],
            "is_restated": False,
            "is_nil": False,
            "parent_label": None,
            "block": ci["axis_group"],
            "notes": ";".join(notes) or None,
            # packet §5.1 fields
            "period_end": meta["period_end"],
            "xbrl_tag": tag,
            "context_ref": ctx_ref,
            "context_period_declared": (decl or {}).get("dates") or None,
            "period_type": period_type,
            "segment_member": member,
            "decimals": decimals,
            "value_inr": value if is_inr else None,
            "value_inr_cr": value / 1e7 if is_inr else None,
            "value_inr_mn": value / 1e6 if is_inr else None,
            "precision_inr_cr": _precision(decimals) if is_inr else None,
            "extraction_method": "xbrl",
            "proposed_line_code": line_code,
        })
    _flag_cce_defects(rows)
    return rows


def _flag_cce_defects(rows: list[dict]) -> None:
    """M1 (G4 r1): opening C&CE = 0 and closing = the period's net change => filing defect.

    FY23 standalone files opening 0.00 / closing 27.08 ₹ cr (= IncreaseDecrease), whereas AR FY23
    shows 50.11 -> 77.19 ₹ cr.  Both facts are kept for audit but lose their line code so they can
    never backfill gold as clean CF.CCE_OPEN / CF.CCE_CLOSE.
    """
    for ctx in {r["context_ref"] for r in rows if r["xbrl_tag"] == CF_CCE_TAG}:
        cce = [r for r in rows if r["xbrl_tag"] == CF_CCE_TAG and r["context_ref"] == ctx]
        chg = [r for r in rows if r["xbrl_tag"] == CF_CCE_CHANGE_TAG and r["context_ref"] == ctx]
        if len(cce) == 2 and chg and cce[0]["parsed_value"] == 0 and cce[1]["parsed_value"] == chg[0]["parsed_value"]:
            for r in cce:
                r["proposed_line_code"] = None
                r["notes"] = ";".join(filter(None, [r["notes"], "cf_cce_filing_defect"]))


def parse_text_facts(path: str | Path, source_name: str | None = None) -> list[dict]:
    """Non-numeric facts (dates, descriptions, flags) of one XBRL file."""
    path = Path(path)
    meta = file_meta(source_name or path)
    root = etree.parse(str(path)).getroot()
    out = []
    for el, tag in _facts(root):
        if el.get("unitRef") is not None:
            continue
        ctx_ref = el.get("contextRef")
        out.append({
            "source_doc": meta["source_doc"], "fiscal_year": meta["fiscal_year"], "scope": meta["scope"],
            "xbrl_tag": tag, "context_ref": ctx_ref, "period_type": context_info(ctx_ref)["period_type"],
            "text": (el.text or "").strip(), "source_text_line": el.sourceline,
        })
    return out


def xbrl_files(xbrl_dir: Path = XBRL_DIR) -> list[Path]:
    return sorted(p for p in xbrl_dir.glob("NSE_XBRL_ONGC_FY*.xml"))


# --------------------------------------------------------------------------- cross-check (V10)
def cross_check(xbrl_rows: list[dict], ten_year_rows: list[dict], tag_map: dict | None = None) -> list[dict]:
    """Standalone FourD facts with a mapped 10-yr label vs every P1.2 edition that has the FY.

    10-yr values are ₹ mn (0 dp) -> ÷ 10 = ₹ cr.  ``status``: ``pass`` (|Δ| ≤ 0.5 ₹ cr),
    ``restated`` (fails and the 10-yr column is marked ``*``), else ``mismatch``.
    """
    tag_map = load_tag_map() if tag_map is None else tag_map
    idx: dict[tuple[str, str, str], dict] = {}
    for r in ten_year_rows:
        if r.get("unit") != "INR_mn" or r.get("scope") != "standalone":
            continue
        k = (r["report_vintage"], r["fiscal_year"], str(r["raw_label"]).strip())
        idx.setdefault(k, r)  # first occurrence per edition (tables are ordered)
    vintages = sorted({r["report_vintage"] for r in ten_year_rows})
    out = []
    for x in xbrl_rows:
        m = tag_map.get(x["xbrl_tag"])
        if not m or not m.get("ten_year_label") or x["scope"] != "standalone" or x["context_ref"] != "FourD":
            continue
        labels = [s.strip() for s in m["ten_year_label"].split("|")]
        for v in vintages:
            ty = next((idx[(v, x["fiscal_year"], lb)] for lb in labels if (v, x["fiscal_year"], lb) in idx), None)
            if ty is None:
                continue
            ty_cr = float(ty["parsed_value"]) / 10
            d = x["value_inr_cr"] - ty_cr
            ok = abs(d) <= TOLERANCE_INR_CR
            pct = abs(d) / abs(ty_cr) * 100 if ty_cr else (0.0 if d == 0 else float("inf"))
            out.append({
                "fiscal_year": x["fiscal_year"], "xbrl_tag": x["xbrl_tag"],
                "proposed_line_code": m["proposed_line_code"],
                "xbrl_inr_cr": round(x["value_inr_cr"], 4), "ten_year_vintage": v,
                "ten_year_label": ty["raw_label"], "ten_year_inr_mn": ty["parsed_value"],
                "ten_year_inr_cr": round(ty_cr, 4), "delta_inr_cr": round(d, 4),
                "ten_year_marked_restated": bool(ty["is_restated"]),
                "status": (status := "pass" if ok else ("restated" if ty["is_restated"] else "mismatch")),
                "explanation": explain(x["fiscal_year"], x["xbrl_tag"], status),
                "delta_pct": round(pct, 3),
                # '*' explains that a restatement happened, not its size: large ones go to P1.6
                "review_flag": "P1.6_review_restated_gt_1pct" if status == "restated" and pct > RESTATED_REVIEW_PCT
                else ("P1.6_conflict_candidate" if status == "mismatch" else None),
                "xbrl_doc": x["source_doc"], "xbrl_line": x["source_text_line"],
                "ten_year_doc": ty["source_doc"], "ten_year_line": ty["source_text_line"],
            })
    return out


# --------------------------------------------------------------------------- CLI
def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--out", default="financial_ssot/out/xbrl_raw.parquet")
    ap.add_argument("--xbrl-dir", default=str(XBRL_DIR))
    ap.add_argument("--ten-year", default=str(TEN_YEAR))
    args = ap.parse_args(argv)
    import pandas as pd  # third-party only for parquet I/O

    stamp = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    tag_map = load_tag_map()
    rows: list[dict] = []
    for f in xbrl_files(Path(args.xbrl_dir)):
        r = parse(f, stamp, tag_map)
        n4 = sum(1 for x in r if x["context_ref"] == "FourD")
        print(f"{f.name[:48]}: {len(r)} numeric facts, {n4} FourD, {len(parse_text_facts(f))} text")
        rows.extend(r)
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    pd.DataFrame(rows).to_parquet(out, index=False)
    ty = pd.read_parquet(args.ten_year).to_dict("records")
    checks = cross_check(rows, ty, tag_map)
    cc = out.parent / "xbrl_crosscheck.csv"
    with cc.open("w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=list(checks[0].keys()))
        w.writeheader()
        w.writerows(checks)
    from collections import Counter

    print(f"cross-check: {len(checks)} comparisons, {dict(Counter(c['status'] for c in checks))}")
    print(f"wrote {out} ({len(rows)} rows) and {cc}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
