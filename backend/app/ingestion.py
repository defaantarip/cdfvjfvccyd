"""Elexon Insights API client. Network I/O only; returns tidy DataFrames.

NOTE: parameter names below must be verified against the live API (Phase 0).
WINDFOR's publishDateTimeFrom/To are documented; FUELHH's settlementDateFrom/To and
fuelType are to be confirmed.
"""
from __future__ import annotations

from datetime import datetime, timedelta

import httpx
import pandas as pd

from .config import ELEXON_BASE_URL


def _rows(payload) -> list[dict]:
    return payload["data"] if isinstance(payload, dict) else payload


def fetch_actuals(start: str, end: str, client: httpx.Client | None = None) -> pd.DataFrame:
    """Actual wind generation (FUELHH, fuelType=WIND). start/end are ISO dates."""
    c = client or httpx.Client(timeout=60)
    r = c.get(
        f"{ELEXON_BASE_URL}/datasets/FUELHH/stream",
        params={"settlementDateFrom": start, "settlementDateTo": end, "fuelType": "WIND"},
    )
    r.raise_for_status()
    df = pd.DataFrame(_rows(r.json()))
    if df.empty:
        return pd.DataFrame(columns=["start_time", "actual_mw"])
    df = df[df["fuelType"] == "WIND"]
    out = pd.DataFrame(
        {"start_time": pd.to_datetime(df["startTime"], utc=True), "actual_mw": df["generation"].astype(float)}
    )
    return out.drop_duplicates("start_time").sort_values("start_time").reset_index(drop=True)


def fetch_forecasts(
    publish_from: datetime, publish_to: datetime, chunk_days: int = 7, client: httpx.Client | None = None
) -> pd.DataFrame:
    """All WINDFOR forecasts published in [publish_from, publish_to], fetched in chunks."""
    c = client or httpx.Client(timeout=60)
    frames, t = [], publish_from
    while t < publish_to:
        t2 = min(t + timedelta(days=chunk_days), publish_to)
        r = c.get(
            f"{ELEXON_BASE_URL}/datasets/WINDFOR/stream",
            params={"publishDateTimeFrom": t.strftime("%Y-%m-%dT%H:%M:%SZ"),
                    "publishDateTimeTo": t2.strftime("%Y-%m-%dT%H:%M:%SZ")},
        )
        r.raise_for_status()
        frames.append(pd.DataFrame(_rows(r.json())))
        t = t2
    df = pd.concat(frames, ignore_index=True) if frames else pd.DataFrame()
    if df.empty:
        return pd.DataFrame(columns=["publish_time", "start_time", "forecast_mw"])
    out = pd.DataFrame({
        "publish_time": pd.to_datetime(df["publishTime"], utc=True),
        "start_time": pd.to_datetime(df["startTime"], utc=True),
        "forecast_mw": df["generation"].astype(float),
    })
    return out.drop_duplicates(["publish_time", "start_time"]).reset_index(drop=True)
