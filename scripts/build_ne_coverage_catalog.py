"""Create an explicit Northeast state/capital/data coverage catalog."""

import hashlib
import json
from datetime import UTC, datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "datasets"
RUNTIME = ROOT / "backend" / "data"
CAPITALS = {
    "Arunachal Pradesh": ("Itanagar", 27.0844, 93.6053, "arunachal-pradesh"),
    "Assam": ("Dispur", 26.1433, 91.7898, "assam"),
    "Manipur": ("Imphal", 24.8170, 93.9368, "manipur"),
    "Meghalaya": ("Shillong", 25.5788, 91.8933, "meghalaya"),
    "Mizoram": ("Aizawl", 23.7271, 92.7176, "mizoram"),
    "Nagaland": ("Kohima", 25.6751, 94.1086, "nagaland"),
    "Sikkim": ("Gangtok", 27.3389, 88.6065, "sikkim"),
    "Tripura": ("Agartala", 23.8315, 91.2868, "tripura"),
}


def sha256(path: Path) -> str:
    with path.open("rb") as handle:
        return hashlib.file_digest(handle, "sha256").hexdigest()


def main() -> None:
    summary = json.loads(
        (DATA / "processed/osm/extraction-summary.json").read_text(encoding="utf-8")
    )
    by_region = {item["region"]: item for item in summary}
    records = []
    for state, (capital, lat, lon, slug) in CAPITALS.items():
        item = by_region[slug]
        runtime_file = RUNTIME / f"osm-{slug}.json"
        graphml_file = RUNTIME / f"osm-{slug}.graphml"
        places_file = DATA / "processed" / "osm" / f"{slug}-places.geojson"
        place_features = 0
        if places_file.exists():
            place_features = len(
                json.loads(places_file.read_text(encoding="utf-8")).get("features", [])
            )
        runtime = None
        if runtime_file.exists():
            runtime = {
                "dataset_id": f"osm-{slug}",
                "file": str(runtime_file.relative_to(ROOT)).replace("\\", "/"),
                "bytes": runtime_file.stat().st_size,
                "sha256": sha256(runtime_file),
                "graphml_file": str(graphml_file.relative_to(ROOT)).replace("\\", "/")
                if graphml_file.exists()
                else None,
                "api_load_strategy": "on-demand bounded memory cache",
            }
        records.append(
            {
                "state": state,
                "capital": capital,
                "capital_coordinates": {"lat": lat, "lon": lon},
                "osm_source": item["source"],
                "roads_file": item["output"],
                "facilities_file": f"datasets/processed/osm/{slug}-facilities.geojson",
                "road_ways": item["road_ways"],
                "facility_features": item["facility_features"],
                "place_features": place_features,
                "places_file": str(places_file.relative_to(ROOT)).replace("\\", "/")
                if places_file.exists()
                else None,
                "searchable_in_state_extract": True,
                "facility_status": "OSM presence only; operating status unverified",
                "runtime_graph": runtime,
            }
        )
    output = {
        "generated_at": datetime.now(UTC).isoformat(),
        "scope": "All eight states of North-East India",
        "state_count": len(records),
        "capital_count": len(records),
        "records": records,
        "source_note": "OSM extracts are buffered by approximately 2 km for boundary connectivity; absence from OSM is not proof of absence.",
        "next_step": "Publish snapshots to versioned object storage and register their metadata in Supabase; serve only the selected state/city graph.",
    }
    path = DATA / "processed/ne-coverage-catalog.json"
    path.write_text(json.dumps(output, indent=2), encoding="utf-8")
    print(
        json.dumps({"path": str(path), "states": len(records), "capitals": len(records)}, indent=2)
    )


if __name__ == "__main__":
    main()
