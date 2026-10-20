from google.auth import default
from google.cloud import bigquery

credentials, _ = default(quota_project_id='ongc-hr-finance-agent')
bq_client = bigquery.Client(
    project='ongc-hr-finance-agent',
    credentials=credentials,
    location='asia-south1',
    default_query_job_config=bigquery.QueryJobConfig(labels={'datacloud': 'ai-agent'})
)

for t in ['travel_claims', 'rti_applications', 'subsidiary_financials', 'corporate_financials', 'receivables', 'forex_hedges']:
    cols = [r.column_name for r in bq_client.query(f"SELECT column_name FROM hrfin_silver.INFORMATION_SCHEMA.COLUMNS WHERE table_name = '{t}'").result()]
    print(f"{t}: {', '.join(cols[:10])}")
