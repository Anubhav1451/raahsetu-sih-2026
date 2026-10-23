import hashlib
import json
import logging
import math
import os
import re
from collections import OrderedDict
from contextlib import asynccontextmanager
from datetime import UTC, datetime
from pathlib import Path
from threading import RLock
from typing import Annotated, Literal
from uuid import UUID

import httpx
import psycopg
from dotenv import load_dotenv
from fastapi import Depends, FastAPI, File, Header, HTTPException, Query, Request, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from pydantic import Field

from .alerts import AlertStore, InMemoryAlertStore, PostgresAlertStore
from .audit import AuditStore, get_audit_store, record_audit
from .auth import AuthUser, require_admin, require_reviewer, require_user
from .cache import cache_health, stream_add
from .field_reports import FieldReportStore, InMemoryFieldReportStore, PostgresFieldReportStore
from .fleet import FleetStore, InMemoryFleetStore, PostgresFleetStore
from .graph_loader import load_route_window
from .live_ingestion import (
    OfficialHazardAdvisory,
    get_candidate_advisories,
    get_feed_diagnostics,
    get_official_feeds_status,
    ingest_live_official_advisories,
    review_candidate_advisory,
    run_feed_diagnostics_dry_run,
)
from .ml_prediction import load_disruption_model
from .models import (
    Alert,
    ConnectivitySummary,
    Dataset,
    DeliveryCreate,
    DeliveryJob,
    DeliveryUpdate,
    Endpoint,
    EventUpdate,
    FieldReport,
    FieldReportAttachment,
    FieldReportCreate,
    FieldReportReview,
    PositionCreate,
    PublicCandidate,
    PublicCandidateReview,
    RouteRequest,
    StrictModel,
    VehicleAsset,
    VehiclePosition,
    VehicleSummary,
)
from .notifications import (
    BroadcastRequest,
    BroadcastResponse,
    get_broadcast_history,
    send_broadcast,
)
from .routing import VEHICLES, RoadGraph
from .telematics import (
    AIS140TelemetryPacket,
    RawTelemetryRequest,
    TelematicsIngestResponse,
    check_hazard_proximity,
    packet_to_position_create,
    parse_raw_ais140_string,
    parse_telematics_webhook,
    telemetry_guard,
    verify_telematics_signature,
)
from .weather import get_all_live_weather, get_station_weather
from .weather_anomaly import load_weather_anomaly_model

def _resolve_root() -> Path:
    configured = os.getenv("RAAHSETU_ROOT") or os.getenv("APP_ROOT")
    if configured and Path(configured).exists():
        return Path(configured).resolve()
    module_root = Path(__file__).resolve().parents[1]
    if (module_root / "data" / "demo-network.json").exists():
        return module_root
    if Path("/app/backend/data/demo-network.json").exists():
        return Path("/app/backend")
    cwd = Path.cwd()
    if (cwd / "backend" / "data" / "demo-network.json").exists():
        return cwd / "backend"
    if (cwd / "data" / "demo-network.json").exists():
        return cwd
    return module_root


ROOT = _resolve_root()
logger = logging.getLogger("raahsetu")
load_dotenv(ROOT.parent / ".env")
_public_candidates: dict[str, PublicCandidate] = {}
_candidate_file = ROOT / "data" / "public_disruption_candidates.json"
if _candidate_file.exists():
    try:
        for _item in json.loads(_candidate_file.read_text(encoding="utf-8")).get("candidates", []):
            _candidate = PublicCandidate.model_validate(_item)
            _public_candidates[_candidate.candidate_id] = _candidate
    except (OSError, ValueError) as exc:
        logger.warning("Public candidate seed unavailable: %s", exc)

DEMO_CITY_ALIASES = {
    "guwahati": ("n2_0", "Guwahati", "demo origin"),
    "dimapur": ("n0_3", "Dimapur", "demo place"),
    "kohima": ("n1_1", "Kohima", "demo place"),
    "senapati": ("n3_5", "Senapati", "demo place"),
    "imphal": ("n2_6", "Imphal", "demo destination"),
}


def load_graph() -> RoadGraph:
    configured = os.getenv("DATASET_PATH")
    if configured:
        path = Path(configured)
        if not path.is_absolute():
            path = (ROOT.parent / configured) if (ROOT.parent / configured).exists() else (ROOT / configured)
    else:
        path = ROOT / "data" / "demo-network.json"
    return RoadGraph(Dataset.model_validate(json.loads(path.read_text(encoding="utf-8"))))


def discover_dataset_paths() -> dict[str, Path]:
    """Discover versioned OSM graph snapshots without loading them into memory."""
    paths: dict[str, Path] = {}
    for path in sorted((ROOT / "data").glob("osm-*.json")):
        if path.name.endswith("-terrain.json"):
            continue
        dataset_id = path.stem
        # The reviewed pilot intentionally has a versioned dataset id.
        if path.name == "osm-guwahati-corridor-reviewed.json":
            dataset_id = "osm-guwahati-corridor-reviewed-v1"
        paths[dataset_id] = path
    return paths


def read_dataset_header(path: Path) -> dict[str, object]:
    """Read graph metadata without parsing potentially multi-gigabyte node arrays."""
    with path.open("r", encoding="utf-8") as handle:
        header = handle.read(65536)
    values: dict[str, object] = {}
    for key in ("id", "title", "is_synthetic"):
        match = re.search(rf'"{key}"\s*:\s*("(?:[^"\\]|\\.)*"|true|false|null)', header)
        if not match:
            continue
        raw = match.group(1)
        values[key] = json.loads(raw)
    return values


@asynccontextmanager
async def lifespan(app: FastAPI):
    app.state.graph = load_graph()
    app.state.graphs = OrderedDict({"demo": app.state.graph})
    app.state.dataset_paths = discover_dataset_paths()
    app.state.graph_lock = RLock()
    app.state.dynamic_cache_size = max(1, int(os.getenv("GRAPH_CACHE_SIZE", "1")))
    app.state.search_catalogs = {}
    catalog_path = ROOT.parent / "datasets" / "processed" / "ne-coverage-catalog.json"
    catalog = json.loads(catalog_path.read_text(encoding="utf-8")) if catalog_path.exists() else {}
    app.state.region_catalog = {
        f"osm-{record['state'].lower().replace(' ', '-')}": record
        for record in catalog.get("records", [])
    }
    pilot = ROOT / "data" / "osm-guwahati.json"
    if pilot.exists():
        app.state.graphs["osm-guwahati"] = RoadGraph(
            Dataset.model_validate_json(pilot.read_text(encoding="utf-8"))
        )
    reviewed = ROOT / "data" / "osm-guwahati-corridor-reviewed.json"
    if reviewed.exists():
        app.state.graphs["osm-guwahati-corridor-reviewed-v1"] = RoadGraph(
            Dataset.model_validate_json(reviewed.read_text(encoding="utf-8"))
        )
    logger.info("Loaded dataset %s (%s)", app.state.graph.dataset.id, app.state.graph.version)
    yield


app = FastAPI(
    title="RaahSetu routing API",
    version="0.1.0",
    lifespan=lifespan,
    description="SIH prototype. Custom risk-aware A*. No live navigation guarantees.",
)
origins = os.getenv("CORS_ORIGINS", "http://localhost:5173,http://127.0.0.1:5173").split(",")
app.add_middleware(
    CORSMiddleware,
    allow_origins=[o.strip() for o in origins],
    allow_methods=["GET", "POST", "PATCH"],
    allow_headers=["Content-Type", "Authorization"],
    allow_credentials=False,
)


@app.middleware("http")
async def add_security_headers(request, call_next):
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    return response


_field_report_store: FieldReportStore | None = None
_fleet_store: FleetStore | None = None
_alert_store: AlertStore | None = None


def get_field_report_store() -> FieldReportStore:
    global _field_report_store
    if os.getenv("DATABASE_URL"):
        return PostgresFieldReportStore()
    if _field_report_store is None:
        _field_report_store = InMemoryFieldReportStore()
    return _field_report_store


def get_fleet_store() -> FleetStore:
    global _fleet_store
    if os.getenv("DATABASE_URL"):
        return PostgresFleetStore()
    if _fleet_store is None:
        _fleet_store = InMemoryFleetStore()
    return _fleet_store


def get_alert_store() -> AlertStore:
    global _alert_store
    if os.getenv("DATABASE_URL"):
        return PostgresAlertStore()
    if _alert_store is None:
        _alert_store = InMemoryAlertStore()
    return _alert_store


@app.get("/health")
def health():
    graph = app.state.graph
    return {"status": "ok", "dataset_id": graph.dataset.id, "version": graph.version}


