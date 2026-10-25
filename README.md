# Gate — Day-ahead wind, as known at the auction

A focused pilot for a Great Britain electricity procurement team. **Gate** reconstructs the national WINDFOR forecast available before a chosen day-ahead auction and compares it with subsequent FUELHH wind output. The interface leads with the forecast, then shows its publication history and measured uncertainty.

**Pilot dates:** purchase decisions 1–31 January 2026; deliveries 2 January–1 February 2026.

**Live app:** add public Vercel production URL after deployment.  
**Demo video:** add unlisted YouTube URL after recording.  
**Repository:** public repository should have an anonymous random name.

## Start it

Prerequisites: Docker Desktop with the Linux engine running (or Docker Engine + Compose).

```bash
docker compose up --build
```

Open **http://localhost:3000**. API documentation: **http://localhost:3000/api/docs**. The same URL works on Windows with Docker Desktop. The repository includes the January 2026 snapshot under `backend/data/processed`, so a reviewer can start it without first contacting Elexon.

Without Docker:

```bash
# Terminal 1, repository root
python -m venv .venv
# Windows: .venv\Scripts\python.exe -m pip install -r backend/requirements-ingest.txt
# macOS/Linux: .venv/bin/pip install -r backend/requirements-ingest.txt
cd backend
python -m uvicorn main:app --reload --port 8000

# Terminal 2, repository root
cd frontend
npm ci
npm run dev
```

Open http://localhost:5173. Vite forwards `/api` to FastAPI on port 8000.

To run verification from the root:

```bash
python -m pytest -q
cd frontend && npm ci && npm run build
```

## What it shows

**The day**: select a delivery day and one of three GB auction cutoffs. Read the official forecast in a sentence, examine its 24 native hourly values and a deliberately labelled *experimental* adjustment, inspect forecast revisions, and optionally reveal observed output. Use the date ribbon and keyboard-accessible hour selectors to navigate. **Export CSV** downloads 48 half-hour actuals with forecast columns only at their native hourly target timestamps.

**The month**: actual–forecast differences by wind level, the daily error pattern, forecast lead times, and a chronological holdout assessment of the adjustment.

**How it works**: the auction assumption, timestamp selection, dataset coverage, and calculation limitations.

The design takes its visual cues from a plain-language weather bulletin: fog background, deep-water ink, and amber reserved for the published forecast. It intentionally avoids KPI-card walls and decorative dashboard chrome.

## Data and selection

Only the two datasets named in the assignment are used:

