#!/usr/bin/env python3
"""Yukti v3 progress tracker.

Builds PROGRESS.md (the holistic, always-current status dashboard) from the
single sources of truth:
  * UPGRADE_CHECKLIST.md                -> steps (status, owner, FEATs, bugs), sponsor actions
  * feature_list_and_verbatims/feature_list/feature_list.md -> features + verbatim mapping
  * BUG_REGISTER.md                      -> bugs (status, severity, closing step)
  * docs/delegation/packets/v3/_INDEX_*  -> step dependencies + packet files
  * docs/reviews/                        -> G4 review evidence
  * git log                              -> step commits (drift detection)

Usage (run from the project root or anywhere):
  python3 scripts/progress/build_progress.py           # regenerate PROGRESS.md
  python3 scripts/progress/build_progress.py --check   # read-only: validate, exit 1 on errors (no write)
  python3 scripts/progress/build_progress.py --check --write   # validate AND regenerate (used by the git hook)

Rule (BUILD.md §4.2): every status change in UPGRADE_CHECKLIST.md / BUG_REGISTER.md
is followed by running this script and committing PROGRESS.md in the same commit.
"""
from __future__ import annotations

import argparse
import datetime as dt
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
CHECKLIST = ROOT / "UPGRADE_CHECKLIST.md"
FEATURES = ROOT / "feature_list_and_verbatims/feature_list/feature_list.md"
BUGS = ROOT / "BUG_REGISTER.md"
PACKETS = ROOT / "docs/delegation/packets/v3"
REVIEWS = ROOT / "docs/reviews"
OUT = ROOT / "PROGRESS.md"

STEP_RE = re.compile(r"\bP(?:0|1|2H|2F|3|4|5)\.\d+[a-z]?\b")
PHASE_ORDER = ["P0", "P1", "P2H", "P2F", "P3", "P4", "P5"]
PHASE_NAMES = {
    "P0": "Stabilise", "P1": "Real finance SSOT", "P2H": "HR: personas, V19, Employee-360",
    "P2F": "Finance diagnostics (V20)", "P3": "Agents + DCF (V22)", "P4": "Visual 9/10 + exports (V21)",
    "P5": "One brain, eval, redeploy",
}
# Step lifecycle (BUILD.md §4): To do -> Built (pre-G4) -> In review -> Done (G4) ; Blocked
STATUS = {
    "✅": ("done", 1.0), "🔍": ("review", 0.75), "🔨": ("built", 0.5),
    "🔄": ("in_progress", 0.25), "⛔": ("blocked", 0.0), "⬜": ("todo", 0.0),
}
STATUS_LABEL = {"done": "✅ Done", "review": "🔍 In review", "built": "🔨 Built (pre-G4)",
                "in_progress": "🔄 In progress", "blocked": "⛔ Blocked", "todo": "⬜ To do"}


def step_key(step: str):
    ph, _, num = step.partition(".")
    m = re.match(r"(\d+)([a-z]?)", num)
    return (PHASE_ORDER.index(ph) if ph in PHASE_ORDER else 99, int(m.group(1)) if m else 0, m.group(2) if m else "")


def phase_of(step: str) -> str:
    return step.split(".")[0]


def status_of(cell: str) -> str:
    for emo, (name, _) in STATUS.items():
        if emo in cell:
            return name
    return "todo"


def iter_tables(text: str):
    """Yield (header_cells, row_cells_list, preceding_heading) for every markdown table."""
    lines = text.splitlines()
    heading = ""
    i = 0
    while i < len(lines):
        line = lines[i]
        if line.startswith("#"):
            heading = line.strip("# ").strip()
        if line.startswith("|") and i + 1 < len(lines) and re.match(r"^\|\s*:?-{3}", lines[i + 1]):
            header = [c.strip().strip("*").strip() for c in line.strip().strip("|").split("|")]
            rows = []
            i += 2
            while i < len(lines) and lines[i].startswith("|"):
                rows.append([c.strip() for c in lines[i].strip().strip("|").split("|")])
                i += 1
            yield header, rows, heading
            continue
        i += 1


def col(header, name):
    for idx, h in enumerate(header):
        if h.lower().startswith(name.lower()):
            return idx
    return None


