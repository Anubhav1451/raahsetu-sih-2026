from datetime import UTC, datetime, timedelta

import pytest

from app.models import PositionCreate
from app.telematics import TelemetryGuard, verify_telematics_signature
from app.weather_anomaly import score_weather_anomaly


def test_real_weather_model_is_available_for_all_states():
    for state in (
        "assam", "arunachal-pradesh", "manipur", "meghalaya",
        "mizoram", "nagaland", "sikkim", "tripura",
    ):
        result = score_weather_anomaly(state, 120, 45, 31, 18)
        assert result["available"] is True
        assert result["training_samples"] >= 1400
        assert 0 <= result["anomaly_score"] <= 1
        assert "not a landslide" in result["meaning"]


def test_telemetry_guard_rejects_stale_and_impossible_jump():
    guard = TelemetryGuard()
    stale = PositionCreate(
        vehicle_id="AS-TEST-0001",
        recorded_at=datetime.now(UTC) - timedelta(hours=1),
        lon=91.73,
        lat=26.14,
        speed_kph=30,
        accuracy_m=5,
    )
    with pytest.raises(ValueError, match="Stale telemetry"):
        guard.validate(stale)

    now = datetime.now(UTC)
    first = stale.model_copy(update={"recorded_at": now})
    guard.validate(first)
    jump = first.model_copy(
        update={"recorded_at": now + timedelta(seconds=10), "lon": 94.0, "lat": 27.0}
    )
    with pytest.raises(ValueError, match="Implausible GPS jump"):
        guard.validate(jump)


def test_signature_is_required_only_when_secret_is_configured(monkeypatch):
    payload = b"vehicle=test"
    monkeypatch.delenv("TELEMETRY_WEBHOOK_SECRET", raising=False)
    verify_telematics_signature(payload, None)
    monkeypatch.setenv("TELEMETRY_WEBHOOK_SECRET", "secret")
    with pytest.raises(ValueError, match="Missing telemetry"):
        verify_telematics_signature(payload, None)
