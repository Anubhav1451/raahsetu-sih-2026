"""Open-Meteo weather ingestion and freshness policy for Northeast corridors."""

from __future__ import annotations

import logging
import os
from datetime import UTC, datetime
from typing import Any

import httpx

from .cache import cache_get, cache_set
from .imd_weather import fetch_imd_current
from .weather_anomaly import score_weather_anomaly

logger = logging.getLogger("raahsetu.weather")

NE_STATIONS: dict[str, dict[str, Any]] = {
    "assam": {"name": "Guwahati", "lat": 26.1445, "lon": 91.7362, "elevation_m": 55},
    "arunachal-pradesh": {"name": "Itanagar", "lat": 27.0844, "lon": 93.6053, "elevation_m": 320},
    "meghalaya": {"name": "Shillong", "lat": 25.5788, "lon": 91.8933, "elevation_m": 1525},
    "manipur": {"name": "Imphal", "lat": 24.8170, "lon": 93.9368, "elevation_m": 786},
    "nagaland": {"name": "Kohima", "lat": 25.6751, "lon": 94.1086, "elevation_m": 1444},
    "mizoram": {"name": "Aizawl", "lat": 23.7271, "lon": 92.7176, "elevation_m": 1132},
    "sikkim": {"name": "Gangtok", "lat": 27.3389, "lon": 88.6065, "elevation_m": 1650},
    "tripura": {"name": "Agartala", "lat": 23.8315, "lon": 91.2868, "elevation_m": 15},
}


