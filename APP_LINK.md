# Yukti AI — Live Application Links

## 1. Local Cloudtop Single-Origin Preview (Recommended for Review, Microphone & Voice)
- **Main Application URL (Port 3300):** [http://localhost:3300](http://localhost:3300)
- **Main Application URL (Port 3200):** [http://localhost:3200](http://localhost:3200)
- **Design System & Chart Showcase URL:** [http://localhost:3300/design-system](http://localhost:3300/design-system) (also on `:3200/design-system`)
- **Backend API & Health Check:** [http://localhost:8095/health](http://localhost:8095/health)
- **Status:** Running in production mode (`node server.js` on both `:3200` and `:3300` proxying `/api/*`, `/health`, and `/ws/live` with TLS/SNI + upstream abort support to `uvicorn app.main:app` on `:8095` with `YUKTI_PLANNER=1`).

## 2. Google Cloud Run Deployment (`ongc-hr-finance-agent` · `asia-south1`)
- **Cloud Run Service URL:** `https://yukti-ai-89038075859.asia-south1.run.app`
- **Service Name / Current Baseline Revision:** `yukti-ai` (`yukti-ai-00001-wlt` — ready for `H1.5b` redeploy upon final sponsor sign-off)
- **Authenticated Local Proxy to Cloud Run (when IAM Org Policy is active):**
  ```bash
  gcloud run services proxy yukti-ai --project ongc-hr-finance-agent --region asia-south1 --port 8080
  ```
- **Rollback Command (if needed after `H1.5b` redeploy):**
  ```bash
  gcloud run services update-traffic yukti-ai --project ongc-hr-finance-agent --region asia-south1 --to-revisions=yukti-ai-00001-wlt=100
  ```
