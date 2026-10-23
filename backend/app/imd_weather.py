"""Small, opt-in adapter for the official IMD current-weather API.

The adapter is deliberately disabled unless IMD_WEATHER_ENABLED is set. This
keeps the existing Open-Meteo fallback working when an IMD station mapping or
network access is unavailable. No response is treated as authoritative without
the source observation timestamp.
"""
from __future__ import annotations

import os
from datetime import UTC, datetime
from typing import Any

import httpx


def fetch_imd_current(station: dict[str, Any]) -> dict[str, Any] | None:
    if os.getenv("IMD_WEATHER_ENABLED", "0").lower() not in {"1", "true", "yes"}:
        return None
    base = os.getenv("IMD_API_BASE_URL", "https://api.imd.gov.in/api/v1/current_wx")
    params: dict[str, str] = {}
    if station.get("imd_station_id"):
        params["id"] = str(station["imd_station_id"])
    else:
        params.update({"lat": str(station["lat"]), "lon": str(station["lon"])})
    try:
        response = httpx.get(base, params=params, timeout=5.0)
        response.raise_for_status()
        payload = response.json()
        rows = payload.get("data", payload) if isinstance(payload, dict) else payload
        if not isinstance(rows, list) or not rows:
            return None
        row = rows[0]
        if not isinstance(row, dict):
            return None
        observed = row.get("Date of Observation") or row.get("date_obs")
        observed_time = row.get("Time of Observation") or row.get("time_obs")
        if not observed:
            return None
        return {
            "temperature_c": float(row.get("Temperature", row.get("temperature", 0)) or 0),
            "humidity_pct": float(row.get("Humidity", row.get("humidity", 0)) or 0),
            "precipitation_mm_24h": float(row.get("Last 24 hrs Rainfall", row.get("rainfall", 0)) or 0),
            "wind_kph": float(row.get("Wind Speed", row.get("wind_speed", 0)) or 0),
            "observed_at": f"{observed} {observed_time or ''}".strip(),
            "fetched_at": datetime.now(UTC),
            "source": "IMD current weather API",
        }
    except (httpx.HTTPError, OSError, ValueError, TypeError, KeyError):
        return None
