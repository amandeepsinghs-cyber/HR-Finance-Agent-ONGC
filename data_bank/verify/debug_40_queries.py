from google.auth import default
from google.cloud import bigquery
import json

credentials, _ = default(quota_project_id='ongc-hr-finance-agent')
bq_client = bigquery.Client(
    project='ongc-hr-finance-agent',
    credentials=credentials,
    location='asia-south1',
    default_query_job_config=bigquery.QueryJobConfig(labels={'datacloud': 'ai-agent'})
)

with open('verify/stress_test_executed_results.json') as f:
    data = json.load(f)

print("--- Inspecting distinct metadata for failed queries ---")

def run(label, sql):
    try:
        rows = list(bq_client.query(sql).result())
        print(f"[{label}] Rows: {len(rows)}")
        if rows:
            print("  Sample:", dict(rows[0]))
    except Exception as e:
        print(f"[{label}] ERROR: {e}")

# Check 1: P_01_1 (mart_field_economics onshore_offshore casing)
run("P_01_1 test", "SELECT field_name, asset_name, AVG(water_cut_pct) FROM hrfin_gold.mart_field_economics WHERE fiscal_year = 'FY26' AND LOWER(onshore_offshore) = 'onshore' GROUP BY 1, 2 LIMIT 3")

# Check 2: P_02_3 (mart_production_reserves onshore_offshore)
run("P_02_3 test", "SELECT asset_name, SUM(total_liquids_production_mt) FROM hrfin_gold.mart_production_reserves WHERE fiscal_year = 'FY26' AND LOWER(onshore_offshore) = 'offshore' GROUP BY 1 LIMIT 3")

# Check 3: P_04_2 (well_type in FY26)
run("P_04_2 test", "SELECT result_status, COUNT(*) FROM hrfin_gold.mart_production_reserves WHERE fiscal_year = 'FY26' GROUP BY 1")

# Check 4: P_06_1 (subsurface discipline in workforce)
run("P_06_1 test", "SELECT discipline_name, count(*) FROM hrfin_gold.mart_workforce WHERE is_near_retirement_2yr = TRUE GROUP BY 1 LIMIT 5")

# Check 5: P_07_1 (hse_incident severity & onshore)
run("P_07_1 test", "SELECT wc_name, count(*) FROM hrfin_gold.mart_hse_incident WHERE fiscal_year = 'FY26' AND LOWER(onshore_offshore) = 'onshore' GROUP BY 1 LIMIT 3")

# Check 6: P_10_2 (hard_station_cat)
run("P_10_2 test", "SELECT hard_station_cat, count(*) FROM hrfin_gold.mart_workforce WHERE hard_station_cat IS NOT NULL GROUP BY 1")

# Check 7: P_12_1 (payroll_benefits sector values)
run("P_12_1 test", "SELECT DISTINCT sector FROM hrfin_gold.mart_payroll_benefits WHERE fiscal_year = 'FY26'")

# Check 8: P_17_3 (field_economics columns)
run("P_17_3 test", "SELECT column_name FROM hrfin_gold.INFORMATION_SCHEMA.COLUMNS WHERE table_name = 'mart_field_economics' AND column_name LIKE '%matur%'")

# Check 9: P_24_1 (mart_corporate_performance oil sales)
run("P_24_1 test", "SELECT column_name FROM hrfin_gold.INFORMATION_SCHEMA.COLUMNS WHERE table_name = 'mart_corporate_performance' AND column_name LIKE '%rev%'")

# Check 10: P_33_1 (icc_committees schema)
run("P_33_1 test", "SELECT column_name FROM hrfin_silver.INFORMATION_SCHEMA.COLUMNS WHERE table_name = 'icc_committees'")

