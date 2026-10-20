import json
import os
import sys
from google.auth import default
from google.cloud import bigquery, discoveryengine_v1 as discoveryengine

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

print("Harness successfully initialized in PROJECT_DIR.")
