"""Pure analysis functions (no I/O): forecast selection, alignment, metrics.

Conventions
-----------
* All timestamps are tz-aware UTC in DataFrames.
* error_mw = forecast - actual. Positive => forecast OVER-estimated wind, so a buyer
  relying on it would UNDER-procure from thermal/other sources.
* Delivery day D is the London-local date of the target's start_time.
  The decision cutoff is `cutoff` (London local time) on day D-1.
"""
from __future__ import annotations

from datetime import time

import numpy as np
import pandas as pd

LONDON = "Europe/London"


def decision_cutoff_utc(start_times: pd.Series, cutoff: time) -> pd.Series:
    """Per target, the UTC instant of the D-1 cutoff (handles BST/GMT correctly)."""
    local_day = start_times.dt.tz_convert(LONDON).dt.tz_localize(None).dt.normalize()
    naive = local_day - pd.Timedelta(days=1) + pd.Timedelta(hours=cutoff.hour, minutes=cutoff.minute)
    localized = naive.dt.tz_localize(
        LONDON, ambiguous=np.full(len(naive), False), nonexistent="shift_forward"
    )
    return localized.dt.tz_convert("UTC")


def select_decision_forecasts(forecasts: pd.DataFrame, cutoff: time) -> pd.DataFrame:
    """For each target start_time, keep the latest forecast published at/before the D-1 cutoff.

    Input columns: publish_time, start_time, forecast_mw.
    Forecasts published after the cutoff are never used (no look-ahead leakage).
    """
    f = forecasts.copy()
    f["cutoff_utc"] = decision_cutoff_utc(f["start_time"], cutoff)
    f = f[f["publish_time"] <= f["cutoff_utc"]]
    f = f.sort_values(["start_time", "publish_time"]).drop_duplicates("start_time", keep="last")
    f["lead_time_h"] = (f["start_time"] - f["publish_time"]) / pd.Timedelta(hours=1)
    return f[["start_time", "publish_time", "forecast_mw", "lead_time_h"]].reset_index(drop=True)


def align_actuals_and_forecasts(
    actuals: pd.DataFrame, selected: pd.DataFrame, tolerance: str = "30min"
) -> pd.DataFrame:
    """Join on the actuals' 30-minute grid.

    If forecasts are coarser (e.g. hourly), a forecast value is held for the following
    half-hour, within `tolerance`. Exact matches always win.
    """
    a = actuals.sort_values("start_time")
    s = selected.sort_values("start_time")
    m = pd.merge_asof(a, s, on="start_time", direction="backward", tolerance=pd.Timedelta(tolerance))
    m["error_mw"] = m["forecast_mw"] - m["actual_mw"]
    return m


def _round(x: float) -> float | None:
    return None if pd.isna(x) else round(float(x), 2)


def compute_metrics(aligned: pd.DataFrame) -> dict:
    """Headline accuracy metrics over rows that have both actual and forecast."""
    d = aligned.dropna(subset=["actual_mw", "forecast_mw"])
    if d.empty:
        return {"n": 0}
    e = d["error_mw"]
    mean_actual = d["actual_mw"].mean()
    mae = e.abs().mean()
    return {
        "n": int(len(d)),
        "mean_actual_mw": _round(mean_actual),
        "mae_mw": _round(mae),
        "rmse_mw": _round(np.sqrt((e**2).mean())),
        "bias_mw": _round(e.mean()),
        "nmae_pct": _round(100 * mae / mean_actual) if mean_actual else None,
        "error_p05_mw": _round(e.quantile(0.05)),
        "error_p50_mw": _round(e.quantile(0.50)),
        "error_p95_mw": _round(e.quantile(0.95)),
        "abs_error_p90_mw": _round(e.abs().quantile(0.90)),
        "mean_lead_time_h": _round(d["lead_time_h"].mean()),
    }


def metrics_by_hour(aligned: pd.DataFrame) -> list[dict]:
    """MAE and bias by London hour of day."""
    d = aligned.dropna(subset=["actual_mw", "forecast_mw"]).copy()
    if d.empty:
        return []
    d["hour"] = d["start_time"].dt.tz_convert(LONDON).dt.hour
    g = d.groupby("hour")["error_mw"]
    out = pd.DataFrame({"mae_mw": g.apply(lambda s: s.abs().mean()), "bias_mw": g.mean()}).reset_index()
    return [
        {"hour": int(r.hour), "mae_mw": _round(r.mae_mw), "bias_mw": _round(r.bias_mw)}
        for r in out.itertuples()
    ]


def cutoff_sensitivity(actuals: pd.DataFrame, forecasts: pd.DataFrame, step_minutes: int = 30) -> list[dict]:
    """Headline metrics for every D-1 cutoff time (shows the value of buying later)."""
    out = []
    for minute in range(0, 24 * 60, step_minutes):
        c = time(minute // 60, minute % 60)
        m = compute_metrics(align_actuals_and_forecasts(actuals, select_decision_forecasts(forecasts, c)))
        if m["n"]:
            out.append({"cutoff": c.strftime("%H:%M"),
                        **{k: m[k] for k in ("n", "mae_mw", "rmse_mw", "bias_mw", "mean_lead_time_h")}})
    return out
