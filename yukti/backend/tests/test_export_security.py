"""H1.3a + P4.6 (SPEC-10 §4.7, §4.9, §4.10, §6 AC 6, 8, 9):
Export path-traversal, download hardening, 11-persona V19 RBAC matrix, cross-principal 403,
24h expiry, honest Sheets/Docs toasts (no `docs.google.com`), naming regex, and JSONL audit logging.
"""

from __future__ import annotations

import io
import json
from pathlib import Path
import time

import openpyxl
import pytest
from fastapi.testclient import TestClient

from app.export_audit import (
    NAMING_REGEX,
    get_artifact_record,
    read_export_audit_rows,
    register_turn_contract,
)
from app.tools.export_tool import DOCS_TOAST, SHEETS_TOAST, DocumentExporter

FIXTURES_DIR = Path(__file__).resolve().parent.parent.parent / "contracts" / "fixtures" / "export"

ALL_11_PERSONAS = {
    "CMD": {"emp_id": "EMP-000001", "display_name": "Arun Mehra", "designation": "CMD", "function": "EXEC", "grade": "CMD"},
    "DIR_HR": {"emp_id": "EMP-000002", "display_name": "Manish Deshpande", "designation": "Director (HR)", "function": "HR", "grade": "DIR"},
    "DIR_FIN": {"emp_id": "EMP-000003", "display_name": "Vivek Rao", "designation": "Director (Finance)", "function": "FIN", "grade": "DIR"},
    "E1_HR": {"emp_id": "EMP-100151", "display_name": "Dinesh Deshmukh", "designation": "HR Officer (E1)", "function": "HR", "grade": "E1"},
    "E2_HR": {"emp_id": "EMP-102451", "display_name": "Pooja Verma", "designation": "HR Executive (E2)", "function": "HR", "grade": "E2"},
    "E3_HR": {"emp_id": "EMP-100144", "display_name": "Pooja Pillai", "designation": "Senior HR Executive (E3)", "function": "HR", "grade": "E3"},
    "E4_HR": {"emp_id": "EMP-100178", "display_name": "Aarti Saikia", "designation": "Dy. Manager HR (E4)", "function": "HR", "grade": "E4"},
    "E1_FIN": {"emp_id": "EMP-100150", "display_name": "Ajay Deshmukh", "designation": "Accounts Officer (E1)", "function": "FIN", "grade": "E1"},
    "E2_FIN": {"emp_id": "EMP-100152", "display_name": "Praveen Nair", "designation": "Finance Executive (E2)", "function": "FIN", "grade": "E2"},
    "E3_FIN": {"emp_id": "EMP-100146", "display_name": "Asha Mishra", "designation": "Finance Officer (E3)", "function": "FIN", "grade": "E3"},
    "E4_FIN": {"emp_id": "EMP-100145", "display_name": "Santosh Banerjee", "designation": "Dy. Manager Finance (E4)", "function": "FIN", "grade": "E4"},
}


def _auth(persona: str = "CMD", monkeypatch: pytest.MonkeyPatch | None = None) -> dict:
    """P0.4: export routes require a signed session token."""
    from app import auth

    if persona not in auth.PERSONA_DIRECTORY and monkeypatch is not None:
        monkeypatch.setitem(auth.PERSONA_DIRECTORY, persona, ALL_11_PERSONAS[persona])
    return {"Authorization": f"Bearer {auth.issue_token(persona)}"}


@pytest.fixture()
def exporter(tmp_path: Path) -> DocumentExporter:
    return DocumentExporter(exports_dir=tmp_path / "exports")


@pytest.mark.parametrize(
    "name",
    ["../../etc/passwd", "/etc/passwd", "..\\..\\win.ini", "a/../../b.docx", ".bashrc", "", "....//....//x.pdf", "ok name (1).docx"],
)
def test_safe_path_never_escapes(exporter: DocumentExporter, name: str) -> None:
    p = exporter.safe_path(name, "docx")
    assert exporter.exports_dir.resolve() in p.parents
    assert not p.name.startswith(".")


def test_word_export_with_traversal_title_stays_inside(exporter: DocumentExporter) -> None:
    out = exporter.export_word("# hi", filename="../../escape.docx")
    assert out.parent == exporter.exports_dir.resolve()
    assert out.exists()


def test_download_rejects_non_minted_ids() -> None:
    from app.main import app

    c = TestClient(app, headers=_auth())
    for bad in ["..", "%2e%2e", ".gitkeep", "exp_1_abc", "anything", "exp_1792656351753_b136f6", "exp_" + "a" * 32 + "/../x"]:
        r = c.get(f"/api/export/{bad}")
        assert r.status_code == 404, bad


