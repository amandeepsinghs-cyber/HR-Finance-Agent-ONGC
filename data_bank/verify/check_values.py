from google.auth import default
from google.cloud import bigquery

credentials, _ = default(quota_project_id='ongc-hr-finance-agent')
bq_client = bigquery.Client(
    project='ongc-hr-finance-agent',
    credentials=credentials,
    location='asia-south1',
    default_query_job_config=bigquery.QueryJobConfig(labels={'datacloud': 'ai-agent'})
)

queries = {
    "cadre": "SELECT DISTINCT cadre FROM hrfin_gold.mart_workforce",
    "entry_mode": "SELECT DISTINCT entry_mode FROM hrfin_gold.mart_workforce",
    "leave_type": "SELECT DISTINCT leave_type FROM hrfin_gold.mart_payroll_benefits",
    "case_type": "SELECT DISTINCT case_type FROM hrfin_gold.mart_employee_relations",
    "rel_status": "SELECT DISTINCT status FROM hrfin_gold.mart_employee_relations",
    "dpc_status": "SELECT DISTINCT dpc_status FROM hrfin_gold.mart_promotions_dpc",
    "vigilance_cleared": "SELECT vigilance_cleared, count(*) FROM hrfin_gold.mart_promotions_dpc GROUP BY 1",
    "service_cat": "SELECT DISTINCT service_category FROM hrfin_gold.mart_contract_workforce LIMIT 10",
    "vendor_cat": "SELECT DISTINCT vendor_category FROM hrfin_gold.mart_procurement_contracts",
    "corp_fy": "SELECT DISTINCT fiscal_year FROM hrfin_gold.mart_corporate_performance",
    "corp_aging": "SELECT aging_bucket, count(*) FROM hrfin_gold.mart_corporate_performance WHERE aging_days IS NOT NULL GROUP BY 1",
    "receivables_aging": "SELECT aging_bucket, count(*) FROM hrfin_silver.receivables GROUP BY 1",
    "cost_overrun_pct": "SELECT cost_overrun_pct, count(*) FROM hrfin_gold.mart_capex_projects WHERE cost_overrun_pct > 0 GROUP BY 1 LIMIT 5",
    "incident_type": "SELECT DISTINCT incident_type FROM hrfin_gold.mart_hse_incident",
    "severity_tier": "SELECT DISTINCT severity_tier FROM hrfin_gold.mart_hse_incident",
    "subsidiary_entities": "SELECT DISTINCT entity_name FROM hrfin_silver.subsidiary_financials",
    "customer_oil_rev": "SELECT column_name FROM hrfin_silver.INFORMATION_SCHEMA.COLUMNS WHERE table_name = 'receivables'"
}

for k, q in queries.items():
    try:
        rows = list(bq_client.query(q).result())
        print(f"=== {k} ===")
        print([dict(r) for r in rows[:6]])
    except Exception as e:
        print(f"=== {k} ERROR: {e} ===")
