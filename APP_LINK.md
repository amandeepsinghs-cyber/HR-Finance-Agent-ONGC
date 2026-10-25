# Yukti AI — Live Application Links

_Last updated: 25-Oct-2026 (v3 release, P5.6)._

## 1. Cloud Run — v3 production (live)
- **Service URL:** https://yukti-ai-b6cmgrx7ka-el.a.run.app (alias: https://yukti-ai-89038075859.asia-south1.run.app)
- **Live revision:** `yukti-ai-00009-kol` (100% traffic) · branch `v3/P5-one-brain` @ `405a438` (D-66 leadership names + aurora orb) · `--max-instances=1` · `BQ_DATASET_SUFFIX=v3` (reads `hrfin_*_v3` datasets)
- **Access:** Google sign-in via Identity-Aware Proxy (IAP, enabled 25-Oct). Open the URL in a browser and sign in with an approved account. Approved today: `admin@amandeepsinghs.altostrat.com`. Add people with:
  ```bash
  gcloud beta iap web add-iam-policy-binding --project=ongc-hr-finance-agent --resource-type=cloud-run --service=yukti-ai --region=asia-south1 --member=user:NAME@DOMAIN --role=roles/iap.httpsResourceAccessor
  ```
  Undo IAP: `gcloud beta run services update yukti-ai --project ongc-hr-finance-agent --region asia-south1 --no-iap`
- **Tagged revision URLs (same sign-in rule):** `https://v3p5c---yukti-ai-b6cmgrx7ka-el.a.run.app` (00009, live) · `https://v3p5b---…` (00006, previous)
- **Rollback:**
  ```bash
  gcloud run services update-traffic yukti-ai --project ongc-hr-finance-agent --region asia-south1 --to-revisions=yukti-ai-00006-bap=100
  # earlier: yukti-ai-00004-vec · original baseline: --to-revisions=yukti-ai-00001-wlt=100
  ```
- Evidence: `docs/reviews/P5.6.md` (smoke tests V19/V20/V22/RBAC/security).

## 2. Local — v3 build on Cloudtop (same code as production)
- **App:** http://localhost:3501 (dev UI, `node server.js --dev`, `PORT=3501`)
- **Backend health:** http://localhost:8295/health (`uvicorn app.main:app`, `BQ_DATASET_SUFFIX=v3`, `YUKTI_PLANNER=1`)
- Source: `HR and Finance_ONGC__v3P5/yukti/{frontend,backend}`
- From a laptop: `ssh -L 3501:localhost:3501 <cloudtop>` then open http://localhost:3501 (microphone needs localhost or HTTPS).

## 3. Local — legacy P0 demo (pre-v3, kept for comparison)
- **App:** http://localhost:3300 and http://localhost:3200 (`node server.js`), backend expected on `:8095` (legacy `hrfin_*` datasets).
- **Design system:** http://localhost:3300/design-system
