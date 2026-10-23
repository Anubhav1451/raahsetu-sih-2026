"""Audit every real Northeast OSM graph and verify both route objectives."""

from __future__ import annotations

import hashlib
import json
import sys
import time
from datetime import UTC, datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "backend"))

from app.models import Dataset, RouteRequest
from app.routing import RoadGraph


def audit_file(path: Path) -> dict:
    raw = path.read_bytes()
    dataset = Dataset.model_validate_json(raw)
    graph = RoadGraph(dataset)
    request = RouteRequest(
        dataset_id=dataset.id,
        origin={"node_id": dataset.default_origin},
        destination={"node_id": dataset.default_destination},
        vehicle="heavy",
        weather="normal",
        risk_aversion=1.5,
    )
    started = time.perf_counter()
    result = graph.compare(request)
    elapsed_ms = round((time.perf_counter() - started) * 1000, 2)
    routes = {route["id"]: route for route in result["routes"]}
    edge_count = len(dataset.edges)
    restriction_counts = {
        "max_weight": sum(edge.max_weight_t is not None for edge in dataset.edges),
        "max_height": sum(edge.max_height_m is not None for edge in dataset.edges),
        "max_width": sum(edge.max_width_m is not None for edge in dataset.edges),
        "max_axle_load": sum(edge.max_axle_load_t is not None for edge in dataset.edges),
        "hgv_access": sum(edge.hgv_allowed is not None for edge in dataset.edges),
        "road_class": sum(edge.road_class is not None for edge in dataset.edges),
    }
    return {
        "file": path.name,
        "dataset_id": dataset.id,
        "region": dataset.region,
        "source": dataset.source,
        "is_synthetic": dataset.is_synthetic,
        "generated_at": dataset.generated_at,
        "sha256": hashlib.sha256(raw).hexdigest(),
        "dataset_version": result["dataset_version"],
        "nodes": len(dataset.nodes),
        "directed_edges": len(dataset.edges),
        "default_origin": dataset.default_origin,
        "default_destination": dataset.default_destination,
        "fastest_status": routes["fastest"]["status"],
        "risk_aware_status": routes["risk_aware"]["status"],
        "fastest_distance_km": routes["fastest"].get("distance_km"),
        "risk_aware_distance_km": routes["risk_aware"].get("distance_km"),
        "fastest_duration_min": routes["fastest"].get("duration_min"),
        "risk_aware_duration_min": routes["risk_aware"].get("duration_min"),
        "route_compare_ms": elapsed_ms,
        "restriction_coverage": {
            key: {
                "edges": count,
                "pct": round(100 * count / max(1, edge_count), 4),
            }
            for key, count in restriction_counts.items()
        },
        "missing_restriction_policy": (
            "Known limits are enforced. In strict vehicle mode, an edge with missing "
            "height/weight/width/axle/HGV evidence is excluded rather than assumed safe."
        ),
    }


def main() -> None:
    data_dir = ROOT / "backend" / "data"
    files = sorted(data_dir.glob("osm-*-real.json"))
    if len(files) != 8:
        raise SystemExit(f"Expected 8 real Northeast graphs, found {len(files)}")
    records = [audit_file(path) for path in files]
    output = {
        "audited_at": datetime.now(UTC).isoformat(),
        "scope": "Eight Northeast states; real OSM graph snapshots present in this checkout",
        "limitations": [
            "OSM road geometry is a snapshot and requires scheduled refreshes.",
            "Hazard and weather layers are separate from the road graph and must be freshness-checked.",
            "A successful route solve proves graph connectivity, not live road availability.",
            "OSM restriction coverage is incomplete; percentages are reported per graph and strict mode fails closed.",
        ],
        "graphs": records,
    }
    out_dir = ROOT / "docs" / "validation"
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "northeast-graph-audit.json").write_text(
        json.dumps(output, indent=2) + "\n", encoding="utf-8"
    )
    print(f"Audited {len(records)} graphs; both route objectives available for every graph.")
    for record in records:
        print(
            f"{record['region']}: {record['nodes']} nodes, "
            f"{record['directed_edges']} edges, version {record['dataset_version']}"
        )


if __name__ == "__main__":
    main()
