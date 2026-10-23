"""Validate large OSM snapshots incrementally to bound JSON parsing memory."""

import json
import re
import sqlite3
from contextlib import closing
from pathlib import Path

import ijson

from .models import Dataset, Edge, Node


def load_route_window(path, origin, destination):
    """Load a bounded real road window; missing connectivity is never interpolated."""
    if origin.lon is None or destination.lon is None:
        raise ValueError("Regional road routing requires coordinate endpoints")
    path = Path(path).resolve()
    if not path.exists():
        raise ValueError("Real road index is missing; run backend/scripts/build_real_ner.py")
    min_lon = min(origin.lon, destination.lon)
    max_lon = max(origin.lon, destination.lon)
    min_lat = min(origin.lat, destination.lat)
    max_lat = max(origin.lat, destination.lat)

    margin_lon = 0.25
    margin_lat = 0.25

    # Western Arunachal (Tawang/Dirang) routes east of Bhutan via Bhalukpong/Tezpur (lon ~92.8)
    if (min_lat < 27.0 and max_lat > 27.2) and (min_lon < 92.2 or max_lon < 92.2):
        max_lon = max(max_lon, 92.85)

    bounds = (
        min_lon - margin_lon,
        max_lon + margin_lon,
        min_lat - margin_lat,
        max_lat + margin_lat,
    )
    with closing(sqlite3.connect(f"{path.as_uri()}?mode=ro", uri=True)) as db:
        metadata = json.loads(db.execute("SELECT payload FROM metadata").fetchone()[0])
        records = db.execute(
            "SELECT id, payload FROM nodes WHERE lon BETWEEN ? AND ? AND lat BETWEEN ? AND ?",
            bounds,
        )
        nodes = {key: Node.model_validate_json(payload) for key, payload in records}
        edges = []
        for node_id in nodes:
            for payload, target in db.execute("SELECT payload, v FROM edges WHERE u=?", (node_id,)):
                if target in nodes:
                    edges.append(Edge.model_validate_json(payload))
                    if len(edges) > 220000:
                        raise ValueError(
                            "Route area exceeds laptop capacity; select a shorter corridor"
                        )
    if not edges:
        raise ValueError("No real road coverage in selected route area")
    metadata.update(
        nodes=list(nodes.values()),
        edges=edges,
        default_origin=edges[0].u,
        default_destination=edges[0].v,
    )
    metadata["limitations"].append(
        "Search bounded to corridor bounding box; detours outside this area are not evaluated."
    )
    return Dataset.model_validate(metadata)


def load_large_snapshot(path):
    with path.open(encoding="utf-8") as handle:
        header = handle.read(65536)
    metadata = json.loads(
        re.split(r'"nodes"\s*:', header, maxsplit=1)[0].rstrip().rstrip(",") + "}"
    )
    for field, model in (("nodes", Node), ("edges", Edge)):
        with path.open("rb") as handle:
            metadata[field] = [
                model.model_validate(item)
                for item in ijson.items(handle, f"{field}.item", use_float=True)
            ]
    return Dataset.model_validate(metadata)
