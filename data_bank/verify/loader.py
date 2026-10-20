"""
loader.py — Discovers landing files, loads them into DuckDB as raw tables,
and creates silver-named VIEWS by applying schema_silver.yaml mappings.

Tolerant: skips tables whose landing files do not exist yet and reports
which are available.
"""

from __future__ import annotations

import os
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple

import duckdb
import pandas as pd
import yaml

DEFAULT_DB_PATH = Path(__file__).resolve().parent / "local.duckdb"
DEFAULT_SCHEMA_PATH = Path(__file__).resolve().parent.parent / "world_bible" / "schema_silver.yaml"
DEFAULT_REF_DIR = Path(__file__).resolve().parent.parent / "world_bible" / "reference"
DEFAULT_LANDING_DIR = Path(__file__).resolve().parent.parent / "landing"


@dataclass
class TableLoadStatus:
    table_name: str
    spec_id: str
    source_format: str
    source_file: Optional[str]
    status: str  # 'loaded', 'skipped', 'error'
    row_count: int = 0
    error_message: Optional[str] = None


@dataclass
class LoadReport:
    available_tables: List[str] = field(default_factory=list)
    skipped_tables: List[str] = field(default_factory=list)
    table_statuses: Dict[str, TableLoadStatus] = field(default_factory=dict)
    errors: List[str] = field(default_factory=list)

    @property
    def is_empty(self) -> bool:
        return len(self.available_tables) == 0


def get_duckdb_type(silver_type: str) -> str:
    """Map BigQuery/Silver type names to DuckDB SQL types."""
    st = silver_type.upper().strip()
    if st == "STRING":
        return "VARCHAR"
    elif st in ("INT64", "INTEGER"):
        return "BIGINT"
    elif st in ("NUMERIC", "FLOAT64", "DOUBLE"):
        return "DOUBLE"
    elif st == "DATE":
        return "DATE"
    elif st == "TIMESTAMP":
        return "TIMESTAMP"
    elif st in ("BOOL", "BOOLEAN"):
        return "BOOLEAN"
    elif "ARRAY" in st:
        return "VARCHAR[]"
    return "VARCHAR"


def setup_duckdb_macros(conn: duckdb.DuckDBPyConnection) -> None:
    """Register helper macros in DuckDB for SQL dialect compatibility."""
    conn.execute("CREATE SCHEMA IF NOT EXISTS hrfin_silver;")
    # Date difference compatibility
    try:
        conn.execute("""
            CREATE OR REPLACE MACRO date_diff(d1, d2, unit) AS
                datediff(unit, d2, d1);
        """)
    except Exception:
        pass


def discover_landing_file(source_table: str, table_name: str, landing_dir: Path) -> Optional[Path]:
    """
    Search landing_dir and subdirectories for source_table or table_name.
    Matches filename case-insensitively and handles common variations.
    """
    if not landing_dir.exists():
        return None

    candidates = {source_table.lower(), f"{table_name.lower()}.csv", f"{table_name.lower()}.xlsx"}
    
    # Check directly under landing_dir and all subdirectories
    for root, _, files in os.walk(landing_dir):
        for f in files:
            fl = f.lower()
            if fl in candidates or (source_table and fl == Path(source_table).name.lower()):
                return Path(root) / f

    return None