# ----------------------------------------------------------------------------- parsers
def parse_steps():
    steps, sponsor = {}, []
    for header, rows, heading in iter_tables(CHECKLIST.read_text(encoding="utf-8")):
        if header and header[0] == "Step" and col(header, "Status") is not None:
            ci = {k: col(header, k) for k in ("Task", "Owner", "FEAT", "Bugs", "Acceptance", "Status", "Packet")}
            for r in rows:
                if not STEP_RE.fullmatch(r[0].strip()):
                    continue
                get = lambda k: r[ci[k]] if ci[k] is not None and ci[k] < len(r) else ""
                steps[r[0]] = {
                    "id": r[0], "phase": phase_of(r[0]), "task": get("Task"), "owner": get("Owner"),
                    "feats": {f"FEAT-{int(x):03d}" for x in re.findall(r"\b0?(\d{2,3})\b", get("FEAT"))},
                    "bugs": {f"BUG-{int(x):02d}" for x in re.findall(r"\b(\d{2})\b", get("Bugs"))},
                    "status": status_of(get("Status")), "packet_cell": get("Packet"), "deps": set(),
                }
        elif header and header[0] == "ID" and col(header, "Action") is not None:
            for r in rows:
                sponsor.append(dict(zip(header, r)))
    return steps, sponsor


def parse_deps(steps):
    for idx in PACKETS.glob("_INDEX_*.md"):
        for header, rows, _ in iter_tables(idx.read_text(encoding="utf-8")):
            dcol = col(header, "Depends")
            if header and header[0] == "Step" and dcol is not None:
                for r in rows:
                    sid = r[0].strip()
                    if sid in steps and dcol < len(r):
                        cell = r[dcol]
                        deps = set(STEP_RE.findall(cell))
                        for ph in re.findall(r"\b(P0|P1|P2H|P2F|P3|P4|P5)\b(?!\.)", cell):
                            deps |= {s for s in steps if steps[s]["phase"] == ph}
                        deps.discard(sid)
                        steps[sid]["deps"] |= deps


# Implicit phase ordering (BUILD.md §1/§5, D-39): everything after P0 needs P0; P2F and P3 need P1;
# P5 needs P0–P4. Explicit per-step dependencies come from the packet indexes.
IMPLICIT_PHASE_DEPS = {"P1": ["P0"], "P2H": ["P0"], "P2F": ["P0", "P1"], "P3": ["P0", "P1"],
                       "P4": ["P0"], "P5": ["P0", "P1", "P2H", "P2F", "P3", "P4"]}


def add_implicit_deps(steps):
    for s in steps.values():
        for ph in IMPLICIT_PHASE_DEPS.get(s["phase"], []):
            s["deps"] |= {x for x in steps if steps[x]["phase"] == ph and x != "P0.0"}


def packet_exists(step_id):
    return any(PACKETS.glob(f"{step_id}.md")) or any(PACKETS.glob(f"{step_id}_*.md"))


def review_exists(step_id):
    return any(p for p in REVIEWS.glob(f"{step_id}*.md") if not p.name.endswith("_evidence.md"))


def parse_features():
    feats = {}
    for header, rows, _ in iter_tables(FEATURES.read_text(encoding="utf-8")):
        if header and header[0] == "ID" and col(header, "v3 status") is not None:
            vcol, scol, ncol = col(header, "Verbatims"), col(header, "v3 status"), col(header, "Feature")
            for r in rows:
                fid = re.sub(r"[*\s]", "", r[0])
                if not fid.startswith("FEAT-"):
                    continue
                verb = set()
                for a, b in re.findall(r"V(\d+)(?:\s*[–-]\s*V?(\d+))?", r[vcol]):
                    verb |= set(range(int(a), int(b or a) + 1))
                cell = r[scol]
                st = "done" if "✅" in cell else "partial" if "🟡" in cell else "broken" if "🔴" in cell else "missing"
                feats[fid] = {"id": fid, "name": r[ncol].strip("* "), "verbatims": verb, "status": st}
    return feats