- [Elexon FUELHH](https://bmrs.elexon.co.uk/api-documentation/endpoint/datasets/FUELHH/stream), `fuelType=WIND` — half-hourly actuals.
- [Elexon WINDFOR](https://bmrs.elexon.co.uk/api-documentation/endpoint/datasets/WINDFOR/stream) — hourly target forecasts with multiple `publishTime` values.

For each hourly delivery target, find the **latest** forecast whose `publishTime` is no later than **gate closure minus an assumed five-minute safety margin**. Forecasts published afterwards are not used to reconstruct the decision. All timestamps are compared in UTC and displayed in `Europe/London`. The cutoffs (UK clock on D−1) are EPEX hourly **09:20**, Nord Pool N2EX hourly **09:50**, and EPEX half-hourly **15:30**. These are illustrative exchange gate scenarios, not a claim about the client's actual order-submission time. The half-hourly auction does **not** add half-hourly WINDFOR target forecasts.

The 31 delivery days contain **1,488 half-hourly actual target observations** and **744 native hourly target timestamps**. WINDFOR contains **17,864** retained target/publication records in the included snapshot. Missing values remain missing, not zero; forecasts are not invented at `:30` targets. Forecast MW are summed over hourly target intervals *as an assumed average hourly output* to illustrate GWh; actual energy uses each half-hour MW × 0.5. These are assumptions, not settlement-quality energy volume calculations.

The two Elexon datasets can differ in the wind assets or measurements represented. The differences shown are **differences between series**, not a proven estimate of the forecasting model's causal error. Curtailment may contribute but cannot be established using only the two allowed sources.

## Exploratory adjustment — strictly historical

Positive error means **WINDFOR > FUELHH**. For each delivery day D, Gate builds three wind-level bins (under 10, 10–14 and over 14 GW) using only **complete delivery days on or before D−2**. The bin's average signed difference is subtracted from the raw forecast. Historical residual quantiles form an illustrative 10th–90th percentile interval. Until seven earlier completed delivery days are available the interface shows **no correction** rather than learning from future January dates.

The month page evaluates only later dates with enough prior history, a *walk-forward* test rather than leave-one-day-out with future data. These empirical coverage percentages are not guarantees and should not determine real trading positions without independent validation across seasons and consistent-generation scope.

### Findings from the included snapshot

| EPEX hourly 09:20 | Result |
| --- | ---: |
| Historical native target comparisons | 744 |
| Mean signed difference (forecast − actual) | +1,746 MW |
| Published forecast MAE, full cohort | 2,022 MW |
| Walk-forward evaluated observations (23 delivery days) | 552 |
| Walk-forward raw MAE on those observations | 2,123 MW |
| Walk-forward trial-adjusted MAE | 1,382 MW |
| Empirical lower-reference coverage | 85.5% (not 90%) |

For delivery **21 January 2026**, the 09:20 scenario has a raw daily mean forecast of approximately **19.4 GW**; the trial adjustment using 18 earlier completed delivery days is approximately **16.5 GW**, while the lower historical reference is around **13.8 GW**. These figures are analytical outputs; the utility's demand, existing procurement and electricity prices were not supplied.

## Code map

| Path | Responsibility |
| --- | --- |
| `backend/app/analytics.py` | UTC timestamps, as-of selection, error primitives |
| `backend/app/planning.py` | Auction cutoffs, prior-only calibration, walk-forward evaluation |
| `backend/app/main.py` | Read-only FastAPI endpoints |
| `backend/app/schemas.py` | Pydantic contracts exposed in OpenAPI |
| `backend/app/store.py` | Validated immutable CSV snapshot reader |
| `backend/scripts/ingest.py` | Fetches raw Elexon endpoints and normalizes records |
| `backend/scripts/audit.py` | Checks source, native forecast coverage and actual matches |
| `backend/data/processed/` | The reproducible January CSVs and source metadata |
| `backend/tests/` | Unit and real-snapshot integration tests |
| `frontend/src/components/` | Headline, chart, date navigation, revision ledger, hourly strip |
| `frontend/src/views/` | Day, month and methodology views |
| `frontend/src/styles/` | Editorial design tokens and readable responsive CSS |
| `notebooks/analysis.ipynb` | Re-run analysis against the included snapshot |
| `docker-compose.yml`, `backend/Dockerfile`, `frontend/Dockerfile` | Two-container local delivery |
| `vercel.json` | Vercel Services configuration (availability must be verified in target account) |
| `.github/workflows/ci.yml` | Python tests and frontend production build on push |

Refresh the snapshot, if necessary, with `python backend/scripts/ingest.py`; it uses the publicly accessible Elexon API and refreshes the generated data in `backend/data/processed`. The original snapshot metadata records the original October download, including overlap counts from its old inclusive date-window implementation; the ingestion script now requests one settlement date per interval. Its old retrieval metadata has intentionally **not** been rewritten without re-fetching the source.

## Deployment and checks

`vercel.json` uses Vercel's Services configuration for the frontend/backend. Availability and build behavior must be checked on the deployment account; Docker Compose is the independently reproducible fallback. Verify production `/api/health`, `/api/meta`, `/api/day`, `/api/month`, `/api/revisions`, and `/api/docs`, then test the client in a signed-out/incognito browser. Add the actual production and unlisted-video links above before submitting the form. No GitHub repository, production URL or video is claimed to exist in this source package.

## Development disclosure

OpenAI ChatGPT (GPT-6) was used for requirements research, programming assistance, code review, tests, and documentation. Additional AI-generated design critique and visual prototypes informed the visual direction. The supplied historical data are from Elexon; numerical claims were recalculated from the included snapshot. Verify the final Docker/Vercel deployment and video links independently.
