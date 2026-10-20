#!/usr/bin/env bash
# medallion/run_dataform.sh: Orchestrate Silver reference loading, Dataform compilation, and execution for Phase 4.3 & 4.4.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BASE_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
DF_DIR="$BASE_DIR/medallion/dataform"

echo "=========================================================="
echo " Starting ONGC Dataform Medallion Pipeline (Silver & Gold)"
echo " Project: ongc-hr-finance-agent | Location: asia-south1"
echo "=========================================================="

export PATH="$HOME/.local/bin:$PATH"
export CLOUDSDK_METRICS_ENVIRONMENT="${CLOUDSDK_METRICS_ENVIRONMENT:+$CLOUDSDK_METRICS_ENVIRONMENT }datacloud.ai-agent"

# 1. Load Reference Dimensions into hrfin_silver
echo "[1/4] Loading Reference Dimensions into hrfin_silver..."
cd "$BASE_DIR"
"$BASE_DIR/.venv/bin/python" medallion/load_reference_dims.py
echo "Reference dimensions loaded successfully."

# 2. Regenerate Dataform models & configurations
echo "[2/4] Generating Dataform project definitions..."
"$BASE_DIR/.venv/bin/python" medallion/generate_dataform_project.py

# 3. Compile Dataform project
echo "[3/4] Compiling Dataform project..."
cd "$DF_DIR"
dataform compile
echo "Dataform compilation successful."

# 4. Execute Dataform pipeline (Silver + Gold + Assertions)
echo "[4/4] Executing Dataform run..."
dataform run

echo "=========================================================="
echo " Dataform Medallion Pipeline Execution Complete!"
echo " All Silver tables, Gold marts, semantic views, and"
echo " assertions successfully created and verified."
echo "=========================================================="
