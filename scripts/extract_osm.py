"""Extract reference-complete drivable ways by state and a Guwahati pilot window.

Pyosmium decodes PBF; OSMnx remains the street-graph processing library. State
polygons are buffered by ~2 km to preserve cross-border connections. Raw PBFs
retain all tags/relations; these road-only extracts do not include turn relations.
"""

import argparse
import json
from contextlib import ExitStack
from pathlib import Path

import osmium
from shapely import STRtree
from shapely.geometry import LineString, Point, box, shape

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "datasets"
DRIVABLE = {
    "motorway",
    "trunk",
    "primary",
    "secondary",
    "tertiary",
    "unclassified",
    "residential",
    "living_street",
    "service",
    "motorway_link",
    "trunk_link",
    "primary_link",
    "secondary_link",
    "tertiary_link",
}


class Extractor(osmium.SimpleHandler):
    def __init__(self, regions, writers):
        super().__init__()
        self.regions = regions
        self.writers = writers
        self.polygons = [r[1] for r in regions]
        self.tree = STRtree(self.polygons)
        self.counts = {r[0]: 0 for r in regions}
        self.facilities = {r[0]: [] for r in regions}

    def facility(self, osm_id, point, tags):
        kind = tags.get("amenity") or tags.get("building") or tags.get("landuse")
        if kind not in {
            "hospital",
            "clinic",
            "pharmacy",
            "fire_station",
            "police",
            "fuel",
            "warehouse",
        }:
            return
        for index in self.tree.query(point, predicate="intersects"):
            name = self.regions[int(index)][0]
            self.facilities[name].append(
                {
                    "type": "Feature",
                    "geometry": {"type": "Point", "coordinates": [point.x, point.y]},
                    "properties": {
                        "osm_id": osm_id,
                        "kind": kind,
                        "name": tags.get("name", "Unnamed facility"),
                        "source": "OpenStreetMap contributors",
                        "verified_operational": False,
                    },
                }
            )

    def node(self, node):
        if node.location.valid() and ("amenity" in node.tags or "building" in node.tags):
            self.facility(f"node/{node.id}", Point(node.location.lon, node.location.lat), node.tags)

    def way(self, way):
        is_road = way.tags.get("highway") in DRIVABLE
        is_facility = any(k in way.tags for k in ("amenity", "building"))
        if not is_road and not is_facility:
            return
        if not all(n.location.valid() for n in way.nodes) or len(way.nodes) < 2:
            return
        line = LineString([(n.lon, n.lat) for n in way.nodes])
        if is_facility:
            self.facility(f"way/{way.id}", line.centroid, way.tags)
        if not is_road:
            return
        # Restricted roads stay in raw PBF. The public drive network omits these ways.
        if any(
            way.tags.get(key) in {"no", "private"} for key in ("access", "motor_vehicle", "vehicle")
        ):
            return
        for index in self.tree.query(line, predicate="intersects"):
            name = self.regions[int(index)][0]
            self.writers[name].add_way(way)
            self.counts[name] += 1


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--only", help="Rebuild just one region, e.g. sikkim")
    args = parser.parse_args()
    boundaries = json.loads(
        (DATA / "processed/boundaries/northeast-states.geojson").read_text(encoding="utf-8")
    )
    regions = [
        (
            f["properties"]["shapeName"].lower().replace(" ", "-"),
            shape(f["geometry"]).simplify(0.0005).buffer(0.02),
        )
        for f in boundaries["features"]
    ]
    out = DATA / "processed/osm"
    out.mkdir(parents=True, exist_ok=True)
    summary_path = out / "extraction-summary.json"
    summary = (
        json.loads(summary_path.read_text(encoding="utf-8"))
        if args.only and summary_path.exists()
        else []
    )
    # Geofabrik's North-Eastern polygon covers all eight states, including Sikkim.
    for zone in ("north-eastern",):
        selected = regions + [("guwahati-pilot", box(91.70, 26.13, 91.79, 26.19))]
        if args.only:
            selected = [(name, poly) for name, poly in selected if name == args.only]
            if not selected:
                raise ValueError("Unknown region")
            summary = [r for r in summary if r["region"] != args.only]
        source = DATA / f"raw/osm/{zone}-zone-latest.osm.pbf"
        with ExitStack() as stack:
            writers = {
                name: stack.enter_context(
                    osmium.BackReferenceWriter(
                        out / f"{name}-roads.osm", source, overwrite=True, remove_tags=False
                    )
                )
                for name, _ in selected
            }
            handler = Extractor(selected, writers)
            handler.apply_file(str(source), locations=True, idx="sparse_mem_array")
            print(f"Filtered {zone}: {handler.counts}", flush=True)
        for name, _ in selected:
            features = handler.facilities[name]
            (out / f"{name}-facilities.geojson").write_text(
                json.dumps({"type": "FeatureCollection", "features": features}), encoding="utf-8"
            )
            summary.append(
                {
                    "region": name,
                    "road_ways": handler.counts[name],
                    "facility_features": len(features),
                    "source": str(source.relative_to(ROOT)),
                    "output": str((out / f"{name}-roads.osm").relative_to(ROOT)),
                    "boundary_buffer_degrees": 0.02 if name != "guwahati-pilot" else 0,
                    "limitations": "OSM completeness varies; facility operation unverified; no turn relations",
                }
            )
        print(f"Reference-complete {zone} extracts saved.", flush=True)
    (out / "extraction-summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")


if __name__ == "__main__":
    main()
