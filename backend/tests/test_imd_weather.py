from app.imd_weather import fetch_imd_current
from app.weather import interpolate_corridor_weather


def test_corridor_weather_keeps_approximation_provenance():
    result = interpolate_corridor_weather(
        [(91.7, 26.1), (91.9, 25.6)],
        [{"station": "Guwahati", "lon": 91.7362, "lat": 26.1445, "temperature_c": 25}],
    )
    assert len(result) == 2
    assert result[0]["source_station"] == "Guwahati"
    assert result[0]["observed"] is False
    assert result[0]["interpolation_method"] == "nearest_reference_station"


class Response:
    def raise_for_status(self):
        return None

    def json(self):
        return {
            "data": [
                {
                    "Date of Observation": "2026-09-23",
                    "Time of Observation": "06:00",
                    "Temperature": "25.4",
                    "Humidity": "82",
                    "Last 24 hrs Rainfall": "18.2",
                    "Wind Speed": "12.0",
                }
            ]
        }


def test_imd_adapter_is_opt_in_and_parses_official_fields(monkeypatch):
    monkeypatch.setenv("IMD_WEATHER_ENABLED", "true")
    monkeypatch.setattr("app.imd_weather.httpx.get", lambda *args, **kwargs: Response())
    result = fetch_imd_current({"lat": 26.14, "lon": 91.73})
    assert result["source"] == "IMD current weather API"
    assert result["precipitation_mm_24h"] == 18.2
    assert result["humidity_pct"] == 82.0
    assert result["observed_at"] == "2026-09-23 06:00"


def test_imd_adapter_disabled_by_default(monkeypatch):
    monkeypatch.delenv("IMD_WEATHER_ENABLED", raising=False)
    assert fetch_imd_current({"lat": 26.14, "lon": 91.73}) is None
