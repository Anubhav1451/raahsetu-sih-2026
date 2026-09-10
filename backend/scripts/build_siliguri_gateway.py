"""Build a provisional Siliguri gateway snapshot with historical landslide matches."""

import csv
import itertools
import json
import math
from datetime import UTC, datetime
from pathlib import Path

from app.models import Dataset
from app.routing import RoadGraph, distance_m

ROOT = Path(__file__).resolve().parents[2]
SOURCE = ROOT / "datasets/raw/landslides/nasa-global-landslide-catalog-2016.csv"
BASE = ROOT / "backend/data/osm-siliguri-gateway.json"
OUT = ROOT / "backend/data/osm-siliguri-gateway-reviewed.json"
REPORT = ROOT / "datasets/processed/road_safety/siliguri-gateway-review.json"

def point_to_polyline(lon, lat, geometry):
    cos = math.cos(math.radians(lat)); best = float("inf")
    for a, b in itertools.pairwise(geometry):
        ax, ay = a[0] * cos, a[1]; bx, by = b[0] * cos, b[1]; px, py = lon * cos, lat
        dx, dy = bx - ax, by - ay
        t = max(0.0, min(1.0, ((px-ax)*dx + (py-ay)*dy) / (dx*dx + dy*dy or 1)))
        best = min(best, distance_m(lon, lat, (ax+t*dx)/cos, ay+t*dy))
    return best

dataset = Dataset.model_validate_json(BASE.read_text(encoding="utf-8"))
graph = RoadGraph(dataset)
with SOURCE.open(encoding="utf-8-sig", newline="") as handle:
    rows = [r for r in csv.DictReader(handle) if 88.20 <= float(r["longitude"]) <= 88.65 and 26.55 <= float(r["latitude"]) <= 26.95]
rows = sorted(rows, key=lambda r: r["event_id"])
matches=[]
for row in rows:
    lon, lat = float(row["longitude"]), float(row["latitude"])
    distance, edge = min(((point_to_polyline(lon, lat, e.geometry), e) for e in dataset.edges), key=lambda x: x[0])
    if distance <= 1500:
        matches.append({"source_record_id":row["event_id"],"kind":"landslide","observed_at":row["event_date"],"title":row["event_title"],"location":row["location_description"],"source_name":row["source_name"],"source_link":row["source_link"],"location_accuracy":row["location_accuracy"],"longitude":lon,"latitude":lat,"matched_edge_id":edge.id,"matched_road":edge.name,"candidate_distance_m":round(distance,1),"decision":"accepted_for_provisional_pilot","review_note":"Historical NASA record; provisional road match for controlled demonstration."})
updated=dataset.model_copy(deep=True); updated.id="osm-siliguri-gateway-reviewed-v1"; updated.title="Siliguri gateway OSM pilot — provisional reviewed hazards"; updated.hazard_source="NASA historical landslide catalog; provisional Siliguri gateway road matches"; updated.limitations=[*dataset.limitations,"Historical gateway observations are provisional matches and are not current closures.","Siliguri is in West Bengal and is included as an operational Northeast access corridor."]
selected={m["matched_edge_id"] for m in matches}
for edge in updated.edges:
    if edge.id in selected:
        edge.accident_score=max(edge.accident_score,0.55); edge.surface_score=max(edge.surface_score,0.35); edge.risk_data_known=True; edge.evidence="Provisional historical landslide match; see Siliguri gateway review"; edge.observed_at=min(m["observed_at"] for m in matches if m["matched_edge_id"]==edge.id)
OUT.write_text(updated.model_dump_json(indent=2), encoding="utf-8")
REPORT.parent.mkdir(parents=True, exist_ok=True); REPORT.write_text(json.dumps({"created_at":datetime.now(UTC).isoformat(),"corridor":"Siliguri–Bagdogra–Sevoke gateway","base_dataset":graph.version,"snapshot_dataset_id":updated.id,"snapshot_version":RoadGraph(updated).version,"matched_observations":len(matches),"observations":matches,"limitations":["Historical records are not live closures.","Source coordinates have kilometre-scale accuracy.","Matches require domain review before operational use."]}, indent=2), encoding="utf-8")
print(json.dumps({"snapshot":str(OUT),"report":str(REPORT),"observations":len(matches)}, indent=2))
