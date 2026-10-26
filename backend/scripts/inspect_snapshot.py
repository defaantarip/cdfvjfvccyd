import pandas as pd
from datetime import time
from app.config import DATA_DIR
from app.analysis import select_decision_forecasts, align_actuals_and_forecasts, compute_metrics

a = pd.read_csv(DATA_DIR / "actuals.csv")
f = pd.read_csv(DATA_DIR / "forecasts.csv")
a["start_time"] = pd.to_datetime(a["start_time"], utc=True)
for c in ("start_time", "publish_time"):
    f[c] = pd.to_datetime(f[c], utc=True)

print("== ACTUALS ==")
print("range:", a.start_time.min(), "->", a.start_time.max())
print("nulls:", a.actual_mw.isna().sum(), "| negatives:", (a.actual_mw < 0).sum(),
      "| dup times:", a.start_time.duplicated().sum())

print("\n== FORECASTS ==")
print("target minute-of-hour counts:\n", f.start_time.dt.minute.value_counts().to_string())
print("\npublish times (HH:MM UTC):\n", f.publish_time.dt.strftime("%H:%M").value_counts().sort_index().to_string())
runs = f.groupby("publish_time").agg(n=("start_time", "size"), first=("start_time", "min"), last=("start_time", "max"))
runs["horizon_h"] = (runs["last"] - runs.index.to_series()) / pd.Timedelta(hours=1)
print("\nvalues per run:\n", runs.n.describe().round(1).to_string())
print("\nhorizon (hours ahead of publish) per run:\n", runs.horizon_h.describe().round(1).to_string())
print("\nnulls:", f.forecast_mw.isna().sum(), "| negatives:", (f.forecast_mw < 0).sum(),
      "| dup (publish,start):", f.duplicated(["publish_time", "start_time"]).sum())

print("\n== DECISION VIEW @ 09:20 ==")
al = align_actuals_and_forecasts(a, select_decision_forecasts(f, time(9, 20)))
print("actual rows with a forecast:", al.forecast_mw.notna().sum(), "of", len(al))
print("selected publish times (HH:MM UTC):\n", al.publish_time.dt.strftime("%H:%M").value_counts().to_string())
print("lead time (h):\n", al.lead_time_h.describe().round(1).to_string())
print("metrics:", compute_metrics(al))