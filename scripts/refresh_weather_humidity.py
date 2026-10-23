"""Refresh the eight Northeast reference series with daily mean humidity.

Open-Meteo documents relative_humidity_2m_mean as a daily historical variable.
The request is intentionally one point per state; this is a reference signal,
not a claim of statewide station coverage.
"""
from __future__ import annotations

import json
from pathlib import Path
from urllib.parse import urlencode

import httpx

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "datasets" / "raw" / "weather"
CAPITALS = {
    "arunachal-pradesh": (27.0844, 93.6053), "assam": (26.1445, 91.7362),
    "meghalaya": (25.5788, 91.8933), "manipur": (24.8170, 93.9368),
    "mizoram": (23.7271, 92.7176), "nagaland": (25.6751, 94.1086),
    "sikkim": (27.3389, 88.6065), "tripura": (23.8315, 91.2868),
}

def main() -> None:
    RAW.mkdir(parents=True, exist_ok=True)
    daily = "temperature_2m_max,temperature_2m_min,precipitation_sum,rain_sum,wind_speed_10m_max,relative_humidity_2m_mean"
    with httpx.Client(timeout=45.0) as client:
        for state, (lat, lon) in CAPITALS.items():
            query = urlencode({"latitude": lat, "longitude": lon, "start_date": "2021-01-01", "end_date": "2025-12-31", "daily": daily, "timezone": "Asia/Kolkata"})
            url = f"https://archive-api.open-meteo.com/v1/archive?{query}"
            response = client.get(url)
            response.raise_for_status()
            payload = response.json()
            humidity = payload.get("daily", {}).get("relative_humidity_2m_mean")
            if not humidity or len(humidity) != len(payload["daily"]["time"]):
                raise RuntimeError(f"incomplete humidity series for {state}")
            (RAW / f"{state}-daily-2021-2025.json").write_text(json.dumps(payload), encoding="utf-8")
            print(state, len(humidity), "daily humidity values")

if __name__ == "__main__":
    main()
