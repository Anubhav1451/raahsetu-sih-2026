"""Create a reproducible, provenance-aware corridor route comparison report."""

from __future__ import annotations

import hashlib
import json
from datetime import UTC, datetime
from pathlib import Path

from app.models import Dataset, Endpoint, RouteRequest
from app.routing import RoadGraph

ROOT = Path(__file__).resolve().parents[2]
SNAPSHOT = ROOT / "backend" / "data" / "osm-northeast.json"
OUTPUT = ROOT / "docs" / "validation" / "osm-northeast-corridor-comparison.json"


def main() -> None:
    raw = SNAPSHOT.read_bytes()
    dataset = Dataset.model_validate_json(raw)
    graph = RoadGraph(dataset)
    request = RouteRequest(
        dataset_id=dataset.id,
        origin=Endpoint(node_id=dataset.default_origin),
        destination=Endpoint(node_id=dataset.default_destination),
        vehicle="heavy",
        risk_aversion=1.5,
        weather="heavy_rain",
        strict_vehicle=True,
    )
    comparison = graph.compare(request)
    report = {
        "generated_at": datetime.now(UTC).isoformat(),
        "corridor": "Guwahati (n2_0) to Imphal (n2_6) benchmark corridor",
        "dataset_id": dataset.id,
        "dataset_version": graph.version,
        "snapshot_sha256": hashlib.sha256(raw).hexdigest(),
        "dataset_is_synthetic": dataset.is_synthetic,
        "hazard_source": dataset.hazard_source,
        "weather_source": "Open-Meteo scenario input: heavy_rain",
        "vehicle_profile": "heavy",
        "routes": comparison["routes"],
        "comparison": comparison["comparison"],
        "explanations": comparison["explanations"],
        "limitations": [
            "This is a controlled benchmark comparison, not a field safety outcome study.",
            "Official NDMA/CWC live warning feeds remain standby until authorised URLs are configured.",
        ],
    }
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps({"output": str(OUTPUT), "dataset_version": graph.version, "route_status": [r["status"] for r in comparison["routes"]]}, indent=2))


if __name__ == "__main__":
    main()
