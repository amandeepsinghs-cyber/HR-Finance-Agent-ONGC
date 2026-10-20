"""Environment and folder layout test for ONGC HR & Finance Data Bank (Step 0.1)."""

from pathlib import Path
import pytest

DATA_BANK_ROOT = Path(__file__).resolve().parent.parent

REQUIRED_DIRECTORIES = [
    "world_bible",
    "world_bible/reference",
    "generators",
    "generators/hr",
    "generators/ops",
    "generators/finance",
    "generators/governance",
    "generators/documents",
    "landing",
    "landing/sap",
    "landing/db_exports",
    "landing/excel",
    "landing/documents/native",
    "landing/documents/scanned",
    "medallion",
    "medallion/bronze",
    "medallion/silver",
    "medallion/gold",
    "answer_key",
    "answer_key/sql",
    "answer_key/expected",
    "tests",
    "reports",
    "reports/step_reports",
]

REQUIRED_IMPORTS = [
    "pandas",
    "numpy",
    "faker",
    "yaml",
    "openpyxl",
    "docx",
    "reportlab",
    "PIL",
    "pdf2image",
    "pytest",
    "google.cloud.bigquery",
    "google.cloud.storage",
    "pyarrow",
]


@pytest.mark.parametrize("dir_rel_path", REQUIRED_DIRECTORIES)
def test_directory_exists(dir_rel_path: str):
    target = DATA_BANK_ROOT / dir_rel_path
    assert target.exists(), f"Missing required directory: {target}"
    assert target.is_dir(), f"Path is not a directory: {target}"


@pytest.mark.parametrize("module_name", REQUIRED_IMPORTS)
def test_required_imports(module_name: str):
    import importlib
    mod = importlib.import_module(module_name)
    assert mod is not None, f"Failed importing {module_name}"


def test_faker_en_in_locale():
    from faker import Faker
    fake = Faker("en_IN")
    name = fake.name()
    assert isinstance(name, str) and len(name) > 0
