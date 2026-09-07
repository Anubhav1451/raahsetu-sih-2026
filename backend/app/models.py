from datetime import UTC, datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid", allow_inf_nan=False)


class Node(StrictModel):
    id: str
    lon: float = Field(ge=-180, le=180)
    lat: float = Field(ge=-90, le=90)
    label: str | None = None


class Edge(StrictModel):
    id: str
    u: str
    v: str
    name: str
    length_m: float = Field(gt=0)
    speed_kph: float = Field(gt=0, le=160)
    geometry: list[tuple[float, float]] = Field(min_length=2)
    accident_score: float = Field(default=0, ge=0, le=1)
    surface_score: float = Field(default=0, ge=0, le=1)
    weather_score: float = Field(default=0, ge=0, le=1)
    flood_susceptibility: float = Field(default=0, ge=0, le=1)
    closed: bool = False
    max_height_m: float | None = Field(default=None, gt=0)
    max_weight_t: float | None = Field(default=None, gt=0)
    max_width_m: float | None = Field(default=None, gt=0)
    hgv_allowed: bool | None = None
    evidence: str = "unknown"
    risk_data_known: bool = True
    observed_at: str | None = None

    @model_validator(mode="after")
    def valid_coordinates(self):
        if any(not (-180 <= lon <= 180 and -90 <= lat <= 90) for lon, lat in self.geometry):
            raise ValueError("Edge geometry must contain finite WGS84 [longitude, latitude] pairs")
        return self


class Scenario(StrictModel):
    id: str
    label: str
    description: str
    closed_edge_ids: list[str]


class Dataset(StrictModel):
    id: str
    title: str
    region: str
    source: str
    generated_at: str
    is_synthetic: bool
    hazard_source: str
    terrain_source: str = "Illustrative terrain; not measured elevation"
    limitations: list[str]
    nodes: list[Node] = Field(min_length=2)
    edges: list[Edge] = Field(min_length=1)
    scenarios: list[Scenario] = []
    default_origin: str
    default_destination: str

    @model_validator(mode="after")
    def references_exist(self):
        node_ids = {node.id for node in self.nodes}
        edge_ids = {edge.id for edge in self.edges}
        if len(node_ids) != len(self.nodes) or len(edge_ids) != len(self.edges):
            raise ValueError("Node and directed edge IDs must be unique")
        if self.default_origin not in node_ids or self.default_destination not in node_ids:
            raise ValueError("Default endpoints must exist")
        if any(edge.u not in node_ids or edge.v not in node_ids for edge in self.edges):
            raise ValueError("Every edge endpoint must exist")
        if any(set(s.closed_edge_ids) - edge_ids for s in self.scenarios):
            raise ValueError("Scenario contains unknown edges")
        return self


class Endpoint(StrictModel):
    node_id: str | None = None
    lat: float | None = Field(default=None, ge=-90, le=90)
    lon: float | None = Field(default=None, ge=-180, le=180)

    @model_validator(mode="after")
    def one_location_format(self):
        node = self.node_id is not None
        coordinates = self.lat is not None and self.lon is not None
        if node == coordinates or (node and (self.lat is not None or self.lon is not None)):
            raise ValueError("Supply node_id OR both lat and lon")
        return self


class RouteRequest(StrictModel):
    dataset_id: str = Field(default="demo", min_length=1, max_length=100)
    origin: Endpoint
    destination: Endpoint
    vehicle: Literal["heavy", "emergency", "light"] = "heavy"
    risk_aversion: float = Field(default=1.5, ge=0, le=5)
    weather: Literal["normal", "heavy_rain"] = "normal"
    closed_edge_ids: list[str] = Field(default_factory=list, max_length=500)
    strict_vehicle: bool = False


