import pandas as pd
import numpy as np
import os

def export_landing_csv():
    # Paths
    ssot_path = "out/fact_financial_statement_line.parquet"
    out_dir = "../data_bank/landing/governance"
    out_csv = os.path.join(out_dir, "corporate_financial_summary.csv")
    out_prov = os.path.join(out_dir, "corporate_financial_summary.provenance.txt")

    # Load SSOT
    df = pd.read_parquet(ssot_path)
    
    # Filter to latest vintage only
    df = df[df["is_latest_vintage"] == True]

    # Target FYs
    fys = [f"FY{yy}" for yy in range(17, 27)]
    
    # Mapping dict: column_name -> (scope, line_code, use_value_col)
    # use_value_col: False means use value_inr_cr, True means use value
    mapping = {
        "gross_revenue_inr_cr": ("standalone", "PL.REV_OPS", False),
        "offshore_revenue_inr_cr": ("standalone", "SEG.REV.OFF", False),
        "onshore_revenue_inr_cr": ("standalone", "SEG.REV.ON", False),
        "statutory_levies_total_inr_cr": ("standalone", "LEVY.TOTAL", False),
        "royalty_inr_cr": ("standalone", "LEVY.ROYALTY", False),
        "oidb_cess_inr_cr": ("standalone", "LEVY.OIDB_CESS", False),
        "saed_windfall_tax_inr_cr": ("standalone", "LEVY.OTHER_SAED", False),
        "employee_cost_total_inr_cr": ("standalone", "OTH.EMP_EXPENDITURE", False),
        "operating_expenses_total_inr_cr": ("standalone", "PL.OPEX_10YR", False),
        "ebitda_inr_cr": ("standalone", "PL.PBIDT", False),
        "dda_inr_cr": ("standalone", "PL.DDA", False),
        "pbt_inr_cr": ("standalone", "PL.PBT", False),
        "pat_inr_cr": ("standalone", "PL.PAT", False),
        "total_capex_spent_inr_cr": ("standalone", "CAPEX.TOTAL", False),
        "dividend_per_share_inr": ("standalone", "RATIO.DPS", True),
        "total_dividend_payout_inr_cr": ("standalone", "OTH.DIVIDEND_DECLARED", False),
        "standalone_roce_pct": ("standalone", "RATIO.ROCE_INCL_EXC", True),
        "consolidated_pat_inr_cr": ("consolidated", "PL.PAT", False)
    }

    # Prepare data rows
    rows = []
    for fy in fys:
        row = {"fiscal_year": fy}
        
        # Populate mapped values
        for col, (scope, code, use_value) in mapping.items():
            match = df[(df["fiscal_year"] == fy) & (df["scope"] == scope) & (df["line_code"] == code)]
            if not match.empty:
                val = match.iloc[0]["value"] if use_value else match.iloc[0]["value_inr_cr"]
                row[col] = round(float(val), 2) if pd.notnull(val) else None
            else:
                row[col] = None
        
        # Compute derived values
        if row.get("total_dividend_payout_inr_cr") is not None and row.get("pat_inr_cr") and row["pat_inr_cr"] != 0:
            row["dividend_payout_ratio_pct"] = round((row["total_dividend_payout_inr_cr"] / row["pat_inr_cr"]) * 100, 2)
        else:
            row["dividend_payout_ratio_pct"] = None

        row["lifting_cost_average_usd_boe"] = None
        row["consolidated_roce_pct"] = None
        
        # Fill missing SAED as 0.0 like old CSV? The old CSV had 0.0 for FY17-FY22, FY26.
        if row.get("saed_windfall_tax_inr_cr") is None:
            row["saed_windfall_tax_inr_cr"] = 0.0

        rows.append(row)

    # Order of columns
    cols = [
        "fiscal_year", "gross_revenue_inr_cr", "offshore_revenue_inr_cr", "onshore_revenue_inr_cr",
        "statutory_levies_total_inr_cr", "royalty_inr_cr", "oidb_cess_inr_cr", "saed_windfall_tax_inr_cr",
        "employee_cost_total_inr_cr", "operating_expenses_total_inr_cr", "ebitda_inr_cr", "dda_inr_cr",
        "pbt_inr_cr", "pat_inr_cr", "total_capex_spent_inr_cr", "dividend_per_share_inr",
        "total_dividend_payout_inr_cr", "dividend_payout_ratio_pct", "lifting_cost_average_usd_boe",
        "standalone_roce_pct", "consolidated_pat_inr_cr", "consolidated_roce_pct"
    ]

    out_df = pd.DataFrame(rows, columns=cols)
    
    os.makedirs(out_dir, exist_ok=True)
    out_df.to_csv(out_csv, index=False)
    
    # Provenance file
    run_id = df.iloc[0]["extract_id"] if not df.empty else "unknown"
    import subprocess
    import datetime
    try:
        git_sha = subprocess.check_output(["git", "rev-parse", "HEAD"]).decode("utf-8").strip()
    except Exception:
        git_sha = "unknown"
    ts = datetime.datetime.now(datetime.UTC).isoformat() + "Z"
    with open(out_prov, "w") as f:
        f.write("Command: uv run financial_ssot/export_landing_csv.py\n")
        f.write("Git SHA: " + git_sha + "\n")
        f.write("Timestamp: " + ts + "\n")
        f.write("Source: fact_financial_statement_line snapshot run " + str(run_id) + "\n")

    print(f"Exported {out_csv} ({len(out_df)} rows)")

if __name__ == "__main__":
    export_landing_csv()
