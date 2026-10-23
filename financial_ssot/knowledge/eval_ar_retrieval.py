"""P1.8 retrieval evaluation: hit@5 of `ARRetriever` on a fixed question set.

Ground truth is computed from the real AR text, not hand-typed page numbers: the gold pages of a
question are the PDF pages of that AR on which ALL of its `gold` regexes match (whitespace
collapsed, case-insensitive). A question is a hit when one of the top-5 retrieved chunks has the
same fiscal year and a gold page.

Two sets:
- `main` (Q01-Q22): written by the builder with the gold regexes in view, so many questions reuse
  the answer page's rare terms (Daman Upside, Mumbai High, KG-DWN-98/2, 51.11%...) and 7 of 22 are
  about reserves/RRR. LEXICAL_WEIGHT (ar_retriever) was tuned on this set, so it is IN-SAMPLE.
- `heldout` (H01-H18): H01-H08 are the G4 reviewer's paraphrases (docs/reviews/P1.8.md §4.4);
  H09-H18 are paraphrases written to avoid the gold page's distinctive vocabulary. Each reuses the
  gold regexes of the main question it paraphrases (`gold_of`). LEXICAL_WEIGHT was frozen at 0.05
  before this set was scored.

Run from the app root (ADC + the loaded table required):
    python -m financial_ssot.knowledge.eval_ar_retrieval [--set main|heldout] [--lexical-weight W]
                                                         [--gold-only] [--out path.json]
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

from financial_ssot.knowledge.chunk_ar import AR_FILES, TEXT_DIR, split_pages

# (id, fiscal_year, question, [gold regexes, all must match on the page])
QUESTIONS = [
    ("Q01", "FY26", "How much 2P reserves did ONGC accrete in FY26 and what was the reserve replacement ratio?",
     [r"accreted 44\.01 MMTOE"]),
    ("Q02", "FY24", "What was the reserve accretion and RRR from domestic fields in FY24?",
     [r"accreted 45\.20 MMTOE", r"Reserve Replacement Ratio"]),
    ("Q03", "FY23", "Reserve replacement ratio and 2P reserve accretion during FY23",
     [r"accreted 40\.62 MMTOE"]),
    ("Q04", "FY19", "What was ONGC's reserve replacement ratio for 2P and 1P reserves in 2018-19?",
     [r"1\.41 and 1\.78"]),
    ("Q05", "FY18", "What was the reserve accretion (2P) and RRR in 2017-18?",
     [r"67\.83", r"Reserve Replacement Ratio"]),
    ("Q06", "FY17", "How many hydrocarbon discoveries did ONGC make in FY17 and what was the reserve accretion?",
     [r"23 Hydrocarbon discoveries", r"64\.54"]),
    ("Q07", "FY22", "When was the Special Additional Excise Duty on crude oil levied and at what rate?",
     [r"Special Additional Excise Duty", r"23,250 per tonne"]),
    ("Q08", "FY26", "How many wells did ONGC drill in FY26 and how many were exploratory?",
     [r"drilled 501 wells"]),
    ("Q09", "FY26", "What was the total capital expenditure of ONGC including subsidiaries in FY26?",
     [r"611,308 Million"]),
    ("Q10", "FY26", "What is the accounting policy for the decommissioning cost of a dry well?",
     [r"decommissioning", r"dry well is expensed as exploratory well cost"]),
    ("Q11", "FY24", "How is the decommissioning cost of dry wells treated in the accounts?",
     [r"decommissioning cost in respect of dry well is expensed as exploratory\s+well cost|"
      r"decommissioning .{0,80}cost in respect of dry well is expensed as .{0,80}exploratory well"]),
    ("Q12", "FY25", "What did the MD&A say about windfall profit taxes on crude oil being abolished?",
     [r"windfall profit taxes"]),
    ("Q13", "FY22", "What is ONGC's Energy Strategy 2040 and its net zero agenda?",
     [r"Energy Strategy 2040", r"Net Zero"]),
    ("Q14", "FY23", "What was the production increase from Mumbai High cluster fields?",
     [r"Mumbai High"]),
    ("Q15", "FY18", "When did ONGC acquire the Government's 51.11% stake in HPCL?",
     [r"51\.11%", r"January 31, 2018"]),
    ("Q16", "FY25", "What was ONGC's CSR expenditure in FY25?",
     [r"CSR expenditure of"]),
    ("Q17", "FY25", "When is the Daman Upside Development Project expected to be monetised?",
     [r"Daman Upside"]),
    ("Q18", "FY24", "What windfall tax or SAED impact did ONGC face in FY24?",
     [r"windfall|Special Additional Excise Duty|SAED"]),
    ("Q19", "FY19", "What did the MD&A say about windfall gains or taxes in 2018-19?",
     [r"windfall"]),
    ("Q20", "FY17", "What is the overall 2P reserve replacement ratio track record in FY17?",
     [r"11th consecutive year"]),
    ("Q21", "FY22", "What interim dividend did ONGC pay in November 2021?",
     [r"interim dividend of"]),
    ("Q22", "FY26", "What happened in the KG-DWN-98/2 block exploration wells during FY26?",
     [r"KG-DWN-98/2", r"proved dry|flowed oil"]),
]


# (id, gold_of, question). FY and gold regexes come from the main question `gold_of`.
HELDOUT = [
    # G4 reviewer paraphrases (P1.8.md §4.4)
    ("H01", "Q01", "new oil and gas added to proven-plus-probable inventory"),
    ("H02", "Q07", "government start taxing unexpected crude profits, per tonne"),
    ("H03", "Q14", "western offshore legacy asset output uplift"),
    ("H04", "Q17", "gas project off Gujarat coast near Daman"),
    ("H05", "Q15", "buy government's stake in refiner HPCL"),
    ("H06", "Q16", "spend on corporate social responsibility"),
    ("H07", "Q21", "interim payout declared late 2021"),
    ("H08", "Q12", "removal of special levy on domestic crude"),
    # builder paraphrases avoiding the gold page's distinctive terms
    ("H09", "Q02", "How much did the company add to its proved plus probable hydrocarbon base in 2023-24, and did additions exceed output?"),
    ("H10", "Q04", "In 2018-19, how did additions to booked oil and gas volumes compare with what was produced, on both proved and proved-plus-probable bases?"),
    ("H11", "Q06", "How many new oil and gas finds were made in 2016-17?"),
    ("H12", "Q08", "What was the count of boreholes completed in the latest year, and how many were for finding new resources?"),
    ("H13", "Q09", "How much did the group invest in capital projects across the parent and its subsidiaries last year?"),
    ("H14", "Q11", "If a well finds nothing, how is the cost of plugging and abandoning it accounted for?"),
    ("H15", "Q13", "What is the long-term plan for diversifying the business and bringing carbon emissions down to zero?"),
    ("H16", "Q22", "Did any wells in the east coast deepwater block find hydrocarbons this year?"),
    ("H17", "Q19", "Did management discuss taxes on unexpected oil price gains in 2018-19?"),
    ("H18", "Q05", "How much did ONGC add to recoverable volumes in 2017-18, and for how many years in a row has it more than replaced production?"),
]


def question_set(name: str) -> list:
    """[(id, fy, question, gold regexes)]"""
    if name == "main":
        return list(QUESTIONS)
    by = {q[0]: q for q in QUESTIONS}
    return [(hid, by[src][1], text, by[src][3]) for hid, src, text in HELDOUT]


def gold_pages(qs: list = None) -> dict:
    cache = {}
    out = {}
    for qid, fy, _q, pats in (qs or QUESTIONS):
        if fy not in cache:
            cache[fy] = [" ".join(p.split()) for p in split_pages((TEXT_DIR / AR_FILES[fy]).read_text(encoding="utf-8"))]
        out[qid] = [i + 1 for i, t in enumerate(cache[fy]) if all(re.search(p, t, re.I) for p in pats)]
    return out


def evaluate(retriever=None, k: int = 5, qset: str = "main") -> dict:
    qs = question_set(qset)
    gold = gold_pages(qs)
    if retriever is None:
        sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "yukti" / "backend"))
        from app.knowledge.ar_retriever import ARRetriever
        retriever = ARRetriever()
    rows, hits = [], 0
    for qid, fy, q, _p in qs:
        res = retriever.retrieve(q, fiscal_year=fy)
        top = res[:k]
        hit_rank = next((i + 1 for i, r in enumerate(top) if r["fiscal_year"] == fy and r["source_page"] in gold[qid]), None)
        hits += hit_rank is not None
        rows.append({
            "id": qid, "fy": fy, "question": q, "gold_pages": gold[qid], "hit_rank": hit_rank,
            "top5": [f"{r['fiscal_year']} p{r['source_page']} ({r['section']}, {r['distance']:.3f})" for r in top],
            "top1_citation": top[0]["citation"] if top else None,
        })
    return {"set": qset, "k": k, "n": len(qs), "hits": hits, "hit_at_k": hits / len(qs), "rows": rows}


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--gold-only", action="store_true")
    ap.add_argument("--set", default="main", choices=["main", "heldout"])
    ap.add_argument("--lexical-weight", type=float, help="override ar_retriever.LEXICAL_WEIGHT (0 = vector + section only)")
    ap.add_argument("--out")
    a = ap.parse_args(argv)
    if a.gold_only:
        for qid, pages in gold_pages(question_set(a.set)).items():
            print(qid, pages)
        return 0
    retriever = None
    if a.lexical_weight is not None:
        sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "yukti" / "backend"))
        from app.knowledge import ar_retriever as arm
        arm.LEXICAL_WEIGHT = a.lexical_weight
        retriever = arm.ARRetriever()
    res = evaluate(retriever, qset=a.set)
    for r in res["rows"]:
        print(f"{r['id']} {r['fy']} hit@{res['k']}={'Y' if r['hit_rank'] else 'N'} rank={r['hit_rank']} gold={r['gold_pages']} top={r['top5']}")
    print(f"[{res['set']}] hit@{res['k']} = {res['hits']}/{res['n']} = {res['hit_at_k']:.2f}")
    if a.out:
        Path(a.out).write_text(json.dumps(res, indent=2), encoding="utf-8")
    return 0


if __name__ == "__main__":
    sys.exit(main())
