import type {
  Bootstrap,
  DataStatus,
  AuthSession,
  AccessibilityEvent,
  Alert,
  ConnectivitySummary,
  VehicleAsset,
  VehiclePosition,
  DeliveryJob,
  Comparison,
  ElevationGrid,
  FieldReport,
  FieldReportInput,
  FieldReportAttachment,
  RoadCandidate,
  Network,
  RouteInput,
  SearchResult,
  Weather,
  AdminSourcesResponse,
  TelemetryHealthResponse,
  CacheHealthResponse,
  AuditEntry,
  ModelRegistryResponse,
  BroadcastHistoryResponse,
  BroadcastHistoryItem,
  PublicCandidate,
  CandidateAdvisoryReviewRequest,
  FeedDiagnosticsResponse,
  LiveFeedsResponse,
  OfficialHazardAdvisory,
} from "./types";

export const getPublicCandidates = (token: string, status?: string) =>
  request<PublicCandidate[]>(`/api/v1/admin/public-candidates${status ? `?status=${encodeURIComponent(status)}` : ""}`, { headers: { Authorization: `Bearer ${token}` } });
export const reviewPublicCandidate = (token: string, candidateId: string, body: { decision: string; road_segment_id?: string; incident_started_at?: string; incident_ended_at?: string; restriction_effective_at?: string; reopening_effective_at?: string; review_note: string }) =>
  request<PublicCandidate>(`/api/v1/admin/public-candidates/${encodeURIComponent(candidateId)}/review`, { method: "PATCH", headers: { "Content-Type": "application/json", Authorization: `Bearer ${token}` }, body: JSON.stringify(body) });

