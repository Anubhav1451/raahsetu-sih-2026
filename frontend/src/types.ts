export type Coordinates = [number, number];
export type ElevationGrid = {
  west: number;
  east: number;
  south: number;
  north: number;
  rows: number;
  cols: number;
  values: (number | null)[][];
  vertical_exaggeration: number;
  source: string;
  void_samples: number;
};
export type Location = { id: string; lon: number; lat: number; label: string };
export type SearchResult = Location & {
  dataset_id: string;
  kind: "road" | "place" | "facility";
  detail?: string;
  snap_distance_m?: number;
};
export type Vehicle = "heavy" | "emergency" | "light";
export type Weather = "normal" | "heavy_rain";
export type Bootstrap = {
  dataset: {
    id: string;
    title: string;
    region: string;
    source: string;
    generated_at: string;
    is_synthetic: boolean;
    hazard_source: string;
    terrain_source: string;
    limitations: string[];
    default_origin: string;
    default_destination: string;
  };
  dataset_version: string;
  available_datasets: { id: string; label: string; is_synthetic: boolean }[];
  counts: { nodes: number; edges: number };
  locations: Location[];
  vehicles: Record<
    Vehicle,
    {
      label: string;
      height_m: number;
      weight_t: number;
      width_m: number;
      speed_kph: number;
    }
  >;
  scenarios: {
    id: string;
    label: string;
    description: string;
    closed_edge_ids: string[];
  }[];
};
export type DataStatus = {
  status: "demo_only" | "ready";
  audited_at: string | null;
  freshness_policy: {
    meaning: string;
    weather_cache_minutes: number;
    official_feed_status: string;
  };
  sources: {
    source_id: string;
    source_name: string;
    kind: string;
    status: string;
    coverage: string;
    last_audited_at: string | null;
    versioning: string;
  }[];
  runtime_snapshots: string[];
  runtime_snapshot_count: number;
  downloaded_files: number;
  downloaded_bytes: number;
  terrain_tiles: number;
  terrain_tiles_planned: number;
  weather_reference_point_days: number;
  historical_ne_landslides: number;
  gaps: string[];
};
export type Network = {
  type: "FeatureCollection";
  metadata: {
    dataset_id: string;
    focus_node: string;
    focus: { lon: number; lat: number };
    radius_km: number;
    returned_features: number;
    total_features: number;
    truncated: boolean;
  };
  features: {
    type: "Feature";
    geometry: { type: "LineString"; coordinates: Coordinates[] };
    properties: {
      id: string;
      name: string;
      u: string;
      v: string;
      risk: number;
      closed: boolean;
      evidence: string;
    };
  }[];
};
export type AvailableRoute = {
  id: "fastest" | "risk_aware";
  status: "available";
  edge_ids: string[];
  geometry: { type: "LineString"; coordinates: Coordinates[] };
  route_geometry?: { type: "LineString"; coordinates: Coordinates[] };
  geometry_complete?: boolean;
  geometry_source?: string;
  distance_km: number;
  duration_min: number;
  risk_exposure: number;
  mean_risk_score: number;
  high_risk_segments: number;
  unknown_restriction_segments: number;
  unknown_risk_segments: number;
  objective_cost: number;
  expanded_nodes: number;
  compute_ms: number;
  roads: string[];
  warnings: string[];
};
export type Route =
  | AvailableRoute
  | { id: "fastest" | "risk_aware"; status: "unreachable"; reason: string };
export type Comparison = {
  snapped?: { origin: string; destination: string; origin_distance_m: number; destination_distance_m: number; origin_coordinates?: Coordinates; destination_coordinates?: Coordinates };
  dataset_id: string;
  dataset_version: string;
  routes: Route[];
  comparison: {
    extra_minutes: number;
    exposure_reduction_pct: number | null;
    same_route: boolean;
  } | null;
  explanations: {
    edge_id: string;
    road: string;
    reason: string;
    score: number;
    evidence: string;
    ml_disruption_probability?: number;
    ml_primary_factor?: string;
  }[];
  assumptions: string[];
};
export type RouteInput = {
  dataset_id: string;
  origin: { node_id: string } | { lon: number; lat: number };
  destination: { node_id: string } | { lon: number; lat: number };
  vehicle: Vehicle;
  risk_aversion: number;
  weather: Weather;
  closed_edge_ids: string[];
  strict_vehicle: boolean;
};

