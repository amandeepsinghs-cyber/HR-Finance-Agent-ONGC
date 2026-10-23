"""P1.8 retrieval evaluation: hit@5 of `ARRetriever` on a fixed question set.

Ground truth is computed from the real AR text, not hand-typed page numbers: the gold pages of a
question are the PDF pages of that AR on which ALL of its `gold` regexes match (whitespace
collapsed, case-insensitive). A question is a hit when one of the top-5 retrieved chunks has the
same fiscal year and a gold page.

Run from the app root (ADC + the loaded table required):
    python -m financial_ssot.knowledge.eval_ar_retrieval [--gold-only] [--out path.json]
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


def gold_pages() -> dict:
    cache = {}
    out = {}
    for qid, fy, _q, pats in QUESTIONS:
        if fy not in cache:
            cache[fy] = [" ".join(p.split()) for p in split_pages((TEXT_DIR / AR_FILES[fy]).read_text(encoding="utf-8"))]
        out[qid] = [i + 1 for i, t in enumerate(cache[fy]) if all(re.search(p, t, re.I) for p in pats)]
    return out


def evaluate(retriever=None, k: int = 5) -> dict:
    gold = gold_pages()
    if retriever is None:
        sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "yukti" / "backend"))
        from app.knowledge.ar_retriever import ARRetriever
        retriever = ARRetriever()
    rows, hits = [], 0
    for qid, fy, q, _p in QUESTIONS:
        res = retriever.retrieve(q, fiscal_year=fy)
        top = res[:k]
        hit_rank = next((i + 1 for i, r in enumerate(top) if r["fiscal_year"] == fy and r["source_page"] in gold[qid]), None)
        hits += hit_rank is not None
        rows.append({
            "id": qid, "fy": fy, "question": q, "gold_pages": gold[qid], "hit_rank": hit_rank,
            "top5": [f"{r['fiscal_year']} p{r['source_page']} ({r['section']}, {r['distance']:.3f})" for r in top],
            "top1_citation": top[0]["citation"] if top else None,
        })
    return {"k": k, "n": len(QUESTIONS), "hits": hits, "hit_at_k": hits / len(QUESTIONS), "rows": rows}


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--gold-only", action="store_true")
    ap.add_argument("--out")
    a = ap.parse_args(argv)
    if a.gold_only:
        for qid, pages in gold_pages().items():
            print(qid, pages)
        return 0
    res = evaluate()
    for r in res["rows"]:
        print(f"{r['id']} {r['fy']} hit@{res['k']}={'Y' if r['hit_rank'] else 'N'} rank={r['hit_rank']} gold={r['gold_pages']} top={r['top5']}")
    print(f"hit@{res['k']} = {res['hits']}/{res['n']} = {res['hit_at_k']:.2f}")
    if a.out:
        Path(a.out).write_text(json.dumps(res, indent=2), encoding="utf-8")
    return 0


if __name__ == "__main__":
    sys.exit(main())