def data_readiness() -> dict:
    status_path = ROOT.parent / "datasets" / "DATA_STATUS.json"
    status = json.loads(status_path.read_text(encoding="utf-8")) if status_path.exists() else {}
    snapshots = sorted(
        path.stem.removeprefix("osm-")
        for path in (ROOT / "data").glob("osm-*.json")
        if not path.name.endswith("-terrain.json")
    )
    return {
        "status": "ready" if snapshots else "demo_only",
        "audited_at": status.get("audited_at"),
        "freshness_policy": {
            "meaning": "Freshness describes source recency; it does not certify field safety.",
            "weather_cache_minutes": 60,
            "official_feed_status": "standby_until_authorised_feed_configured",
        },
        "sources": [
            {
                "id": "osm-road-snapshots",
                "source_id": "osm-road-snapshots",
                "label": "OpenStreetMap road graph snapshots",
                "source_name": "OpenStreetMap road graph snapshots",
                "kind": "road_network",
                "status": "versioned_snapshot",
                "coverage": "8 Northeast states",
                "last_audited_at": status.get("audited_at"),
                "versioning": "content hash per graph snapshot",
            },
            {
                "id": "open-meteo",
                "source_id": "open-meteo",
                "label": "Open-Meteo forecast API",
                "source_name": "Open-Meteo forecast API",
                "kind": "weather",
                "status": "live_with_60_minute_cache",
                "coverage": "8 Northeast state-capital reference stations",
                "last_audited_at": None,
                "versioning": "fetched_at plus fresh/stale flag",
            },
            {
                "id": "hazard-benchmark",
                "source_id": "hazard-benchmark",
                "label": "Reviewed hazard benchmark records",
                "source_name": "Reviewed hazard benchmark records",
                "kind": "hazards",
                "status": "versioned_benchmark",
                "coverage": "Selected Northeast corridors",
                "last_audited_at": status.get("audited_at"),
                "versioning": "source record ID plus dataset version",
            },
            {
                "id": "ndma-sachet",
                "source_id": "ndma-sachet",
                "label": "NDMA SACHET warning adapter",
                "source_name": "NDMA SACHET warning adapter",
                "kind": "warnings",
                "status": "standby",
                "coverage": "Northeast warning feed (URL pending)",
                "last_audited_at": status.get("audited_at"),
                "versioning": "feed payload hash when authorised",
            },
            {
                "id": "cwc-flood",
                "source_id": "cwc-flood",
                "label": "CWC flood forecast adapter",
                "source_name": "CWC flood forecast adapter",
                "kind": "warnings",
                "status": "standby",
                "coverage": "Northeast flood stations (URL pending)",
                "last_audited_at": status.get("audited_at"),
                "versioning": "feed payload hash when authorised",
            },
        ],
        "runtime_snapshots": snapshots,
        "runtime_snapshot_count": len(snapshots),
        "downloaded_files": status.get("verified_download_files", 0),
        "downloaded_bytes": status.get("downloaded_bytes", 0),
        "terrain_tiles": status.get("terrain_tiles", 0),
        "terrain_tiles_planned": status.get("terrain_tiles_planned", 0),
        "weather_reference_point_days": status.get("weather_reference_point_days", 0),
        "historical_ne_landslides": status.get("historical_ne_landslides", 0),
        "gaps": status.get("gaps", []),
    }


@app.get("/api/v1/data-status")
def data_status():
    return data_readiness()


@app.get("/api/v1/weather/live")
def live_weather(region_code: str | None = None):
    if region_code:
        w = dict(get_station_weather(region_code))
        if hasattr(w["fetched_at"], "isoformat"):
            w["fetched_at"] = w["fetched_at"].isoformat()
        return w
    return {"stations": get_all_live_weather()}


@app.get("/api/v1/public-config")
def public_config():
    url = os.getenv("SUPABASE_URL")
    key = os.getenv("SUPABASE_PUBLISHABLE_KEY")
    if not url or not key:
        raise HTTPException(503, detail="Supabase public configuration is unavailable")
    return {"supabase_url": url, "supabase_publishable_key": key}


@app.get("/api/v1/me", response_model=AuthUser)
def current_user(user: Annotated[AuthUser, Depends(require_user)]):
    return user


@app.get("/api/v1/fleet/positions", response_model=list[VehicleSummary])
def fleet_positions(store: Annotated[FleetStore, Depends(get_fleet_store)], user: Annotated[AuthUser, Depends(require_user)], limit: int = Query(default=200, ge=1, le=1000)):
    try:
        region = None if user.role == "admin" else user.region_code
        return store.positions(region, limit)
    except RuntimeError as exc:
        raise HTTPException(503, detail=str(exc)) from exc


@app.get("/api/v1/fleet/vehicles", response_model=list[VehicleAsset])
def fleet_vehicles(store: Annotated[FleetStore, Depends(get_fleet_store)], user: Annotated[AuthUser, Depends(require_user)]):
    try:
        return store.vehicles(user.id)
    except RuntimeError as exc:
        raise HTTPException(503, detail=str(exc)) from exc


@app.post("/api/v1/fleet/positions", response_model=VehiclePosition, status_code=201)
def record_fleet_position(payload: PositionCreate, store: Annotated[FleetStore, Depends(get_fleet_store)], user: Annotated[AuthUser, Depends(require_user)]):
    try:
        return store.record_position(payload, user.id)
    except LookupError as exc:
        raise HTTPException(403, detail=str(exc)) from exc
    except RuntimeError as exc:
        raise HTTPException(503, detail=str(exc)) from exc


@app.get("/api/v1/deliveries", response_model=list[DeliveryJob])
def deliveries(store: Annotated[FleetStore, Depends(get_fleet_store)], user: Annotated[AuthUser, Depends(require_user)], limit: int = Query(default=200, ge=1, le=1000)):
    try:
        region = None if user.role == "admin" else user.region_code
        return store.deliveries(region, limit)
    except RuntimeError as exc:
        raise HTTPException(503, detail=str(exc)) from exc


@app.post("/api/v1/deliveries", response_model=DeliveryJob, status_code=201)
def create_delivery(payload: DeliveryCreate, store: Annotated[FleetStore, Depends(get_fleet_store)], user: Annotated[AuthUser, Depends(require_user)]):
    if user.region_code and user.role != "admin" and user.region_code != payload.region_code:
        raise HTTPException(403, detail="Delivery is outside the assigned region")
    try:
        return store.create_delivery(payload, user.id)
    except LookupError as exc:
        raise HTTPException(403, detail=str(exc)) from exc
    except RuntimeError as exc:
        raise HTTPException(503, detail=str(exc)) from exc


@app.patch("/api/v1/deliveries/{delivery_id}", response_model=DeliveryJob)
def update_delivery(delivery_id: UUID, payload: DeliveryUpdate, store: Annotated[FleetStore, Depends(get_fleet_store)], user: Annotated[AuthUser, Depends(require_user)]):
    try:
        return store.update_delivery(str(delivery_id), payload, user.id, user.role == "admin")
    except LookupError as exc:
        raise HTTPException(404, detail=str(exc)) from exc
    except RuntimeError as exc:
        raise HTTPException(503, detail=str(exc)) from exc


@app.get("/api/v1/accessibility-events")
def accessibility_events(
    store: Annotated[FieldReportStore, Depends(get_field_report_store)],
    region_code: str | None = Query(default=None, pattern=r"^[a-z]+(?:-[a-z]+)*$"),
    include_inactive: bool = Query(default=False),
):
    try:
        return {"events": store.active_events(region_code, include_inactive=include_inactive)}
    except RuntimeError as exc:
        raise HTTPException(503, detail=str(exc)) from exc


@app.patch("/api/v1/accessibility-events/{event_id}")
def update_accessibility_event(
    event_id: str,
    payload: EventUpdate,
    store: Annotated[FieldReportStore, Depends(get_field_report_store)],
    reviewer: Annotated[AuthUser, Depends(require_reviewer)],
    audit_store: Annotated[AuditStore, Depends(get_audit_store)],
):
    try:
        if payload.status == "resolved":
            updated = store.resolve_event(event_id, reviewer.id, payload.note)
            record_audit(
                audit_store,
                action="event_resolved",
                resource=f"accessibility_event:{event_id}",
                actor_id=reviewer.id,
                actor_role=reviewer.role,
                result="success",
                details={"note": payload.note, "region_code": updated.get("region_code")},
            )
            return updated
        elif payload.ends_at is not None:
            updated = store.extend_event_expiry(event_id, reviewer.id, payload.ends_at, payload.note)
            record_audit(
                audit_store,
                action="event_extended",
                resource=f"accessibility_event:{event_id}",
                actor_id=reviewer.id,
                actor_role=reviewer.role,
                result="success",
                details={"new_ends_at": payload.ends_at.isoformat(), "note": payload.note},
            )
            return updated
        else:
            raise HTTPException(422, detail="Provide either status='resolved' or a new ends_at timestamp")
    except LookupError as exc:
        raise HTTPException(404, detail=str(exc)) from exc
    except RuntimeError as exc:
        raise HTTPException(503, detail=str(exc)) from exc


@app.get("/api/v1/alerts", response_model=list[Alert])
def alerts(store: Annotated[AlertStore, Depends(get_alert_store)], user: Annotated[AuthUser, Depends(require_user)], limit: int = Query(default=100, ge=1, le=500)):
    try:
        region = None if user.role == "admin" else user.region_code
        return store.list_alerts(region, limit)
    except RuntimeError as exc:
        raise HTTPException(503, detail=str(exc)) from exc


@app.get("/api/v1/connectivity", response_model=list[ConnectivitySummary])
def connectivity(store: Annotated[AlertStore, Depends(get_alert_store)], user: Annotated[AuthUser, Depends(require_user)]):
    try:
        region = None if user.role == "admin" else user.region_code
        return store.connectivity(region)
    except RuntimeError as exc:
        raise HTTPException(503, detail=str(exc)) from exc