def generate_dim_calendar(conn: duckdb.DuckDBPyConnection) -> int:
    """Generate dim_calendar dimension table covering FY13 to FY28."""
    sql = """
    CREATE OR REPLACE TABLE main.raw_dim_calendar AS
    WITH dates AS (
        SELECT DATE '2012-04-01' + INTERVAL (i) DAY AS d
        FROM range(0, 5844) t(i) -- 16 years (FY13 to FY28)
    )
    SELECT
        d AS date,
        CASE
            WHEN EXTRACT(month FROM d) >= 4 THEN 'FY' || RIGHT(CAST(EXTRACT(year FROM d) + 1 AS VARCHAR), 2)
            ELSE 'FY' || RIGHT(CAST(EXTRACT(year FROM d) AS VARCHAR), 2)
        END AS fiscal_year,
        CASE
            WHEN EXTRACT(month FROM d) IN (4, 5, 6) THEN 'Q1'
            WHEN EXTRACT(month FROM d) IN (7, 8, 9) THEN 'Q2'
            WHEN EXTRACT(month FROM d) IN (10, 11, 12) THEN 'Q3'
            ELSE 'Q4'
        END AS fiscal_quarter,
        CASE
            WHEN EXTRACT(month FROM d) >= 4 THEN CAST(EXTRACT(month FROM d) - 3 AS BIGINT)
            ELSE CAST(EXTRACT(month FROM d) + 9 AS BIGINT)
        END AS fiscal_month_num,
        CAST(EXTRACT(year FROM d) AS BIGINT) AS calendar_year,
        CAST(EXTRACT(month FROM d) AS BIGINT) AS calendar_month_num,
        STRFTIME(d, '%B') AS month_name,
        STRFTIME(d, '%Y-%m') AS year_month,
        STRFTIME(d, '%A') AS day_of_week,
        CASE WHEN EXTRACT(dayofweek FROM d) IN (0, 6) THEN TRUE ELSE FALSE END AS is_weekend,
        FALSE AS is_holiday
    FROM dates;
    """
    conn.execute(sql)
    # Create views
    conn.execute("CREATE OR REPLACE VIEW main.dim_calendar AS SELECT * FROM main.raw_dim_calendar;")
    conn.execute("CREATE OR REPLACE VIEW main.silver_dim_calendar AS SELECT * FROM main.dim_calendar;")
    conn.execute("CREATE OR REPLACE VIEW hrfin_silver.dim_calendar AS SELECT * FROM main.dim_calendar;")
    row_count = conn.execute("SELECT COUNT(*) FROM main.dim_calendar").fetchone()[0]
    return row_count


def load_yaml_reference_table(
    conn: duckdb.DuckDBPyConnection,
    table_def: Dict[str, Any],
    ref_dir: Path,
) -> int:
    """Load a reference YAML file into DuckDB and create views."""
    tname = table_def["table_name"]
    src_table = table_def.get("source_table")
    if not src_table:
        return 0

    yaml_path = ref_dir / src_table
    if not yaml_path.exists():
        return 0

    with open(yaml_path, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f)

    # Extract list of records
    records = []
    if isinstance(data, list):
        records = data
    elif isinstance(data, dict):
        for k, v in data.items():
            if isinstance(v, list) and v:
                records = v
                break

    if not records:
        return 0

    # Handle special transformations for dim_geography if needed
    if tname == "dim_geography" and records and "districts" in records[0]:
        flat_records = []
        for r in records:
            dists = r.get("districts", [])
            flat_records.append({
                "state_code": r.get("state_code"),
                "state_name": r.get("state_name"),
                "capital": r.get("capital"),
                "region_sector": r.get("region_sector"),
                "districts_count": len(dists),
                "has_aspirational_districts": any(d.get("is_aspirational", False) for d in dists),
                "ongc_operational_presence": any(d.get("ongc_presence", False) for d in dists),
            })
        records = flat_records

    df = pd.DataFrame(records)
    conn.register(f"df_{tname}", df)
    conn.execute(f"CREATE OR REPLACE TABLE main.raw_{tname} AS SELECT * FROM df_{tname}")
    conn.unregister(f"df_{tname}")

    create_silver_view(conn, table_def, f"raw_{tname}")
    return len(df)


def create_silver_view(
    conn: duckdb.DuckDBPyConnection,
    table_def: Dict[str, Any],
    raw_table_name: str,
) -> None:
    """
    Create a clean silver view applying sap_field_map, type casting,
    and column renaming.
    """
    tname = table_def["table_name"]
    sap_map = table_def.get("sap_field_map") or {}
    columns_def = table_def.get("columns", [])

    # Get raw column names in DuckDB
    raw_cols = [r[0] for r in conn.execute(f"DESCRIBE main.{raw_table_name}").fetchall()]
    raw_cols_lower = {c.lower(): c for c in raw_cols}

    # Invert sap_map to map raw SAP name -> target silver name
    # Also check if raw already has silver names
    select_exprs = []
    for col_info in columns_def:
        col_name = col_info["name"]
        duck_type = get_duckdb_type(col_info.get("type", "STRING"))

        # Find raw column match
        raw_source_col = None
        # 1. Exact match on silver column name
        if col_name.lower() in raw_cols_lower:
            raw_source_col = raw_cols_lower[col_name.lower()]
        else:
            # 2. Check if a SAP field maps to this silver column
            for sap_k, silver_v in sap_map.items():
                if silver_v.lower() == col_name.lower() and sap_k.lower() in raw_cols_lower:
                    raw_source_col = raw_cols_lower[sap_k.lower()]
                    break

        if raw_source_col:
            select_exprs.append(f'TRY_CAST("{raw_source_col}" AS {duck_type}) AS "{col_name}"')
        else:
            # Column not in raw table: provide typed NULL
            select_exprs.append(f'CAST(NULL AS {duck_type}) AS "{col_name}"')

    select_clause = ",\n    ".join(select_exprs)
    sql = f"""
    CREATE OR REPLACE VIEW main.{tname} AS
    SELECT
    {select_clause}
    FROM main.{raw_table_name};
    """
    conn.execute(sql)
    conn.execute(f"CREATE OR REPLACE VIEW main.silver_{tname} AS SELECT * FROM main.{tname};")
    conn.execute(f"CREATE OR REPLACE VIEW hrfin_silver.{tname} AS SELECT * FROM main.{tname};")


