# Yukti AI — Live Application Links

## 1. Local Cloudtop Single-Origin URL (Recommended for Microphone & Voice)
- **URL:** [http://localhost:3200](http://localhost:3200)
- **Status:** Running in production mode (`node server.js` on `:3200` proxying `/api/*` and `/ws/live` to `uvicorn app.main:app` on `:8095`).

## 2. Google Cloud Run Deployment (`ongc-hr-finance-agent` · `asia-south1`)
- **Cloud Run Service URL:** `https://yukti-ai-89038075859.asia-south1.run.app`
- **Service Name / Revision:** `yukti-ai` (`yukti-ai-00001-wlt`)
- **Authenticated Local Proxy to Cloud Run (if Google Corp Org Policy requires IAM auth):**
  ```bash
  gcloud run services proxy yukti-ai --project ongc-hr-finance-agent --region asia-south1 --port 8080
  ```
