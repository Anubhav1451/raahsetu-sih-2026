"""Prepare an OSMnx graph from a local OSM extract or an explicit small Overpass bbox."""

import argparse
import re
from datetime import UTC, datetime
from pathlib import Path

import networkx as nx
import osmnx as ox

from app.models import Dataset

ROOT = Path(__file__).resolve().parents[2]


def numeric_limit(value):
    if isinstance(value, list):
        parsed = [numeric_limit(v) for v in value]
        return min(parsed) if all(v is not None for v in parsed) else None
    if value is None:
        return None
    # Do not guess ambiguous units, conditional tags, feet/inches or semicolon values.
    text = str(value).strip()
    return float(text) if re.fullmatch(r"\d+(\.\d+)?", text) and float(text) > 0 else None


def main():
    parser = argparse.ArgumentParser()
    source = parser.add_mutually_exclusive_group(required=True)
    source.add_argument("--xml", type=Path)
    source.add_argument("--bbox", nargs=4, type=float, metavar=("WEST", "SOUTH", "EAST", "NORTH"))
    parser.add_argument("--name", default="guwahati")
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    ox.settings.use_cache = True
    ox.settings.cache_folder = str(ROOT / "datasets" / "raw" / "osm" / "cache")
    for tag in ("maxheight", "maxweight", "maxwidth", "hgv", "access", "motor_vehicle", "surface"):
        if tag not in ox.settings.useful_tags_way:
            ox.settings.useful_tags_way.append(tag)
    if args.xml:
        graph = ox.graph_from_xml(args.xml, simplify=True, retain_all=True)
    else:
        graph = ox.graph_from_bbox(tuple(args.bbox), network_type="drive", retain_all=True)
    # Keep disconnected components; accessibility checks must not silently discard them.
    graph = ox.routing.add_edge_speeds(graph, fallback=30)
    graph = ox.routing.add_edge_travel_times(graph)
    path = args.output or ROOT / "backend" / "data" / f"osm-{args.name}.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    ox.save_graphml(graph, filepath=path.with_suffix(".graphml"))
    nodes = [
        {"id": str(n), "lon": data["x"], "lat": data["y"], "label": None}
        for n, data in graph.nodes(data=True)
    ]
    largest = max(nx.strongly_connected_components(graph), key=len)
    candidates = sorted(largest, key=lambda n: graph.nodes[n]["x"])
    landmark_ids = [candidates[int(i * (len(candidates) - 1) / 7)] for i in range(8)]
    landmarks = {
        str(n): f"Road junction {i + 1}" for i, n in enumerate(dict.fromkeys(landmark_ids))
    }
    for node in nodes:
        node["label"] = landmarks.get(node["id"])
    edges = []
    for u, v, key, data in graph.edges(keys=True, data=True):
        if data.get("length", 0) <= 0:
            continue
        a, b = graph.nodes[u], graph.nodes[v]
        geometry = (
            list(data["geometry"].coords)
            if "geometry" in data
            else [(a["x"], a["y"]), (b["x"], b["y"])]
        )
        hgv = data.get("hgv")
        allowed = (
            False if hgv in ("no", "private") else True if hgv in ("yes", "designated") else None
        )
        name = data.get("name", data.get("ref", "Unnamed road"))
        if isinstance(name, list):
            name = " / ".join(str(n) for n in name)
        edges.append(
            {
                "id": f"{u}>{v}:{key}",
                "u": str(u),
                "v": str(v),
                "name": str(name),
                "length_m": float(data["length"]),
                "speed_kph": min(160, max(5, float(data["speed_kph"]))),
                "geometry": geometry,
                "risk_data_known": False,
                "evidence": "No verified hazard observation joined",
                "max_height_m": numeric_limit(data.get("maxheight")),
                "max_weight_t": numeric_limit(data.get("maxweight")),
                "max_width_m": numeric_limit(data.get("maxwidth")),
                "hgv_allowed": allowed,
            }
        )
    dataset = Dataset.model_validate(
        {
            "id": f"osm-{args.name}",
            "title": f"{args.name.title()} OSM pilot",
            "region": args.name.title(),
            "source": "OpenStreetMap contributors / Geofabrik; ODbL 1.0",
            "generated_at": datetime.now(UTC).isoformat(),
            "is_synthetic": False,
            "hazard_source": "No verified hazards joined; missing risk is unknown, not safe",
            "limitations": [
                "OSM road coverage and restrictions may be incomplete.",
                "Speeds are estimated from OSM tags/class averages; no live traffic feed.",
                "Historical hazard files are downloaded separately and require reviewed road matching.",
                "No turn restrictions or conditional access enforcement in this prototype.",
                "Terrain remains illustrative until measured DEM samples are integrated.",
            ],
            "nodes": nodes,
            "edges": edges,
            "default_origin": str(landmark_ids[0]),
            "default_destination": str(landmark_ids[-1]),
        }
    )
    path.write_text(dataset.model_dump_json(indent=2), encoding="utf-8")
    print(f"OSMnx prepared {len(nodes):,} nodes, {len(edges):,} edges: {path}")


if __name__ == "__main__":
    main()