def load_csv_landing_table(
    conn: duckdb.DuckDBPyConnection,
    table_def: Dict[str, Any],
    file_path: Path,
) -> int:
    """Load CSV landing file into raw table and create silver view."""
    tname = table_def["table_name"]
    raw_tbl = f"raw_{tname}"
    
    # Use DuckDB read_csv_auto
    conn.execute(f"""
        CREATE OR REPLACE TABLE main.{raw_tbl} AS
        SELECT * FROM read_csv_auto('{file_path.as_posix()}', all_varchar=true);
    """)
    create_silver_view(conn, table_def, raw_tbl)
    count = conn.execute(f"SELECT COUNT(*) FROM main.{tname}").fetchone()[0]
    return count


def load_xlsx_landing_table(
    conn: duckdb.DuckDBPyConnection,
    table_def: Dict[str, Any],
    file_path: Path,
) -> int:
    """Load Excel (.xlsx) landing file into raw table and create silver view, applying _parsing_specs.yaml if present."""
    tname = table_def["table_name"]
    raw_tbl = f"raw_{tname}"
    fname = file_path.name

    # Check for parsing specifications
    specs_file = file_path.parent / "_parsing_specs.yaml"
    parsing_spec = None
    if specs_file.exists():
        try:
            with open(specs_file, "r", encoding="utf-8") as f:
                specs_data = yaml.safe_load(f)
                parsing_spec = specs_data.get("workbooks", {}).get(fname)
        except Exception:
            parsing_spec = None

    excel_file = pd.ExcelFile(file_path)

    if parsing_spec:
        strat = parsing_spec.get("sheet_strategy", {})
        mode = strat.get("mode", "all_visible")
        exclude_sheets = set(strat.get("exclude_sheets", []))

        if mode == "named":
            sheets_to_read = [strat["sheet_name"]]
        elif mode == "all_visible":
            sheets_to_read = [s for s in excel_file.sheet_names if s not in exclude_sheets and not s.startswith("_")]
        else:
            sheets_to_read = [excel_file.sheet_names[0]]

        header_idx = parsing_spec.get("header_row", 1) - 1
        data_start_idx = parsing_spec.get("data_start_row", 2) - 1

        dfs = []
        for s in sheets_to_read:
            df_sheet = pd.read_excel(excel_file, sheet_name=s, header=header_idx)
            skip_count = data_start_idx - header_idx - 1
            if skip_count > 0:
                df_sheet = df_sheet.iloc[skip_count:].reset_index(drop=True)
            dfs.append(df_sheet)

        df = pd.concat(dfs, ignore_index=True) if len(dfs) > 1 else dfs[0]

        for dc in parsing_spec.get("drop_columns", []):
            if dc in df.columns:
                df = df.drop(columns=[dc])

        sub_filter = parsing_spec.get("subtotal_filter")
        if sub_filter:
            col = sub_filter["column"]
            patterns = "|".join(sub_filter["patterns"])
            df = df[~df[col].astype(str).str.contains(patterns, regex=True, na=False)]

        foot_filter = parsing_spec.get("footer_filter")
        if foot_filter:
            col = foot_filter["column"]
            patterns = "|".join(foot_filter["patterns"])
            df = df[~df[col].astype(str).str.contains(patterns, regex=True, na=False)]

        pk = parsing_spec.get("primary_key", [df.columns[0]])
        df = df.dropna(subset=pk).copy()

        # Clean string commas from numeric and integer columns
        clean_num_cols = set(parsing_spec.get("numeric_columns", {}).keys()) | set(parsing_spec.get("integer_columns", []))
        for col in clean_num_cols:
            if col in df.columns:
                df[col] = df[col].astype(str).str.replace(",", "", regex=False).str.strip()
    else:
        sheet_names = excel_file.sheet_names
        target_sheet = sheet_names[0]
        for s in sheet_names:
            if s.lower() == tname.lower() or s.lower() in tname.lower():
                target_sheet = s
                break
        df = pd.read_excel(excel_file, sheet_name=target_sheet)

    # Convert all columns to string for uniform raw ingestion
    df = df.astype(str)

    conn.register(f"df_{tname}", df)
    conn.execute(f"CREATE OR REPLACE TABLE main.{raw_tbl} AS SELECT * FROM df_{tname}")
    conn.unregister(f"df_{tname}")

    create_silver_view(conn, table_def, raw_tbl)
    count = conn.execute(f"SELECT COUNT(*) FROM main.{tname}").fetchone()[0]
    return count


