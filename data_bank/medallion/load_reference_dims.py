#!/usr/bin/env python3
"""medallion/load_reference_dims.py: Load YAML reference datasets and generated calendar into hrfin_silver.

Tables loaded:
1. hrfin_silver.dim_work_centre (from world_bible/reference/work_centres.yaml)
2. hrfin_silver.dim_grade (from world_bible/reference/grades.yaml)
3. hrfin_silver.dim_discipline (from world_bible/reference/disciplines.yaml)
4. hrfin_silver.dim_field (from world_bible/reference/fields.yaml)
5. hrfin_silver.dim_project (from world_bible/reference/projects.yaml)
6. hrfin_silver.dim_cost_centre (from world_bible/reference/cost_centres.yaml)
7. hrfin_silver.dim_customer (from world_bible/reference/customers.yaml)
8. hrfin_silver.dim_vendor (from world_bible/reference/vendors.yaml)
9. hrfin_silver.dim_geography (from world_bible/reference/geography.yaml)
10. hrfin_silver.dim_price_fx (from world_bible/reference/prices_fx.yaml)
11. hrfin_silver.dim_calendar (generated 2000-04-01 to 2030-03-31)
"""

from __future__ import annotations

import datetime
from pathlib import Path
from typing import Any, Dict, List

import pandas as pd
import yaml
from google.cloud import bigquery

PROJECT_ID = "ongc-hr-finance-agent"
DATASET_ID = "hrfin_silver"
BASE_DIR = Path(__file__).resolve().parent.parent
REF_DIR = BASE_DIR / "world_bible" / "reference"

JOB_LABELS = {"datacloud": "ai-agent"}


