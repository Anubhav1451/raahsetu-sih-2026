"""Unit tests for the automated scheduled data refresh runner."""

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.scheduled_refresh import check_official_feeds, run_refresh_cycle, update_data_status


def test_update_data_status_dry_run():
    status = update_data_status(weather_count=8, advisory_count=2, dry_run=True)
    assert "last_scheduled_refresh" in status
    assert status["weather_stations_live"] == 8
    assert status["active_early_warning_advisories"] == 2


def test_check_official_feeds():
    status_list, _advisories = check_official_feeds()
    assert len(status_list) >= 3
    source_names = [s.source_name for s in status_list]
    assert "Open-Meteo forecast API" in source_names
    assert "NDMA SACHET CAP adapter" in source_names
    assert "CWC flood forecast adapter" in source_names


def test_run_refresh_cycle_dry_run():
    result = run_refresh_cycle(dry_run=True)
    assert result["weather_stations"] >= 8
    assert "refreshed_at" in result
