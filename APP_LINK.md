# Yukti AI — Live Application Links

_Last updated: 27-Oct-2026 (v3p8: "How Yukti works" architecture page; v3p7: revenue drivers + rupee, portfolio mix, DCF follow-ups, ±3% production sensitivity)._

## 1. Cloud Run — v3 production (live)
- **Service URL:** https://yukti-ai-b6cmgrx7ka-el.a.run.app (alias: https://yukti-ai-89038075859.asia-south1.run.app)
- **Architecture ("How Yukti works"):** https://yukti-ai-b6cmgrx7ka-el.a.run.app/architecture — also the network icon in the top bar · source doc `docs/ARCHITECTURE.md` on `v3/P5-one-brain`
- **Live revision:** `yukti-ai-arch-76de3bb` (100% traffic, labels `commit=76de3bb`, `change=architecture-added`) · image `yukti-ai:v3p8` (sha256:57903ab0…) · built from `v3/P5-one-brain` commit `76de3bb` "architecture added" (pushed 27-Oct) · `--max-instances=1` · `BQ_DATASET_SUFFIX=v3`
- **Access:** Google sign-in via Identity-Aware Proxy (IAP, enabled 25-Oct). Open the URL in a browser and sign in with an approved account. Approved today: `admin@amandeepsinghs.altostrat.com`. Add people with:
  ```bash
  gcloud beta iap web add-iam-policy-binding --project=ongc-hr-finance-agent --resource-type=cloud-run --service=yukti-ai --region=asia-south1 --member=user:NAME@DOMAIN --role=roles/iap.httpsResourceAccessor
  ```
  Undo IAP: `gcloud beta run services update yukti-ai --project ongc-hr-finance-agent --region asia-south1 --no-iap`
- **Tagged revision URLs (same sign-in rule):** `https://arch---yukti-ai-b6cmgrx7ka-el.a.run.app` (arch-76de3bb, live) · `https://v3p8---yukti-ai-b6cmgrx7ka-el.a.run.app` (00015, same image) · `https://v3p7---yukti-ai-b6cmgrx7ka-el.a.run.app` (00013, previous)
- **Rollback:**
  ```bash
  gcloud run services update-traffic yukti-ai --project ongc-hr-finance-agent --region asia-south1 --to-revisions=yukti-ai-00013-fod=100
  # earlier: yukti-ai-00011-nuy · yukti-ai-00009-kol · yukti-ai-00006-bap · yukti-ai-00004-vec · original baseline: --to-revisions=yukti-ai-00001-wlt=100
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