export type FieldReportInput = {
  client_report_id: string;
  region_code: string;
  district?: string;
  place_name?: string;
  kind:
    | "road_blocked"
    | "road_damage"
    | "bridge_damage"
    | "landslide"
    | "flood"
    | "heavy_rain"
    | "traffic_congestion"
    | "other";
  accessibility_status: "open" | "restricted" | "blocked" | "unknown";
  severity: number;
  lon: number;
  lat: number;
  description: string;
  observed_at: string;
  offline_created_at?: string;
  details?: Record<string, unknown>;
};

export type FieldReport = FieldReportInput & {
  id: string;
  submitted_at: string;
  review_status: "pending" | "corroborated" | "accepted" | "authority_verified" | "rejected" | "expired";
  valid_until: string | null;
};
export type FieldReportAttachment = {
  id: string;
  report_id: string;
  storage_path: string;
  mime_type: string;
  byte_size: number;
  sha256: string;
  captured_at: string | null;
};
export type AccessibilityEvent = {
  id: string;
  region_code: string;
  dataset_id: string | null;
  edge_id: string | null;
  kind: string;
  accessibility_status: "open" | "restricted" | "blocked";
  severity: number;
  lon: number;
  lat: number;
  starts_at: string;
  ends_at: string | null;
  source: string;
  details: Record<string, unknown>;
};
export type Alert = {
  id: string;
  event_id: string;
  region_code: string;
  alert_type: "blocked_route" | "high_risk" | "delay" | "reopened";
  severity: number;
  title: string;
  message_key: string;
  message_params: Record<string, unknown>;
  created_at: string;
  expires_at: string | null;
};
export type ConnectivitySummary = {
  region_code: string;
  state_name: string;
  active_events: number;
  blocked_events: number;
  restricted_events: number;
  status: "open" | "restricted" | "blocked";
  last_event_at: string | null;
};
export type VehicleAsset = { id: string; region_code: string; registration: string; vehicle_type: Vehicle; active: boolean; metadata: Record<string, unknown> };
export type VehiclePosition = { id: string; vehicle_id: string; recorded_at: string; lon: number; lat: number; speed_kph: number | null; heading: number | null; status: string; accuracy_m: number | null; metadata: Record<string, unknown> };
export type DeliveryJob = { id: string; vehicle_id: string; region_code: string; commodity: string; origin_name: string; destination_name: string; status: "planned" | "en_route" | "delayed" | "delivered" | "cancelled"; eta_at: string | null; delivered_at: string | null; created_at: string; metadata: Record<string, unknown> };
export type RoadCandidate = { edge_id: string; name: string; distance_m: number };

export type AuthSession = {
  access_token: string;
  refresh_token: string;
  expires_in: number;
  expires_at?: number;
  user: { id: string; email?: string };
};

export interface AdminSourceItem {
  id: string;
  name: string;
  category: string;
  status: "LIVE" | "FRESH" | "STALE" | "STANDBY" | "SIMULATED" | "STATIC" | "ONLINE" | "UNAVAILABLE";
  last_updated: string | null;
  age: string;
  version_hash: string;
  coverage: string;
  coverage_scope: string;
  is_refreshable: boolean;
  error_message: string | null;
  provenance: string;
  disclaimer: string;
}

export interface AdminSourcesResponse {
  sources: AdminSourceItem[];
}

export interface TelemetryRejection {
  vehicle_id: string;
  timestamp: string;
  reason: string;
  coordinates?: [number, number];
  error_type?: string;
  details?: string;
}

export interface TelemetryHealthResponse {
  total_packets_received: number;
  accepted_packets: number;
  rejected_packets: number;
  rejection_summary: Record<string, number>;
  recent_rejections: TelemetryRejection[];
  simulated_disclosure: string;
  is_simulated: boolean;
  acceptance_window_seconds: number;
  service_area: string;
  tracked_vehicles: number;
}

export interface CacheHealthResponse {
  configured: boolean;
  backend: "redis" | "in-memory";
  reachable: boolean;
  redis_version?: string | null;
  authoritative_store: string;
}

export interface AuditEntry {
  id: string;
  actor_id: string | null;
  actor_role: string | null;
  action: string;
  resource: string;
  result: "success" | "failure" | "denied";
  details: Record<string, unknown>;
  timestamp: string;
}

