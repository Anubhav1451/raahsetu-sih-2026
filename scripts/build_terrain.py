"""Sample downloaded HGT elevation for the OSM pilot; retain voids as null."""

import gzip
import json
import math
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]


def main():
    dataset = json.loads((ROOT / "backend/data/osm-guwahati.json").read_text(encoding="utf-8"))
    points = [p for e in dataset["edges"] for p in e["geometry"]]
    west = min(p[0] for p in points) - 0.025
    east = max(p[0] for p in points) + 0.025
    south = min(p[1] for p in points) - 0.025
    north = max(p[1] for p in points) + 0.025
    tiles = {}
    for lat in range(math.floor(south), math.ceil(north)):
        for lon in range(math.floor(west), math.ceil(east)):
            tile = f"N{lat:02}E{lon:03}"
            path = ROOT / f"datasets/raw/terrain/{tile}.hgt.gz"
            if path.exists():
                with gzip.open(path, "rb") as file:
                    values = np.frombuffer(file.read(), dtype=">i2")
                side = math.isqrt(len(values))
                if side * side != len(values):
                    raise ValueError(f"Invalid HGT dimensions: {tile}")
                tiles[(lat, lon)] = values.reshape(side, side)
    rows, cols = 100, 120
    values = []
    for row in range(rows):
        lat = north - (north - south) * row / (rows - 1)
        line = []
        for col in range(cols):
            lon = west + (east - west) * col / (cols - 1)
            key = (math.floor(lat), math.floor(lon))
            tile = tiles.get(key)
            if tile is None:
                line.append(None)
                continue
            size = tile.shape[0] - 1
            y = min(size, max(0, round((key[0] + 1 - lat) * size)))
            x = min(size, max(0, round((lon - key[1]) * size)))
            elevation = int(tile[y, x])
            line.append(elevation if elevation != -32768 else None)
        values.append(line)
    grid = {
        "west": west,
        "east": east,
        "south": south,
        "north": north,
        "rows": rows,
        "cols": cols,
        "values": values,
        "units": "metres",
        "source": "Tilezen / AWS Terrain Tiles, Skadi HGT",
        "vertical_exaggeration": 2,
        "void_samples": sum(v is None for r in values for v in r),
        "note": "Resampled elevation for visualization; vertical scale exaggerated 2x. Not a landslide model.",
    }
    out = ROOT / "backend/data/osm-guwahati-terrain.json"
    out.write_text(json.dumps(grid), encoding="utf-8")
    dataset["terrain_source"] = (
        "Tilezen / AWS Terrain Tiles Skadi HGT, resampled, 2x vertical exaggeration"
    )
    dataset["limitations"] = [
        s for s in dataset["limitations"] if not s.startswith("Terrain remains illustrative")
    ]
    (ROOT / "backend/data/osm-guwahati.json").write_text(json.dumps(dataset), encoding="utf-8")
    print(f"Terrain samples: {rows * cols}; missing: {grid['void_samples']}")


if __name__ == "__main__":
    main()
