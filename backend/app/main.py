"""Thin HTTP layer: load data, call analysis functions, return JSON."""
from __future__ import annotations

import json
from datetime import time
from functools import lru_cache

import pandas as pd
from fastapi import FastAPI, HTTPException, Query

from . import analysis
from .config import DATA_DIR, DEFAULT_CUTOFF

app = FastAPI(title="Wind forecast accuracy API")


@lru_cache(maxsize=1)
def _load_snapshot() -> tuple[pd.DataFrame, pd.DataFrame]:
    try:
        a = pd.read_csv(DATA_DIR / "actuals.csv")
        f = pd.read_csv(DATA_DIR / "forecasts.csv")
    except FileNotFoundError as exc:
        raise HTTPException(503, "Snapshot missing. Run: python -m scripts.build_snapshot") from exc
    for df, cols in ((a, ["start_time"]), (f, ["start_time", "publish_time"])):
        for c in cols:
            df[c] = pd.to_datetime(df[c], utc=True)
    return a, f


@app.get("/api/health")
def health():
    return {"status": "ok"}


@app.get("/api/analysis")
def get_analysis(cutoff: str = Query(DEFAULT_CUTOFF.strftime("%H:%M"), pattern=r"^\d{2}:\d{2}$")):
    try:
        cut = time.fromisoformat(cutoff)
    except ValueError as exc:
        raise HTTPException(422, "cutoff must be HH:MM") from exc
    actuals, forecasts = _load_snapshot()
    selected = analysis.select_decision_forecasts(forecasts, cut)
    aligned = analysis.align_actuals_and_forecasts(actuals, selected)
    out = aligned.copy()
    for c in ("start_time", "publish_time"):
        out[c] = out[c].dt.strftime("%Y-%m-%dT%H:%M:%SZ")
    # to_json turns NaN/NaT into null, keeping the payload valid JSON
    series = json.loads(out.to_json(orient="records"))
    return {
        "cutoff_london": cutoff,
        "source": "snapshot",
        "metrics": analysis.compute_metrics(aligned),
        "by_hour": analysis.metrics_by_hour(aligned),
        "series": series,
    }


@app.get("/api/cutoff-sensitivity")
def get_cutoff_sensitivity():
    actuals, forecasts = _load_snapshot()
    return {"source": "snapshot", "points": analysis.cutoff_sensitivity(actuals, forecasts)}
