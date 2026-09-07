"""Build a reproducible, provisional Guwahati hazard-reviewed graph snapshot.

Only two 1 km accuracy historical NASA observations inside the pilot are used.
The output is a review artifact, not a live closure feed or a safety claim.
"""

import csv
import itertools
import json
import math
from datetime import UTC, datetime
from pathlib import Path

from app.models import Dataset
from app.routing import RoadGraph, distance_m

ROOT = Path(__file__).resolve().parents[2]
SOURCE = ROOT / "datasets" / "processed" / "landslides" / "nasa-landslides-northeast.csv"
BASE = ROOT / "backend" / "data" / "osm-guwahati.json"
OUT = ROOT / "backend" / "data" / "osm-guwahati-corridor-reviewed.json"
REPORT = ROOT / "datasets" / "processed" / "road_safety" / "guwahati-corridor-review.json"


def point_to_polyline(lon: float, lat: float, geometry: list[list[float]]) -> float:
    """Good-enough local lon/lat distance for candidate ranking."""
    cos = math.cos(math.radians(lat))
    best = float("inf")
    for a, b in itertools.pairwise(geometry):
        ax, ay = a[0] * cos, a[1]
        bx, by = b[0] * cos, b[1]
        px, py = lon * cos, lat
        dx, dy = bx - ax, by - ay
        t = max(0.0, min(1.0, ((px - ax) * dx + (py - ay) * dy) / (dx * dx + dy * dy or 1)))
        best = min(best, distance_m(lon, lat, (ax + t * dx) / cos, ay + t * dy))
    return best


def main() -> None:
    dataset = Dataset.model_validate_json(BASE.read_text(encoding="utf-8"))
    graph = RoadGraph(dataset)
    wanted = {"10004", "10007"}
    with SOURCE.open(encoding="utf-8-sig", newline="") as handle:
        observations = [r for r in csv.DictReader(handle) if r["event_id"] in wanted]
    if len(observations) != 2:
        raise SystemExit("Expected the two selected 1 km Guwahati observations")

    matches = []
    for row in observations:
        lon, lat = float(row["longitude"]), float(row["latitude"])
        candidates = sorted(
            ((point_to_polyline(lon, lat, edge.geometry), edge) for edge in dataset.edges),
            key=lambda item: item[0],
        )
        distance, edge = candidates[0]
        if distance > 1500:
            raise SystemExit(f"No corridor edge within review radius for {row['event_id']}")
        matches.append(
            {
                "source_record_id": row["event_id"],
                "kind": "landslide",
                "observed_at": row["event_date_iso"],
                "title": row["event_title"],
                "location": row["location_description"],
                "source_name": row["source_name"],
                "source_link": row["source_link"],
                "location_accuracy": row["location_accuracy"],
                "longitude": lon,
                "latitude": lat,
                "matched_edge_id": edge.id,
                "matched_road": edge.name,
                "candidate_distance_m": round(distance, 1),
                "decision": "accepted_for_provisional_pilot",
                "review_note": "Historical 1 km observation; candidate accepted for reproducible demo scoring only.",
            }
        )

    selected = {m["matched_edge_id"] for m in matches}
    updated = dataset.model_copy(deep=True)
    updated.id = "osm-guwahati-corridor-reviewed-v1"
    updated.title = "Guwahati corridor OSM pilot — provisional reviewed hazards"
    updated.is_synthetic = False
    updated.hazard_source = "NASA historical landslide catalog; two 1 km observations, provisional road matches"
    updated.limitations = [
        *dataset.limitations,
        "Reviewed pilot observations: NASA event IDs 10004 and 10007; see the corridor review report.",
        "Historical evidence is not a current closure and does not establish accident probability.",
    ]
    for edge in updated.edges:
        if edge.id in selected:
            edge.accident_score = max(edge.accident_score, 0.55)
            edge.surface_score = max(edge.surface_score, 0.35)
            edge.risk_data_known = True
            edge.evidence = "Provisional reviewed historical landslide match; see corridor review report"
            edge.observed_at = min(m["observed_at"] for m in matches if m["matched_edge_id"] == edge.id)

    OUT.write_text(updated.model_dump_json(indent=2), encoding="utf-8")
    report = {
        "created_at": datetime.now(UTC).isoformat(),
        "corridor": "Guwahati city west distribution hub to east medical depot",
        "base_dataset": graph.version,
        "snapshot_dataset_id": updated.id,
        "snapshot_version": RoadGraph(updated).version,
        "observations": matches,
        "limitations": [
            "Historical NASA records, not live closures.",
            "The 1 km source accuracy exceeds exact lane-level certainty.",
            "Matches are provisional for a controlled pilot and require domain review before operational use.",
            "No accident probability or safety improvement is inferred.",
        ],
    }
    REPORT.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps({"snapshot": str(OUT), "report": str(REPORT), "matches": matches}, indent=2))


if __name__ == "__main__":
    main()
