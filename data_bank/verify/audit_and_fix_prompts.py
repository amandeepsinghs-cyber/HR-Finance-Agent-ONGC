import json
from google.auth import default
from google.cloud import bigquery, discoveryengine_v1 as discoveryengine
from decimal import Decimal

credentials, _ = default(quota_project_id='ongc-hr-finance-agent')
bq_client = bigquery.Client(
    project='ongc-hr-finance-agent',
    credentials=credentials,
    location='asia-south1',
    default_query_job_config=bigquery.QueryJobConfig(labels={'datacloud': 'ai-agent'})
)
search_client = discoveryengine.SearchServiceClient(credentials=credentials)
serving_config = search_client.serving_config_path(
    project='ongc-hr-finance-agent',
    location='global',
    data_store='hrfin-doc-search-store',
    serving_config='default_search',
)

with open('verify/stress_test_executed_results.json') as f:
    data = json.load(f)

results = data['results']

# Collect the 42 zero-row or error prompts
bad_prompts = []
for r in results:
    s = r.get('result_summary', '')
    if '0 rows' in s or 'Error' in s or 'error' in s:
        bad_prompts.append(r)

print(f"Total zero-row/error prompts to diagnose: {len(bad_prompts)}")
for bp in bad_prompts:
    print(f"ID: {bp['prompt_id']} | Text: {bp['text'][:50]} | Status: {bp['status']}")
