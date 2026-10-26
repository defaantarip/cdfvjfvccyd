import numpy as np
import pandas as pd
from datetime import time
from app.config import DATA_DIR
from app.analysis import select_decision_forecasts, align_actuals_and_forecasts, compute_metrics

a = pd.read_csv(DATA_DIR / "actuals.csv")
f = pd.read_csv(DATA_DIR / "forecasts.csv")
a["start_time"] = pd.to_datetime(a["start_time"], utc=True)
for c in ("start_time", "publish_time"):
    f[c] = pd.to_datetime(f[c], utc=True)

sel = select_decision_forecasts(f, time(9, 20))
al = align_actuals_and_forecasts(a, sel)

print("== 1. TIMESTAMP SHIFT TEST (minimum MAE should be at 0) ==")
for k in range(-6, 7):
    s = a.copy()
    s["start_time"] = s["start_time"] + pd.Timedelta(minutes=30 * k)
    m = align_actuals_and_forecasts(s, sel)
    print(f"{k*30:+5d} min  MAE={m.error_mw.abs().mean():8.1f}  bias={m.error_mw.mean():8.1f}")

d = al.dropna(subset=["forecast_mw"]).copy()
print("\n== 2. RELATIONSHIP ==")
print("correlation:", round(d.forecast_mw.corr(d.actual_mw), 3))
slope, intercept = np.polyfit(d.forecast_mw, d.actual_mw, 1)
print(f"actual ~ {slope:.2f} * forecast + {intercept:.0f}")

print("\n== 3. DAILY MEAN ERROR (MW) ==")
d["day"] = d.start_time.dt.date
print(d.groupby("day").error_mw.mean().round(0).to_string())

print("\n== 4. ERROR BY ACTUAL WIND LEVEL ==")
d["level"] = pd.qcut(d.actual_mw, 4, labels=["Q1 low", "Q2", "Q3", "Q4 high"])
print(d.groupby("level", observed=True).error_mw.agg(
    bias="mean", mae=lambda s: s.abs().mean()).round(0).to_string())

print("\n== 5. CUTOFF SENSITIVITY (D-1 London time) ==")
for hhmm in ["02:35", "04:35", "09:20", "09:50", "12:00", "18:40", "23:00"]:
    h, mi = map(int, hhmm.split(":"))
    m = compute_metrics(align_actuals_and_forecasts(a, select_decision_forecasts(f, time(h, mi))))
    print(f"{hhmm}  n={m['n']}  bias={m['bias_mw']}  mae={m['mae_mw']}  "
          f"rmse={m['rmse_mw']}  lead_h={m['mean_lead_time_h']}")