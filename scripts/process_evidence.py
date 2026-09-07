"""Produce analysis-ready NE subsets without manufacturing missing risk labels."""

import csv
import json
from collections import Counter
from datetime import datetime
from pathlib import Path

from pypdf import PdfReader
from shapely.geometry import Point, shape

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "datasets"


def write_csv(path, rows, fieldnames=None):
    path.parent.mkdir(parents=True, exist_ok=True)
    if fieldnames is None:
        fieldnames = list(dict.fromkeys(key for row in rows for key in row))
    with path.open("w", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(file, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def main():
    boundaries = json.loads(
        (DATA / "processed/boundaries/northeast-states.geojson").read_text(encoding="utf-8")
    )
    polygons = [
        (f["properties"]["shapeName"], shape(f["geometry"])) for f in boundaries["features"]
    ]
    weather_rows = []
    for path in sorted((DATA / "raw/weather").glob("*-daily-2021-2025.json")):
        raw = json.loads(path.read_text(encoding="utf-8"))
        daily = raw["daily"]
        for i, date in enumerate(daily["time"]):
            weather_rows.append(
                {
                    "state": path.name.split("-daily")[0],
                    "date": date,
                    "grid_latitude": raw["latitude"],
                    "grid_longitude": raw["longitude"],
                    "coverage": "one reference point; not statewide observations",
                    **{key: values[i] for key, values in daily.items() if key != "time"},
                }
            )
    write_csv(DATA / "processed/weather/ne-reference-points-daily-2021-2025.csv", weather_rows)
    source = DATA / "raw/landslides/nasa-global-landslide-catalog-2016.csv"
    selected, features, all_dates = [], [], []
    if source.exists():
        with source.open(encoding="utf-8-sig", newline="") as file:
            records = list(csv.DictReader(file))
        for row in records:
            try:
                date = (
                    datetime.strptime(row["event_date"], "%m/%d/%Y %I:%M:%S %p").date().isoformat()
                )
                all_dates.append(date)
            except ValueError:
                date = row["event_date"]
            try:
                lon, lat = float(row["longitude"]), float(row["latitude"])
            except (KeyError, ValueError):
                continue
            if not (87 <= lon <= 98 and 21 <= lat <= 30):
                continue
            point = Point(lon, lat)
            state = next((name for name, poly in polygons if poly.covers(point)), None)
            if state:
                output = {"matched_state": state, "event_date_iso": date, **row}
                selected.append(output)
                features.append(
                    {
                        "type": "Feature",
                        "geometry": {"type": "Point", "coordinates": [lon, lat]},
                        "properties": output,
                    }
                )
        out = DATA / "processed/landslides"
        out.mkdir(parents=True, exist_ok=True)
        write_csv(
            out / "nasa-landslides-northeast.csv",
            selected,
            ["matched_state", "event_date_iso"] + list(records[0]),
        )
        (out / "nasa-landslides-northeast.geojson").write_text(
            json.dumps({"type": "FeatureCollection", "features": features}), encoding="utf-8"
        )
        summary = {
            "raw_records": len(records),
            "northeast_records": len(selected),
            "counts_by_state": {
                name: Counter(r["matched_state"] for r in selected)[name] for name, _ in polygons
            },
            "observed_file_event_range": [min(all_dates), max(all_dates)] if all_dates else None,
            "catalog_metadata_note": "NASA landing page says 2016-03-07 export; actual file date range is reported above. Do not infer freshness from page update date.",
            "limitations": [
                "Historical reported incidents, not a complete inventory or current closures.",
                "Location accuracy varies; retain location_accuracy before matching roads.",
                "A zero state count means no matched records, not no landslide risk.",
            ],
        }
        (out / "summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
        print(json.dumps(summary, indent=2), flush=True)
    report = DATA / "raw/road_safety/morth-road-accidents-2023.pdf"
    if report.exists():
        reader = PdfReader(report)
        out = DATA / "processed/road_safety"
        out.mkdir(parents=True, exist_ok=True)
        index = []
        with (out / "morth-2023-extracted.txt").open("w", encoding="utf-8") as file:
            for number, page in enumerate(reader.pages, start=1):
                text = page.extract_text() or ""
                file.write(f"\n\n--- PDF PAGE {number} ---\n{text}")
                names = [name for name, _ in polygons if name.lower() in text.lower()]
                if names:
                    index.append(
                        {
                            "pdf_page": number,
                            "states_mentioned": names,
                            "note": "Text extraction only; verify tables visually before quoting.",
                        }
                    )
        (out / "morth-2023-ne-page-index.json").write_text(
            json.dumps(index, indent=2), encoding="utf-8"
        )
    print(
        f"Weather: {len(weather_rows)} state-reference-point days. Evidence subsets ready.",
        flush=True,
    )


if __name__ == "__main__":
    main()