def parse_bugs():
    bugs = {}
    sev = ""
    for header, rows, heading in iter_tables(BUGS.read_text(encoding="utf-8")):
        if heading.lower().startswith(("blocker", "important", "cosmetic")):
            sev = heading.split()[0]
        if header and header[0] == "ID" and col(header, "Status") is not None:
            scol, stcol = col(header, "Status"), col(header, "Step")
            for r in rows:
                if not re.fullmatch(r"BUG-\d\d", r[0]):
                    continue
                c = r[scol]
                st = "closed" if "✅" in c else "regressed" if "↩" in c else "in_progress" if "🟠" in c else "open"
                bugs[r[0]] = {"id": r[0], "status": st, "severity": sev, "steps": set(STEP_RE.findall(r[stcol])) if stcol is not None else set(),
                              "symptom": r[2] if len(r) > 2 else ""}
    return bugs


def git(*args):
    try:
        return subprocess.run(["git", *args], cwd=ROOT, capture_output=True, text=True, timeout=20).stdout.strip()
    except Exception:  # noqa: BLE001 - tracker must never crash on git issues
        return ""


# ----------------------------------------------------------------------------- report
def bar(frac, width=20):
    n = round(frac * width)
    return "█" * n + "░" * (width - n)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--check", action="store_true", help="validate only (read-only); exit 1 if integrity errors are found")
    ap.add_argument("--write", action="store_true", help="with --check: also regenerate PROGRESS.md")
    args = ap.parse_args()

    steps, sponsor = parse_steps()
    parse_deps(steps)
    add_implicit_deps(steps)
    feats = parse_features()
    bugs = parse_bugs()
    log = git("log", "--all", "--pretty=%h|%cs|%s", "-n", "400")
    commits = [l.split("|", 2) for l in log.splitlines() if l.count("|") >= 2]
    sha = git("rev-parse", "--short", "HEAD")
    branch = git("branch", "--show-current")

    errors, warnings = [], []
    committed = {}
    for h, d, msg in commits:
        m = re.match(r"^(P(?:0|1|2H|2F|3|4|5)\.\d+[a-z]?)\b", msg)
        if m and m.group(1) not in committed:
            committed[m.group(1)] = (h, d, msg)
    for s in steps.values():
        if s["status"] == "done" and "S" not in s["owner"].replace("→", " ").split() and s["id"] != "P0.0" and not review_exists(s["id"]):
            errors.append(f"{s['id']} is ✅ but has no G4 review file in docs/reviews/ ({s['id']}*.md).")
        if s["status"] == "todo" and s["id"] in committed:
            h = committed[s["id"]][0]
            errors.append(f"{s['id']} has commit {h} but the checklist still says ⬜ — update the status (🔨 Built / 🔍 In review / ✅ Done).")
        if s["status"] == "done":
            for b in sorted(s["bugs"]):
                if b in bugs and bugs[b]["status"] != "closed" and bugs[b]["steps"] and all(steps.get(x, {}).get("status") == "done" for x in bugs[b]["steps"] if x in steps):
                    warnings.append(f"{b} is still {bugs[b]['status']} although all its steps ({', '.join(sorted(bugs[b]['steps']))}) are ✅ — close it in BUG_REGISTER.md.")
        if s["phase"] != "P5" and s["id"] not in ("P0.0", "P0.8", "P1.1") and not packet_exists(s["id"]):
            warnings.append(f"{s['id']} has no packet file in docs/delegation/packets/v3/.")
    for b in bugs.values():
        if b["status"] == "closed":
            open_steps = [x for x in b["steps"] if x in steps and steps[x]["status"] != "done"]
            if open_steps:
                errors.append(f"{b['id']} is ✅ closed but its step(s) {', '.join(sorted(open_steps))} are not ✅.")
    for f in feats.values():
        fsteps = [s for s in steps.values() if f["id"] in s["feats"]]
        if f["status"] == "done" and any(s["status"] != "done" for s in fsteps):
            warnings.append(f"{f['id']} is ✅ in the feature list but has unfinished steps: {', '.join(s['id'] for s in fsteps if s['status'] != 'done')}.")

    total = len(steps)
    counts = {k: sum(1 for s in steps.values() if s["status"] == k) for k in STATUS_LABEL}
    weighted = sum(STATUS[e][1] for s in steps.values() for e, (n, _) in STATUS.items() if n == s["status"]) / max(total, 1)

    now = dt.datetime.now(dt.timezone.utc).strftime("%d-%b-%Y %H:%M UTC")
    L = []
    w = L.append
    w("# Yukti v3 — Progress Dashboard (`PROGRESS.md`)\n")
    w(f"> **Generated — do not edit by hand.** Source of truth: [`UPGRADE_CHECKLIST.md`](UPGRADE_CHECKLIST.md), [`BUG_REGISTER.md`](BUG_REGISTER.md), "
      f"[feature list](feature_list_and_verbatims/feature_list/feature_list.md), packet indexes, `docs/reviews/`, git. "
      f"Regenerate: `python3 scripts/progress/build_progress.py` · Generated {now} · branch `{branch}` @ `{sha}`\n")
    open_blockers = [b for b in bugs.values() if b["severity"] == "Blockers" and b["status"] != "closed"]
    ready = [s for s in steps.values() if s["status"] == "todo" and all(steps.get(d, {}).get("status") == "done" for d in s["deps"])]
    w("> [!IMPORTANT]")
    w(f"> **Overall: {weighted*100:.0f}% complete (weighted)** — {counts['done']}/{total} steps ✅ done, "
      f"{counts['review']+counts['built']+counts['in_progress']} in flight, {counts['todo']} to do, {counts['blocked']} blocked. "
      f"**{len(open_blockers)} blocker bugs open.** Integrity: {len(errors)} error(s), {len(warnings)} warning(s).\n")

    w("## 1. Phase progress\n")
    w("| Phase | Name | Progress | ✅ | 🔍 | 🔨 | 🔄 | ⬜ | ⛔ | Steps |")
    w("|---|---|---|---|---|---|---|---|---|---|")
    for ph in PHASE_ORDER:
        ps = [s for s in steps.values() if s["phase"] == ph]
        if not ps:
            continue
        frac = sum(STATUS[e][1] for s in ps for e, (n, _) in STATUS.items() if n == s["status"]) / len(ps)
        c = {k: sum(1 for s in ps if s["status"] == k) for k in STATUS_LABEL}
        w(f"| **{ph}** | {PHASE_NAMES[ph]} | `{bar(frac)}` {frac*100:.0f}% | {c['done']} | {c['review']} | {c['built']} | {c['in_progress']} | {c['todo']} | {c['blocked']} | {len(ps)} |")
    w("")

    w("## 2. Next actionable steps (all dependencies ✅)\n")
    in_flight = [s for s in steps.values() if s["status"] in ("built", "review", "in_progress", "blocked")]
    if in_flight:
        w("**In flight — finish these first:**\n")
        w("| Step | Status | Task | Owner | Next action |")
        w("|---|---|---|---|---|")
        nxt = {"built": "Run G4 review → docs/reviews/<step>.md", "review": "Apply review findings / approve", "in_progress": "Complete build + evidence", "blocked": "Resolve blocker / sponsor decision"}
        for s in sorted(in_flight, key=lambda s: (PHASE_ORDER.index(s["phase"]), s["id"])):
            w(f"| {s['id']} | {STATUS_LABEL[s['status']]} | {s['task'][:110]} | {s['owner']} | {nxt[s['status']]} |")
        w("")
    w("**Ready to start:**\n")
    w("| Step | Task | Owner | Unblocked by |")
    w("|---|---|---|---|")
    if not ready:
        w("| — | Nothing is unblocked: finish the in-flight steps above (G4 reviews) first. | | |")
    for s in sorted(ready, key=lambda s: (PHASE_ORDER.index(s["phase"]), s["id"]))[:15]:
        exp = sorted(d for d in s["deps"] if phase_of(d) == s["phase"])
        w(f"| {s['id']} | {s['task'][:110]} | {s['owner']} | {', '.join(exp) or 'phase gates met'} |")
    w("")

    w("## 3. Sponsor action items\n")
    if sponsor:
        hdr = list(sponsor[0].keys())
        w("| " + " | ".join(hdr) + " |")
        w("|" + "---|" * len(hdr))
        for r in sponsor:
            w("| " + " | ".join(r.get(h, "") for h in hdr) + " |")
    else:
        w("_None recorded (UPGRADE_CHECKLIST.md Part E)._")
    w("")

    w("## 4. Requirement coverage by verbatim (V1–V23)\n")
    w("| Verbatim | Features | Feature status | Open steps | Coverage |")
    w("|---|---|---|---|---|")
    icon = {"done": "✅", "partial": "🟡", "broken": "🔴", "missing": "⛔"}
    for v in range(1, 24):
        fs = [f for f in feats.values() if v in f["verbatims"]]
        if not fs:
            continue
        open_steps = sorted({s["id"] for s in steps.values() if s["status"] != "done" and s["feats"] & {f["id"] for f in fs}},
                            key=step_key)
        st = [f["status"] for f in fs]
        cov = "✅" if all(x == "done" for x in st) else "⛔" if all(x == "missing" for x in st) else "🔴" if all(x in ("missing", "broken") for x in st) else "🟡"
        w(f"| V{v} | {', '.join(f['id'] for f in fs)} | {' '.join(icon[f['status']] for f in fs)} | {', '.join(open_steps[:8])}{' …' if len(open_steps) > 8 else ''} | {cov} |")
    unmapped = [f"V{v}" for v in range(1, 24) if not any(v in f["verbatims"] for f in feats.values())]
    if unmapped:
        w(f"\n_Not mapped to a feature (process / question-bank / naming verbatims, tracked in UPGRADE_CHECKLIST Part A and docs/question_bank.md): {', '.join(unmapped)}._")
    w("")

    w("## 5. Features (v3 status from the feature list)\n")
    fc = {k: sum(1 for f in feats.values() if f["status"] == k) for k in icon}
    w(f"✅ {fc['done']} · 🟡 {fc['partial']} · 🔴 {fc['broken']} · ⛔ {fc['missing']} = {len(feats)}\n")
    w("| Feature | Status | Steps done / total |")
    w("|---|---|---|")
    for f in feats.values():
        fs = [s for s in steps.values() if f["id"] in s["feats"]]
        w(f"| {f['id']} {f['name'][:70]} | {icon[f['status']]} | {sum(1 for s in fs if s['status']=='done')}/{len(fs)} |")
    w("")

    w("## 6. Bugs\n")
    for sv in ("Blockers", "Important", "Cosmetic"):
        bs = [b for b in bugs.values() if b["severity"] == sv]
        if not bs:
            continue
        c = {k: sum(1 for b in bs if b["status"] == k) for k in ("open", "in_progress", "regressed", "closed")}
        w(f"- **{sv}:** {len(bs)} total — 🔴 open {c['open']} · 🟠 in progress {c['in_progress']} · ↩ regressed {c['regressed']} · ✅ closed {c['closed']}")
    w("\n**Open blockers:**\n")
    w("| Bug | Status | Symptom | Closing step(s) | Step status |")
    w("|---|---|---|---|---|")
    for b in open_blockers:
        sst = " ".join(f"{x}:{STATUS_LABEL.get(steps.get(x, {}).get('status', 'todo'), '?').split()[0]}" for x in sorted(b["steps"]))
        w(f"| {b['id']} | {b['status']} | {b['symptom'][:90]} | {', '.join(sorted(b['steps']))} | {sst} |")
    w("")

    w("## 7. Recent step commits\n")
    w("| Commit | Date | Message |")
    w("|---|---|---|")
    for h, d, msg in [c for c in commits if re.match(r"^P(?:0|1|2H|2F|3|4|5)\.", c[2])][:15]:
        w(f"| `{h}` | {d} | {msg[:130]} |")
    w("")

    w("## 8. Integrity checks\n")
    if not errors and not warnings:
        w("✅ No inconsistencies between checklist, bug register, feature list, packets, reviews and git.")
    for e in errors:
        w(f"- ❌ **Error:** {e}")
    for x in warnings:
        w(f"- ⚠️ {x}")
    w("\n---\n**How this stays current:** every step completion = (1) update the step's Status in `UPGRADE_CHECKLIST.md` "
      "(⬜ → 🔨 Built → 🔍 In review → ✅ Done only with a `docs/reviews/<step>.md` APPROVE), (2) close the linked bugs in `BUG_REGISTER.md`, "
      "(3) run `python3 scripts/progress/build_progress.py` (regenerate) and `--check` (validate), (4) commit all three files together. "
      "The optional git hook (`scripts/progress/install_hook.sh`) blocks commits when `--check` fails.")
    if not args.check or args.write:
        OUT.write_text("\n".join(L) + "\n", encoding="utf-8")
    print(f"PROGRESS.md {'written' if (not args.check or args.write) else 'checked (not written)'}: {weighted*100:.0f}% | {counts} | errors={len(errors)} warnings={len(warnings)}")
    for e in errors:
        print("ERROR:", e)
    if args.check and errors:
        sys.exit(1)


if __name__ == "__main__":
    main()
