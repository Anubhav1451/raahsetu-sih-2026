"""Download versioned public source files with provenance and content hashes.

Safe to rerun: verified existing downloads are reused. Partial downloads are never
treated as usable data. This is a curated inventory, not a claim of exhaustive access.
"""

import argparse
import concurrent.futures
import hashlib
import json
import time
import urllib.request
from datetime import UTC, datetime
from pathlib import Path
from urllib.parse import urlsplit, urlunsplit

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "datasets"

SOURCES = [
    {
        "id": "osm_northeast",
        "url": "https://download.geofabrik.de/asia/india/north-eastern-zone-latest.osm.pbf",
        "file": "raw/osm/north-eastern-zone-latest.osm.pbf",
        "license": "ODbL 1.0; OpenStreetMap contributors",
        "purpose": "Raw OSM nodes, ways and relations; routing and facilities",
        "coverage": "Geofabrik North-Eastern Zone; verify polygon for exact coverage",
    },
    {
        "id": "osm_eastern",
        "url": "https://download.geofabrik.de/asia/india/eastern-zone-latest.osm.pbf",
        "file": "raw/osm/eastern-zone-latest.osm.pbf",
        "license": "ODbL 1.0; OpenStreetMap contributors",
        "purpose": "Optional adjacent-region context; not needed for core eight-state coverage",
        "coverage": "Eastern Zone overlaps only the southern Sikkim border; North-Eastern Zone covers Sikkim fully",
    },
    {
        "id": "osm_northeast_polygon",
        "url": "https://download.geofabrik.de/asia/india/north-eastern-zone.poly",
        "file": "raw/osm/north-eastern-zone.poly",
        "license": "Geofabrik extract metadata",
        "purpose": "Exact regional extract boundary",
        "coverage": "North-Eastern Zone",
    },
    {
        "id": "osm_eastern_polygon",
        "url": "https://download.geofabrik.de/asia/india/eastern-zone.poly",
        "file": "raw/osm/eastern-zone.poly",
        "license": "Geofabrik extract metadata",
        "purpose": "Exact regional extract boundary",
        "coverage": "Eastern Zone",
    },
    {
        "id": "morth_accidents_2023",
        "url": "https://morth.nic.in/sites/default/files/Road-Accident-in-India-2023-Publications.pdf",
        "file": "raw/road_safety/morth-road-accidents-2023.pdf",
        "license": "Government publication; verify reuse terms",
        "purpose": "Official aggregate road safety statistics; not geolocated edge risk",
        "coverage": "India including all eight NE states; reporting year 2023",
    },
    {
        "id": "morth_blackspot_measures",
        "url": "https://morth.nic.in/sites/default/files/Black_Spots_measure.pdf",
        "file": "raw/road_safety/morth-blackspot-measures.pdf",
        "license": "Government publication; verify reuse terms",
        "purpose": "Blackspot identification/rectification context; not a coordinate inventory",
        "coverage": "State-level summary",
    },
]


def digest(path):
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def download(source):
    path = DATA / source["file"]
    receipt = path.with_suffix(path.suffix + ".receipt.json")
    if path.exists() and receipt.exists():
        previous = json.loads(receipt.read_text(encoding="utf-8"))
        if digest(path) == previous.get("sha256"):
            print(f"REUSE {source['id']} ({path.stat().st_size:,} bytes)", flush=True)
            return previous
    path.parent.mkdir(parents=True, exist_ok=True)
    part = path.with_suffix(path.suffix + ".part")
    record = {**source, "accessed_at": datetime.now(UTC).isoformat()}
    for attempt in range(3):
        try:
            req = urllib.request.Request(
                source["url"], headers={"User-Agent": "RaahSetu-SIH-Research/0.1"}
            )
            with urllib.request.urlopen(req, timeout=90) as response, part.open("wb") as f:
                resolved = urlsplit(response.url)
                record["resolved_url"] = urlunsplit(
                    (resolved.scheme, resolved.netloc, resolved.path, "", "")
                )
                record["last_modified"] = response.headers.get("Last-Modified")
                record["content_type"] = response.headers.get("Content-Type")
                expected = int(response.headers.get("Content-Length", "0"))
                count = 0
                for chunk in iter(lambda: response.read(1024 * 1024), b""):
                    f.write(chunk)
                    count += len(chunk)
                if expected and count != expected:
                    raise ValueError(f"Incomplete response: expected {expected}, got {count}")
            prefix = part.open("rb").read(64)
            if path.suffix == ".pdf" and not prefix.startswith(b"%PDF"):
                raise ValueError("Source returned a non-PDF response")
            if path.suffix == ".pbf" and (b"html" in prefix.lower() or count < 1000):
                raise ValueError("Source returned a non-PBF response")
            if path.suffix in (".json", ".geojson"):
                json.loads(part.read_text(encoding="utf-8"))
            part.replace(path)
            record.update(status="downloaded", bytes=path.stat().st_size, sha256=digest(path))
            receipt.write_text(json.dumps(record, indent=2), encoding="utf-8")
            print(f"OK {source['id']} ({record['bytes']:,} bytes)", flush=True)
            return record
        except Exception as exc:
            record.update(status="unavailable", error=f"{type(exc).__name__}: {exc}")
            if attempt < 2:
                time.sleep(2 * (attempt + 1))
    print(f"GAP {source['id']}: {record['error']}", flush=True)
    return record


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--catalog", type=Path)
    args = parser.parse_args()
    sources = json.loads(args.catalog.read_text(encoding="utf-8")) if args.catalog else SOURCES
    DATA.mkdir(exist_ok=True)
    with concurrent.futures.ThreadPoolExecutor(max_workers=3) as pool:
        records = list(pool.map(download, sources))
    suffix = args.catalog.stem if args.catalog else "core"
    manifest = DATA / f"manifest-{suffix}.json"
    manifest.write_text(json.dumps(records, indent=2), encoding="utf-8")
    print(f"Manifest: {manifest}", flush=True)


if __name__ == "__main__":
    main()