def test_create_then_download_roundtrip() -> None:
    from app.main import app

    c = TestClient(app, headers=_auth())
    r = c.post("/api/export", json={"format": "pdf", "title": "../../Board Note", "content": "Hello"})
    assert r.status_code == 200
    j = r.json()
    assert "/" not in j["filename"] and ".." not in j["filename"]
    assert NAMING_REGEX.fullmatch(j["filename"]), j["filename"]
    d = c.get(f"/api/export/{j['export_id']}")
    assert d.status_code == 200
    assert d.headers["content-type"].startswith("application/pdf")


def test_export_ids_are_128_bit_and_extension_is_forced(tmp_path: Path) -> None:
    from app.main import app

    c = TestClient(app, headers=_auth())
    j = c.post("/api/export", json={"format": "xlsx", "title": "t", "columns": ["a"], "rows": [{"a": 1}]}).json()
    assert len(j["export_id"]) == 4 + 32
    ex = DocumentExporter(exports_dir=tmp_path / "e")
    assert ex.export_word("# x", filename="x.pdf").suffix == ".docx"
    assert ex.export_xlsx(columns=["a"], rows=[{"a": 1}], filename="noext").suffix == ".xlsx"


def test_old_exports_are_swept(monkeypatch) -> None:
    import os, time
    import app.main as m

    import pathlib, tempfile

    tmp = pathlib.Path(tempfile.mkdtemp())
    monkeypatch.setattr(m, "EXPORTS_DIR", tmp)
    old = m.EXPORTS_DIR / "exp_old_file_for_sweep.pdf"
    old.write_bytes(b"x")
    os.utime(old, (time.time() - 7200, time.time() - 7200))
    m._sweep_old_exports()
    assert not old.exists()


def test_errors_do_not_leak_internals(monkeypatch) -> None:
    import app.main as m

    def boom(**_):
        raise ValueError("/secret/path/here")

    monkeypatch.setattr(m.exporter, "export_pdf", boom)
    r = TestClient(m.app, headers=_auth()).post("/api/export", json={"format": "pdf", "title": "t", "content": "x"})
    assert r.status_code == 500 and "/secret" not in r.text


