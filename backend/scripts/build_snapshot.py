"""Fetch January 2026 data from Elexon and write CSV snapshots.

Run from backend/:  python -m scripts.build_snapshot
"""
from datetime import datetime, timezone

from app.config import DATA_DIR, FORECAST_LOOKBACK_START, TARGET_END, TARGET_START
from app.ingestion import fetch_actuals, fetch_forecasts

DATA_DIR.mkdir(parents=True, exist_ok=True)
actuals = fetch_actuals(TARGET_START, TARGET_END)
forecasts = fetch_forecasts(
    datetime.fromisoformat(FORECAST_LOOKBACK_START).replace(tzinfo=timezone.utc),
    datetime.fromisoformat(TARGET_END + "T23:59:59").replace(tzinfo=timezone.utc),
)
# Keep only forecasts whose target falls in January 2026 (UTC == London in January).
lo, hi = f"{TARGET_START}T00:00:00Z", f"{TARGET_END}T23:59:59Z"
forecasts = forecasts[(forecasts.start_time >= lo) & (forecasts.start_time <= hi)]
actuals.to_csv(DATA_DIR / "actuals.csv", index=False)
forecasts.to_csv(DATA_DIR / "forecasts.csv", index=False)
print(f"actuals: {len(actuals)} rows | forecasts: {len(forecasts)} rows | "
      f"distinct publish times: {forecasts.publish_time.nunique()}")
