"""Re-execute answer-key entries and rewrite expected JSON + answer MD.

Usage (from data_bank/answer_key):
    uv run python -m semantic_audit.run_entry C11 C11__why ...      # execute + write
    uv run python -m semantic_audit.run_entry --dry C11             # execute, print, do not write
    uv run python -m semantic_audit.run_entry --render-only C11     # re-render MD from stored JSON

MD rendering: if the entry has a narrative in narratives_*.py it is used; otherwise the
original build_answer_key.render_markdown_answer is used, and the run FAILS if that would
produce the generic template text.
"""

from __future__ import annotations

import json
import sys

from semantic_audit import common as C


def _legacy_render(eid, res):
    import importlib.util
    spec = importlib.util.spec_from_file_location("bak", C.AK_DIR / "build_answer_key.py")
    bak = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(bak)
    q = C.question_map()[eid]
    return bak.render_markdown_answer(eid, q["question"], q["type"], res, q["parent"] is not None, q["kind"])


def process(eid: str, narratives, write: bool, render_only: bool) -> bool:
    qm = C.question_map()
    if eid not in qm:
        print(f"[{eid}] unknown id")
        return False
    if render_only:
        res = C.load_json(eid)
    else:
        sql = C.clean_sql(C.sql_path(eid).read_text(encoding="utf-8"))
        try:
            res = C.execute_sql(sql)
        except Exception as e:  # noqa: BLE001
            print(f"[{eid}] SQL ERROR: {e}")
            return False

    ok = True
    if res["row_count"] == 0:
        print(f"[{eid}] WARNING: 0 rows")
        ok = False
    parent = qm[eid]["parent"]
    if parent:
        prow = C.load_json(parent)["rows"]
        if prow == res["rows"]:
            print(f"[{eid}] ERROR: identical to parent {parent}")
            ok = False

    if eid in narratives:
        try:
            narr = narratives[eid](res["rows"])
        except Exception as e:  # noqa: BLE001
            print(f"[{eid}] NARRATIVE ERROR: {type(e).__name__}: {e}")
            return False
        md = C.render_md(eid, res, narr)
    else:
        md = _legacy_render(eid, res)
        if C.GENERIC_MARKER in md:
            print(f"[{eid}] ERROR: no narrative registered and legacy renderer is generic")
            ok = False

    print(f"[{eid}] rows={res['row_count']} cols={res['columns']}")
    for r in res["rows"][:6]:
        print("   ", json.dumps(r, default=str)[:300])
    print("  HEADLINE:", C.headline_from_md(md))
    if eid in narratives:
        print("  NARRATIVE:", narr.replace("\n", " ")[:900])

    if write and ok:
        if not render_only:
            C.json_path(eid).write_text(json.dumps(res, indent=2), encoding="utf-8")
        C.md_path(eid).write_text(md, encoding="utf-8")
        print(f"  -> written")
    elif write:
        print(f"  -> NOT written (errors)")
    return ok


def main(argv):
    write = "--dry" not in argv
    render_only = "--render-only" in argv
    ids = [a for a in argv if not a.startswith("--")]
    narratives = C.load_narratives()
    bad = [e for e in ids if not process(e, narratives, write, render_only)]
    if bad:
        print("FAILED:", bad)
        sys.exit(1)


if __name__ == "__main__":
    main(sys.argv[1:])