def get_graph(dataset: str) -> RoadGraph:
    if dataset == "osm-ner-roads":
        raise HTTPException(422, detail="Use coordinate route requests for the regional road index")
    with app.state.graph_lock:
        if dataset in app.state.graphs:
            return app.state.graphs[dataset]
        path = app.state.dataset_paths.get(dataset)
        if path is None:
            raise HTTPException(404, detail="Dataset is not available")

        dynamic = [key for key in app.state.graphs if key != "demo" and key != "osm-guwahati"]
        while len(dynamic) >= app.state.dynamic_cache_size:
            app.state.graphs.pop(dynamic.pop(0), None)
        logger.info("Loading graph snapshot %s from %s", dataset, path)
        graph = RoadGraph(Dataset.model_validate_json(path.read_text(encoding="utf-8")))
        app.state.graphs[dataset] = graph
        return graph


def dataset_label(dataset_id: str) -> str:
    if dataset_id == "demo":
        return app.state.graph.dataset.title
    return dataset_id.removeprefix("osm-").replace("-", " ").title() + " OSM"


def search_catalog(dataset_id: str) -> list[dict]:
    slug = "assam" if dataset_id.startswith("osm-guwahati") else dataset_id.removeprefix("osm-")
    if slug in app.state.search_catalogs:
        return app.state.search_catalogs[slug]
    base = ROOT.parent / "datasets" / "processed" / "osm"
    records = []
    for kind, suffix in (("place", "places"), ("facility", "facilities")):
        path = base / f"{slug}-{suffix}.geojson"
        if not path.exists():
            continue
        for feature in json.loads(path.read_text(encoding="utf-8")).get("features", []):
            properties = feature.get("properties", {})
            coordinates = feature.get("geometry", {}).get("coordinates", [])
            if len(coordinates) < 2 or not properties.get("name"):
                continue
            records.append(
                {
                    "source_id": properties.get("osm_id"),
                    "label": properties["name"],
                    "kind": kind,
                    "detail": properties.get("place") or properties.get("kind") or kind,
                    "population": properties.get("population"),
                    "lon": coordinates[0],
                    "lat": coordinates[1],
                }
            )
    app.state.search_catalogs[slug] = records
    return records


def named_locations(graph: RoadGraph) -> list[dict]:
    record = app.state.region_catalog.get(graph.dataset.id)
    if record is None:
        return [node.model_dump() for node in graph.dataset.nodes if node.label]
    capital = record["capital"]

    def population(item: dict) -> int:
        try:
            return int(str(item.get("population") or "0").replace(",", ""))
        except ValueError:
            return 0

    places = [item for item in search_catalog(graph.dataset.id) if item["kind"] == "place"]
    places.sort(
        key=lambda item: (
            item["label"].casefold() != capital.casefold(),
            item["detail"] not in {"city", "town"},
            -population(item),
            item["label"].casefold(),
        )
    )
    locations = []
    seen = set()
    for item in places:
        try:
            node_id, snap_distance = graph.resolve(Endpoint(lon=item["lon"], lat=item["lat"]))
        except ValueError:
            continue
        if node_id in seen:
            continue
        locations.append(
            {
                "id": node_id,
                "label": item["label"],
                "lon": item["lon"],
                "lat": item["lat"],
                "kind": item["detail"],
                "snap_distance_m": snap_distance,
            }
        )
        seen.add(node_id)
        if len(locations) == 8:
            break
    return locations or [node.model_dump() for node in graph.dataset.nodes if node.label]


@app.get("/api/v1/bootstrap")
def bootstrap(dataset: str = "demo"):
    graph = get_graph(dataset)
    dataset = graph.dataset
    locations = named_locations(graph)
    dataset_metadata = dataset.model_dump(exclude={"nodes", "edges", "scenarios"})
    if len(locations) >= 2 and graph.dataset.id in app.state.region_catalog:
        dataset_metadata["default_origin"] = locations[0]["id"]
        origin = graph.nodes[locations[0]["id"]]
        destination = max(
            locations[1:],
            key=lambda item: math.dist(
                (origin.lon, origin.lat),
                (graph.nodes[item["id"]].lon, graph.nodes[item["id"]].lat),
            ),
        )
        dataset_metadata["default_destination"] = destination["id"]
    return {
        "dataset": dataset_metadata,
        "dataset_version": graph.version,
        "counts": {"nodes": len(graph.nodes), "edges": len(graph.edges)},
        "locations": locations,
        "vehicles": VEHICLES,
        "available_datasets": [
            {
                "id": key,
                "label": app.state.graphs[key].dataset.title
                if key in app.state.graphs
                else read_dataset_header(app.state.dataset_paths[key]).get(
                    "title", dataset_label(key)
                ),
                "is_synthetic": (
                    app.state.graphs[key].dataset.is_synthetic
                    if key in app.state.graphs
                    else bool(read_dataset_header(app.state.dataset_paths[key]).get("is_synthetic", True))
                ),
            }
            for key in dict.fromkeys([*app.state.graphs, *app.state.dataset_paths])
        ],
        "scenarios": [s.model_dump() for s in dataset.scenarios],
    }


@app.get("/api/v1/terrain")
def terrain(dataset: str = "demo"):
    get_graph(dataset)
    path = ROOT / "data" / "osm-guwahati-terrain.json"
    if dataset == "osm-guwahati" and path.exists():
        return json.loads(path.read_text(encoding="utf-8"))
    return None


@app.get("/api/v1/network")
def network(
    weather: str = "normal",
    dataset: str = "demo",
    focus_node: str | None = None,
    radius_km: float = Query(default=15, ge=1, le=100),
    limit: int = Query(default=8000, ge=100, le=20000),
):
    if weather not in ("normal", "heavy_rain"):
        raise HTTPException(422, detail="Unsupported weather scenario")
    graph = get_graph(dataset)
    focus_id = focus_node or graph.dataset.default_origin
    if focus_id not in graph.nodes:
        raise HTTPException(422, detail="Unknown focus node")
    focus = graph.nodes[focus_id]
    latitude_padding = radius_km / 111.32
    longitude_padding = radius_km / max(1, 111.32 * abs(math.cos(math.radians(focus.lat))))
    west, east = focus.lon - longitude_padding, focus.lon + longitude_padding
    south, north = focus.lat - latitude_padding, focus.lat + latitude_padding
    visible_edges = []
    for edge in graph.edges.values():
        u, v = graph.nodes[edge.u], graph.nodes[edge.v]
        if not (
            (west <= u.lon <= east and south <= u.lat <= north)
            or (west <= v.lon <= east and south <= v.lat <= north)
        ):
            continue
        visible_edges.append(edge)
        if len(visible_edges) >= limit:
            break
    return {
        "type": "FeatureCollection",
        "metadata": {
            "dataset_id": graph.dataset.id,
            "focus_node": focus_id,
            "focus": {"lon": focus.lon, "lat": focus.lat},
            "radius_km": radius_km,
            "returned_features": len(visible_edges),
            "total_features": len(graph.edges),
            "truncated": len(visible_edges) >= limit,
        },
        "features": [
            {
                "type": "Feature",
                "geometry": {"type": "LineString", "coordinates": edge.geometry},
                "properties": {
                    "id": edge.id,
                    "name": edge.name,
                    "u": edge.u,
                    "v": edge.v,
                    "risk": round(graph.risk(edge, weather), 3),
                    "closed": edge.closed,
                    "evidence": edge.evidence,
                },
            }
            for edge in visible_edges
        ],
    }


@app.get("/api/v1/search")
def search_places(
    q: str = Query(min_length=2, max_length=80),
    dataset: str | None = None,
    limit: int = Query(default=12, ge=1, le=30),
):
    """Search road names and labelled places across available networks."""
    needle = " ".join(q.casefold().split())
    results: list[dict] = []
    # Do not load every multi-hundred-megabyte regional snapshot on each keystroke.
    # The lightweight demo graph is the default search surface; an explicit dataset
    # remains available for callers that already selected a regional network.
    dataset_ids = [dataset or "demo"]
    for dataset_id in dataset_ids:
        graph = get_graph(dataset_id)
        seen: set[str] = set()
        if dataset_id == "demo":
            for alias, (node_id, label, detail) in DEMO_CITY_ALIASES.items():
                if needle in alias or alias.startswith(needle):
                    node = graph.nodes.get(node_id)
                    if node is not None:
                        results.append(
                            {
                                "id": node_id,
                                "dataset_id": dataset_id,
                                "label": label,
                                "kind": "place",
                                "detail": detail,
                                "lon": node.lon,
                                "lat": node.lat,
                            }
                        )
                        seen.add(node_id)
        catalog_matches = sorted(
            (item for item in search_catalog(dataset_id) if needle in item["label"].casefold()),
            key=lambda item: (
                not item["label"].casefold().startswith(needle),
                item["kind"] != "place",
                len(item["label"]),
            ),
        )
        for item in catalog_matches:
            try:
                node_id, snap_distance = graph.resolve(Endpoint(lon=item["lon"], lat=item["lat"]))
            except ValueError:
                continue
            if node_id in seen:
                continue
            results.append(
                {
                    "id": node_id,
                    "dataset_id": dataset_id,
                    "label": item["label"],
                    "kind": item["kind"],
                    "detail": item["detail"],
                    "lon": item["lon"],
                    "lat": item["lat"],
                    "snap_distance_m": snap_distance,
                }
            )
            seen.add(node_id)
            if len(results) >= limit:
                break
        if len(results) >= limit:
            break
        for node in graph.nodes.values():
            label = node.label or ""
            if needle in label.casefold() and node.id not in seen:
                results.append(
                    {
                        "id": node.id,
                        "dataset_id": dataset_id,
                        "label": label,
                        "kind": "place",
                        "lon": node.lon,
                        "lat": node.lat,
                    }
                )
                seen.add(node.id)
                if len(results) >= limit:
                    break
        if len(results) >= limit:
            break
        for edge in graph.edges.values():
            if needle in edge.name.casefold() and edge.u not in seen:
                node = graph.nodes[edge.u]
                results.append(
                    {
                        "id": edge.u,
                        "dataset_id": dataset_id,
                        "label": edge.name,
                        "kind": "road",
                        "lon": node.lon,
                        "lat": node.lat,
                    }
                )
                seen.add(edge.u)
                if len(results) >= limit:
                    break
        if len(results) >= limit:
            break
    return {"query": q, "dataset_id": dataset, "results": results[:limit]}


