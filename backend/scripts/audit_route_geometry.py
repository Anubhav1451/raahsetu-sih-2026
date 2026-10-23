"""Reproducible real-snapshot geometry and cross-state route checks."""

import json
import sys
from itertools import pairwise
from pathlib import Path
from types import SimpleNamespace

import ijson

# Allow this audit to run from the repository root or directly by path.
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.graph_loader import load_route_window
from app.models import RouteRequest
from app.routing import RoadGraph, distance_m


def main():
    root = Path(__file__).resolve().parents[1]
    snapshot = root / "data/osm-ner-roads.json"
    with snapshot.open("rb") as handle:
        nodes = {
            n["id"]: SimpleNamespace(lon=n["lon"], lat=n["lat"])
            for n in ijson.items(handle, "nodes.item", use_float=True)
        }
    reversed_count = 0
    invalid = []
    two_point = 0
    from app.route_geometry import assemble_geometry

    count = 0
    with snapshot.open("rb") as handle:
        for data in ijson.items(handle, "edges.item", use_float=True):
            edge = SimpleNamespace(**data)
            count += 1
            try:
                geometry, _ = assemble_geometry([edge], nodes)
                reversed_count += geometry["coordinates"][0] != edge.geometry[0]
                two_point += len(edge.geometry) == 2
            except ValueError:
                invalid.append(edge.id)
    print(f"Audited {count} shapes; {len(invalid)} invalid", flush=True)
    cases = [
        ("Guwahati-Shillong", (91.7362, 26.1445), (91.8933, 25.5788)),
        ("Shillong-Guwahati", (91.8933, 25.5788), (91.7362, 26.1445)),
        ("Guwahati-Tawang", (91.7362, 26.1445), (91.8594, 27.5861)),
    ]
    results = []
    for name, origin, destination in cases:
        request = RouteRequest(
            origin={"lon": origin[0], "lat": origin[1]},
            destination={"lon": destination[0], "lat": destination[1]},
            vehicle="light",
        )
        try:
            graph = RoadGraph(
                load_route_window(
                    root / "data/osm-ner-roads.sqlite", request.origin, request.destination
                )
            )
            result = graph.compare(request)
            for route in result["routes"]:
                if route["status"] == "available":
                    coords = route["route_geometry"]["coordinates"]
                    route["shape_length_km"] = (
                        sum(distance_m(*a, *b) for a, b in pairwise(coords)) / 1000
                    )
                    route["coordinate_count"] = len(coords)
            results.append({"case": name, "result": result})
            print(
                name,
                [(r["status"], r.get("coordinate_count")) for r in result["routes"]],
                flush=True,
            )
        except ValueError as exc:
            results.append({"case": name, "error": str(exc)})
    report = {
        "nodes": len(nodes),
        "edges": count,
        "reversed_shapes": reversed_count,
        "two_point_shapes": two_point,
        "invalid_edge_ids": invalid,
        "routes": results,
    }
    output = root.parent / "work/route-geometry-audit.json"
    output.parent.mkdir(exist_ok=True)
    output.write_text(json.dumps(report), encoding="utf-8")
    print(f"Invalid shapes: {len(invalid)}; evidence: {output}", flush=True)
    if invalid:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
