from datetime import time

import pandas as pd
import pytest

from app import analysis as an


def fc(rows):
    df = pd.DataFrame(rows, columns=["publish_time", "start_time", "forecast_mw"])
    df["publish_time"] = pd.to_datetime(df["publish_time"], utc=True)
    df["start_time"] = pd.to_datetime(df["start_time"], utc=True)
    return df


def test_picks_latest_forecast_before_cutoff():
    # Target: 2026-01-10 12:00. Cutoff = 2026-01-09 09:20.
    f = fc([
        ("2026-01-08T22:30", "2026-01-10T12:00", 100),
        ("2026-01-09T07:30", "2026-01-10T12:00", 200),  # latest before cutoff -> chosen
        ("2026-01-09T09:30", "2026-01-10T12:00", 300),  # after cutoff -> must be ignored
    ])
    sel = an.select_decision_forecasts(f, time(9, 20))
    assert sel.forecast_mw.tolist() == [200]


def test_forecast_published_exactly_at_cutoff_is_included():
    f = fc([("2026-01-09T09:20", "2026-01-10T12:00", 150)])
    assert an.select_decision_forecasts(f, time(9, 20)).forecast_mw.tolist() == [150]


def test_forecast_published_on_delivery_day_is_excluded():
    f = fc([("2026-01-10T02:30", "2026-01-10T12:00", 999)])
    assert an.select_decision_forecasts(f, time(9, 20)).empty


def test_cutoff_respects_bst():
    # July: 09:20 London == 08:20 UTC. A 08:30 UTC publication is AFTER the cutoff.
    f = fc([
        ("2026-07-09T08:10", "2026-07-10T12:00", 1),
        ("2026-07-09T08:30", "2026-07-10T12:00", 2),
    ])
    assert an.select_decision_forecasts(f, time(9, 20)).forecast_mw.tolist() == [1]


def test_hourly_forecast_is_held_across_half_hours():
    actuals = pd.DataFrame({
        "start_time": pd.to_datetime(["2026-01-10T12:00", "2026-01-10T12:30", "2026-01-10T13:00"], utc=True),
        "actual_mw": [90.0, 110.0, 100.0],
    })
    f = fc([("2026-01-09T07:30", "2026-01-10T12:00", 100), ("2026-01-09T07:30", "2026-01-10T13:00", 120)])
    al = an.align_actuals_and_forecasts(actuals, an.select_decision_forecasts(f, time(9, 20)))
    assert al.forecast_mw.tolist() == [100, 100, 120]


def test_metrics_and_sign_convention():
    actuals = pd.DataFrame({
        "start_time": pd.to_datetime(["2026-01-10T00:00", "2026-01-10T00:30"], utc=True),
        "actual_mw": [100.0, 200.0],
    })
    f = fc([("2026-01-09T07:30", "2026-01-10T00:00", 110), ("2026-01-09T07:30", "2026-01-10T00:30", 180)])
    al = an.align_actuals_and_forecasts(actuals, an.select_decision_forecasts(f, time(9, 20)))
    m = an.compute_metrics(al)
    assert m["bias_mw"] == pytest.approx(-5.0)  # errors +10 and -20 -> mean -5
    assert m["mae_mw"] == pytest.approx(15.0)
    assert m["rmse_mw"] == pytest.approx(((100 + 400) / 2) ** 0.5, abs=0.01)
    assert m["n"] == 2


def test_cutoff_sensitivity_later_cutoff_means_shorter_lead_time():
    idx = pd.date_range("2026-01-10", periods=48, freq="30min", tz="UTC")
    actuals = pd.DataFrame({"start_time": idx, "actual_mw": 100.0})
    rows = []
    for t in idx[::2]:
        for hh in (2.5, 7.5, 22.5):
            rows.append(((t.normalize() - pd.Timedelta(days=1) + pd.Timedelta(hours=hh)).isoformat(),
                         t.isoformat(), 100.0))
    pts = an.cutoff_sensitivity(actuals, fc(rows))
    by = {p["cutoff"]: p for p in pts}
    assert by["23:00"]["mean_lead_time_h"] < by["09:20" if "09:20" in by else "09:00"]["mean_lead_time_h"]
