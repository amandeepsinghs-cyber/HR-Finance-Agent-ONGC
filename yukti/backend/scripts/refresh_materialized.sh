#!/usr/bin/env bash
# scripts/refresh_materialized.sh
# Refreshes the 4 approved materialized summary tables in hrfin_gold with mandatory label datacloud:ai-agent.

set -euo pipefail

PROJECT_ID="ongc-hr-finance-agent"
LOCATION="asia-south1"
DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
SQL_DIR="$DIR/sql/materialize"

echo "================================================================="
echo "Refreshing Yukti AI Materialized Summary Tables in hrfin_gold..."
echo "Project: $PROJECT_ID | Location: $LOCATION | Label: datacloud=ai-agent"
echo "================================================================="

export CLOUDSDK_METRICS_ENVIRONMENT="${CLOUDSDK_METRICS_ENVIRONMENT:+$CLOUDSDK_METRICS_ENVIRONMENT }datacloud.ai-agent"

for sql_file in "$SQL_DIR"/*.sql; do
    echo "Executing $sql_file..."
    bq query \
        --project_id="$PROJECT_ID" \
        --location="$LOCATION" \
        --use_legacy_sql=false \
        --label="datacloud:ai-agent" \
        < "$sql_file"
    echo "✓ Finished $(basename "$sql_file")"
done

echo "================================================================="
echo "All 4 Materialized Summary Tables refreshed successfully."
echo "================================================================="