# ------------------------------------------------------------------ P4.6 extensions (SPEC-10 §4.7, §4.9, §4.10)
@pytest.mark.parametrize("persona", list(ALL_11_PERSONAS.keys()))
def test_11_personas_v19_roster_export_rbac_and_audit(persona: str, monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    from app.main import app

    audit_file = tmp_path / "export_audit.jsonl"
    monkeypatch.setenv("YUKTI_EXPORT_AUDIT_LOG", str(audit_file))

    v19 = json.loads((FIXTURES_DIR / "v19_delhi_roster_synthetic.json").read_text(encoding="utf-8"))
    turn_id = f"turn_v19_{persona.lower()}"
    emp_id = ALL_11_PERSONAS[persona]["emp_id"]
    # Ensure auth directory has the persona with its canonical emp_id
    from app import auth

    monkeypatch.setitem(auth.PERSONA_DIRECTORY, persona, ALL_11_PERSONAS[persona])
    register_turn_contract(turn_id=turn_id, contract=v19, emp_id=emp_id, persona=persona, session_id=f"sess_{persona}")

    client = TestClient(app, headers=_auth(persona, monkeypatch))
    resp = client.post("/api/export", json={"turn_id": turn_id, "format": "xlsx"})
    assert resp.status_code == 200, (persona, resp.text)
    data = resp.json()
    artifact = data["artifact"]

    # Naming regex AC 9
    assert NAMING_REGEX.fullmatch(artifact["filename"]), artifact["filename"]
    stem = artifact["filename"].rsplit(".", 1)[0]
    assert len(stem) <= 80

    # Download file as creator principal
    dl = client.get(f"/api/export/{artifact['export_id']}")
    assert dl.status_code == 200
    wb = openpyxl.load_workbook(io.BytesIO(dl.content))
    ws = wb[wb.sheetnames[0]]
    hdrs = [ws.cell(row=4, column=c).value for c in range(1, ws.max_column + 1)]

    if persona in ("CMD", "DIR_HR"):
        assert artifact["masked"] is False
        assert not artifact["filename"].endswith("_aggregate.xlsx")
        assert "Name" in hdrs
        assert artifact["rows"] == 65
    else:
        # DIR_FIN and all 8 juniors (E1_HR..E4_HR, E1_FIN..E4_FIN) get aggregate xlsx with _aggregate suffix
        assert artifact["masked"] is True
        assert artifact["filename"].endswith("_aggregate.xlsx"), artifact["filename"]
        assert "Name" not in hdrs and "name" not in hdrs
        assert f"Aggregate view (access level: {persona})" in str(ws["A3"].value)
        if persona != "DIR_FIN":
            # Junior personas also have small cells (<5) suppressed
            vals = [ws.cell(row=r, column=2).value for r in range(5, ws.max_row + 1)]
            assert "<5" in vals

    # Every export writes 1 audit row (100%)
    audit_rows = read_export_audit_rows(audit_file)
    assert len(audit_rows) == 1
    ar = audit_rows[0]
    assert ar["persona"] == persona
    assert ar["emp_id"] == emp_id
    assert ar["turn_id"] == turn_id
    assert ar["format"] == "xlsx"
    assert ar["filename"] == artifact["filename"]
    assert ar["sha256"] == artifact["sha256"]
    assert ar["masked"] is artifact["masked"]


def test_cross_principal_turn_export_and_download_return_403_and_24h_expiry_returns_404(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    from app.main import app

    audit_file = tmp_path / "export_audit.jsonl"
    monkeypatch.setenv("YUKTI_EXPORT_AUDIT_LOG", str(audit_file))

    v19 = json.loads((FIXTURES_DIR / "v19_delhi_roster_synthetic.json").read_text(encoding="utf-8"))
    register_turn_contract(
        turn_id="turn_cmd_owned",
        contract=v19,
        emp_id="DEMO-CMD",
        persona="CMD",
        session_id="sess_cmd",
    )

    cmd_client = TestClient(app, headers=_auth("CMD"))
    e2_client = TestClient(app, headers=_auth("E2_HR"))

    # 1. E2_HR trying to export CMD's turn_id -> 403
    r_turn_403 = e2_client.post("/api/export", json={"turn_id": "turn_cmd_owned", "format": "xlsx"})
    assert r_turn_403.status_code == 403

    # 2. CMD creates an export -> 200; E2_HR trying to GET /api/export/{CMD's export_id} -> 403 (BEH-04.50)
    r_ok = cmd_client.post("/api/export", json={"turn_id": "turn_cmd_owned", "format": "xlsx"})
    assert r_ok.status_code == 200
    exp_id = r_ok.json()["export_id"]

    assert e2_client.get(f"/api/export/{exp_id}").status_code == 403
    assert e2_client.get(f"/api/download/{exp_id}").status_code == 403
    assert cmd_client.get(f"/api/export/{exp_id}").status_code == 200
    assert cmd_client.get(f"/api/download/{exp_id}").status_code == 200

    # 3. 24-hour expiry: expire the artifact record and verify GET returns 404
    rec = get_artifact_record(exp_id)
    assert rec is not None
    assert rec.expires_epoch - rec.created_epoch == pytest.approx(24 * 3600)
    rec.expires_epoch = time.time() - 10
    assert cmd_client.get(f"/api/export/{exp_id}").status_code == 404


def test_honest_sheets_and_docs_toast_and_zero_fake_google_urls(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    from app.main import app
    import app.tools.export_tool as et

    monkeypatch.setenv("YUKTI_EXPORT_AUDIT_LOG", str(tmp_path / "export_audit.jsonl"))
    client = TestClient(app, headers=_auth("CMD"))

    # Sheets -> downloads xlsx with SHEETS_TOAST, never docs.google.com
    r_sheets = client.post(
        "/api/export",
        json={"format": "sheets", "title": "P&L Statement", "columns": ["fy", "rev"], "rows": [{"fy": "FY26", "rev": 132508}]},
    )
    assert r_sheets.status_code == 200
    j_sheets = r_sheets.json()
    assert j_sheets["format"] == "xlsx"
    assert j_sheets["toast"] == SHEETS_TOAST
    assert "docs.google.com" not in json.dumps(j_sheets)
    assert j_sheets["url"].startswith("/api/export/exp_")

    # Docs -> downloads docx with DOCS_TOAST, never docs.google.com
    r_docs = client.post(
        "/api/export",
        json={"format": "docs", "title": "Board Note", "content": "# Heading\nBody text"},
    )
    assert r_docs.status_code == 200
    j_docs = r_docs.json()
    assert j_docs["format"] == "docx"
    assert j_docs["toast"] == DOCS_TOAST
    assert "docs.google.com" not in json.dumps(j_docs)
    assert j_docs["url"].startswith("/api/export/exp_")

    # Verify export_google_docs is deleted and no docs.google.com URL exists in export_tool.py
    assert not hasattr(et.DocumentExporter, "export_google_docs")
    src = Path(et.__file__).read_text(encoding="utf-8")
    assert "https://docs.google.com" not in src


def test_client_png_svg_audit_endpoint_and_naming_regex_all_formats(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    from app.main import app

    audit_file = tmp_path / "export_audit.jsonl"
    monkeypatch.setenv("YUKTI_EXPORT_AUDIT_LOG", str(audit_file))
    client = TestClient(app, headers=_auth("CMD"))

    for fmt in ("png", "svg"):
        r = client.post("/api/export/audit", json={"turn_id": "turn_waterfall_1", "format": fmt, "rows": 10})
        assert r.status_code == 200
        j = r.json()
        assert NAMING_REGEX.fullmatch(j["filename"]), j["filename"]

    rows = read_export_audit_rows(audit_file)
    assert len(rows) == 2
    assert [r["format"] for r in rows] == ["png", "svg"]
