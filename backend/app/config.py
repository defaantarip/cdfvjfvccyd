"""Central configuration. Everything tunable lives here, overridable by env vars."""
import os
from datetime import time
from pathlib import Path

DATA_DIR = Path(os.getenv("DATA_DIR", Path(__file__).resolve().parent.parent / "data" / "snapshot"))
ELEXON_BASE_URL = os.getenv("ELEXON_BASE_URL", "https://data.elexon.co.uk/bmrs/api/v1")

# Day-ahead gate closure on D-1, London local time. EPEX GB auction closes 09:20 UK time.
DEFAULT_CUTOFF = time.fromisoformat(os.getenv("DEFAULT_CUTOFF", "09:20"))

# Scope of the challenge: purchase decisions for January 2026.
TARGET_START = "2026-01-01"
TARGET_END = "2026-01-31"
# Forecasts for early-Jan targets are published in late December.
FORECAST_LOOKBACK_START = "2025-12-25"