def load_data(
    conn: Optional[duckdb.DuckDBPyConnection] = None,
    db_path: Optional[Path] = None,
    schema_path: Path = DEFAULT_SCHEMA_PATH,
    ref_dir: Path = DEFAULT_REF_DIR,
    landing_dir: Path = DEFAULT_LANDING_DIR,
    rebuild: bool = True,
) -> Tuple[duckdb.DuckDBPyConnection, LoadReport]:
    """
    Main loader function:
    1. Connects to DuckDB (rebuilding from scratch if rebuild=True).
    2. Loads available reference YAML tables.
    3. Generates dim_calendar.
    4. Discovers landing files (CSV, XLSX) and creates raw tables and silver views.
    5. Returns connection and structured LoadReport.
    """
    if landing_dir is None:
        landing_dir = DEFAULT_LANDING_DIR
    if ref_dir is None:
        ref_dir = DEFAULT_REF_DIR
    if schema_path is None:
        schema_path = DEFAULT_SCHEMA_PATH

    if conn is None:
        target_db = str(db_path) if db_path else str(DEFAULT_DB_PATH)
        if target_db != ":memory:":
            target_path = Path(target_db)
            if rebuild and target_path.exists():
                try:
                    target_path.unlink()
                except Exception:
                    pass
            target_path.parent.mkdir(parents=True, exist_ok=True)
        conn = duckdb.connect(target_db)

    setup_duckdb_macros(conn)

    report = LoadReport()

    if not schema_path.exists():
        report.errors.append(f"Schema file not found at {schema_path}")
        return conn, report

    with open(schema_path, "r", encoding="utf-8") as f:
        schema_data = yaml.safe_load(f)

    tables = schema_data.get("tables", [])

    for table_def in tables:
        tname = table_def["table_name"]
        spec_id = table_def.get("spec_id", "")
        src_fmt = (table_def.get("source_format") or "CSV").upper()
        src_table = table_def.get("source_table") or ""

        status = TableLoadStatus(
            table_name=tname,
            spec_id=spec_id,
            source_format=src_fmt,
            source_file=src_table,
            status="skipped",
        )

        try:
            if src_fmt == "GENERATED" and tname == "dim_calendar":
                count = generate_dim_calendar(conn)
                status.status = "loaded"
                status.row_count = count
                report.available_tables.append(tname)
            elif src_fmt == "YAML":
                count = load_yaml_reference_table(conn, table_def, ref_dir)
                if count > 0:
                    status.status = "loaded"
                    status.row_count = count
                    report.available_tables.append(tname)
                else:
                    report.skipped_tables.append(tname)
            elif src_fmt in ("CSV", "XLSX", "BIGQUERY"):
                file_found = discover_landing_file(src_table, tname, landing_dir)
                if file_found:
                    if file_found.suffix.lower() == ".xlsx":
                        count = load_xlsx_landing_table(conn, table_def, file_found)
                    else:
                        count = load_csv_landing_table(conn, table_def, file_found)
                    status.status = "loaded"
                    status.row_count = count
                    status.source_file = file_found.name
                    report.available_tables.append(tname)
                else:
                    report.skipped_tables.append(tname)
            else:
                report.skipped_tables.append(tname)
        except Exception as e:
            status.status = "error"
            status.error_message = str(e)
            report.errors.append(f"Error loading {tname}: {e}")
            report.skipped_tables.append(tname)

        report.table_statuses[tname] = status

    return conn, report


if __name__ == "__main__":
    conn, rep = load_data()
    print("=" * 60)
    print("DuckDB Loader Summary")
    print(f"Available tables: {len(rep.available_tables)}")
    print(f"Skipped tables:   {len(rep.skipped_tables)}")
    print(f"Errors:           {len(rep.errors)}")
    print("Available tables loaded:")
    for t in sorted(rep.available_tables):
        st = rep.table_statuses[t]
        print(f"  - {t:<28} ({st.spec_id:<4}): {st.row_count:>6} rows")
    if rep.skipped_tables:
        print(f"\nSkipped (pending generation): {len(rep.skipped_tables)} tables")
    print("=" * 60)
