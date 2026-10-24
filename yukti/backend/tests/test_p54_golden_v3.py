from pathlib import Path
import subprocess
import sys
import yaml

BACKEND_DIR = Path(__file__).resolve().parents[1]
REPO_ROOT = BACKEND_DIR.parents[1]
GOLDEN_DIR = BACKEND_DIR / "eval" / "golden_v3"


def test_finance_cases_schema_and_coverage():
    cases = yaml.safe_load((GOLDEN_DIR / "cases_finance.yaml").read_text(encoding="utf-8"))
    by_id = {c["id"]: c for c in cases}
    for i in range(1, 53):
        cid = f"F{i:02d}"
        assert cid in by_id, f"Missing finance golden case {cid}"
        assert len(by_id[cid].get("phrasings", [])) >= 3, f"{cid} must have 3 phrasings"
    # Verify forbidden content assertions on F32 and F48
    assert "Mumbai High" in by_id["F32"]["expect"].get("forbidden_content", [])
    assert "only up to 2026" in by_id["F48"]["expect"].get("forbidden_content", [])


def test_hr_cases_schema_and_coverage():
    cases = yaml.safe_load((GOLDEN_DIR / "cases_hr.yaml").read_text(encoding="utf-8"))
    assert len(cases) == 15
    by_id = {c["id"]: c for c in cases}
    for i in range(1, 16):
        cid = f"H{i:02d}"
        assert cid in by_id, f"Missing HR golden case {cid}"
        assert len(by_id[cid].get("phrasings", [])) == 3, f"{cid} must have 3 phrasings"


def test_chains_v19_v20_v22_and_beh07():
    chains = yaml.safe_load((GOLDEN_DIR / "chains.yaml").read_text(encoding="utf-8"))
    by_id = {c["id"]: c for c in chains}
    for req_id in ("V19", "V20", "V22", "BEH-07.30", "BEH-07.35"):
        assert req_id in by_id, f"Missing chain {req_id}"
        assert by_id[req_id].get("fresh_session") is True
        assert len(by_id[req_id].get("steps", [])) >= 2


def test_voice_smoke_six_utterances():
    cases = yaml.safe_load((GOLDEN_DIR / "voice_smoke.yaml").read_text(encoding="utf-8"))
    assert len(cases) == 6
    for c in cases:
        exp = c.get("expect", {})
        assert exp.get("fragment_bubbles") == 0
        assert exp.get("verbatim_tts_match") is True


def test_legacy_stress_test_archived_and_offline_runner_passes():
    archived = REPO_ROOT / "docs" / "archive" / "v2_2026-10-22" / "run_30x4_stress_test.py"
    assert archived.exists(), "Legacy run_30x4_stress_test.py must be archived (SPEC-11 AC-07)"

    report_path = GOLDEN_DIR / "report.md"
    result = subprocess.run(
        [sys.executable, str(GOLDEN_DIR / "run_golden.py"), "--offline-subset", "--report", str(report_path)],
        cwd=str(BACKEND_DIR),
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, f"run_golden.py failed: {result.stderr}\n{result.stdout}"
    report = report_path.read_text(encoding="utf-8")
    assert "Release Gate Scorecard (`SPEC-11 §9`)" in report
    assert "Wrong number on any KPI line" in report
    assert "PASS" in report
