"""Filter NE boundaries and prepare reproducible terrain/weather acquisition catalogs."""

import json
import math
from pathlib import Path
from urllib.parse import urlencode

from shapely.geometry import box, shape

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "datasets"
STATES = [
    "Arunachal Pradesh",
    "Assam",
    "Manipur",
    "Meghalaya",
    "Mizoram",
    "Nagaland",
    "Sikkim",
    "Tripura",
]
STATE_CODES = {
    "IN-AR": "Arunachal Pradesh",
    "IN-AS": "Assam",
    "IN-MN": "Manipur",
    "IN-ML": "Meghalaya",
    "IN-MZ": "Mizoram",
    "IN-NL": "Nagaland",
    "IN-SK": "Sikkim",
    "IN-TR": "Tripura",
}
CAPITALS = {
    "Arunachal Pradesh": (27.0844, 93.6053, "Itanagar"),
    "Assam": (26.1445, 91.7362, "Guwahati"),
    "Manipur": (24.8170, 93.9368, "Imphal"),
    "Meghalaya": (25.5788, 91.8933, "Shillong"),
    "Mizoram": (23.7271, 92.7176, "Aizawl"),
    "Nagaland": (25.6751, 94.1086, "Kohima"),
    "Sikkim": (27.3389, 88.6065, "Gangtok"),
    "Tripura": (23.8315, 91.2868, "Agartala"),
}


def main():
    raw = json.loads((DATA / "raw/boundaries/india-adm1.geojson").read_text(encoding="utf-8"))
    selected = [f for f in raw["features"] if f["properties"]["shapeISO"] in STATE_CODES]
    for feature in selected:
        feature["properties"]["originalShapeName"] = feature["properties"]["shapeName"]
        feature["properties"]["shapeName"] = STATE_CODES[feature["properties"]["shapeISO"]]
    assert len(selected) == 8, [f["properties"] for f in selected]
    out = DATA / "processed/boundaries"
    out.mkdir(parents=True, exist_ok=True)
    (out / "northeast-states.geojson").write_text(
        json.dumps({"type": "FeatureCollection", "features": selected}), encoding="utf-8"
    )
    coverage = []
    tiles = set()
    for feature in selected:
        name = feature["properties"]["shapeName"]
        geometry = shape(feature["geometry"])
        w, s, e, n = geometry.bounds
        coverage.append(
            {
                "state": name,
                "bbox": [w, s, e, n],
                "source": "geoBoundaries gbOpen IND ADM1",
                "boundary_year": 2011,
                "license": "CC BY 2.5 IN",
            }
        )
        for lon in range(math.floor(w), math.ceil(e)):
            for lat in range(math.floor(s), math.ceil(n)):
                if geometry.intersects(box(lon, lat, lon + 1, lat + 1)):
                    tiles.add((lat, lon))
    (out / "coverage.json").write_text(json.dumps(coverage, indent=2), encoding="utf-8")
    terrain = []
    for lat, lon in sorted(tiles):
        tile = f"N{lat:02}E{lon:03}"
        terrain.append(
            {
                "id": f"terrain_{tile}",
                "url": f"https://s3.amazonaws.com/elevation-tiles-prod/skadi/N{lat:02}/{tile}.hgt.gz",
                "file": f"raw/terrain/{tile}.hgt.gz",
                "license": "Tilezen elevation source attribution; see docs/DATA.md",
                "coverage": f"1 degree tile [{lon},{lat},{lon + 1},{lat + 1}] intersecting NE states",
                "purpose": "Terrain elevation; derived slope is not landslide probability",
            }
        )
    (DATA / "catalog-terrain.json").write_text(json.dumps(terrain, indent=2), encoding="utf-8")
    weather = []
    for state, (lat, lon, city) in CAPITALS.items():
        params = urlencode(
            {
                "latitude": lat,
                "longitude": lon,
                "start_date": "2021-01-01",
                "end_date": "2025-12-31",
                "daily": "temperature_2m_max,temperature_2m_min,precipitation_sum,rain_sum,wind_speed_10m_max",
                "timezone": "Asia/Kolkata",
            }
        )
        weather.append(
            {
                "id": f"weather_{state.lower().replace(' ', '_')}",
                "url": f"https://archive-api.open-meteo.com/v1/archive?{params}",
                "file": f"raw/weather/{state.lower().replace(' ', '-')}-daily-2021-2025.json",
                "license": "CC BY 4.0; Open-Meteo and underlying reanalysis providers",
                "coverage": f"{city} reference point ({lat}, {lon}); NOT statewide road-level observations",
                "purpose": "Historical weather prototype features; model/reanalysis data, not station measurements",
            }
        )
    weather.append(
        {
            "id": "nasa_glc_2016",
            "url": "https://data.nasa.gov/docs/legacy/Global_Landslide_Catalog_Export/Global_Landslide_Catalog_Export_rows.csv",
            "file": "raw/landslides/nasa-global-landslide-catalog-2016.csv",
            "license": "NASA catalog terms; cite Kirschbaum et al. 2010 and 2015",
            "coverage": "Global historical one-time export, current as of 2016-03-07",
            "purpose": "Historical reported rainfall-triggered landslides; spatially filter NE; incomplete and reporting-biased",
        }
    )
    (DATA / "catalog-weather-landslides.json").write_text(
        json.dumps(weather, indent=2), encoding="utf-8"
    )
    print(
        f"Prepared 8 state boundaries, {len(tiles)} elevation tiles, 8 weather series and NASA catalog."
    )


if __name__ == "__main__":
    main()