class FieldReportCreate(StrictModel):
    client_report_id: str = Field(min_length=8, max_length=120, pattern=r"^[A-Za-z0-9._:-]+$")
    region_code: str = Field(min_length=3, max_length=40, pattern=r"^[a-z]+(?:-[a-z]+)*$")
    district: str | None = Field(default=None, max_length=120)
    place_name: str | None = Field(default=None, max_length=160)
    kind: Literal[
        "road_blocked",
        "road_damage",
        "bridge_damage",
        "landslide",
        "flood",
        "heavy_rain",
        "traffic_congestion",
        "other",
    ]
    accessibility_status: Literal["open", "restricted", "blocked", "unknown"]
    severity: float = Field(ge=0, le=1)
    lon: float = Field(ge=-180, le=180)
    lat: float = Field(ge=-90, le=90)
    description: str = Field(min_length=5, max_length=2000)
    observed_at: datetime
    valid_until: datetime | None = None
    offline_created_at: datetime | None = None
    details: dict = Field(default_factory=dict)

    @model_validator(mode="after")
    def valid_times(self):
        observed = self.observed_at
        if observed.tzinfo is None:
            raise ValueError("observed_at must include a timezone")
        if observed > datetime.now(UTC):
            raise ValueError("observed_at cannot be in the future")
        if self.valid_until is not None:
            if self.valid_until.tzinfo is None:
                raise ValueError("valid_until must include a timezone")
            if self.valid_until < observed:
                raise ValueError("valid_until cannot be before observed_at")
        return self


class FieldReport(StrictModel):
    id: str
    client_report_id: str
    region_code: str
    district: str | None
    place_name: str | None
    kind: str
    accessibility_status: str
    severity: float
    lon: float
    lat: float
    description: str
    observed_at: datetime
    submitted_at: datetime
    review_status: str
    valid_until: datetime | None
    offline_created_at: datetime | None
    details: dict


class FieldReportReview(StrictModel):
    decision: Literal["accepted", "rejected"]
    review_note: str = Field(min_length=5, max_length=1000)
    dataset_id: str | None = Field(default=None, max_length=100)
    edge_id: str | None = Field(default=None, max_length=200)

    @model_validator(mode="after")
    def requires_match_for_acceptance(self):
        if self.decision == "accepted" and (not self.dataset_id or not self.edge_id):
            raise ValueError("Accepted reports require a reviewed dataset and road edge")
        return self


class FieldReportAttachment(StrictModel):
    id: str
    report_id: str
    storage_path: str
    mime_type: str
    byte_size: int
    sha256: str
    captured_at: datetime | None = None


class PositionCreate(StrictModel):
    vehicle_id: str
    recorded_at: datetime
    lon: float = Field(ge=-180, le=180)
    lat: float = Field(ge=-90, le=90)
    speed_kph: float | None = Field(default=None, ge=0, le=200)
    heading: float | None = Field(default=None, ge=0, le=360)
    status: Literal["en_route", "delayed", "stopped", "delivered"] = "en_route"
    accuracy_m: float | None = Field(default=None, ge=0, le=10000)
    metadata: dict = Field(default_factory=dict)


class VehiclePosition(StrictModel):
    id: str
    vehicle_id: str
    recorded_at: datetime
    lon: float
    lat: float
    speed_kph: float | None
    heading: float | None
    status: str
    accuracy_m: float | None
    metadata: dict


class VehicleSummary(VehiclePosition):
    region_code: str
    registration: str
    vehicle_type: str


class VehicleAsset(StrictModel):
    id: str
    region_code: str
    registration: str
    vehicle_type: Literal["heavy", "emergency", "light"]
    active: bool
    metadata: dict


class DeliveryJob(StrictModel):
    id: str
    vehicle_id: str
    region_code: str
    commodity: str
    origin_name: str
    destination_name: str
    status: Literal["planned", "en_route", "delayed", "delivered", "cancelled"]
    eta_at: datetime | None
    delivered_at: datetime | None
    created_at: datetime
    metadata: dict


class DeliveryCreate(StrictModel):
    vehicle_id: str
    region_code: str = Field(min_length=3, max_length=40, pattern=r"^[a-z]+(?:-[a-z]+)*$")
    commodity: str = Field(min_length=2, max_length=120)
    origin_name: str = Field(min_length=2, max_length=160)
    destination_name: str = Field(min_length=2, max_length=160)
    eta_at: datetime | None = None
    metadata: dict = Field(default_factory=dict)


class DeliveryUpdate(StrictModel):
    status: Literal["planned", "en_route", "delayed", "delivered", "cancelled"]
    eta_at: datetime | None = None


class Alert(StrictModel):
    id: str
    event_id: str
    region_code: str
    alert_type: Literal["blocked_route", "high_risk", "delay", "reopened"]
    severity: float
    title: str
    message_key: str
    message_params: dict
    created_at: datetime
    expires_at: datetime | None


class ConnectivitySummary(StrictModel):
    region_code: str
    state_name: str
    active_events: int
    blocked_events: int
    restricted_events: int
    status: Literal["open", "restricted", "blocked"]
    last_event_at: datetime | None
