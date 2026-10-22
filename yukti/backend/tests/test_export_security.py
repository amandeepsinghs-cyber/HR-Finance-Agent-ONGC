"""H1.3a: export path-traversal and download hardening."""
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.tools.export_tool import DocumentExporter


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

    c = TestClient(app)
    for bad in ["..", "%2e%2e", ".gitkeep", "exp_1_abc", "anything", "exp_1792656351753_b136f6", "exp_" + "a" * 32 + "/../x"]:
        r = c.get(f"/api/export/{bad}")
        assert r.status_code == 404, bad


def test_create_then_download_roundtrip() -> None:
    from app.main import app

    c = TestClient(app)
    r = c.post("/api/export", json={"format": "pdf", "title": "../../Board Note", "content": "Hello"})
    assert r.status_code == 200
    j = r.json()
    assert "/" not in j["filename"] and ".." not in j["filename"]
    d = c.get(f"/api/export/{j['export_id']}")
    assert d.status_code == 200
    assert d.headers["content-type"].startswith("application/pdf")


def test_export_ids_are_128_bit_and_extension_is_forced(tmp_path: Path) -> None:
    from app.main import app

    c = TestClient(app)
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
    r = TestClient(m.app).post("/api/export", json={"format": "pdf", "title": "t", "content": "x"})
    assert r.status_code == 500 and "/secret" not in r.text
