"""Reproducible route evaluation; never equates index reduction with real safety."""

import csv
import json
from pathlib import Path

from app.main import load_graph
from app.models import Endpoint, RouteRequest


def main():
    graph = load_graph()
    places = [n.id for n in graph.dataset.nodes if n.label]
    rows = []
    for source in places:
        for target in places:
            if source == target:
                continue
            req = RouteRequest(
                origin=Endpoint(node_id=source), destination=Endpoint(node_id=target)
            )
            result = graph.compare(req)
            baseline, recommended = result["routes"]
            row = {
                "source": source,
                "target": target,
                "dataset_version": graph.version,
                "status": recommended["status"],
            }
            if result["comparison"]:
                row.update(
                    fastest_minutes=baseline["duration_min"],
                    risk_aware_minutes=recommended["duration_min"],
                    fastest_exposure=baseline["risk_exposure"],
                    risk_aware_exposure=recommended["risk_exposure"],
                    extra_minutes=result["comparison"]["extra_minutes"],
                    exposure_reduction_pct=result["comparison"]["exposure_reduction_pct"],
                )
            rows.append(row)
    out = Path(__file__).resolve().parents[2] / "docs" / "validation"
    out.mkdir(parents=True, exist_ok=True)
    keys = list(dict.fromkeys(k for row in rows for k in row))
    with (out / "route-evaluation.csv").open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=keys)
        writer.writeheader()
        writer.writerows(rows)
    summary = {
        "dataset_id": graph.dataset.id,
        "dataset_version": graph.version,
        "journeys": len(rows),
        "synthetic": graph.dataset.is_synthetic,
        "meaning": "Controlled route-cost experiment. Not a field safety study.",
        "available": sum(r["status"] == "available" for r in rows),
        "lower_exposure": sum(
            r.get("exposure_reduction_pct", 0) is not None
            and r.get("exposure_reduction_pct", 0) > 0
            for r in rows
        ),
    }
    (out / "evaluation-summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