def interpolate_corridor_weather(points: list[tuple[float, float]], station_weather: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Attach nearest-station weather to corridor points with explicit provenance.

    This is a spatial approximation for visualization/risk context, not a new
    observation. Every returned record retains the source station and marks the
    method as nearest_reference_station so callers cannot present it as a gauge.
    """
    if not points or not station_weather:
        return []
    valid = [s for s in station_weather if isinstance(s.get("lat"), (int, float)) and isinstance(s.get("lon"), (int, float))]
    results: list[dict[str, Any]] = []
    for lon, lat in points:
        source = min(valid, key=lambda s: (float(s["lat"]) - lat) ** 2 + (float(s["lon"]) - lon) ** 2) if valid else None
        results.append({
            "lon": lon,
            "lat": lat,
            "weather": dict(source) if source else None,
            "source_station": source.get("station") if source else None,
            "interpolation_method": "nearest_reference_station",
            "observed": False,
            "provenance_note": "Spatial approximation from nearest NER reference station; not a corridor gauge observation.",
        })
    return results

_weather_cache: dict[str, dict[str, Any]] = {}
CACHE_TTL_SECONDS = 3600  # 60-minute freshness policy


def get_station_weather(region_code: str) -> dict[str, Any]:
    """Retrieve weather for a state station respecting the 60-minute freshness policy."""
    station = NE_STATIONS.get(region_code, NE_STATIONS["assam"])
    cached = _weather_cache.get(region_code)
    now = datetime.now(UTC)

    if cached and (now - cached["fetched_at"]).total_seconds() < CACHE_TTL_SECONDS:
        return cached

    # Redis is an optional acceleration layer. It is only consulted when
    # explicitly configured, so local tests and offline mode remain deterministic.
    if os.getenv("REDIS_URL"):
        shared = cache_get(f"weather:station:{region_code}")
        if isinstance(shared, dict):
            fetched_at = shared.get("fetched_at")
            if isinstance(fetched_at, str):
                try:
                    shared["fetched_at"] = datetime.fromisoformat(fetched_at)
                except ValueError:
                    shared = None
            if shared is not None:
                _weather_cache[region_code] = shared
                return shared

    # IMD is opt-in because station identifiers/credentials and endpoint
    # availability vary. If it is unavailable, continue to Open-Meteo.
    imd = fetch_imd_current(station)
    if imd:
        precip_mm = imd["precipitation_mm_24h"]
        weather_data = {
            "region_code": region_code,
            "station": station["name"],
            "lat": station["lat"],
            "lon": station["lon"],
            **imd,
            "condition": "heavy_rain" if precip_mm >= 50 else "rain" if precip_mm > 5 else "normal",
            "heavy_rain_warning": precip_mm >= 50,
            "fresh": True,
            "stale": False,
        }
        weather_data["ml_weather_anomaly"] = score_weather_anomaly(
            region_code, precip_mm, imd["wind_kph"], imd["temperature_c"], imd["temperature_c"], imd["humidity_pct"], imd["observed_at"]
        )
        _weather_cache[region_code] = weather_data
        if os.getenv("REDIS_URL"):
            cache_set(f"weather:station:{region_code}", weather_data, CACHE_TTL_SECONDS)
        return weather_data

    # Attempt live fetch from Open-Meteo archive/forecast API
    url = (
        f"https://api.open-meteo.com/v1/forecast?latitude={station['lat']}&longitude={station['lon']}"
        "&current=temperature_2m,relative_humidity_2m,precipitation,rain,wind_speed_10m"
        "&daily=precipitation_sum,rain_sum,temperature_2m_max,temperature_2m_min,relative_humidity_2m_mean"
        "&timezone=Asia%2FKolkata&forecast_days=1"
    )

    try:
        response = httpx.get(url, timeout=4.0)
        if response.status_code == 200:
            data = response.json()
            current = data.get("current", {})
            daily = data.get("daily", {})
            precip_mm = daily.get("precipitation_sum", [0.0])[0] or current.get("precipitation", 0.0)
            temperature_max = daily.get("temperature_2m_max", [current.get("temperature_2m", 0.0)])[0]
            temperature_min = daily.get("temperature_2m_min", [current.get("temperature_2m", 0.0)])[0]

            is_heavy = precip_mm >= 50.0
            condition = "heavy_rain" if is_heavy else "rain" if precip_mm > 5.0 else "normal"

            weather_data = {
                "region_code": region_code,
                "station": station["name"],
                "lat": station["lat"],
                "lon": station["lon"],
                "temperature_c": current.get("temperature_2m", 24.0),
                "humidity_pct": current.get("relative_humidity_2m", 75),
                "precipitation_mm_24h": round(precip_mm, 1),
                "wind_kph": current.get("wind_speed_10m", 12.0),
                "condition": condition,
                "heavy_rain_warning": is_heavy,
                "fetched_at": now,
                "fresh": True,
                "stale": False,
                "source": "Open-Meteo forecast API",
            }
            weather_data["ml_weather_anomaly"] = score_weather_anomaly(
                region_code,
                float(precip_mm),
                float(current.get("wind_speed_10m", 0.0) or 0.0),
                float(temperature_max or 0.0),
                float(temperature_min or 0.0),
                float(current.get("relative_humidity_2m", 0.0) or 0.0),
                data.get("current", {}).get("time"),
            )
            _weather_cache[region_code] = weather_data
            if os.getenv("REDIS_URL"):
                cache_set(f"weather:station:{region_code}", weather_data, CACHE_TTL_SECONDS)
            return weather_data
    except (httpx.HTTPError, OSError, ValueError, KeyError) as exc:
        logger.warning("Live weather fetch failed for %s: %s; using calibrated baseline", region_code, exc)

    # Fallback to calibrated seasonal reference if live fetch fails or is offline
    baseline = {
        "region_code": region_code,
        "station": station["name"],
        "lat": station["lat"],
        "lon": station["lon"],
        "temperature_c": 22.5,
        "humidity_pct": 78,
        "precipitation_mm_24h": 12.5,
        "wind_kph": 10.0,
        "condition": "normal",
        "heavy_rain_warning": False,
        "fetched_at": now,
        "fresh": False,
        "stale": True,
        "source": "Calibrated Northeast Seasonal Reference",
    }
    baseline["ml_weather_anomaly"] = {
        "available": False,
        "model_version": None,
        "anomaly_score": None,
        "level": "unknown",
        "factors": [],
        "meaning": "Live weather is unavailable; no anomaly inference is presented.",
    }
    _weather_cache[region_code] = baseline
    if os.getenv("REDIS_URL"):
        cache_set(f"weather:station:{region_code}", baseline, CACHE_TTL_SECONDS)
    return baseline


def get_all_live_weather() -> list[dict[str, Any]]:
    """Return weather telemetry for all 8 Northeast state stations."""
    results = []
    for region in NE_STATIONS:
        w = dict(get_station_weather(region))
        w["fetched_at"] = w["fetched_at"].isoformat()
        results.append(w)
    return results
