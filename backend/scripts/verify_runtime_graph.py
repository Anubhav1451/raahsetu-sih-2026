"""Validate one generated graph snapshot and smoke-test both routing objectives."""

import argparse
import json
from pathlib import Path

from app.models import Dataset, Endpoint, RouteRequest
from app.routing import RoadGraph


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("snapshot", type=Path)
    args = parser.parse_args()

    dataset = Dataset.model_validate_json(args.snapshot.read_text(encoding="utf-8"))
    graph = RoadGraph(dataset)
    result = graph.compare(
        RouteRequest(
            dataset_id=dataset.id,
            origin=Endpoint(node_id=dataset.default_origin),
            destination=Endpoint(node_id=dataset.default_destination),
            vehicle="light",
            risk_aversion=1.5,
            weather="normal",
        )
    )
    routes = {route["id"]: route["status"] for route in result["routes"]}
    if routes != {"fastest": "available", "risk_aware": "available"}:
        raise SystemExit(f"Route smoke test failed: {routes}")
    print(
        json.dumps(
            {
                "dataset_id": dataset.id,
                "nodes": len(dataset.nodes),
                "directed_edges": len(dataset.edges),
                "version": graph.version,
                "route_status": routes,
            }
        )
    )


if __name__ == "__main__":
    main()
