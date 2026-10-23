"""Merge real state snapshots by OSM node identity; never bridge missing roads.

Uses disk-backed staging and streaming JSON to avoid loading eight graphs at once.
Overlapping state edges retain namespaced identities, restrictions and full shapes.
"""

import json
import shutil
import sqlite3
import tempfile
from contextlib import closing
from datetime import UTC, datetime
from pathlib import Path

import ijson

ROOT = Path(__file__).resolve().parents[1]
STATES = (
    "assam",
    "arunachal-pradesh",
    "manipur",
    "meghalaya",
    "mizoram",
    "nagaland",
    "sikkim",
    "tripura",
)


def main():
    paths = [ROOT / "data" / f"osm-{state}-real.json" for state in STATES]
    if any(not p.exists() for p in paths):
        raise RuntimeError("All eight real snapshots are required")
    output = ROOT / "data/osm-ner-roads.json"
    with tempfile.TemporaryDirectory(prefix="raahsetu-merge-") as temp:  # noqa: SIM117
        with closing(sqlite3.connect(Path(temp) / "merge.sqlite")) as db:
            db.execute("CREATE TABLE nodes (id TEXT PRIMARY KEY, payload TEXT, lon REAL, lat REAL)")
            db.execute("CREATE TABLE edges (id TEXT PRIMARY KEY, payload TEXT, u TEXT, v TEXT)")
            for state, path in zip(STATES, paths, strict=True):
                with path.open("rb") as handle:
                    synthetic = next(ijson.items(handle, "is_synthetic"))
                if synthetic:
                    raise RuntimeError(f"Synthetic source rejected: {path.name}")
                for kind in ("nodes", "edges"):
                    with path.open("rb") as handle:
                        for item in ijson.items(handle, f"{kind}.item", use_float=True):
                            if kind == "edges":
                                item["id"] = f"{state}:{item['id']}"
                            extra = (
                                (item["lon"], item["lat"])
                                if kind == "nodes"
                                else (item["u"], item["v"])
                            )
                            db.execute(
                                f"INSERT OR IGNORE INTO {kind} VALUES (?, ?, ?, ?)",
                                (item["id"], json.dumps(item, separators=(",", ":")), *extra),
                            )
                    db.commit()
                print(f"Merged {state}", flush=True)
            first = db.execute("SELECT id FROM nodes ORDER BY id LIMIT 1").fetchone()[0]
            meta = {
                "id": "osm-ner-roads",
                "title": "NER real OSM road snapshots",
                "region": "Northeast India",
                "source": "OpenStreetMap contributors / Geofabrik; ODbL 1.0",
                "generated_at": datetime.now(UTC).isoformat(),
                "is_synthetic": False,
                "hazard_source": "Inherited snapshot evidence; missing observations remain unknown",
                "limitations": [
                    "No invented cross-border connectors; disconnected routes stay unreachable.",
                    "Snapshot coverage, turn restrictions and live accessibility are not guaranteed.",
                ],
                "default_origin": first,
                "default_destination": first,
            }
            partial = output.with_suffix(".tmp")
            with partial.open("w", encoding="utf-8") as handle:
                handle.write(json.dumps(meta)[:-1])
                for kind in ("nodes", "edges"):
                    handle.write(f',"{kind}":[')
                    sep = ""
                    for (payload,) in db.execute(f"SELECT payload FROM {kind} ORDER BY id"):
                        handle.write(sep + payload)
                        sep = ","
                    handle.write("]")
                handle.write("}")
            partial.replace(output)
            db.execute("CREATE INDEX node_location ON nodes(lon, lat)")
            db.execute("CREATE INDEX edge_start ON edges(u)")
            db.execute("CREATE TABLE metadata (payload TEXT)")
            db.execute("INSERT INTO metadata VALUES (?)", (json.dumps(meta),))
            db.commit()
            shutil.copyfile(Path(temp) / "merge.sqlite", output.with_suffix(".sqlite"))
            print(
                {
                    kind: db.execute(f"SELECT count(*) FROM {kind}").fetchone()[0]
                    for kind in ("nodes", "edges")
                },
                flush=True,
            )


if __name__ == "__main__":
    main()