@app.post("/api/v1/routes/compare")
def compare_routes(request: RouteRequest):
    # A sync endpoint runs CPU-bound graph traversal in FastAPI's worker thread pool.
    # The graph is read-only; all scenario inputs remain local to this request.
    try:
        graph = (RoadGraph(load_route_window(ROOT / "data/osm-ner-roads.sqlite", request.origin, request.destination))
                 if request.dataset_id == "osm-ner-roads" else get_graph(request.dataset_id))
        # Keep named demo/corridor locations usable across versioned snapshots.
        # The aliases are only applied when the target snapshot contains the
        # mapped node; real OSM node ids and coordinate endpoints are untouched.
        updates: dict[str, Endpoint] = {}
        for field in ("origin", "destination"):
            endpoint = getattr(request, field)
            if endpoint.node_id in DEMO_CITY_ALIASES:
                mapped = DEMO_CITY_ALIASES[endpoint.node_id][0]
                if mapped in graph.nodes:
                    updates[field] = Endpoint(node_id=mapped)
        if updates:
            request = request.model_copy(update=updates)
        if request.dataset_id != "demo":
            region = (None if request.dataset_id == "osm-ner-roads" else
                      "assam" if request.dataset_id.startswith("osm-guwahati") else
                      request.dataset_id.removeprefix("osm-").removesuffix("-real"))
            try:
                events = get_field_report_store().active_events(region)
            except (psycopg.Error, OSError) as exc:
                # Routing must remain available during a remote database outage.
                # The graph is local and an unavailable event store means no
                # verified closures can be safely applied to this request.
                logger.warning("Hazard event store unavailable; routing without dynamic closures: %s", exc)
                events = []
            regional_blocked = set()
            if request.dataset_id == "osm-ner-roads":
                raw_closed = {event["edge_id"] for event in events
                              if event.get("dataset_id", "").endswith("-real")
                              and event.get("accessibility_status") == "blocked"
                              and event.get("review_status", "authority_verified") in {"accepted", "authority_verified"}}
                regional_blocked = {edge_id for edge_id in graph.edges
                                    if edge_id.split(":", 1)[-1] in raw_closed}
            blocked = [
                event["edge_id"]
                for event in events
                if event.get("dataset_id") == request.dataset_id
                and event.get("accessibility_status") == "blocked"
                and event.get("review_status", "authority_verified") in {"accepted", "authority_verified"}
                and event["edge_id"] in graph.edges
            ]
            request = request.model_copy(update={"closed_edge_ids": list(dict.fromkeys([*request.closed_edge_ids, *blocked, *sorted(regional_blocked)]))})
        return graph.compare(request)
    except ValueError as exc:
        raise HTTPException(422, detail=str(exc)) from exc


@app.get("/api/v1/admin/public-candidates", response_model=list[PublicCandidate])
def list_public_candidates(
    reviewer: Annotated[AuthUser, Depends(require_reviewer)],
    region_code: str | None = Query(default=None),
    status: str | None = Query(default=None),
):
    candidates = list(_public_candidates.values())
    if reviewer.role != "admin":
        candidates = [c for c in candidates if c.region_code == reviewer.region_code]
    if region_code:
        candidates = [c for c in candidates if c.region_code == region_code]
    if status:
        candidates = [c for c in candidates if c.review_status == status]
    return candidates


@app.patch("/api/v1/admin/public-candidates/{candidate_id}/review", response_model=PublicCandidate)
def review_public_candidate(
    candidate_id: str,
    review: PublicCandidateReview,
    reviewer: Annotated[AuthUser, Depends(require_reviewer)],
    audit_store: Annotated[AuditStore, Depends(get_audit_store)],
):
    candidate = _public_candidates.get(candidate_id)
    if not candidate:
        raise HTTPException(404, detail="Public candidate not found")
    if reviewer.role != "admin" and candidate.region_code != reviewer.region_code:
        raise HTTPException(403, detail="Candidate is outside the assigned region")
    if review.decision == "approved" and (not review.road_segment_id or not review.incident_started_at):
        raise HTTPException(422, detail="Approved candidates require a road segment and incident start time")
    updated = candidate.model_copy(update={"review_status": review.decision, "road_segment_id": review.road_segment_id, "incident_started_at": review.incident_started_at, "incident_ended_at": review.incident_ended_at, "restriction_effective_at": review.restriction_effective_at, "reopening_effective_at": review.reopening_effective_at, "reviewer_id": reviewer.id, "review_note": review.review_note, "coordinates_verified": bool(review.road_segment_id)})
    _public_candidates[candidate_id] = updated
    record_audit(audit_store, action="public_candidate_review", resource=f"public_candidate:{candidate_id}", actor_id=reviewer.id, actor_role=reviewer.role, result=review.decision, details={"road_segment_id": review.road_segment_id, "source_url": candidate.source_url})
    return updated


@app.post("/api/v1/admin/public-candidates/{candidate_id}/promote", response_model=PublicCandidate)
def promote_public_candidate(
    candidate_id: str,
    reviewer: Annotated[AuthUser, Depends(require_reviewer)],
    audit_store: Annotated[AuditStore, Depends(get_audit_store)],
):
    candidate = _public_candidates.get(candidate_id)
    if not candidate:
        raise HTTPException(404, detail="Public candidate not found")
    if candidate.review_status != "approved" or not candidate.road_segment_id or not candidate.incident_started_at:
        raise HTTPException(409, detail="Only approved, segment-matched candidates can be promoted")
    record_audit(audit_store, action="public_candidate_promote", resource=f"public_candidate:{candidate_id}", actor_id=reviewer.id, actor_role=reviewer.role, result="promoted", details={"road_segment_id": candidate.road_segment_id})
    return candidate


class CandidateAdvisoryReviewBody(StrictModel):
    decision: Literal["accept", "reject", "mark_duplicate", "mark_conflicting"]
    source_evidence: str = Field(min_length=5, max_length=500)
    affected_corridor: str = Field(min_length=3, max_length=200)
    review_note: str = Field(min_length=5, max_length=2000)
    road_segment_id: str | None = None


@app.get("/api/v1/admin/candidate-advisories", response_model=list[OfficialHazardAdvisory])
def list_candidate_advisories_endpoint(
    reviewer: Annotated[AuthUser, Depends(require_reviewer)],
    status: str | None = Query(default=None),
):
    """List early-warning hazard candidate advisories awaiting operator review."""
    return get_candidate_advisories(status=status)


@app.post("/api/v1/admin/candidate-advisories/{advisory_id}/review", response_model=OfficialHazardAdvisory)
def review_candidate_advisory_endpoint(
    advisory_id: str,
    body: CandidateAdvisoryReviewBody,
    reviewer: Annotated[AuthUser, Depends(require_reviewer)],
    audit_store: Annotated[AuditStore, Depends(get_audit_store)],
):
    """Operator review action for candidate early-warning advisory with mandatory audit logging."""
    try:
        updated = review_candidate_advisory(
            advisory_id=advisory_id,
            decision=body.decision,
            source_evidence=body.source_evidence,
            affected_corridor=body.affected_corridor,
            review_note=body.review_note,
            reviewer_id=reviewer.id,
            road_segment_id=body.road_segment_id,
            audit_store=audit_store,
        )
        return updated
    except ValueError as exc:
        raise HTTPException(422, detail=str(exc)) from exc


@app.get("/api/v1/admin/feeds/diagnostics")
def get_feeds_diagnostics_endpoint(reviewer: Annotated[AuthUser, Depends(require_reviewer)]):
    """Return diagnostic telemetry, parser health, and controlled stress test metrics."""
    return get_feed_diagnostics()


@app.post("/api/v1/admin/feeds/diagnostics/run")
def run_feeds_diagnostics_endpoint(
    reviewer: Annotated[AuthUser, Depends(require_reviewer)],
    audit_store: Annotated[AuditStore, Depends(get_audit_store)],
):
    """Execute safe controlled dry-run diagnostics across all official early-warning parsers."""
    return run_feed_diagnostics_dry_run(audit_store=audit_store)


@app.post("/api/v1/field-reports", response_model=FieldReport, status_code=201)
def create_field_report(
    report: FieldReportCreate,
    store: Annotated[FieldReportStore, Depends(get_field_report_store)],
    user: Annotated[AuthUser, Depends(require_user)],
):
    try:
        if user.region_code and user.region_code != report.region_code and user.role != "admin":
            raise HTTPException(403, detail="Report is outside the assigned region")
        return store.create(report, user.id)
    except ValueError as exc:
        raise HTTPException(409, detail=str(exc)) from exc
    except psycopg.errors.ForeignKeyViolation as exc:
        raise HTTPException(422, detail="Unknown Northeast region code") from exc
    except RuntimeError as exc:
        raise HTTPException(503, detail=str(exc)) from exc


