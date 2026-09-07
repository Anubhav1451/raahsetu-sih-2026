"""Extract a local Northeast place gazetteer from the downloaded OSM PBF."""

import json
from collections import defaultdict
from datetime import UTC, datetime
from pathlib import Path

import osmium
from shapely import STRtree
from shapely.geometry import Point, shape

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "datasets"
PLACE_TYPES = {"city", "town", "village", "hamlet", "suburb", "locality"}


class PlaceExtractor(osmium.SimpleHandler):
    def __init__(self, regions):
        super().__init__()
        self.regions = regions
        self.tree = STRtree([polygon for _, polygon in regions])
        self.features = defaultdict(list)

    def node(self, node):
        place_type = node.tags.get("place")
        name = node.tags.get("name:en") or node.tags.get("name")
        if place_type not in PLACE_TYPES or not name or not node.location.valid():
            return
        point = Point(node.location.lon, node.location.lat)
        matches = self.tree.query(point, predicate="intersects")
        if len(matches) != 1:
            return
        region = self.regions[int(matches[0])][0]
        population = node.tags.get("population")
        self.features[region].append(
            {
                "type": "Feature",
                "geometry": {
                    "type": "Point",
                    "coordinates": [node.location.lon, node.location.lat],
                },
                "properties": {
                    "osm_id": f"node/{node.id}",
                    "name": name,
                    "place": place_type,
                    "population": population,
                    "source": "OpenStreetMap contributors",
                },
            }
        )


def main() -> None:
    boundaries = json.loads(
        (DATA / "processed/boundaries/northeast-states.geojson").read_text(encoding="utf-8")
    )
    regions = [
        (
            feature["properties"]["shapeName"].lower().replace(" ", "-"),
            shape(feature["geometry"]),
        )
        for feature in boundaries["features"]
    ]
    handler = PlaceExtractor(regions)
    source = DATA / "raw/osm/north-eastern-zone-latest.osm.pbf"
    handler.apply_file(str(source), locations=False)

    output = DATA / "processed/osm"
    summary = []
    for region, _ in regions:
        features = sorted(
            handler.features[region],
            key=lambda feature: (
                feature["properties"]["place"],
                feature["properties"]["name"].casefold(),
            ),
        )
        path = output / f"{region}-places.geojson"
        path.write_text(
            json.dumps({"type": "FeatureCollection", "features": features}),
            encoding="utf-8",
        )
        summary.append(
            {"region": region, "places": len(features), "file": str(path.relative_to(ROOT))}
        )

    (output / "places-summary.json").write_text(
        json.dumps(
            {
                "generated_at": datetime.now(UTC).isoformat(),
                "source": str(source.relative_to(ROOT)),
                "place_types": sorted(PLACE_TYPES),
                "states": summary,
                "limitations": "OSM names and place classification vary; this is a local search gazetteer, not an official administrative register.",
            },
            indent=2,
        ),
        encoding="utf-8",
    )
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