def load_yaml(filename: str) -> Any:
    with open(REF_DIR / filename, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def build_work_centres() -> List[Dict[str, Any]]:
    data = load_yaml("work_centres.yaml")["work_centres"]
    records = []
    for r in data:
        records.append({
            "wc_id": str(r["wc_id"]),
            "name": str(r["name"]),
            "short_name": str(r.get("short_name", r["name"])),
            "type": str(r["type"]),
            "director_owner": str(r["director_owner"]),
            "city": str(r["city"]),
            "state": str(r["state"]),
            "state_code": str(r["state_code"]),
            "sector": str(r["sector"]),
            "cluster_id": str(r["cluster_id"]),
            "cluster_name": str(r["cluster_name"]),
            "hard_station_cat": str(r["hard_station_cat"]),
            "onshore_offshore": str(r["onshore_offshore"]),
            "is_corporate_hq": bool(r.get("is_corporate_hq", False)),
            "aliases": [str(a) for a in r.get("aliases", [])],
        })
    return records


def build_grades() -> List[Dict[str, Any]]:
    data = load_yaml("grades.yaml")["grades"]
    records = []
    for r in data:
        gid = str(r["grade_id"])
        cadre = str(r["cadre"])
        grp = str(r.get("group", "Group A"))
        if gid in ["CMD", "DIR", "E8", "E9"]:
            travel_class = "Business_Air"
            lodging = 10000.0
        elif gid in ["E4", "E5", "E6", "E7"]:
            travel_class = "Economy_Air"
            lodging = 6500.0
        elif gid in ["E0", "E1", "E2", "E3"]:
            travel_class = "Economy_Air"
            lodging = 4500.0
        elif gid == "GRP-B":
            travel_class = "AC_First_Class"
            lodging = 3500.0
        elif gid == "GRP-C":
            travel_class = "AC_2_Tier"
            lodging = 2500.0
        else:
            travel_class = "AC_2_Tier"
            lodging = 2000.0

        records.append({
            "grade_id": gid,
            "cadre": cadre,
            "group": grp,
            "designation": str(r["designation"]),
            "pay_scale_min_inr": float(r["pay_scale_min_inr"]),
            "pay_scale_max_inr": float(r["pay_scale_max_inr"]),
            "scale_type": str(r.get("scale_type", "DPE-3rd-PRC")),
            "scale_source": str(r.get("scale_source", "DPE Guidelines")),
            "promotion_mode": str(r.get("promotion_mode", "merit")),
            "typical_residency_years": int(r.get("typical_residency_years", 3)),
            "dpc_evaluation_type": str(r.get("dpc_evaluation_type", "Merit Evaluation")),
            "level_order": int(r.get("level_order", 1)),
            "ta_da_travel_class": travel_class,
            "daily_lodging_limit_cat_a_inr": lodging,
        })
    return records


def build_disciplines() -> List[Dict[str, Any]]:
    data = load_yaml("disciplines.yaml")["disciplines"]
    records = []
    for r in data:
        records.append({
            "discipline_id": str(r["discipline_id"]),
            "code": str(r["code"]),
            "name": str(r["name"]),
            "function": str(r["function"]),
            "applicable_cadres": [str(c) for c in r.get("applicable_cadres", ["executive", "non_executive"])],
            "description": str(r.get("description", r["name"])),
        })
    return records


def build_fields() -> List[Dict[str, Any]]:
    data = load_yaml("fields.yaml")["fields"]
    records = []
    for r in data:
        records.append({
            "field_id": str(r["field_id"]),
            "name": str(r["name"]),
            "asset_wc_id": str(r["asset_wc_id"]),
            "basin": str(r["basin"]),
            "onshore_offshore": str(r["onshore_offshore"]),
            "discovery_year": int(r.get("discovery_year", 1974)),
            "hydrocarbon": str(r.get("hydrocarbon", "oil_and_gas")),
            "maturity": str(r.get("maturity", "mature")),
            "notes": str(r["notes"]) if r.get("notes") is not None else None,
            "aliases": [str(a) for a in r.get("aliases", [])],
        })
    return records


def build_projects() -> List[Dict[str, Any]]:
    data = load_yaml("projects.yaml")["projects"]
    records = []
    for r in data:
        s_date = str(r["start_date"])[:10]
        p_date = str(r["planned_completion"])[:10]
        a_date = str(r.get("actual_or_revised_completion", p_date))[:10]
        records.append({
            "prj_id": str(r["prj_id"]),
            "name": str(r["name"]),
            "sanctioned_cost_inr_cr": float(r.get("sanctioned_cost_inr_cr", r.get("sanctioned_cost_cr", 1000.0))),
            "start_date": s_date,
            "planned_completion": p_date,
            "actual_or_revised_completion": a_date,
            "asset_wc_id": str(r.get("asset_wc_id", "WC-DEL")),
            "director_owner": str(r.get("director_owner", "Director (Production)")),
            "category": str(r.get("category", "Development")),
            "status": str(r.get("status", "ongoing")),
            "notes": str(r["notes"]) if r.get("notes") is not None else None,
        })
    return records


def build_cost_centres() -> List[Dict[str, Any]]:
    data = load_yaml("cost_centres.yaml")["cost_centres"]
    records = []
    for r in data:
        records.append({
            "cost_centre_id": str(r["cost_centre_id"]),
            "wc_id": str(r["wc_id"]),
            "field_id": str(r["field_id"]) if r.get("field_id") else None,
            "name": str(r["name"]),
            "cost_centre_type": str(r.get("cost_centre_type", "Operational")),
            "hierarchy_area": str(r.get("hierarchy_area", "Production")),
            "profit_centre_id": str(r["profit_centre_id"]) if r.get("profit_centre_id") else None,
        })
    return records


def build_customers() -> List[Dict[str, Any]]:
    data = load_yaml("customers.yaml")["customers"]
    state_code_map = {
        "Delhi": "DL", "Gujarat": "GJ", "Maharashtra": "MH", "Assam": "AS",
        "Tamil Nadu": "TN", "Andhra Pradesh": "AP", "Uttar Pradesh": "UP",
        "West Bengal": "WB", "Tripura": "TR", "Rajasthan": "RJ", "Karnataka": "KA",
        "Odisha": "OD", "Kerala": "KL", "Goa": "GA", "Haryana": "HR"
    }
    records = []
    for r in data:
        st = r.get("state", "Delhi")
        records.append({
            "customer_id": str(r["customer_id"]),
            "name": str(r["name"]),
            "short_name": str(r.get("short_name", r["name"])),
            "type": str(r.get("type", "PSU")),
            "key_products": [str(p) for p in r.get("key_products", ["Crude Oil"])],
            "headquarters_city": str(r.get("headquarters_city", "New Delhi")),
            "state": str(st),
            "state_code": state_code_map.get(st, "DL"),
            "notes": str(r["notes"]) if r.get("notes") is not None else None,
        })
    return records


def build_vendors() -> List[Dict[str, Any]]:
    data = load_yaml("vendors.yaml")["vendors"]
    records = []
    for r in data:
        records.append({
            "vendor_id": str(r["vendor_id"]),
            "name": str(r["name"]),
            "category": str(r["category"]),
            "state": str(r["state"]),
            "state_code": str(r["state_code"]),
            "mse_flag": bool(r.get("mse_flag", False)),
            "gstin": str(r["gstin"]),
            "pan": str(r["pan"]),
        })
    return records


def build_geography() -> List[Dict[str, Any]]:
    data = load_yaml("geography.yaml")["states"]
    records = []
    for r in data:
        districts = r.get("districts", [])
        has_asp = any(d.get("is_aspirational", False) for d in districts)
        ongc_pres = any(d.get("ongc_presence", False) for d in districts)
        records.append({
            "state_code": str(r["state_code"]),
            "state_name": str(r["state_name"]),
            "capital": str(r["capital"]),
            "region_sector": str(r["region_sector"]),
            "districts_count": len(districts),
            "has_aspirational_districts": has_asp,
            "ongc_operational_presence": ongc_pres,
        })
    return records


def build_price_fx() -> List[Dict[str, Any]]:
    data = load_yaml("prices_fx.yaml")["prices_fx"]
    records = []
    for r in data:
        non_apm = r.get("non_apm_deepwater_gas_price_usd_mmbtu")
        records.append({
            "month": str(r["month"]),
            "fiscal_year": str(r["fiscal_year"]),
            "brent_usd_bbl": float(r["brent_usd_bbl"]),
            "ongc_crude_net_realisation_usd_bbl": float(r["ongc_crude_net_realisation_usd_bbl"]),
            "ongc_crude_net_realisation_inr_bbl": float(r["ongc_crude_net_realisation_inr_bbl"]),
            "apm_gas_price_usd_mmbtu": float(r["apm_gas_price_usd_mmbtu"]),
            "non_apm_deepwater_gas_price_usd_mmbtu": float(non_apm) if non_apm is not None and str(non_apm).strip() != "" else None,
            "inr_usd_fx_rate": float(r["inr_usd_fx_rate"]),
            "da_percentage": float(r["da_percentage"]),
            "windfall_tax_saed_usd_bbl": float(r.get("windfall_tax_saed_usd_bbl", 0.0)),
            "windfall_tax_saed_inr_bbl": float(r.get("windfall_tax_saed_inr_bbl", 0.0)),
            "cess_per_barrel_usd": float(r.get("cess_per_barrel_usd", 0.0)),
            "royalty_per_barrel_usd": float(r.get("royalty_per_barrel_usd", 0.0)),
            "anchor_source": str(r.get("anchor_source", "PPAC / DPE OM")),
        })
    return records


def build_calendar() -> List[Dict[str, Any]]:
    start_date = datetime.date(2000, 4, 1)
    end_date = datetime.date(2030, 3, 31)
    delta = datetime.timedelta(days=1)
    cur = start_date

    records = []
    while cur <= end_date:
        month = cur.month
        year = cur.year

        # Indian Fiscal Year: Apr-Mar
        if month >= 4:
            fy_num = year % 100 + 1
            f_quarter = f"Q{(month - 4) // 3 + 1}"
            f_month_seq = month - 3
        else:
            fy_num = year % 100
            f_quarter = f"Q{(month + 8) // 3 + 1}"
            f_month_seq = month + 9
        fy_str = f"FY{fy_num:02d}"

        is_wknd = cur.weekday() in (5, 6)
        # Standard national holidays in India
        is_hol = (cur.month, cur.day) in [
            (1, 26),  # Republic Day
            (8, 15),  # Independence Day
            (10, 2),  # Gandhi Jayanti
            (5, 1),   # May Day
            (12, 25), # Christmas
        ]

        records.append({
            "date": cur.isoformat(),
            "fiscal_year": fy_str,
            "fiscal_quarter": f_quarter,
            "fiscal_month_num": f_month_seq,
            "calendar_year": year,
            "calendar_month_num": month,
            "month_name": cur.strftime("%B"),
            "year_month": cur.strftime("%Y-%m"),
            "day_of_week": cur.strftime("%A"),
            "is_weekend": is_wknd,
            "is_holiday": is_hol,
        })
        cur += delta
    return records


def get_table_schema(table_name: str) -> List[bigquery.SchemaField]:
    with open(BASE_DIR / "world_bible" / "schema_silver.yaml", "r", encoding="utf-8") as f:
        schema_yaml = yaml.safe_load(f)
    for t in schema_yaml["tables"]:
        if t["table_name"] == table_name:
            fields = []
            for c in t["columns"]:
                cname = c["name"]
                ctype = c["type"]
                nullable = c.get("nullable", True)
                if ctype == "ARRAY<STRING>":
                    fields.append(bigquery.SchemaField(cname, "STRING", mode="REPEATED"))
                else:
                    fields.append(bigquery.SchemaField(cname, ctype, mode="NULLABLE" if nullable else "REQUIRED"))
            return fields
    return []


def build_grade_pay_scales() -> List[Dict[str, Any]]:
    grades_data = load_yaml("grades.yaml")["grades"]
    rules_data = load_yaml("allowance_rules.yaml")
    scales_2017 = rules_data.get("pay_scales_2017", {})
    scales_2007 = rules_data.get("pay_scales_2007", {})
    records: List[Dict[str, Any]] = []
    for g in grades_data:
        gid = str(g["grade_id"])
        s17 = scales_2017.get(gid, {})
        records.append({
            "grade_id": gid,
            "scale_version": "2017",
            "pay_scale_min_inr": float(s17.get("min_inr", g["pay_scale_min_inr"])),
            "pay_scale_max_inr": float(s17.get("max_inr", g["pay_scale_max_inr"])),
            "increment_pct": 3.0,
            "prp_ceiling_pct_bp": float(s17.get("prp_ceiling_pct", 40.0)),
            "source": str(s17.get("source_doc", g.get("scale_source", "DPE OM 3-Aug-2017"))),
        })
        if gid in scales_2007:
            s07 = scales_2007[gid]
            records.append({
                "grade_id": gid,
                "scale_version": "2007",
                "pay_scale_min_inr": float(s07["min_inr"]),
                "pay_scale_max_inr": float(s07["max_inr"]),
                "increment_pct": 3.0,
                "prp_ceiling_pct_bp": float(s17.get("prp_ceiling_pct", 40.0)),
                "source": "DPE OM 3-Aug-2017 Annex I (2007 scale)",
            })
    return records


def build_ida_rates() -> List[Dict[str, Any]]:
    data = load_yaml("ida_rates.yaml")["ida_rates"]
    records: List[Dict[str, Any]] = []
    for r in data:
        records.append({
            "effective_date": str(r["effective_date"]),
            "scale_version": str(r["scale_version"]),
            "ida_pct": float(r["ida_pct"]),
            "status": str(r.get("status", "real")),
            "source_doc": str(r.get("source_doc", "DPE OM")),
        })
    return records


def build_hra_rates() -> List[Dict[str, Any]]:
    data = load_yaml("hra_rates.yaml")["hra_rates"]
    records: List[Dict[str, Any]] = []
    for r in data:
        records.append({
            "city_class": str(r["city_class"]),
            "population_band": str(r["population_band"]),
            "hra_pct_ida_lt_25": float(r["hra_pct_ida_lt_25"]),
            "hra_pct_ida_25_to_50": float(r["hra_pct_ida_25_to_50"]),
            "hra_pct_ida_ge_50": float(r["hra_pct_ida_ge_50"]),
            "hrr_pct_bp": float(r["hrr_pct_bp"]),
            "status": str(r.get("status", "real")),
            "source_doc": str(r.get("source_doc", "DPE OM 4-Aug-2017")),
        })
    return records


def build_allowance_rules() -> List[Dict[str, Any]]:
    data = load_yaml("allowance_rules.yaml")["allowance_rules"]
    records: List[Dict[str, Any]] = []
    for r in data:
        cap = r.get("cap_pct_bp", r.get("cap_pct_bp_plus_da"))
        records.append({
            "allowance_id": str(r["allowance_code"]),
            "rule_desc": str(r["rule"]),
            "ceiling_pct_bp": float(cap) if cap is not None else None,
            "status": str(r.get("status", "real")),
            "source_doc": str(r.get("source_doc", "DPE Guidelines")),
        })
    return records


def build_payroll_policy_fy() -> List[Dict[str, Any]]:
    csv_path = BASE_DIR / "landing" / "sap" / "payroll_policy_fy.csv"
    df = pd.read_csv(csv_path)
    records: List[Dict[str, Any]] = []
    for _, row in df.iterrows():
        arr_month = row.get("arrears_month")
        notes_val = row.get("notes")
        records.append({
            "fiscal_year": str(row["fiscal_year"]),
            "da_q1_pct": float(row["da_q1_pct"]),
            "da_q2_pct": float(row["da_q2_pct"]),
            "da_q3_pct": float(row["da_q3_pct"]),
            "da_q4_pct": float(row["da_q4_pct"]),
            "da_fy_avg_pct": float(row["da_fy_avg_pct"]),
            "prp_pool_factor": float(row["prp_pool_factor"]),
            "increment_rate_pct": float(row["Increment_rate_pct"]),
            "arrears_factor": float(row["arrears_factor"]),
            "arrears_month": str(arr_month) if pd.notna(arr_month) and str(arr_month) != "None" else None,
            "prbs_rate_pct": float(row["prbs_rate_pct"]),
            "u_fy": float(row["u_fy"]),
            "k_fy": float(row["k_fy"]),
            "ot_fy": float(row["ot_fy"]),
            "residual_pool_pct": float(row["residual_pool_pct"]),
            "notes": str(notes_val) if pd.notna(notes_val) else None,
        })
    return records


def build_field_econ_targets_fy() -> List[Dict[str, Any]]:
    csv_path = REFERENCE_DIR / "real_targets" / "field_econ_targets_fy.csv"
    df = pd.read_csv(csv_path)
    records: List[Dict[str, Any]] = []
    for _, row in df.iterrows():
        records.append({
            "fiscal_year": str(row["fiscal_year"]),
            "line_code": str(row["line_code"]),
            "value": float(row["value"]),
            "unit": str(row["unit"]),
            "source_doc": str(row["source_doc"]),
            "source_page": int(row["source_page"]),
            "source_text_line": int(row["source_text_line"]),
            "verified": bool(row["verified"]),
        })
    return records


def load_hrfin_ref_dims(client: bigquery.Client | None = None) -> None:
    if client is None:
        client = bigquery.Client(project=PROJECT_ID)
    dataset_ref = f"{PROJECT_ID}.hrfin_ref"

    schema_grade = [
        bigquery.SchemaField("grade_id", "STRING", mode="REQUIRED"),
        bigquery.SchemaField("scale_version", "STRING", mode="REQUIRED"),
        bigquery.SchemaField("pay_scale_min_inr", "NUMERIC"),
        bigquery.SchemaField("pay_scale_max_inr", "NUMERIC"),
        bigquery.SchemaField("increment_pct", "NUMERIC"),
        bigquery.SchemaField("prp_ceiling_pct_bp", "NUMERIC"),
        bigquery.SchemaField("source", "STRING"),
    ]

    schema_ida = [
        bigquery.SchemaField("effective_date", "DATE", mode="REQUIRED"),
        bigquery.SchemaField("scale_version", "STRING", mode="REQUIRED"),
        bigquery.SchemaField("ida_pct", "NUMERIC"),
        bigquery.SchemaField("status", "STRING"),
        bigquery.SchemaField("source_doc", "STRING"),
    ]

    schema_hra = [
        bigquery.SchemaField("city_class", "STRING", mode="REQUIRED"),
        bigquery.SchemaField("population_band", "STRING"),
        bigquery.SchemaField("hra_pct_ida_lt_25", "NUMERIC"),
        bigquery.SchemaField("hra_pct_ida_25_to_50", "NUMERIC"),
        bigquery.SchemaField("hra_pct_ida_ge_50", "NUMERIC"),
        bigquery.SchemaField("hrr_pct_bp", "NUMERIC"),
        bigquery.SchemaField("status", "STRING"),
        bigquery.SchemaField("source_doc", "STRING"),
    ]

    schema_allowance = [
        bigquery.SchemaField("allowance_id", "STRING", mode="REQUIRED"),
        bigquery.SchemaField("rule_desc", "STRING"),
        bigquery.SchemaField("ceiling_pct_bp", "NUMERIC"),
        bigquery.SchemaField("status", "STRING"),
        bigquery.SchemaField("source_doc", "STRING"),
    ]

    schema_policy = [
        bigquery.SchemaField("fiscal_year", "STRING", mode="REQUIRED"),
        bigquery.SchemaField("da_q1_pct", "NUMERIC"),
        bigquery.SchemaField("da_q2_pct", "NUMERIC"),
        bigquery.SchemaField("da_q3_pct", "NUMERIC"),
        bigquery.SchemaField("da_q4_pct", "NUMERIC"),
        bigquery.SchemaField("da_fy_avg_pct", "NUMERIC"),
        bigquery.SchemaField("prp_pool_factor", "NUMERIC"),
        bigquery.SchemaField("increment_rate_pct", "NUMERIC"),
        bigquery.SchemaField("arrears_factor", "NUMERIC"),
        bigquery.SchemaField("arrears_month", "STRING"),
        bigquery.SchemaField("prbs_rate_pct", "NUMERIC"),
        bigquery.SchemaField("u_fy", "NUMERIC"),
        bigquery.SchemaField("k_fy", "NUMERIC"),
        bigquery.SchemaField("ot_fy", "NUMERIC"),
        bigquery.SchemaField("residual_pool_pct", "NUMERIC"),
        bigquery.SchemaField("notes", "STRING"),
    ]

    schema_fe_targets = [
        bigquery.SchemaField("fiscal_year", "STRING", mode="REQUIRED"),
        bigquery.SchemaField("line_code", "STRING", mode="REQUIRED"),
        bigquery.SchemaField("value", "NUMERIC"),
        bigquery.SchemaField("unit", "STRING"),
        bigquery.SchemaField("source_doc", "STRING"),
        bigquery.SchemaField("source_page", "INT64"),
        bigquery.SchemaField("source_text_line", "INT64"),
        bigquery.SchemaField("verified", "BOOL"),
    ]

    ref_tables_to_load = [
        ("dim_grade_pay_scale", build_grade_pay_scales(), schema_grade),
        ("dim_ida_rate", build_ida_rates(), schema_ida),
        ("dim_hra_rate", build_hra_rates(), schema_hra),
        ("dim_allowance_rule", build_allowance_rules(), schema_allowance),
        ("dim_payroll_policy_fy", build_payroll_policy_fy(), schema_policy),
        ("field_econ_targets_fy", build_field_econ_targets_fy(), schema_fe_targets),
    ]

    for tbl_name, rows, schema_fields in ref_tables_to_load:
        tbl_id = f"{dataset_ref}.{tbl_name}"
        print(f"Loading {tbl_name} ({len(rows)} rows) into {tbl_id}...")
        job_config = bigquery.LoadJobConfig(
            schema=schema_fields,
            write_disposition=bigquery.WriteDisposition.WRITE_TRUNCATE,
            labels=JOB_LABELS,
        )
        job = client.load_table_from_json(rows, tbl_id, job_config=job_config)
        job.result()
        print(f"  Successfully loaded {tbl_name} to {tbl_id}")


def main():
    client = bigquery.Client(project=PROJECT_ID)
    tables_to_load = [
        ("dim_work_centre", build_work_centres()),
        ("dim_grade", build_grades()),
        ("dim_discipline", build_disciplines()),
        ("dim_field", build_fields()),
        ("dim_project", build_projects()),
        ("dim_cost_centre", build_cost_centres()),
        ("dim_customer", build_customers()),
        ("dim_vendor", build_vendors()),
        ("dim_geography", build_geography()),
        ("dim_price_fx", build_price_fx()),
        ("dim_calendar", build_calendar()),
    ]

    for tbl_name, rows in tables_to_load:
        print(f"Loading {tbl_name} ({len(rows)} rows)...")
        tbl_id = f"{PROJECT_ID}.{DATASET_ID}.{tbl_name}"
        schema_fields = get_table_schema(tbl_name)
        job_config = bigquery.LoadJobConfig(
            schema=schema_fields if schema_fields else None,
            write_disposition=bigquery.WriteDisposition.WRITE_TRUNCATE,
            labels=JOB_LABELS,
        )
        job = client.load_table_from_json(rows, tbl_id, job_config=job_config)
        job.result()
        print(f"  Successfully loaded {tbl_name} to {tbl_id}")

    load_hrfin_ref_dims(client)


if __name__ == "__main__":
    main()