export interface ModelSpecification {
  id: string;
  name: string;
  type: string;
  status?: string;
  version?: string | null;
  coverage: string;
  training_source?: string | null;
  training_window?: { start: string; end: string } | null;
  holdout_window?: { start: string; end: string } | null;
  features: string[];
  target_definition: string;
  field_safety_claim: boolean;
  explicit_false_claims: string[];
  limitations: string;
  artifact_hash?: string | null;
}

export interface ModelRegistryResponse {
  models: ModelSpecification[];
  datasets: { id: string; label: string; is_synthetic: boolean; source: string }[];
  disclosures: {
    field_safety_claim: boolean;
    live_traffic_guarantee: boolean;
    ml_landslide_prediction: boolean;
  };
}

export interface PublicCandidate {
  candidate_id: string;
  region_code: string;
  road_text: string;
  source_url: string;
  source_type: string;
  published_at: string;
  reported_status: string;
  review_status: string;
  coordinates_verified: boolean;
  road_segment_id?: string | null;
  incident_started_at?: string | null;
  incident_ended_at?: string | null;
  restriction_effective_at?: string | null;
  reopening_effective_at?: string | null;
  evidence_note?: string;
  reviewer_id?: string | null;
  review_note?: string;
}

export interface DeliveryReceipt {
  recipient: string;
  status: "DELIVERED" | "QUEUED" | "SIMULATED_SUCCESS" | "FAILED";
  message_id: string;
  sent_at: string;
  carrier: string;
}

export interface BroadcastHistoryItem {
  broadcast_id: string;
  provider: string;
  is_simulated: boolean;
  language: string;
  template_used: string;
  message_body: string;
  recipient_count: number;
  deliveries: DeliveryReceipt[];
  note: string;
}

export interface BroadcastHistoryResponse {
  broadcasts: BroadcastHistoryItem[];
}

export interface FeedSourceStatus {
  source_id: string;
  source_name: string;
  agency: string;
  feed_type: "REST_API" | "CAP_XML" | "RSS_FEED" | "NWP_GRID" | "JSON_FEED";
  status: "ONLINE" | "SYNCED" | "DEGRADED" | "STANDBY" | "STALE" | "ERROR";
  last_synced_at: string;
  active_advisories_count: number;
  coverage: string;
  last_attempted_fetch?: string | null;
  last_successful_fetch?: string | null;
  source_timestamp?: string | null;
  freshness_threshold_seconds: number;
  is_stale: boolean;
  parser_errors: string[];
  requires_auth: boolean;
  credentials_configured: boolean;
  required_credentials: string[];
  authority_approval_required: string;
  audit_notes?: string | null;
}

export interface OfficialHazardAdvisory {
  advisory_id: string;
  source_agency: string;
  state: string;
  severity: "WARNING" | "ALERT" | "WATCH" | "ADVISORY";
  headline: string;
  affected_corridors: string[];
  effective_from: string;
  effective_until: string;
  coordinates: [number, number];
  recommended_action: string;
  source_timestamp?: string | null;
  source_feed_id?: string | null;
  raw_payload_hash?: string | null;
  review_status: "candidate_advisory" | "pending_review" | "accepted" | "rejected" | "conflicting" | "duplicate";
  is_stale?: boolean;
  conflict_detected?: boolean;
  conflict_note?: string | null;
  reviewer_id?: string | null;
  review_note?: string | null;
  reviewed_at?: string | null;
  source_evidence?: string | null;
  road_segment_id?: string | null;
}

export interface LiveFeedsResponse {
  sources: FeedSourceStatus[];
  active_advisories: OfficialHazardAdvisory[];
}

export interface FeedDiagnosticsResponse {
  parser_health: Record<string, string>;
  duplicate_suppression_count: number;
  conflict_detection_count: number;
  candidate_advisories_awaiting_review: number;
  diagnostic_runs_count: number;
  last_diagnostic_at: string | null;
  simulation_disclosure: string;
}

export interface CandidateAdvisoryReviewRequest {
  decision: "accept" | "reject" | "mark_duplicate" | "mark_conflicting";
  source_evidence: string;
  affected_corridor: string;
  review_note: string;
  road_segment_id?: string | null;
}
