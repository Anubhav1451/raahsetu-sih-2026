"""Transactional PostGIS graph/CSV import and immutable JSON snapshot export."""

import argparse
import csv
import json
import os
from pathlib import Path

import psycopg
from dotenv import load_dotenv
from psycopg.types.json import Jsonb

from app.models import Dataset, Edge, Node
from app.routing import RoadGraph

ROOT = Path(__file__).resolve().parents[2]
load_dotenv(ROOT / ".env")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "action",
        choices=[
            "apply-migration",
            "import-regions",
            "import-graph",
            "import-hazards",
            "export-graph",
            "reconcile-hash",
            "verify-hazard-candidates",
            "status",
        ],
    )
    parser.add_argument("path", type=Path, nargs="?")
    parser.add_argument("--dataset-id")
    args = parser.parse_args()
    url = os.getenv("DATABASE_URL")
    if not url:
        raise SystemExit(
            "Set DATABASE_URL in the root .env file; never put it in frontend settings."
        )
    with psycopg.connect(url, sslmode="require") as conn:
        conn.execute("set search_path = public, extensions")
        if args.action == "apply-migration":
            if args.path is None:
                raise SystemExit("Migration SQL path is required")
            conn.execute(args.path.read_text(encoding="utf-8"))
            print(f"Applied migration: {args.path}")
        elif args.action == "import-regions":
            catalog_path = args.path or ROOT / "datasets/processed/ne-coverage-catalog.json"
            boundary_path = ROOT / "datasets/processed/boundaries/northeast-states.geojson"
            catalog = json.loads(catalog_path.read_text(encoding="utf-8"))
            boundaries = json.loads(boundary_path.read_text(encoding="utf-8"))
            boundary_by_name = {
                feature["properties"]["shapeName"]: feature["geometry"]
                for feature in boundaries["features"]
            }
            for record in catalog["records"]:
                code = record["state"].lower().replace(" ", "-")
                capital = record["capital_coordinates"]
                conn.execute(
                    """insert into region_catalog
                    (code,state_name,capital_name,capital_geom,boundary,road_ways,
                     place_features,facility_features,runtime_graph,source_metadata,updated_at)
                    values(%s,%s,%s,st_setsrid(st_makepoint(%s,%s),4326),
                     st_multi(st_setsrid(st_geomfromgeojson(%s),4326)),%s,%s,%s,%s,%s,now())
                    on conflict(code) do update set
                      state_name=excluded.state_name, capital_name=excluded.capital_name,
                      capital_geom=excluded.capital_geom, boundary=excluded.boundary,
                      road_ways=excluded.road_ways, place_features=excluded.place_features,
                      facility_features=excluded.facility_features,
                      runtime_graph=excluded.runtime_graph,
                      source_metadata=excluded.source_metadata, updated_at=now()""",
                    (
                        code,
                        record["state"],
                        record["capital"],
                        capital["lon"],
                        capital["lat"],
                        json.dumps(boundary_by_name[record["state"]]),
                        record["road_ways"],
                        record.get("place_features", 0),
                        record["facility_features"],
                        Jsonb(record.get("runtime_graph")),
                        Jsonb(
                            {
                                "osm_source": record["osm_source"],
                                "roads_file": record["roads_file"],
                                "places_file": record.get("places_file"),
                                "facilities_file": record["facilities_file"],
                                "facility_status": record["facility_status"],
                            }
                        ),
                    ),
                )
            print(f"Imported {len(catalog['records'])} Northeast region records.")
        elif args.action == "status":
            size = conn.execute("select pg_database_size(current_database())").fetchone()[0]
            tables = conn.execute(
                """select relname, pg_total_relation_size(relid)
                from pg_catalog.pg_statio_user_tables
                order by pg_total_relation_size(relid) desc"""
            ).fetchall()
            print(json.dumps({"database_bytes": size, "tables": dict(tables)}, indent=2))
        elif args.action == "import-graph":
            if args.path is None:
                raise SystemExit("Graph JSON path is required")
            dataset = Dataset.model_validate_json(args.path.read_text(encoding="utf-8"))
            graph = RoadGraph(dataset)
            existing = conn.execute(
                "select content_hash from dataset_versions where id=%s", (dataset.id,)
            ).fetchone()
            if existing:
                if existing[0] == graph.version:
                    print("Identical graph already imported.")
                    return
                raise SystemExit(
                    "Dataset ID exists with different content. Choose a new version ID."
                )
            conn.execute(
                "insert into dataset_versions(id,content_hash,metadata) values(%s,%s,%s)",
                (dataset.id, graph.version, Jsonb(dataset.model_dump(exclude={"nodes", "edges"}))),
            )
            with conn.cursor() as cur:
                cur.executemany(
                    "insert into road_nodes values (%s,%s,%s,st_setsrid(st_makepoint(%s,%s),4326))",
                    [(dataset.id, n.id, n.label, n.lon, n.lat) for n in dataset.nodes],
                )
                cur.executemany(
                    "insert into road_edges values (%s,%s,%s,%s,%s,st_setsrid(st_geomfromgeojson(%s),4326),%s)",
                    [
                        (
                            dataset.id,
                            e.id,
                            e.u,
                            e.v,
                            e.name,
                            json.dumps({"type": "LineString", "coordinates": e.geometry}),
                            Jsonb(e.model_dump(exclude={"geometry"})),
                        )
                        for e in dataset.edges
                    ],
                )
            print(
                f"Imported {len(dataset.nodes)} nodes and {len(dataset.edges)} edges transactionally."
            )
        elif args.action == "import-hazards":
            if args.path is None:
                raise SystemExit("Hazard CSV path is required")
            with args.path.open(encoding="utf-8-sig", newline="") as f:
                rows = list(csv.DictReader(f))
            for row in rows:
                node = Node(
                    id="validation", lon=float(row["longitude"]), lat=float(row["latitude"])
                )
                severity = float(row["severity"])
                if not 0 <= severity <= 1:
                    raise ValueError("severity must be between 0 and 1")
                conn.execute(
                    """insert into hazard_observations
                    (source,source_record_id,kind,severity,geom,observed_at,is_synthetic,details)
                    values(%s,%s,%s,%s,st_setsrid(st_makepoint(%s,%s),4326),%s,%s,%s)
                    on conflict(source,source_record_id) do nothing""",
                    (
                        row["source"],
                        row["source_record_id"],
                        row["kind"],
                        severity,
                        node.lon,
                        node.lat,
                        row["observed_at"],
                        row.get("is_synthetic", "false").lower() == "true",
                        Jsonb(row),
                    ),
                )
            print(f"Processed {len(rows)} observations. Review road matches before assigning risk.")
        elif args.action in {"export-graph", "reconcile-hash"}:
            if not args.dataset_id:
                raise SystemExit("--dataset-id is required")
            if args.path is None:
                raise SystemExit("Graph path is required")
            record = conn.execute(
                "select metadata,content_hash from dataset_versions where id=%s", (args.dataset_id,)
            ).fetchone()
            if not record:
                raise SystemExit("Unknown dataset ID")
            metadata = dict(record[0])
            metadata["nodes"] = [
                Node(id=r[0], label=r[1], lon=r[2], lat=r[3]).model_dump()
                for r in conn.execute(
                    "select node_id,label,st_x(geom),st_y(geom) from road_nodes where dataset_id=%s order by node_id",
                    (args.dataset_id,),
                )
            ]
            metadata["edges"] = [
                Edge(**r[0], geometry=json.loads(r[1])["coordinates"]).model_dump()
                for r in conn.execute(
                    "select attributes,st_asgeojson(geom) from road_edges where dataset_id=%s order by edge_id",
                    (args.dataset_id,),
                )
            ]
            dataset = Dataset.model_validate(metadata)
            if args.action == "export-graph":
                args.path.write_text(dataset.model_dump_json(indent=2), encoding="utf-8")
                print(
                    f"Exported immutable base graph: {args.path}. "
                    "Hazard scoring requires reviewed joins."
                )
            else:
                local = Dataset.model_validate_json(args.path.read_text(encoding="utf-8"))
                database_version = RoadGraph(dataset).version
                local_version = RoadGraph(local).version
                if database_version != local_version:
                    raise SystemExit("Database graph differs from the supplied local graph; hash unchanged.")
                conn.execute(
                    "update dataset_versions set content_hash=%s where id=%s",
                    (database_version, args.dataset_id),
                )
                print(
                    f"Verified identical graph content and reconciled version hash: {database_version}"
                )
        else:
            rows = conn.execute(
                "select id,source_record_id from hazard_observations order by observed_at,id"
            ).fetchall()
            results = []
            for hazard_id, source_record_id in rows:
                candidates = conn.execute(
                    "select edge_id,distance_m from hazard_edge_candidates(%s,%s,%s)",
                    (args.dataset_id, hazard_id, 2000.0),
                ).fetchall()
                results.append(
                    {
                        "source_record_id": source_record_id,
                        "candidate_count": len(candidates),
                        "nearest_distance_m": round(candidates[0][1], 1) if candidates else None,
                    }
                )
            print(json.dumps(results, indent=2))


if __name__ == "__main__":
    main()
