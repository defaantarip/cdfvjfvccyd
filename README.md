# Day-ahead wind forecast accuracy (GB, January 2026)

A web app for an energy buyer who must decide, on the day before delivery, how much power to buy
beyond what wind will supply. It shows **the wind forecast that was actually available at the
decision time**, compares it with metered wind output, and quantifies the error.

- **Live app:** https://cdfvjfvccyd.vercel.app/
- **Video (pitch + walkthrough):** https://youtu.be/1tZrnFIrsF4

## What it does

| View | Purpose |
|---|---|
| Delivery day | For a chosen day: the forecast available at the cutoff vs. actual output, which forecast run was used, how stale it was, and that day's miss. |
| Forecast accuracy | January-wide MAE, RMSE, bias, error range (P5–P95), error histogram, error by hour, and how the error changes with the decision time. |
| Cutoff control | Change the D-1 decision time (default 09:20 London, the EPEX GB day-ahead gate closure); every number recomputes. |

## Method and assumptions

- **Data (Elexon BMRS, national level, wind only):** `WINDFOR` for forecasts (with `publishTime`) and
  `FUELHH` filtered to `fuelType=WIND` for actual output.
- **Forecast selection:** for each half-hour of delivery day D, use the forecast with the latest
  `publishTime` at or before the cutoff on D-1 (London time). Later forecasts are never used.
- **Resolution:** forecasts are hourly, actuals half-hourly. Each forecast value is held for the
  following half-hour.
- **Error sign:** `error = forecast - actual`. Positive means the forecast was too high, so a buyer
  relying on it would under-buy.
- **Data snapshot:** January 2026 is fixed historical data, so it is fetched once
  (`backend/scripts/build_snapshot.py`) and committed as CSV. The app does not call Elexon at runtime.

## Findings worth knowing

At the 09:20 cutoff every half-hour is served by the 07:30 run (the 09:30 run lands after the gate
closes). The forecast averaged about 1.85 GW above actual output, with positive errors on 27 of 31
days. Buying later reduces the average miss modestly but barely changes the bias.
**Limit:** with only these two datasets we cannot say why the forecast ran high (dataset coverage
differences, curtailment and genuine forecast error are all possible).

## Repository guide

```
backend/
  app/analysis.py       pure logic: forecast selection, alignment, metrics (no I/O)
  app/ingestion.py      Elexon API client
  app/main.py           FastAPI routes: /api/health, /api/analysis, /api/cutoff-sensitivity
  app/config.py         cutoff, dates, paths (env-overridable)
  scripts/              build_snapshot.py, inspect_snapshot.py, diagnose_bias.py
  data/snapshot/        committed January 2026 CSVs
  tests/                unit tests for the selection and metric logic
  Dockerfile            local image;  Dockerfile.vercel: image used on Vercel
frontend/               React + TypeScript (Vite) + Recharts
docker-compose.yml      runs backend and frontend locally
vercel.json             Vercel Services config (frontend + containerised API)
```

## Run it

**With Docker:**
```bash
docker compose up --build
# open http://localhost:8080
```

**Without Docker** (two terminals):
```bash
# backend
cd backend
python -m venv .venv && source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
python -m pytest
uvicorn app.main:app --reload --port 8000

# frontend
cd frontend
npm install
npm run dev        # http://localhost:5173 (proxies /api to port 8000)
```

**Refresh the data snapshot** (needs internet): from `backend/`, run `python -m scripts.build_snapshot`.

## Deployment

Deployed on Vercel using Vercel Services: the frontend builds as a static Vite app and the API runs
as a Docker container (`backend/Dockerfile.vercel`), both behind one URL (`/api/*` routes to the API).

## AI tools disclosure

<EDIT THIS TO MATCH WHAT YOU ACTUALLY DID, e.g.: "I used Claude (Anthropic) as an assistant for
planning, generating code, and reviewing it. I ran and tested the code myself, verified the data
behaviour against the live Elexon API, and can explain every part of it.">