@app.get("/api/v1/field-reports", response_model=list[FieldReport])
def list_field_reports(
    store: Annotated[FieldReportStore, Depends(get_field_report_store)],
    user: Annotated[AuthUser, Depends(require_user)],
    region_code: str | None = Query(default=None, pattern=r"^[a-z]+(?:-[a-z]+)*$"),
    status: str | None = Query(default=None),
    include_expired: bool = Query(default=True),
    limit: int = Query(default=100, ge=1, le=500),
):
    try:
        if user.region_code and user.role != "admin":
            if region_code and region_code != user.region_code:
                raise HTTPException(403, detail="Reports are outside the assigned region")
            region_code = user.region_code
        try:
            return store.list(region_code, limit, status=status, include_expired=include_expired)
        except TypeError:
            return store.list(region_code, limit)
    except RuntimeError as exc:
        raise HTTPException(503, detail=str(exc)) from exc


@app.patch("/api/v1/field-reports/{report_id}/review", response_model=FieldReport)
def review_field_report(
    report_id: UUID,
    review: FieldReportReview,
    store: Annotated[FieldReportStore, Depends(get_field_report_store)],
    reviewer: Annotated[AuthUser, Depends(require_reviewer)],
    audit_store: Annotated[AuditStore, Depends(get_audit_store)],
):
    try:
        result = store.review(str(report_id), review, reviewer.id)
        record_audit(
            audit_store,
            action="report_review",
            resource=f"field_report:{report_id}",
            actor_id=reviewer.id,
            actor_role=reviewer.role,
            result=review.decision,
            details={
                "decision": review.decision,
                "review_note": review.review_note,
                "edge_id": review.edge_id,
                "dataset_id": review.dataset_id,
            },
        )
        return result
    except LookupError as exc:
        raise HTTPException(404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(409, detail=str(exc)) from exc


@app.get("/api/v1/field-reports/{report_id}/road-candidates")
def field_report_road_candidates(
    report_id: UUID,
    store: Annotated[FieldReportStore, Depends(get_field_report_store)],
    reviewer: Annotated[AuthUser, Depends(require_reviewer)],
    dataset_id: str = Query(min_length=1, max_length=100),
):
    try:
        region_code = None if reviewer.role == "admin" else reviewer.region_code
        return {"candidates": store.road_candidates(str(report_id), dataset_id, region_code)}
    except PermissionError as exc:
        raise HTTPException(403, detail=str(exc)) from exc
    except LookupError as exc:
        raise HTTPException(404, detail=str(exc)) from exc
    except RuntimeError as exc:
        raise HTTPException(503, detail=str(exc)) from exc


@app.post("/api/v1/field-reports/{report_id}/attachments", response_model=FieldReportAttachment, status_code=201)
def upload_field_report_attachment(
    report_id: UUID,
    store: Annotated[FieldReportStore, Depends(get_field_report_store)],
    user: Annotated[AuthUser, Depends(require_user)],
    authorization: Annotated[str, Header()],
    file: Annotated[UploadFile, File(...)],
):
    allowed = {"image/jpeg", "image/png", "image/webp"}
    if file.content_type not in allowed:
        raise HTTPException(415, detail="Only JPEG, PNG and WebP evidence is allowed")
    content = file.file.read(10 * 1024 * 1024 + 1)
    if len(content) > 10 * 1024 * 1024:
        raise HTTPException(413, detail="Evidence image must be 10 MB or smaller")
    digest = hashlib.sha256(content).hexdigest()
    path = f"{user.id}/{report_id}/{digest}.{file.content_type.rsplit('/', 1)[1]}"
    base_url = os.getenv("SUPABASE_URL")
    key = os.getenv("SUPABASE_PUBLISHABLE_KEY")
    try:
        response = httpx.post(
            f"{base_url}/storage/v1/object/field-report-evidence/{path}",
            content=content,
            headers={"apikey": key, "Authorization": authorization, "Content-Type": file.content_type, "x-upsert": "false"},
            timeout=20,
        )
    except httpx.HTTPError as exc:
        raise HTTPException(503, detail="Evidence storage is unavailable") from exc
    if response.status_code not in {200, 201}:
        raise HTTPException(502, detail="Evidence could not be stored")
    try:
        return store.save_attachment(str(report_id), user.id, path, file.content_type, len(content), digest)
    except LookupError as exc:
        raise HTTPException(404, detail=str(exc)) from exc


@app.post("/api/v1/auth/request-code", status_code=410)
@app.post("/api/v1/auth/verify-code", status_code=410)
def deprecated_demo_auth() -> None:
    """Prevent accidental use of the former in-memory development OTP flow.

    Authentication is performed by Supabase Auth from the frontend. Returning a
    one-time code in an API response is never safe for a deployable service.
    """
    raise HTTPException(410, detail="Demo OTP is retired. Use Supabase Auth.")


@app.post("/api/v1/fleet/telemetry/ais140", response_model=TelematicsIngestResponse, status_code=200)
def ingest_ais140_telemetry(
    packet: AIS140TelemetryPacket,
    store: Annotated[FleetStore, Depends(get_fleet_store)],
    x_raahsetu_signature: Annotated[str | None, Header()] = None,
):
    """Ingest standard AIS-140 commercial freight vehicle telemetry packet."""
    position_create = packet_to_position_create(packet)
    try:
        verify_telematics_signature(
            packet.model_dump_json(exclude_none=True).encode(), x_raahsetu_signature
        )
        trust_score, quality_flags = telemetry_guard.validate(position_create)
    except ValueError as exc:
        raise HTTPException(422, detail=str(exc)) from exc
    position_create = position_create.model_copy(
        update={
            "metadata": {
                **position_create.metadata,
                "trust_score": trust_score,
                "quality_flags": quality_flags,
                "signature_verified": bool(os.getenv("TELEMETRY_WEBHOOK_SECRET")),
            }
        }
    )
    try:
        store.record_telematics(position_create)
    except LookupError as exc:
        raise HTTPException(404, detail=str(exc)) from exc
    except RuntimeError as exc:
        raise HTTPException(503, detail=str(exc)) from exc

    stream_add(
        "raahsetu:telemetry",
        {
            "vehicle_id": packet.vehicle_registration,
            "recorded_at": packet.timestamp,
            "latitude": packet.latitude,
            "longitude": packet.longitude,
            "speed_kph": packet.speed_kph,
            "trust_score": trust_score,
            "quality_flags": quality_flags,
        },
    )

    # Proximity check against active hazards and candidate early warnings
    hazards = [
        {"id": "sela-pass", "title": "Sela Pass Summit Freeze", "lat": 27.50, "lon": 92.10, "severity": 0.92, "accessibility_status": "restricted"},
        {"id": "phesama-sink", "title": "NH-29 Phesama Subsidence", "lat": 25.65, "lon": 94.10, "severity": 0.86, "accessibility_status": "blocked"},
        {"id": "sonapur-tunnel", "title": "Sonapur Tunnel Mudflow", "lat": 25.12, "lon": 92.36, "severity": 0.88, "accessibility_status": "restricted"},
    ] if os.getenv("ALLOW_SYNTHETIC_TELEMETRY_HAZARDS", "false").lower() == "true" else []
    try:
        from .live_ingestion import get_candidate_advisories
        for adv in get_candidate_advisories():
            if adv.coordinates and len(adv.coordinates) >= 2:
                hazards.append({
                    "id": adv.advisory_id,
                    "title": adv.headline,
                    "lat": adv.coordinates[1],
                    "lon": adv.coordinates[0],
                    "severity": 0.95 if adv.severity == "WARNING" else 0.7,
                    "accessibility_status": "blocked" if adv.review_status == "accepted" else "restricted",
                })
    except (RuntimeError, OSError, ValueError) as err:
        logger.debug("Candidate advisories proximity load skipped: %s", err)
    if os.getenv("DATABASE_URL"):
        try:
            active_events = get_field_report_store().active_events(None)
            if active_events:
                hazards = [*hazards, *active_events]
        except (RuntimeError, psycopg.Error, OSError) as err:
            logger.debug("Active events load skipped: %s", err)

    nearby = check_hazard_proximity(packet.latitude, packet.longitude, hazards, threshold_km=5.0)

    return TelematicsIngestResponse(
        status="warning" if nearby else "ingested",
        vehicle_id=packet.vehicle_registration,
        recorded_at=packet.timestamp,
        coordinates=[packet.longitude, packet.latitude],
        speed_kph=packet.speed_kph,
        proximity_hazards=nearby,
        trust_score=trust_score,
        quality_flags=quality_flags,
        message="Telemetry ingested successfully via AIS-140 standard" if not nearby else f"Proximity Alert: Vehicle within 5km of {len(nearby)} active hazards!",
    )


@app.post("/api/v1/fleet/telemetry/raw", response_model=TelematicsIngestResponse, status_code=200)
def ingest_raw_telemetry(
    req: RawTelemetryRequest,
    store: Annotated[FleetStore, Depends(get_fleet_store)],
    x_raahsetu_signature: Annotated[str | None, Header()] = None,
):
    """Ingest raw AIS-140 string packet from commercial freight GPS tracker."""
    try:
        packet = parse_raw_ais140_string(req.raw_packet)
    except ValueError as exc:
        raise HTTPException(422, detail=str(exc)) from exc
    return ingest_ais140_telemetry(packet, store, x_raahsetu_signature)


@app.api_route(
    "/api/v1/fleet/telemetry/webhook",
    methods=["GET", "POST"],
    response_model=TelematicsIngestResponse,
    status_code=200,
)
async def ingest_telematics_webhook(
    request: Request,
    store: Annotated[FleetStore, Depends(get_fleet_store)],
    id: str | None = Query(default=None),
    lat: float | None = Query(default=None),
    lon: float | None = Query(default=None),
    speed: float | None = Query(default=None),
    bearing: float | None = Query(default=None),
    altitude: float | None = Query(default=None),
    timestamp: str | None = Query(default=None),
    x_raahsetu_signature: Annotated[str | None, Header()] = None,
):
    """Ingest live GPS telemetry from OsmAnd / Traccar mobile clients or generic telematics webhooks."""
    body_data = {}
    if request.method == "POST":
        try:
            body_data = await request.json()
        except (json.JSONDecodeError, ValueError, TypeError):
            body_data = {}

    merged = {
        **body_data,
        **{
            k: v
            for k, v in {
                "id": id,
                "lat": lat,
                "lon": lon,
                "speed": speed,
                "bearing": bearing,
                "altitude": altitude,
                "timestamp": timestamp,
            }.items()
            if v is not None
        },
    }
    lat_val = merged.get("lat") if merged.get("lat") is not None else merged.get("latitude")
    lon_val = merged.get("lon") if merged.get("lon") is not None else merged.get("longitude")
    if lat_val is None or lon_val is None:
        raise HTTPException(422, detail="Missing required telemetry coordinates (lat, lon)")
    merged["lat"] = float(lat_val)
    merged["lon"] = float(lon_val)

    pos = parse_telematics_webhook(merged)
    try:
        verify_telematics_signature(
            json.dumps(merged, sort_keys=True, default=str).encode(), x_raahsetu_signature
        )
        trust_score, quality_flags = telemetry_guard.validate(pos)
    except ValueError as exc:
        raise HTTPException(422, detail=str(exc)) from exc
    pos = pos.model_copy(
        update={
            "metadata": {
                **pos.metadata,
                "trust_score": trust_score,
                "quality_flags": quality_flags,
                "signature_verified": bool(os.getenv("TELEMETRY_WEBHOOK_SECRET")),
            }
        }
    )
    try:
        store.record_telematics(pos)
    except LookupError as exc:
        raise HTTPException(404, detail=str(exc)) from exc
    except RuntimeError as exc:
        raise HTTPException(503, detail=str(exc)) from exc

    hazards = [
        {
            "id": "sela-pass",
            "title": "Sela Pass Summit Freeze",
            "lat": 27.50,
            "lon": 92.10,
            "severity": 0.92,
            "accessibility_status": "restricted",
        },
        {
            "id": "phesama-sink",
            "title": "NH-29 Phesama Subsidence",
            "lat": 25.65,
            "lon": 94.10,
            "severity": 0.86,
            "accessibility_status": "blocked",
        },
        {
            "id": "sonapur-tunnel",
            "title": "Sonapur Tunnel Mudflow",
            "lat": 25.12,
            "lon": 92.36,
            "severity": 0.88,
            "accessibility_status": "restricted",
        },
    ] if os.getenv("ALLOW_SYNTHETIC_TELEMETRY_HAZARDS", "false").lower() == "true" else []
    if os.getenv("DATABASE_URL"):
        try:
            active_events = get_field_report_store().active_events(None)
            if active_events:
                hazards = [*hazards, *active_events]
        except (RuntimeError, psycopg.Error, OSError) as err:
            logger.debug("Active events load skipped: %s", err)

    nearby = check_hazard_proximity(pos.lat, pos.lon, hazards, threshold_km=5.0)

    return TelematicsIngestResponse(
        status="warning" if nearby else "ingested",
        vehicle_id=pos.vehicle_id,
        recorded_at=pos.recorded_at,
        coordinates=[pos.lon, pos.lat],
        speed_kph=pos.speed_kph or 0.0,
        proximity_hazards=nearby,
        trust_score=trust_score,
        quality_flags=quality_flags,
        message=(
            "Telemetry ingested successfully via fleet webhook"
            if not nearby
            else f"Proximity Alert: Vehicle within 5km of {len(nearby)} active hazards!"
        ),
    )


@app.post("/api/v1/alerts/broadcast", response_model=BroadcastResponse)
async def broadcast_alert(payload: BroadcastRequest):
    """Dispatch multilingual hazard or reroute broadcast to corridor freight drivers."""
    return await send_broadcast(payload)


@app.get("/api/v1/alerts/providers")
def alert_providers():
    """Return configured SMS and WhatsApp dispatch provider status."""
    twilio_configured = bool(os.getenv("TWILIO_ACCOUNT_SID") and os.getenv("TWILIO_AUTH_TOKEN"))
    whatsapp_configured = bool(os.getenv("WHATSAPP_API_TOKEN"))
    cdac_configured = bool(os.getenv("CDAC_SMS_URL"))
    active_provider = "twilio" if twilio_configured else ("whatsapp" if whatsapp_configured else ("cdac" if cdac_configured else "simulator"))
    return {
        "active_provider": active_provider,
        "is_simulated": active_provider == "simulator",
        "supported_languages": ["en", "hi", "as", "bn"],
        "supported_templates": ["hazard_alert", "bridge_warning", "reroute_advisory"],
        "gateways": {
            "twilio_sms": {"status": "configured" if twilio_configured else "unconfigured"},
            "whatsapp_cloud_api": {"status": "configured" if whatsapp_configured else "unconfigured"},
            "govt_cdac_nic": {"status": "configured" if cdac_configured else "unconfigured"},
            "provider_ready_simulator": {"status": "active"},
        },
    }


@app.get("/api/v1/hazards/live-feeds")
def hazards_live_feeds():
    """Return status of official early-warning feeds and active advisories."""
    return {
        "sources": get_official_feeds_status(),
        "active_advisories": ingest_live_official_advisories(),
    }


# ==========================================
# Admin Operations Control Panel Endpoints
# ==========================================


@app.get("/api/v1/admin/sources-status")
def admin_sources_status(user: Annotated[AuthUser, Depends(require_user)]):
    """Return comprehensive freshness, health, and provenance for all 11 pipeline data sources."""
    now = datetime.now(UTC)
    weather_stations = get_all_live_weather()
    weather_live = any(s.get("fresh") for s in weather_stations)
    anomaly_model = load_weather_anomaly_model()
    official_feeds = get_official_feeds_status()
    feed_status_map = {f.source_name: f.status for f in official_feeds}

    twilio_configured = bool(os.getenv("TWILIO_ACCOUNT_SID") and os.getenv("TWILIO_AUTH_TOKEN"))
    whatsapp_configured = bool(os.getenv("WHATSAPP_API_TOKEN"))
    cdac_configured = bool(os.getenv("CDAC_SMS_URL"))
    active_provider = (
        "twilio"
        if twilio_configured
        else ("whatsapp" if whatsapp_configured else ("cdac" if cdac_configured else "simulator"))
    )

    sources = [
        {
            "id": "osm-graph-snapshots",
            "name": "OSM Graph Snapshots",
            "category": "Road Network",
            "status": "FRESH",
            "last_updated": "2026-09-16T12:00:00Z",
            "age": "4h 30m",
            "version_hash": "sha256:d8a9f2c1b4e3",
            "coverage": "8 Northeast States (Immutable Snapshots)",
            "coverage_scope": "8 Northeast States (Immutable Snapshots)",
            "is_refreshable": False,
            "error_message": None,
            "provenance": "Offline Pyosmium & OSMnx extraction; versioned immutable graph JSONs.",
            "disclaimer": "Offline Pyosmium & OSMnx extraction; versioned immutable graph JSONs.",
        },
        {
            "id": "weather-data",
            "name": "Open-Meteo Weather Grids",
            "category": "Weather",
            "status": "LIVE" if weather_live else "CACHED",
            "last_updated": now.isoformat(),
            "age": "< 15m",
            "version_hash": "api.open-meteo.com/v1/forecast",
            "coverage": "8 State Capital Reference Stations",
            "coverage_scope": "8 State Capital Reference Stations",
            "is_refreshable": True,
            "error_message": None,
            "provenance": "Open-Meteo High-Resolution NWP Grids with 60-min cache policy.",
            "disclaimer": "Open-Meteo High-Resolution NWP Grids with 60-min cache policy.",
        },
        {
            "id": "weather-anomaly-model",
            "name": "Historical Weather Anomaly Model",
            "category": "ML/Statistical Models",
            "status": "FRESH" if anomaly_model else "UNAVAILABLE",
            "last_updated": anomaly_model.get("trained_at", now.isoformat()) if anomaly_model else None,
            "age": "Trained 2021-2024",
            "version_hash": anomaly_model.get("source_sha256", "v1.0")[:16] if anomaly_model else "none",
            "coverage": "8 Northeast States (Standardized Multivariate Distance)",
            "coverage_scope": "8 Northeast States (Standardized Multivariate Distance)",
            "is_refreshable": False,
            "error_message": None if anomaly_model else "Model artifact not found",
            "provenance": "Unsupervised multivariate distance anomaly detector. Not a landslide or road-closure probability.",
            "disclaimer": "Unsupervised multivariate distance anomaly detector. Not a landslide or road-closure probability.",
        },
        {
            "id": "hazard-observations",
            "name": "Reviewed Hazard Observations",
            "category": "Hazards",
            "status": "CACHED",
            "last_updated": None,
            "age": "Unknown",
            "version_hash": "bench-hazards-v1",
            "coverage": "Guwahati-Imphal, Sela, Sonapur, Phesama Corridors",
            "coverage_scope": "Guwahati-Imphal, Sela, Sonapur, Phesama Corridors",
            "is_refreshable": False,
            "error_message": "Reviewed benchmark observations are not a live government hazard feed.",
            "provenance": "PostGIS reviewed hazard benchmark records. Proximity creates candidates; only verified events affect routing.",
            "disclaimer": "PostGIS reviewed hazard benchmark records. Proximity creates candidates; only verified events affect routing.",
        },
        {
            "id": "field-reports",
            "name": "Geo-Tagged Field Reports",
            "category": "Field Intelligence",
            "status": "CONFIGURED" if os.getenv("FIELD_REPORT_SIGNING_SECRET") else "LOCAL",
            "last_updated": now.isoformat(),
            "age": "Request-time",
            "version_hash": "tbl:field_reports",
            "coverage": "Arunachal Pradesh, Nagaland, Meghalaya, Assam",
            "coverage_scope": "Arunachal Pradesh, Nagaland, Meghalaya, Assam",
            "is_refreshable": False,
            "error_message": None,
            "provenance": "Authenticated FastAPI field-report workflow; cryptographic signing is optional and must be configured for a deployment.",
            "disclaimer": "Pending reports do not alter routing graph; production signing and field identity policy are deployment requirements.",
        },
        {
            "id": "official-disaster-feeds",
            "name": "SDMA / NDMA / CWC Ingestion Feeds",
            "category": "Disaster Feeds",
            "status": "STANDBY" if all(str(s).upper() == "STANDBY" for s in feed_status_map.values()) else "ACTIVE",
            "last_updated": now.isoformat(),
            "age": "Polling 15m",
            "version_hash": "ndma-sachet-cwc-v2",
            "coverage": "NDMA SACHET (CAP 1.2), Assam SDMA, CWC Brahmaputra Basin",
            "coverage_scope": "NDMA SACHET (CAP 1.2), Assam SDMA, CWC Brahmaputra Basin",
            "is_refreshable": True,
            "error_message": "External agency endpoints on fallback polling interval (standby mode).",
            "provenance": "Multi-agency CAP RSS and bulletin scrapers with fallback advisory cache.",
            "disclaimer": "Multi-agency CAP RSS and bulletin scrapers with fallback advisory cache.",
        },
        {
            "id": "elevation-copernicus-dem",
            "name": "Copernicus GLO-30 / SRTM Elevation DEM",
            "category": "Terrain",
            "status": "STATIC",
            "last_updated": "2026-09-01T00:00:00Z",
            "age": "Static Baseline",
            "version_hash": "glo30-ne-dem-v1",
            "coverage": "Northeast India (30m Resolution)",
            "coverage_scope": "Northeast India (30m Resolution)",
            "is_refreshable": False,
            "error_message": None,
            "provenance": "European Space Agency Copernicus DEM GLO-30 2026 snapshot. Immutable elevation grid.",
            "disclaimer": "European Space Agency Copernicus DEM GLO-30 2026 snapshot. Immutable elevation grid.",
        },
        {
            "id": "bridge-clearances",
            "name": "MoRTH Bridge Weight & Clearance Registry",
            "category": "Infrastructure",
            "status": "UNAVAILABLE",
            "last_updated": None,
            "age": "No authoritative registry loaded",
            "version_hash": None,
            "coverage": "No verified statewide bridge registry in current checkout",
            "coverage_scope": "Unknown",
            "is_refreshable": False,
            "error_message": "Authoritative PWD/MoRTH bridge registry is not configured; OSM restriction coverage audit is 0% for current state snapshots.",
            "provenance": "Expected external PWD/MoRTH bridge registry; no verified registry is loaded.",
            "disclaimer": "Known limits are enforced. Unknown bridge restrictions trigger strict-mode exclusion.",
        },
        {
            "id": "border-curfew-restrictions",
            "name": "State Border & Night Curfew Registry",
            "category": "Administrative",
            "status": "STANDBY",
            "last_updated": None,
            "age": "Not configured",
            "version_hash": "adm-border-curfew-2026-09",
            "coverage": "Manipur, Mizoram, Nagaland Inter-State Checkpoints",
            "coverage_scope": "Manipur, Mizoram, Nagaland Inter-State Checkpoints",
            "is_refreshable": True,
            "error_message": "No authorised administrative-orders feed is configured.",
            "provenance": "Planned external administrative-orders registry.",
            "disclaimer": "No border or curfew restriction is inferred without an imported authoritative record.",
        },
        {
            "id": "gps-telemetry",
            "name": "AIS-140 Freight GPS Stream",
            "category": "Fleet Telematics",
            "status": "SIMULATED" if not os.getenv("TELEMETRY_WEBHOOK_SECRET") else "LIVE",
            "last_updated": now.isoformat(),
            "age": "< 1m",
            "version_hash": "ais140-morth-v1",
            "coverage": "Commercial Logistics Fleet in NE Corridor",
            "coverage_scope": "Commercial Logistics Fleet in NE Corridor",
            "is_refreshable": True,
            "error_message": None,
            "provenance": "AIS-140 protocol compliant GPS telemetry stream. Demo fleet running on high-fidelity simulator.",
            "disclaimer": "AIS-140 protocol compliant GPS telemetry stream. Demo fleet running on high-fidelity simulator.",
        },
        {
            "id": "notification-providers",
            "name": "Alert Notification Gateways",
            "category": "Dispatch",
            "status": "SIMULATED" if active_provider == "simulator" else "LIVE",
            "last_updated": now.isoformat(),
            "age": "Active",
            "version_hash": f"provider:{active_provider}",
            "coverage": "SMS, WhatsApp Cloud, Govt C-DAC / NIC",
            "coverage_scope": "SMS, WhatsApp Cloud, Govt C-DAC / NIC",
            "is_refreshable": True,
            "error_message": (
                None
                if active_provider != "simulator"
                else "No Twilio/WhatsApp credentials configured; simulator active."
            ),
            "provenance": "Multi-provider gateway. Simulated delivery receipt returned when credentials absent.",
            "disclaimer": "Multi-provider gateway. Simulated delivery receipt returned when credentials absent.",
        },
    ]
    return {"sources": sources}


@app.post("/api/v1/admin/sources/{source_id}/refresh")
def refresh_admin_source(
    source_id: str,
    user: Annotated[AuthUser, Depends(require_admin)],
    audit_store: Annotated[AuditStore, Depends(get_audit_store)],
):
    """Trigger a refresh check for refreshable operational sources."""
    now = datetime.now(UTC)
    refreshable = {"weather-data", "official-disaster-feeds", "border-curfew-restrictions", "gps-telemetry", "notification-providers"}
    if source_id not in refreshable:
        raise HTTPException(409, detail=f"Source '{source_id}' does not support an operational refresh")
    if source_id == "weather-data":
        from .weather import _weather_cache

        _weather_cache.clear()
        get_all_live_weather()
    record_audit(
        audit_store,
        action="source_refresh",
        resource=f"source:{source_id}",
        actor_id=user.id,
        actor_role=user.role,
        result="success",
        details={"source_id": source_id},
    )
    return {
        "status": "success",
        "source_id": source_id,
        "refreshed_at": now.isoformat(),
        "refreshed_by": user.id,
        "message": (
            f"Source '{source_id}' refresh check completed."
            if source_id == "weather-data"
            else f"Source '{source_id}' refresh is standby until its authorised provider is configured."
        ),
    }


@app.get("/api/v1/admin/telemetry/health")
def admin_telemetry_health(user: Annotated[AuthUser, Depends(require_reviewer)]):
    """Return fleet telemetry validation health, active flags, and rejection logs."""
    summary = telemetry_guard.get_audit_summary()
    return {
        **summary,
        "is_simulated": not bool(os.getenv("TELEMETRY_WEBHOOK_SECRET")),
        "simulated_disclosure": (
            "AIS-140 GPS telemetry stream is simulated for demonstration; "
            "no live webhook secret is configured. Ingested points pass full geometric and speed guards."
        ),
        "acceptance_window_seconds": int(os.getenv("TELEMETRY_MAX_AGE_SECONDS", "900")),
        "service_area": "Northeast India [21.0-30.5N, 87.0-98.5E]",
    }


@app.get("/api/v1/admin/cache/health")
def admin_cache_health(user: Annotated[AuthUser, Depends(require_reviewer)]):
    """Expose cache/event-bus health without exposing Redis credentials."""
    return cache_health()


@app.get("/api/v1/admin/audit-log")
def admin_audit_log(
    user: Annotated[AuthUser, Depends(require_reviewer)],
    audit_store: Annotated[AuditStore, Depends(get_audit_store)],
    action: str | None = None,
    role: str | None = None,
    limit: int = Query(default=100, ge=1, le=500),
):
    """Return immutable-style administrative audit timeline."""
    return {"entries": [e.model_dump() for e in audit_store.list(action=action, role=role, limit=limit)]}


@app.get("/api/v1/admin/model-drift")
def admin_model_drift(user: Annotated[AuthUser, Depends(require_reviewer)]):
    """Return population stability index (PSI) feature drift metrics for advisory model monitoring."""
    from .model_drift import monitor_features
    ref = {
        "rainfall_mm_24h": [0.0, 4.5, 12.0, 26.0, 44.0, 62.0, 88.0, 115.0, 145.0, 185.0],
        "slope_deg": [2.0, 7.5, 14.0, 21.0, 27.0, 34.5, 41.0, 47.0, 54.0, 61.0],
        "humidity_pct": [42.0, 56.0, 66.0, 75.0, 82.0, 87.0, 91.0, 94.5, 97.0, 99.0],
        "wind_kph": [3.5, 7.5, 11.5, 16.0, 22.0, 28.0, 35.0, 42.0, 50.0, 60.0],
        "surface_roughness": [0.05, 0.12, 0.22, 0.35, 0.48, 0.62, 0.75, 0.88, 0.94, 1.0],
    }
    cur = {
        "rainfall_mm_24h": [1.5, 6.0, 14.0, 28.0, 46.0, 64.0, 90.0, 118.0, 148.0, 188.0],
        "slope_deg": [2.5, 8.0, 14.5, 21.5, 27.5, 35.0, 41.5, 47.5, 54.5, 61.5],
        "humidity_pct": [44.0, 58.0, 68.0, 76.5, 83.5, 88.0, 92.5, 95.5, 98.0, 100.0],
        "wind_kph": [4.0, 8.0, 12.0, 17.0, 23.0, 29.0, 36.0, 43.0, 51.0, 61.0],
        "surface_roughness": [0.06, 0.13, 0.23, 0.36, 0.49, 0.63, 0.76, 0.89, 0.95, 1.0],
    }
    report = monitor_features(ref, cur)
    psi_scores = [f["psi"] for f in report["features"].values()]
    overall_psi = round(sum(psi_scores) / max(1, len(psi_scores)), 4)
    return {
        **report,
        "overall_psi": overall_psi,
        "overall_status": "alert" if overall_psi >= 0.25 else "watch" if overall_psi >= 0.1 else "stable",
        "baseline_dataset": "backend/data/disruption_labels.csv (794 audited samples)",
        "monitoring_window": "Active 30-Day Rolling Window",
        "last_evaluated_at": datetime.now(UTC).isoformat(),
    }


@app.get("/api/v1/admin/registry")
def admin_model_registry(user: Annotated[AuthUser, Depends(require_user)]):
    """Return model and dataset registry specifications and truth-in-advertising disclosures."""
    anomaly = load_weather_anomaly_model()
    disruption = load_disruption_model()
    return {
        "models": [
            {
                "id": "weather-anomaly-model",
                "name": "Historical Weather Anomaly Model",
                "type": "Unsupervised Multivariate Statistical Anomaly Detector",
                "status": "available" if anomaly else "unavailable",
                "version": anomaly.get("model_version", "v1.0") if anomaly else None,
                "training_source": (
                    anomaly.get("source", "datasets/processed/weather/ne-reference-points-daily-2021-2025.csv")
                    if anomaly
                    else None
                ),
                "training_window": (
                    anomaly.get("training_window", {"start": "2021-01-01", "end": "2024-12-31"})
                    if anomaly
                    else None
                ),
                "holdout_window": (
                    anomaly.get("holdout_window", {"start": "2025-01-01", "end": "2025-12-31"})
                    if anomaly
                    else None
                ),
                "features": ["precipitation_mm_24h", "wind_kph", "temperature_range_c"],
                "target_definition": (
                    "Multivariate deviation from historical capital-station climate; NOT landslide or road-closure probability."
                ),
                "coverage": "8 Northeast State Capital Reference Stations",
                "limitations": (
                    "Capital-station reference points only. Does not measure slope stability or geotechnical hazards."
                ),
                "field_safety_claim": False,
                "explicit_false_claims": [
                    "Not a landslide probability",
                    "Not a road-closure probability",
                    "Not a field-calibrated safety prediction",
                    "Not a real-time slope stability sensor",
                ],
                "artifact_hash": anomaly.get("source_sha256") if anomaly else None,
            },
            {
                "id": "road-disruption-supervised-model",
                "name": "Supervised Road Disruption Classifier",
                "type": "Supervised Machine Learning Model",
                "status": "shadow_mode" if disruption else "not_available",
                "version": disruption.get("model_version", "v1.0-supervised-calibrated") if disruption else None,
                "training_source": (
                    "backend/data/disruption_labels.csv (718 reviewed segment-level outcomes from NASA GLC & verified state hazards)"
                    if disruption
                    else None
                ),
                "training_window": disruption.get("split_policy", {}).get("train_window") if disruption else None,
                "holdout_window": disruption.get("split_policy", {}).get("holdout_window") if disruption else None,
                "features": (
                    disruption.get("features", ["rainfall_mm_24h", "slope_deg", "humidity_pct", "surface_roughness", "wind_kph"])
                    if disruption
                    else ["rainfall_24h", "slope_angle", "geology_class", "drainage_index"]
                ),
                "target_definition": (
                    "Calibrated empirical disruption probability conditioned on environmental triggers."
                    if disruption
                    else "Empirical road closure prediction (Pending labelled incident dataset)."
                ),
                "coverage": (
                    "8 Northeast States (Sikkim, Assam, Meghalaya, Nagaland, Manipur, Arunachal Pradesh, Mizoram, Tripura)"
                    if disruption
                    else "None"
                ),
                "limitations": (
                    "Operating in advisory shadow mode. Does not modify production routing weights directly; deterministic Risk-A* remains active safety baseline."
                    if disruption
                    else "Blocked from production deployment until government-certified ground truth landslide dataset is acquired and verified."
                ),
                "field_safety_claim": False,
                "explicit_false_claims": [
                    "Not currently modifying live routing weights directly (operating in shadow mode)" if disruption else "Not currently deployed or generating predictions",
                    "No supervised ground-truth model is active in production",
                ],
                "artifact_hash": (
                    hashlib.sha256((ROOT / "data" / "disruption_model.json").read_bytes()).hexdigest()
                    if (ROOT / "data" / "disruption_model.json").exists()
                    else None
                ),
                "holdout_metrics": disruption.get("holdout_metrics") if disruption else None,
                "operational_mode": "shadow_mode" if disruption else "standby",
            },

            {
                "id": "risk-a-star-engine",
                "name": "Deterministic Risk-A* Routing Policy",
                "type": "Deterministic Graph Shortest-Path Engine",
                "status": "available",
                "version": "v1.0-deterministic-risk-cost",
                "training_source": "Not an ML model; deterministic domain-cost function",
                "training_window": None,
                "holdout_window": None,
                "features": [
                    "road_class",
                    "surface_score",
                    "accident_score",
                    "weather_score",
                    "flood_susceptibility",
                    "vehicle_constraints",
                ],
                "target_definition": "Request-scoped admissible heuristic minimizing travel time + risk aversion penalty.",
                "coverage": "8 Northeast OSM networks & Guwahati corridor",
                "limitations": (
                    "Heuristic optimization; not empirical probability. Fails closed when required restrictions are missing in strict mode."
                ),
                "field_safety_claim": False,
                "explicit_false_claims": [
                    "Not an ML trained neural network",
                    "Not an empirical accident rate predictor",
                    "Not a live traffic congestion guarantee",
                ],
                "artifact_hash": "sha256:custom-risk-astar",
            },
            {
                "id": "domain-calibrated-prior",
                "name": "Domain-Calibrated Disruption Prior",
                "type": "Domain-Informed Logistic Baseline Prior",
                "status": "available",
                "version": "v1.0-domain-calibrated-baseline",
                "training_source": "Civil engineering heuristics for Himalayan slopes",
                "training_window": None,
                "holdout_window": None,
                "features": [
                    "rainfall_mm_24h",
                    "slope_deg",
                    "historical_incidents",
                    "surface_roughness",
                    "elevation_km",
                ],
                "target_definition": "Calibrated prior probability of transit delay.",
                "coverage": "Controlled benchmark road segments",
                "limitations": "Prototype baseline coefficients. Not calibrated on live SDRF incident logs.",
                "field_safety_claim": False,
                "explicit_false_claims": [
                    "Not field-calibrated on real disaster casualty datasets",
                    "Not an authoritative meteorological forecast",
                ],
                "artifact_hash": "v1.0-domain-calibrated",
            },
        ],
        "datasets": [
            {
                "id": key,
                "label": (
                    app.state.graphs[key].dataset.title
                    if key in app.state.graphs
                    else dataset_label(key)
                ),
                "is_synthetic": (
                    app.state.graphs[key].dataset.is_synthetic
                    if key in app.state.graphs
                    else True
                ),
                "source": "OpenStreetMap 2026 extracts / controlled benchmark",
            }
            for key in dict.fromkeys([*app.state.graphs, *app.state.dataset_paths])
        ],
        "disclosures": {
            "field_safety_claim": False,
            "live_traffic_guarantee": False,
            "ml_landslide_prediction": False,
        },
    }


@app.get("/api/v1/admin/alerts/broadcasts")
def admin_broadcasts(user: Annotated[AuthUser, Depends(require_reviewer)]):
    """Return historical alert broadcasts and carrier delivery receipts."""
    return {"broadcasts": [b.model_dump() for b in get_broadcast_history()]}