const API = (import.meta.env.VITE_API_BASE_URL ?? "").replace(/\/+$/, "");
async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${API}${path}`, {
    ...init,
    signal: init?.signal ?? AbortSignal.timeout(20000),
  });
  if (!response.ok) {
    const body = await response.json().catch(() => null);
    throw new Error(
      typeof body?.detail === "string"
        ? body.detail
        : `Request failed (${response.status}).`,
    );
  }
  return response.json() as Promise<T>;
}
export const getBootstrap = (dataset = "demo") =>
  request<Bootstrap>(
    `/api/v1/bootstrap?dataset=${encodeURIComponent(dataset)}`,
  );
export const getDataStatus = () => request<DataStatus>("/api/v1/data-status");
export const getTerrain = (dataset = "demo") =>
  request<ElevationGrid | null>(
    `/api/v1/terrain?dataset=${encodeURIComponent(dataset)}`,
  );
export const getNetwork = (
  weather: Weather = "normal",
  dataset = "demo",
  focusNode?: string,
) =>
  request<Network>(
    `/api/v1/network?weather=${weather}&dataset=${encodeURIComponent(dataset)}${focusNode ? `&focus_node=${encodeURIComponent(focusNode)}` : ""}`,
  );
export const compareRoutes = (input: RouteInput, signal: AbortSignal) =>
  request<Comparison>("/api/v1/routes/compare", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(input),
    signal,
  });
export const searchPlaces = (query: string, dataset?: string) =>
  request<{ results: SearchResult[] }>(
    `/api/v1/search?q=${encodeURIComponent(query)}${dataset ? `&dataset=${encodeURIComponent(dataset)}` : ""}`,
  );
export const createFieldReport = (input: FieldReportInput, token: string) =>
  request<FieldReport>("/api/v1/field-reports", {
    method: "POST",
    headers: { "Content-Type": "application/json", Authorization: `Bearer ${token}` },
    body: JSON.stringify(input),
  });
export const uploadFieldReportAttachment = (token: string, reportId: string, file: File) => {
  const body = new FormData();
  body.append("file", file);
  return request<FieldReportAttachment>(`/api/v1/field-reports/${encodeURIComponent(reportId)}/attachments`, {
    method: "POST",
    headers: { Authorization: `Bearer ${token}` },
    body,
  });
};
export const getFieldReports = (token: string, regionCode?: string) =>
  request<FieldReport[]>(
    `/api/v1/field-reports${regionCode ? `?region_code=${encodeURIComponent(regionCode)}` : ""}`,
    { headers: { Authorization: `Bearer ${token}` } },
  );
export const getAccessibilityEvents = (regionCode?: string) =>
  request<{ events: AccessibilityEvent[] }>(
    `/api/v1/accessibility-events${regionCode ? `?region_code=${encodeURIComponent(regionCode)}` : ""}`,
  );
export const getAlerts = (token: string) => request<Alert[]>("/api/v1/alerts", { headers: { Authorization: `Bearer ${token}` } });
export const getConnectivity = (token: string) => request<ConnectivitySummary[]>("/api/v1/connectivity", { headers: { Authorization: `Bearer ${token}` } });
export const getFleetVehicles = (token: string) => request<VehicleAsset[]>("/api/v1/fleet/vehicles", { headers: { Authorization: `Bearer ${token}` } });
export const sendFleetPosition = (
  token: string,
  payload: {
    vehicle_id: string;
    recorded_at: string;
    lon: number;
    lat: number;
    speed_kph?: number | null;
    heading?: number | null;
    status?: "en_route" | "delayed" | "stopped" | "delivered";
    accuracy_m?: number | null;
  },
) => request<VehiclePosition>("/api/v1/fleet/positions", { method: "POST", headers: { "Content-Type": "application/json", Authorization: `Bearer ${token}` }, body: JSON.stringify(payload) });
export const getDeliveries = (token: string) => request<DeliveryJob[]>("/api/v1/deliveries", { headers: { Authorization: `Bearer ${token}` } });
export const updateDelivery = (token: string, deliveryId: string, payload: Pick<DeliveryJob, "status"> & { eta_at?: string | null }) => request<DeliveryJob>(`/api/v1/deliveries/${encodeURIComponent(deliveryId)}`, { method: "PATCH", headers: { "Content-Type": "application/json", Authorization: `Bearer ${token}` }, body: JSON.stringify(payload) });

export type LiveWeatherStation = {
  region_code: string;
  station: string;
  lat: number;
  lon: number;
  temperature_c: number;
  humidity_pct: number;
  precipitation_mm_24h: number;
  wind_kph: number;
  condition: string;
  heavy_rain_warning: boolean;
  source: string;
  fetched_at: string;
  fresh: boolean;
  stale: boolean;
};

export const getLiveWeather = (regionCode?: string) =>
  request<LiveWeatherStation>(
    `/api/v1/weather/live${regionCode ? `?region_code=${encodeURIComponent(regionCode)}` : ""}`,
  );
export const getAllLiveWeather = () =>
  request<{ stations: LiveWeatherStation[] }>("/api/v1/weather/live");

type PublicConfig = { supabase_url: string; supabase_publishable_key: string };
export class AuthError extends Error {
  constructor(message: string, public status: number) { super(message); }
}
let publicConfig: Promise<PublicConfig> | undefined;
const getPublicConfig = () =>
  (publicConfig ??= request<PublicConfig>("/api/v1/public-config").catch((error) => {
    publicConfig = undefined;
    throw error;
  }));

async function authRequest(path: string, body: Record<string, unknown>) {
  const config = await getPublicConfig();
  const response = await fetch(`${config.supabase_url}/auth/v1/${path}`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      apikey: config.supabase_publishable_key,
    },
    body: JSON.stringify(body),
    signal: AbortSignal.timeout(15000),
  });
  const payload = await response.json().catch(() => ({}));
  if (!response.ok) throw new AuthError(payload.msg || payload.error_description || "Authentication failed.", response.status);
  if (payload.access_token && !payload.expires_at) {
    payload.expires_at = Math.floor(Date.now() / 1000) + payload.expires_in;
  }
  return payload as AuthSession;
}

export const signIn = (email: string, password: string) =>
  authRequest("token?grant_type=password", { email, password });
export const signUp = (email: string, password: string, displayName: string) =>
  authRequest("signup", { email, password, data: { display_name: displayName } });

export const consumeOAuthCallback = async (): Promise<AuthSession | null> => {
  if (!window.location.hash.includes("access_token=")) return null;
  const params = new URLSearchParams(window.location.hash.slice(1));
  const accessToken = params.get("access_token");
  const refreshToken = params.get("refresh_token");
  if (!accessToken || !refreshToken) throw new AuthError("The Google sign-in response was incomplete.", 400);
  const config = await getPublicConfig();
  const response = await fetch(`${config.supabase_url}/auth/v1/user`, {
    headers: { apikey: config.supabase_publishable_key, Authorization: `Bearer ${accessToken}` },
    signal: AbortSignal.timeout(15000),
  });
  const user = await response.json().catch(() => ({}));
  if (!response.ok || !user.id) throw new AuthError("Google sign-in could not verify this account.", response.status);
  const expiresIn = Number(params.get("expires_in") || 3600);
  const session: AuthSession = {
    access_token: accessToken,
    refresh_token: refreshToken,
    expires_in: expiresIn,
    expires_at: Math.floor(Date.now() / 1000) + expiresIn,
    user: { id: user.id, email: user.email },
  };
  window.history.replaceState({}, document.title, window.location.pathname + window.location.search);
  return session;
};

export const refreshSession = (refreshToken: string) =>
  authRequest("token?grant_type=refresh_token", { refresh_token: refreshToken });

export const getProfile = (token: string) =>
  request<{ id: string; role: string; region_code: string | null }>("/api/v1/me", {
    headers: { Authorization: `Bearer ${token}` },
  });

export const reviewFieldReport = (
  token: string,
  id: string,
  decision: "accepted" | "rejected" | "evidence_requested",
  reviewNote: string,
  datasetId?: string,
  edgeId?: string,
  validUntil?: string,
) =>
  request<FieldReport>(`/api/v1/field-reports/${encodeURIComponent(id)}/review`, {
    method: "PATCH",
    headers: { "Content-Type": "application/json", Authorization: `Bearer ${token}` },
    body: JSON.stringify({
      decision,
      review_note: reviewNote,
      dataset_id: datasetId,
      edge_id: edgeId,
      valid_until: validUntil,
    }),
  });

export const getRoadCandidates = (token: string, id: string, datasetId: string) =>
  request<{ candidates: RoadCandidate[] }>(
    `/api/v1/field-reports/${encodeURIComponent(id)}/road-candidates?dataset_id=${encodeURIComponent(datasetId)}`,
    { headers: { Authorization: `Bearer ${token}` } },
  );

export const getAdminSourcesStatus = (token: string) =>
  request<AdminSourcesResponse>("/api/v1/admin/sources-status", {
    headers: { Authorization: `Bearer ${token}` },
  });

export const refreshAdminSource = (token: string, sourceId: string) =>
  request<{ status: string; source_id: string; refreshed_at: string; message: string }>(
    `/api/v1/admin/sources/${encodeURIComponent(sourceId)}/refresh`,
    {
      method: "POST",
      headers: { Authorization: `Bearer ${token}` },
    },
  );

export const resolveAccessibilityEvent = (token: string, eventId: string, note: string) =>
  request<AccessibilityEvent>(`/api/v1/accessibility-events/${encodeURIComponent(eventId)}`, {
    method: "PATCH",
    headers: { "Content-Type": "application/json", Authorization: `Bearer ${token}` },
    body: JSON.stringify({ status: "resolved", note }),
  });

export const extendAccessibilityEvent = (token: string, eventId: string, endsAtIso: string, note: string) =>
  request<AccessibilityEvent>(`/api/v1/accessibility-events/${encodeURIComponent(eventId)}`, {
    method: "PATCH",
    headers: { "Content-Type": "application/json", Authorization: `Bearer ${token}` },
    body: JSON.stringify({ ends_at: endsAtIso, note }),
  });

export const getTelemetryHealth = (token: string) =>
  request<TelemetryHealthResponse>("/api/v1/admin/telemetry/health", {
    headers: { Authorization: `Bearer ${token}` },
  });

export const getCacheHealth = (token: string) =>
  request<CacheHealthResponse>("/api/v1/admin/cache/health", {
    headers: { Authorization: `Bearer ${token}` },
  });

export const getAuditLog = (token: string, options?: { action?: string; role?: string; limit?: number }) => {
  const params = new URLSearchParams();
  if (options?.action) params.set("action", options.action);
  if (options?.role) params.set("role", options.role);
  if (options?.limit) params.set("limit", String(options.limit));
  const query = params.toString() ? `?${params.toString()}` : "";
  return request<{ entries: AuditEntry[] }>(`/api/v1/admin/audit-log${query}`, {
    headers: { Authorization: `Bearer ${token}` },
  });
};

export const getModelRegistry = (token: string) =>
  request<ModelRegistryResponse>("/api/v1/admin/registry", {
    headers: { Authorization: `Bearer ${token}` },
  });

export const getBroadcastHistory = (token: string) =>
  request<BroadcastHistoryResponse>("/api/v1/admin/alerts/broadcasts", {
    headers: { Authorization: `Bearer ${token}` },
  });

export const sendBroadcastAlert = (
  token: string,
  payload: {
    corridor: string;
    template_type: "hazard_alert" | "bridge_warning" | "reroute_advisory";
    language: "en" | "hi" | "as" | "bn";
    recipients: string[];
    template_params: Record<string, string>;
  },
) =>
  request<BroadcastHistoryItem>("/api/v1/notifications/broadcast", {
    method: "POST",
    headers: { "Content-Type": "application/json", Authorization: `Bearer ${token}` },
    body: JSON.stringify(payload),
  });

export const getLiveFeeds = () =>
  request<LiveFeedsResponse>("/api/v1/hazards/live-feeds");

export const getCandidateAdvisories = (token: string, status?: string) => {
  const query = status ? `?status=${encodeURIComponent(status)}` : "";
  return request<OfficialHazardAdvisory[]>(`/api/v1/admin/candidate-advisories${query}`, {
    headers: { Authorization: `Bearer ${token}` },
  });
};

export const reviewCandidateAdvisory = (
  token: string,
  advisoryId: string,
  review: CandidateAdvisoryReviewRequest,
) =>
  request<OfficialHazardAdvisory>(
    `/api/v1/admin/candidate-advisories/${encodeURIComponent(advisoryId)}/review`,
    {
      method: "POST",
      headers: { "Content-Type": "application/json", Authorization: `Bearer ${token}` },
      body: JSON.stringify(review),
    },
  );

export const getFeedDiagnostics = (token: string) =>
  request<FeedDiagnosticsResponse>("/api/v1/admin/feeds/diagnostics", {
    headers: { Authorization: `Bearer ${token}` },
  });

export const runFeedDiagnostics = (token: string) =>
  request<FeedDiagnosticsResponse & { status: string; parsed_items_count: number }>(
    "/api/v1/admin/feeds/diagnostics/run",
    {
      method: "POST",
      headers: { Authorization: `Bearer ${token}` },
    },
  );

export interface AIS140TelemetryPacketPayload {
  imei: string;
  vehicle_registration: string;
  timestamp: string;
  latitude: number;
  longitude: number;
  speed_kph: number;
  heading_deg: number;
  altitude_m: number;
  gps_fix: boolean;
  ignition_on: boolean;
  emergency_state: boolean;
  tamper_alert?: boolean;
  metadata?: Record<string, any>;
}

export interface AIS140IngestResponse {
  status: "ingested" | "warning" | "rejected";
  vehicle_id: string;
  recorded_at: string;
  coordinates: [number, number];
  speed_kph: number;
  proximity_hazards: Array<{
    hazard_id: string;
    title: string;
    severity: number;
    distance_m: number;
    accessibility_status: string;
  }>;
  trust_score: number;
  quality_flags: string[];
  message: string;
}

export const ingestAis140Telemetry = (packet: AIS140TelemetryPacketPayload) =>
  request<AIS140IngestResponse>("/api/v1/fleet/telemetry/ais140", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(packet),
  });
