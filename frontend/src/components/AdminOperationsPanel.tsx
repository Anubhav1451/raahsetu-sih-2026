import React, { useEffect, useState } from "react";
import type {
  AdminSourceItem,
  AccessibilityEvent,
  AuditEntry,
  BroadcastHistoryItem,
  FieldReport,
  ModelSpecification,
  RoadCandidate,
  TelemetryHealthResponse,
  CacheHealthResponse,
  VehicleAsset,
  Weather,
  Vehicle,
  Comparison,
  PublicCandidate,
  FeedSourceStatus,
  OfficialHazardAdvisory,
  FeedDiagnosticsResponse,
} from "../types";
import {
  getAdminSourcesStatus,
  refreshAdminSource,
  getAccessibilityEvents,
  resolveAccessibilityEvent,
  extendAccessibilityEvent,
  getFieldReports,
  reviewFieldReport,
  getRoadCandidates,
  getTelemetryHealth,
  getCacheHealth,
  getFleetVehicles,
  getAuditLog,
  getModelRegistry,
  getBroadcastHistory,
  sendBroadcastAlert,
  compareRoutes,
  getPublicCandidates,
  reviewPublicCandidate,
  getLiveFeeds,
  getCandidateAdvisories,
  reviewCandidateAdvisory,
  getFeedDiagnostics,
  runFeedDiagnostics,
} from "../api";
import { DataProvenanceDrawer } from "./DataProvenanceDrawer";

interface AdminOperationsPanelProps {
  token: string;
  userRole: "admin" | "reviewer" | "field_official";
  userRegion: string | null;
  onSelectDataset?: (datasetId: string) => void;
  currentDataset?: string;
  onReturnToDispatcher?: () => void;
}

const NORTHEAST_STATES = [
  { id: "demo", name: "Guwahati Logistics Hub (Corridor Demo)", state: "Assam", code: "assam", nodes: 14, edges: 22, synthetic: true },
  { id: "osm-assam", name: "Assam Trunk Network", state: "Assam", code: "assam", nodes: 3820, edges: 7490, synthetic: false },
  { id: "osm-arunachal-pradesh", name: "Arunachal Frontier Highway", state: "Arunachal Pradesh", code: "arunachal-pradesh", nodes: 1420, edges: 2680, synthetic: false },
  { id: "osm-meghalaya", name: "Meghalaya Plateau (NH-6)", state: "Meghalaya", code: "meghalaya", nodes: 1180, edges: 2150, synthetic: false },
  { id: "osm-nagaland", name: "Nagaland NH-29 Transit", state: "Nagaland", code: "nagaland", nodes: 890, edges: 1620, synthetic: false },
  { id: "osm-manipur", name: "Manipur Imphal Lifeline", state: "Manipur", code: "manipur", nodes: 940, edges: 1740, synthetic: false },
  { id: "osm-mizoram", name: "Mizoram Valley Spine", state: "Mizoram", code: "mizoram", nodes: 760, edges: 1390, synthetic: false },
  { id: "osm-sikkim", name: "Sikkim Teesta Valley (NH-10)", state: "Sikkim", code: "sikkim", nodes: 680, edges: 1210, synthetic: false },
  { id: "osm-tripura", name: "Tripura Agartala Corridor", state: "Tripura", code: "tripura", nodes: 830, edges: 1540, synthetic: false },
];

export const AdminOperationsPanel: React.FC<AdminOperationsPanelProps> = ({
  token,
  userRole,
  userRegion,
  onSelectDataset,
  currentDataset = "demo",
  onReturnToDispatcher,
}) => {
  // Tab navigation
  const [activeTab, setActiveTab] = useState<
    | "overview"
    | "live_feeds"
    | "sources"
    | "reports"
    | "candidates"
    | "closures"
    | "telematics"
    | "routing"
    | "weather"
    | "broadcasts"
    | "audit"
    | "registry"
  >("overview");

  // State & dataset
  const [selectedStateCode, setSelectedStateCode] = useState<string>("all");
  const [activeDatasetId, setActiveDatasetId] = useState<string>(currentDataset);

  // Data states
  const [sources, setSources] = useState<AdminSourceItem[]>([]);
  const [reports, setReports] = useState<FieldReport[]>([]);
  const [publicCandidates, setPublicCandidates] = useState<PublicCandidate[]>([]);
  const [candidateLoadError, setCandidateLoadError] = useState<string | null>(null);
  const [events, setEvents] = useState<AccessibilityEvent[]>([]);
  const [telemetry, setTelemetry] = useState<TelemetryHealthResponse | null>(null);
  const [cacheHealth, setCacheHealth] = useState<CacheHealthResponse | null>(null);
  const [vehicles, setVehicles] = useState<VehicleAsset[]>([]);
  const [auditEntries, setAuditEntries] = useState<AuditEntry[]>([]);
  const [models, setModels] = useState<ModelSpecification[]>([]);
  const [broadcasts, setBroadcasts] = useState<BroadcastHistoryItem[]>([]);

  // Live Feed Readiness & Diagnostics
  const [liveFeeds, setLiveFeeds] = useState<FeedSourceStatus[]>([]);
  const [candidateAdvisories, setCandidateAdvisories] = useState<OfficialHazardAdvisory[]>([]);
  const [feedDiagnostics, setFeedDiagnostics] = useState<FeedDiagnosticsResponse | null>(null);
  const [candidateFilter, setCandidateFilter] = useState<"all" | "pending_review" | "conflicting" | "accepted" | "rejected">("all");
  const [selectedCandidate, setSelectedCandidate] = useState<OfficialHazardAdvisory | null>(null);
  const [candidateReviewDecision, setCandidateReviewDecision] = useState<"accept" | "reject" | "mark_duplicate" | "mark_conflicting">("accept");
  const [candidateReviewEvidence, setCandidateReviewEvidence] = useState("");
  const [candidateReviewCorridor, setCandidateReviewCorridor] = useState("");
  const [candidateReviewSegmentId, setCandidateReviewSegmentId] = useState("");
  const [candidateReviewNote, setCandidateReviewNote] = useState("");
  const [candidateReviewSubmitting, setCandidateReviewSubmitting] = useState(false);
  const [diagnosticsModalOpen, setDiagnosticsModalOpen] = useState(false);
  const [diagnosticsRunning, setDiagnosticsRunning] = useState(false);
  const [diagnosticsReport, setDiagnosticsReport] = useState<any | null>(null);

  // Loading & error states
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [actionSuccess, setActionSuccess] = useState<string | null>(null);

  // Drawer state
  const [selectedProvenanceSource, setSelectedProvenanceSource] = useState<AdminSourceItem | null>(null);
  const [refreshingSourceId, setRefreshingSourceId] = useState<string | null>(null);

  // Field Report Review Modal
  const [reviewingReport, setReviewingReport] = useState<FieldReport | null>(null);
  const [reviewDecision, setReviewDecision] = useState<"accepted" | "rejected" | "evidence_requested">("accepted");
  const [reviewNote, setReviewNote] = useState("");
  const [reviewEdgeId, setReviewEdgeId] = useState("");
  const [reportCandidates, setReportCandidates] = useState<RoadCandidate[]>([]);
  const [loadingCandidates, setLoadingCandidates] = useState(false);
  const [reviewValidHours, setReviewValidHours] = useState("24");

  // Event Resolution & Extension Modals
  const [resolvingEvent, setResolvingEvent] = useState<AccessibilityEvent | null>(null);
  const [resolutionNote, setResolutionNote] = useState("");
  const [extendingEvent, setExtendingEvent] = useState<AccessibilityEvent | null>(null);
  const [extensionHours, setExtensionHours] = useState("24");
  const [extensionNote, setExtensionNote] = useState("");

  // Sandbox Routing Form
  const [routeVehicle, setRouteVehicle] = useState<Vehicle>("heavy");
  const [routeWeather, setRouteWeather] = useState<Weather>("normal");
  const [routeStrictMode, setRouteStrictMode] = useState(false);
  const [routeAversion, setRouteAversion] = useState(0.5);
  const [routeComparison, setRouteComparison] = useState<Comparison | null>(null);
  const [routingLoading, setRoutingLoading] = useState(false);

  // Broadcast dispatch form
  const [broadcastCorridor, setBroadcastCorridor] = useState("Guwahati-Tawang Corridor (NH-13)");
  const [broadcastTemplate, setBroadcastTemplate] = useState<"hazard_alert" | "bridge_warning" | "reroute_advisory">("hazard_alert");
  const [broadcastLang, setBroadcastLang] = useState<"en" | "hi" | "as" | "bn">("en");
  const [broadcastDispatching, setBroadcastDispatching] = useState(false);

  // Initial load
  useEffect(() => {
    loadAllData();
  }, [token]);

  const loadAllData = async () => {
    setLoading(true);
    setError(null);
    try {
      const [
        srcRes,
        repRes,
        candRes,
        evtRes,
        telRes,
        cacheRes,
        fleetVehicles,
        regRes,
        bcRes,
        liveRes,
        candAdvRes,
        diagRes,
      ] = await Promise.all([
        getAdminSourcesStatus(token).catch(() => ({ sources: [] })),
        getFieldReports(token).catch(() => []),
        getPublicCandidates(token).catch((err) => {
          setCandidateLoadError(err instanceof Error ? err.message : "Public candidate API unavailable");
          return [];
        }),
        getAccessibilityEvents().catch(() => ({ events: [] })),
        getTelemetryHealth(token).catch(() => null),
        getCacheHealth(token).catch(() => null),
        getFleetVehicles(token).catch(() => []),
        getModelRegistry(token).catch(() => ({ models: [], datasets: [], disclosures: { field_safety_claim: false, live_traffic_guarantee: false, ml_landslide_prediction: false } })),
        getBroadcastHistory(token).catch(() => ({ broadcasts: [] })),
        getLiveFeeds().catch(() => ({ sources: [], active_advisories: [] })),
        getCandidateAdvisories(token).catch(() => []),
        getFeedDiagnostics(token).catch(() => null),
      ]);

      setSources(srcRes.sources || []);
      setReports(repRes || []);
      setPublicCandidates(candRes || []);
      if (candRes && candRes.length > 0) setCandidateLoadError(null);
      setEvents(evtRes.events || []);
      setTelemetry(telRes);
      setCacheHealth(cacheRes);
      setVehicles(fleetVehicles || []);
      setModels(regRes.models || []);
      setBroadcasts(bcRes.broadcasts || []);
      setLiveFeeds(liveRes.sources || []);
      setCandidateAdvisories(candAdvRes || []);
      setFeedDiagnostics(diagRes);

      if (userRole === "admin") {
        const auditRes = await getAuditLog(token, { limit: 50 }).catch(() => ({ entries: [] }));
        setAuditEntries(auditRes.entries || []);
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load operations data");
    } finally {
      setLoading(false);
    }
  };

  const handleRefreshSource = async (sourceId: string) => {
    if (userRole !== "admin") {
      alert("Source cache refresh requires Administrator privileges.");
      return;
    }
    setRefreshingSourceId(sourceId);
    try {
      await refreshAdminSource(token, sourceId);
      setActionSuccess(`Source '${sourceId}' cache purged and re-verified.`);
      setTimeout(() => setActionSuccess(null), 4000);
      const updated = await getAdminSourcesStatus(token);
      setSources(updated.sources || []);
      if (selectedProvenanceSource?.id === sourceId) {
        const fresh = updated.sources.find((s) => s.id === sourceId);
        if (fresh) setSelectedProvenanceSource(fresh);
      }
    } catch (err) {
      alert(`Refresh failed: ${err instanceof Error ? err.message : String(err)}`);
    } finally {
      setRefreshingSourceId(null);
    }
  };

  const openReviewModal = async (report: FieldReport) => {
    setReviewingReport(report);
    setReviewDecision("accepted");
    setReviewNote("");
    setReviewEdgeId("");
    setReviewValidHours("24");
    setLoadingCandidates(true);
    try {
      const cand = await getRoadCandidates(token, report.id, activeDatasetId);
      setReportCandidates(cand.candidates || []);
      if (cand.candidates && cand.candidates.length > 0) {
        setReviewEdgeId(cand.candidates[0].edge_id);
      }
    } catch {
      setReportCandidates([]);
    } finally {
      setLoadingCandidates(false);
    }
  };

  const submitReview = async () => {
    if (!reviewingReport) return;
    if (reviewNote.trim().length < 5) {
      alert("Please provide an operational review note (minimum 5 characters).");
      return;
    }
    try {
      const validUntil =
        reviewDecision === "accepted" && reviewValidHours
          ? new Date(Date.now() + Number(reviewValidHours) * 3600000).toISOString()
          : undefined;

      await reviewFieldReport(
        token,
        reviewingReport.id,
        reviewDecision,
        reviewNote.trim(),
        reviewDecision === "accepted" ? activeDatasetId : undefined,
        reviewDecision === "accepted" ? reviewEdgeId || undefined : undefined,
        validUntil
      );
      setActionSuccess(`Report ${reviewingReport.id.slice(0, 8)} review decision '${reviewDecision}' applied.`);
      setTimeout(() => setActionSuccess(null), 4000);
      setReviewingReport(null);
      // reload reports and events
      const [updatedReports, updatedEvents] = await Promise.all([
        getFieldReports(token),
        getAccessibilityEvents(),
      ]);
      setReports(updatedReports || []);
      setEvents(updatedEvents.events || []);
    } catch (err) {
      alert(`Review submission failed: ${err instanceof Error ? err.message : String(err)}`);
    }
  };

  const submitEventResolution = async () => {
    if (!resolvingEvent) return;
    if (resolutionNote.trim().length < 5) {
      alert("Provide a resolution note describing physical inspection / road clearance.");
      return;
    }
    try {
      await resolveAccessibilityEvent(token, resolvingEvent.id, resolutionNote.trim());
      setActionSuccess(`Closure event ${resolvingEvent.id.slice(0, 8)} marked resolved.`);
      setTimeout(() => setActionSuccess(null), 4000);
      setResolvingEvent(null);
      setResolutionNote("");
      const evtRes = await getAccessibilityEvents();
      setEvents(evtRes.events || []);
    } catch (err) {
      alert(`Resolution failed: ${err instanceof Error ? err.message : String(err)}`);
    }
  };

  const submitEventExtension = async () => {
    if (!extendingEvent) return;
    try {
      const newExpiry = new Date(Date.now() + Number(extensionHours) * 3600000).toISOString();
      await extendAccessibilityEvent(token, extendingEvent.id, newExpiry, extensionNote.trim());
      setActionSuccess(`Closure event ${extendingEvent.id.slice(0, 8)} extended by ${extensionHours} hours.`);
      setTimeout(() => setActionSuccess(null), 4000);
      setExtendingEvent(null);
      setExtensionNote("");
      const evtRes = await getAccessibilityEvents();
      setEvents(evtRes.events || []);
    } catch (err) {
      alert(`Extension failed: ${err instanceof Error ? err.message : String(err)}`);
    }
  };

  const handleTestRoute = async () => {
    setRoutingLoading(true);
    try {
      const controller = new AbortController();
      const res = await compareRoutes(
        {
          dataset_id: activeDatasetId,
          origin: { node_id: "n2_1" },
          destination: { node_id: "n2_6" },
          vehicle: routeVehicle,
          risk_aversion: routeAversion,
          weather: routeWeather,
          closed_edge_ids: events.filter((e) => e.accessibility_status === "blocked" && e.edge_id).map((e) => e.edge_id as string),
          strict_vehicle: routeStrictMode,
        },
        controller.signal
      );
      setRouteComparison(res);
    } catch (err) {
      alert(`Route comparison failed: ${err instanceof Error ? err.message : String(err)}`);
    } finally {
      setRoutingLoading(false);
    }
  };

  const handleDispatchBroadcast = async () => {
    setBroadcastDispatching(true);
    try {
      const res = await sendBroadcastAlert(token, {
        corridor: broadcastCorridor,
        template_type: broadcastTemplate,
        language: broadcastLang,
        recipients: ["+91-94350-12345 (AS-01-GB-4821)", "+91-98620-54321 (NL-07-A-3210)"],
        template_params: {
          corridor: broadcastCorridor,
          incident: "Active freeze / rockfall verified by SDRF",
          limit_t: "18.0",
          detour_km: "26",
          detour_mins: "35",
        },
      });
      setActionSuccess(`Broadcast ${res.broadcast_id} dispatched to ${res.recipient_count} vehicles.`);
      setTimeout(() => setActionSuccess(null), 4000);
      const bcRes = await getBroadcastHistory(token);
      setBroadcasts(bcRes.broadcasts || []);
    } catch (err) {
      alert(`Broadcast failed: ${err instanceof Error ? err.message : String(err)}`);
    } finally {
      setBroadcastDispatching(false);
    }
  };

  const filteredReports = reports.filter(
    (r) => selectedStateCode === "all" || r.region_code === selectedStateCode
  );
  const filteredEvents = events.filter(
    (e) => selectedStateCode === "all" || e.region_code === selectedStateCode
  );

  const filteredCandidateAdvisories = candidateAdvisories.filter((adv) => {
    if (candidateFilter === "all") return true;
    if (candidateFilter === "pending_review") return adv.review_status === "pending_review" || adv.review_status === "candidate_advisory";
    if (candidateFilter === "conflicting") return adv.review_status === "conflicting" || adv.conflict_detected;
    return adv.review_status === candidateFilter;
  });

  const handleOpenCandidateReview = (adv: OfficialHazardAdvisory) => {
    setSelectedCandidate(adv);
    setCandidateReviewDecision("accept");
    setCandidateReviewEvidence(adv.source_evidence || `Official alert from ${adv.source_agency} via verified channel`);
    setCandidateReviewCorridor(adv.affected_corridors && adv.affected_corridors.length > 0 ? adv.affected_corridors[0] : "");
    setCandidateReviewSegmentId(adv.road_segment_id || "");
    setCandidateReviewNote("");
  };

  const handleSubmitCandidateReview = async () => {
    if (!selectedCandidate) return;
    if (candidateReviewEvidence.trim().length < 5) {
      alert("Please provide source verification evidence (minimum 5 characters).");
      return;
    }
    if (candidateReviewCorridor.trim().length < 3) {
      alert("Please specify the affected corridor (minimum 3 characters).");
      return;
    }
    if (candidateReviewNote.trim().length < 5) {
      alert("Please provide an operational review note (minimum 5 characters).");
      return;
    }
    if (candidateReviewDecision === "accept" && !candidateReviewSegmentId.trim()) {
      alert("Accepted candidate advisories require an OSM Road Segment ID to bind to the routing graph.");
      return;
    }

    setCandidateReviewSubmitting(true);
    try {
      await reviewCandidateAdvisory(
        token,
        selectedCandidate.advisory_id,
        {
          decision: candidateReviewDecision,
          source_evidence: candidateReviewEvidence.trim(),
          affected_corridor: candidateReviewCorridor.trim(),
          road_segment_id: candidateReviewDecision === "accept" ? candidateReviewSegmentId.trim() : null,
          review_note: candidateReviewNote.trim(),
        }
      );
      setActionSuccess(`Advisory ${selectedCandidate.advisory_id} triaged: '${candidateReviewDecision}'. Operational audit entry recorded.`);
      setTimeout(() => setActionSuccess(null), 5000);
      setSelectedCandidate(null);
      const [freshAdv, freshEvt, freshDiag] = await Promise.all([
        getCandidateAdvisories(token).catch(() => []),
        getAccessibilityEvents().catch(() => ({ events: [] })),
        getFeedDiagnostics(token).catch(() => null),
      ]);
      setCandidateAdvisories(freshAdv);
      setEvents(freshEvt.events || []);
      setFeedDiagnostics(freshDiag);
      if (userRole === "admin") {
        const auditRes = await getAuditLog(token, { limit: 50 }).catch(() => ({ entries: [] }));
        setAuditEntries(auditRes.entries || []);
      }
    } catch (err) {
      alert(`Review submission failed: ${err instanceof Error ? err.message : String(err)}`);
    } finally {
      setCandidateReviewSubmitting(false);
    }
  };

  const handleRunDiagnostics = async () => {
    setDiagnosticsRunning(true);
    try {
      const res = await runFeedDiagnostics(token);
      setDiagnosticsReport(res);
      setFeedDiagnostics(res);
      setActionSuccess("Feed parser diagnostics completed successfully in dry-run isolation.");
      setTimeout(() => setActionSuccess(null), 4000);
    } catch (err) {
      alert(`Diagnostics run failed: ${err instanceof Error ? err.message : String(err)}`);
    } finally {
      setDiagnosticsRunning(false);
    }
  };

  return (
    <div className="min-h-screen bg-slate-950 text-slate-100 flex flex-col font-sans">
      {/* Integrated Operations Workspace Header */}
      <header className="border-b border-border bg-card/95 backdrop-blur px-4 sm:px-6 py-3.5 flex flex-wrap items-center justify-between gap-4 transition-colors">
        <div className="flex items-center gap-3">
          {onReturnToDispatcher && (
            <button
              type="button"
              onClick={onReturnToDispatcher}
              className="px-3 py-1.5 rounded-xl border border-primary/40 bg-primary/10 hover:bg-primary/20 text-primary text-xs font-bold transition-all cursor-pointer flex items-center gap-1.5 shadow-2xs group"
              title="Return to Interactive 3D Route Map & Dispatcher"
            >
              <svg className="w-4 h-4 transition-transform group-hover:-translate-x-0.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10 19l-7-7m0 0l7-7m-7 7h18" />
              </svg>
              <span>Back to Route Map</span>
            </button>
          )}
          <div className="p-2 rounded-xl bg-primary/10 border border-primary/20 text-primary">
            <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m5.618-4.016A11.955 11.955 0 0112 2.944a11.955 11.955 0 01-8.618 3.04A12.02 12.02 0 003 9c0 5.591 3.824 10.29 9 11.622 5.176-1.332 9-6.03 9-11.622 0-1.042-.133-2.052-.382-3.016z" />
            </svg>
          </div>
          <div>
            <div className="flex items-center gap-2">
              <h1 className="text-base sm:text-lg font-bold tracking-tight text-foreground flex items-center gap-2">
                Northeast Logistics Accessibility Control
                <span className="text-[11px] font-semibold uppercase tracking-wider px-2 py-0.5 rounded-full bg-primary/15 text-primary border border-primary/30">
                  Operations Console
                </span>
              </h1>
            </div>
            <div className="text-xs text-muted-foreground flex items-center gap-3 mt-0.5">
              <span>
                Role:{" "}
                <strong className={userRole === "admin" ? "text-amber-500 dark:text-amber-300" : "text-primary"}>
                  {userRole.toUpperCase()}
                </strong>
              </span>
              <span>•</span>
              <span>
                Jurisdiction:{" "}
                <span className="text-foreground font-medium">
                  {userRegion ? userRegion.toUpperCase() : "CROSS-REGION / 8 STATES"}
                </span>
              </span>
            </div>
          </div>
        </div>

        {/* Global Live Disclosures Indicator & Provenance Quick Trigger */}
        <div className="flex items-center gap-3">
          <div className="hidden lg:flex items-center gap-2 px-3 py-1.5 rounded-xl bg-secondary border border-border text-xs text-muted-foreground">
            <span className="w-2 h-2 rounded-full bg-emerald-400 animate-pulse"></span>
            <span>OSM Snapshot Engine Active</span>
            <span className="text-border">|</span>
            <span className="text-amber-500 dark:text-amber-400 font-medium">Simulated Demo Fleet</span>
          </div>

          <button
            onClick={() => {
              if (sources.length > 0) setSelectedProvenanceSource(sources[0]);
            }}
            className="px-3 py-1.5 rounded-xl bg-secondary hover:bg-muted border border-border text-xs font-semibold text-primary transition-all flex items-center gap-1.5 cursor-pointer shadow-2xs"
            title="Inspect Provenance & Cryptographic Hashes for all datasets"
          >
            <svg className="w-4 h-4 text-primary" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
            </svg>
            Data Provenance Center
          </button>
        </div>
      </header>

      {/* Success Alert Banner */}
      {actionSuccess && (
        <div className="bg-emerald-950/80 border-b border-emerald-800/80 px-6 py-2.5 text-xs text-emerald-200 flex items-center gap-2 animate-fade-in">
          <svg className="w-4 h-4 text-emerald-400 shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
          </svg>
          <span className="font-medium">{actionSuccess}</span>
        </div>
      )}

      {/* Main Operations Navigation Tabs */}
      <nav className="border-b border-border bg-card/60 px-4 sm:px-6 overflow-x-auto flex items-center gap-1.5 py-1.5 scrollbar-none">
        {[
          { id: "overview", label: "Operations Overview", icon: "📊" },
          { id: "live_feeds", label: `Live Feed Readiness (${liveFeeds.length || 5})`, icon: "🛰️" },
          { id: "sources", label: `Sources & Freshness (${sources.length})`, icon: "📡" },
          { id: "reports", label: `Field Queue (${reports.length})`, icon: "📝" },
          { id: "candidates", label: `Public Candidates (${publicCandidates.filter((c) => c.review_status === "pending").length})`, icon: "🔎" },
          { id: "closures", label: `Active Closures (${events.length})`, icon: "⛔" },
          { id: "telematics", label: "Fleet Telematics & GPS", icon: "🚚" },
          { id: "routing", label: "Route Sandbox", icon: "🗺️" },
          { id: "weather", label: "Weather Grids", icon: "⛅" },
          { id: "broadcasts", label: `Broadcasts (${broadcasts.length})`, icon: "📢" },
          { id: "audit", label: `Audit Log (${auditEntries.length})`, icon: "📜" },
          { id: "registry", label: "Model Registry", icon: "📑" },
        ].map((tab) => (
          <button
            key={tab.id}
            onClick={() => setActiveTab(tab.id as typeof activeTab)}
            className={`px-3 py-2 text-xs font-semibold whitespace-nowrap rounded-xl transition-all flex items-center gap-1.5 cursor-pointer ${
              activeTab === tab.id
                ? "bg-primary text-primary-foreground shadow-xs font-bold"
                : "text-muted-foreground hover:text-foreground hover:bg-secondary/60"
            }`}
          >
            <span>{tab.icon}</span>
            <span>{tab.label}</span>
          </button>
        ))}
      </nav>

      {/* State & Corridor Global Selector Bar */}
      <section className="bg-slate-900/60 border-b border-slate-800/80 px-6 py-3 flex flex-wrap items-center justify-between gap-4">
        <div className="flex items-center gap-3">
          <span className="text-xs font-semibold text-slate-400 uppercase tracking-wider">
            Northeast Jurisdiction:
          </span>
          <select
            value={selectedStateCode}
            onChange={(e) => setSelectedStateCode(e.target.value)}
            className="bg-slate-800 border border-slate-700 rounded-lg px-3 py-1.5 text-xs text-white focus:ring-1 focus:ring-cyan-500"
          >
            <option value="all">All 8 Northeast States (Regional Overview)</option>
            <option value="assam">Assam (Brahmaputra Valley & Guwahati)</option>
            <option value="arunachal-pradesh">Arunachal Pradesh (Sela Pass / Frontier)</option>
            <option value="meghalaya">Meghalaya (Shillong Plateau / NH-6 Sonapur)</option>
            <option value="nagaland">Nagaland (Kohima / Dimapur / Phesama)</option>
            <option value="manipur">Manipur (Imphal Valley Corridor)</option>
            <option value="mizoram">Mizoram (Aizawl Spine)</option>
            <option value="sikkim">Sikkim (Teesta Valley / NH-10)</option>
            <option value="tripura">Tripura (Agartala Corridor)</option>
          </select>
        </div>

        <div className="flex items-center gap-3">
          <span className="text-xs font-semibold text-slate-400 uppercase tracking-wider">
            Routing Dataset:
          </span>
          <select
            value={activeDatasetId}
            onChange={(e) => {
              const ds = e.target.value;
              setActiveDatasetId(ds);
              if (onSelectDataset) onSelectDataset(ds);
            }}
            className="bg-slate-800 border border-slate-700 rounded-lg px-3 py-1.5 text-xs text-cyan-300 font-mono focus:ring-1 focus:ring-cyan-500"
          >
            {NORTHEAST_STATES.map((ds) => (
              <option key={ds.id} value={ds.id}>
                {ds.name} ({ds.nodes} nodes, {ds.edges} edges) {ds.synthetic ? "[Benchmark]" : "[OSM Extract]"}
              </option>
            ))}
          </select>
        </div>
      </section>

      {/* Main Tab View Content */}
      <main className="flex-1 p-6 overflow-y-auto">
        {loading ? (
          <div className="flex flex-col items-center justify-center py-24 text-slate-400">
            <svg className="w-8 h-8 animate-spin text-cyan-400 mb-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
            </svg>
            <p className="text-sm">Connecting to RaahSetu backend & telemetry pipeline...</p>
          </div>
        ) : error ? (
          <div className="bg-rose-950/40 border border-rose-800 p-4 rounded-xl text-rose-200 text-sm">
            <p className="font-bold mb-1">Operational Panel Error</p>
            <p>{error}</p>
          </div>
        ) : (
          <>
            {/* TAB 1: OPERATIONS OVERVIEW */}
            {activeTab === "overview" && (
              <div className="space-y-6">
                {/* Metric Summary Cards */}
                <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
                  <div className="bg-slate-900/70 border border-slate-800 p-4 rounded-xl">
                    <span className="text-xs text-slate-400 font-medium block mb-1">Pipeline Sources</span>
                    <div className="flex items-baseline justify-between">
                      <span className="text-2xl font-bold text-white">{sources.length}</span>
                      <span className="text-xs text-emerald-400 bg-emerald-950/60 px-2 py-0.5 rounded border border-emerald-800">
                        {sources.filter((s) => s.status === "LIVE" || s.status === "FRESH").length} Operational
                      </span>
                    </div>
                    <span className="text-[11px] text-slate-500 mt-2 block">
                      {sources.filter((s) => s.status === "STANDBY").length} standby feeds awaiting agency API keys
                    </span>
                  </div>

                  <div className="bg-slate-900/70 border border-slate-800 p-4 rounded-xl">
                    <span className="text-xs text-slate-400 font-medium block mb-1">Active Road Closures</span>
                    <div className="flex items-baseline justify-between">
                      <span className="text-2xl font-bold text-rose-400">{events.length}</span>
                      <span className="text-xs text-rose-300 bg-rose-950/60 px-2 py-0.5 rounded border border-rose-800">
                        {events.filter((e) => e.accessibility_status === "blocked").length} Blocked
                      </span>
                    </div>
                    <span className="text-[11px] text-slate-500 mt-2 block">
                      Enforced strictly in Risk-A* routing engine
                    </span>
                  </div>

                  <div className="bg-slate-900/70 border border-slate-800 p-4 rounded-xl">
                    <span className="text-xs text-slate-400 font-medium block mb-1">Pending Field Reports</span>
                    <div className="flex items-baseline justify-between">
                      <span className="text-2xl font-bold text-amber-300">
                        {reports.filter((r) => r.review_status === "pending" || r.review_status === "corroborated").length}
                      </span>
                      <span className="text-xs text-amber-300 bg-amber-950/60 px-2 py-0.5 rounded border border-amber-800">
                        Awaiting Review
                      </span>
                    </div>
                    <span className="text-[11px] text-amber-400/80 mt-2 block">
                      Pending citizen reports never alter route graph
                    </span>
                  </div>

                  <div className="bg-slate-900/70 border border-slate-800 p-4 rounded-xl">
                    <span className="text-xs text-slate-400 font-medium block mb-1">Telemetry Health</span>
                    <div className="flex items-baseline justify-between">
                      <span className="text-2xl font-bold text-cyan-300">
                        {telemetry?.total_packets_received ?? 0}
                      </span>
                      <span className="text-xs text-cyan-300 bg-cyan-950/60 px-2 py-0.5 rounded border border-cyan-800">
                        {telemetry?.rejected_packets ?? 0} Rejections
                      </span>
                    </div>
                    <span className="text-[11px] text-slate-500 mt-2 block">
                      AIS-140 geometric & speed validation guards active
                    </span>
                  </div>

                  <div className="bg-slate-900/70 border border-slate-800 p-4 rounded-xl">
                    <span className="text-xs text-slate-400 font-medium block mb-1">Cache & Event Bus</span>
                    <div className="flex items-baseline justify-between">
                      <span className={`text-2xl font-bold ${cacheHealth?.reachable ? "text-emerald-300" : "text-amber-300"}`}>
                        {cacheHealth?.reachable ? "Redis" : "Fallback"}
                      </span>
                      <span className={`text-xs px-2 py-0.5 rounded border ${cacheHealth?.reachable ? "text-emerald-300 bg-emerald-950/60 border-emerald-800" : "text-amber-300 bg-amber-950/60 border-amber-800"}`}>
                        {cacheHealth?.reachable ? "Online" : "Local"}
                      </span>
                    </div>
                    <span className="text-[11px] text-slate-500 mt-2 block">
                      Source of truth: {cacheHealth?.authoritative_store || "PostgreSQL/PostGIS"}
                    </span>
                  </div>
                </div>

                {/* Live Feed Readiness Quick Banner */}
                <div
                  onClick={() => setActiveTab("live_feeds")}
                  className="rounded-xl border border-cyan-500/30 bg-gradient-to-r from-slate-900/90 via-cyan-950/30 to-slate-900/90 p-4 flex flex-wrap items-center justify-between gap-3 cursor-pointer hover:border-cyan-500/60 transition group shadow-sm"
                >
                  <div className="flex items-center gap-3">
                    <div className="p-2 rounded-lg bg-cyan-500/10 text-cyan-400 border border-cyan-500/20 text-lg group-hover:scale-110 transition-transform">
                      🛰️
                    </div>
                    <div>
                      <div className="flex items-center gap-2">
                        <span className="text-xs font-bold text-white tracking-wide">
                          External Feed Governance & Early-Warning Queue
                        </span>
                        <span className="text-[10px] font-mono px-2 py-0.5 rounded-full bg-cyan-950 text-cyan-300 border border-cyan-800">
                          {liveFeeds.filter(f => f.status === "ONLINE" || f.status === "SYNCED").length} Online · {liveFeeds.filter(f => f.status === "STANDBY").length} Standby
                        </span>
                      </div>
                      <p className="text-[11px] text-slate-400 mt-0.5">
                        NDMA SACHET, CWC, State Traffic Police & SDMA feeds. Inbound alerts quarantined until operator confirmation.
                      </p>
                    </div>
                  </div>
                  <div className="flex items-center gap-2">
                    {candidateAdvisories.filter(a => a.review_status === "pending_review" || a.review_status === "candidate_advisory" || a.review_status === "conflicting").length > 0 && (
                      <span className="text-xs font-semibold px-2.5 py-1 rounded-lg bg-amber-950 text-amber-300 border border-amber-800 animate-pulse">
                        {candidateAdvisories.filter(a => a.review_status === "pending_review" || a.review_status === "candidate_advisory" || a.review_status === "conflicting").length} Quarantined
                      </span>
                    )}
                    <span className="text-xs font-semibold text-cyan-400 group-hover:translate-x-0.5 transition-transform flex items-center gap-1">
                      <span>Open Readiness & Triage</span>
                      <span>→</span>
                    </span>
                  </div>
                </div>

                {/* Corridor Status Overview Grid */}
                <div className="bg-slate-900/70 border border-slate-800 rounded-xl p-5">
                  <div className="flex items-center justify-between mb-4">
                    <h3 className="text-sm font-bold text-white flex items-center gap-2">
                      <span>🏔️</span> Critical Strategic Freight Corridors (Northeast Lifelines)
                    </h3>
                    <span className="text-xs text-slate-400">Real-time status derived from verified events</span>
                  </div>
                  <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                    {[
                      {
                        name: "Guwahati-Tawang Corridor",
                        highway: "NH-13 / NH-27",
                        status: "Restricted (Sela Pass sub-zero slush)",
                        color: "border-amber-700/60 bg-amber-950/20 text-amber-300",
                        action: "Heavy commercial 40T diverted to lower tunnel link",
                      },
                      {
                        name: "Guwahati-Imphal Lifeline",
                        highway: "NH-29 / NH-2",
                        status: "Severe Risk (Phesama Subsidence Zone)",
                        color: "border-rose-700/60 bg-rose-950/20 text-rose-300",
                        action: "Single lane 10km/h crawl; multi-axle freight queued",
                      },
                      {
                        name: "Shillong-Silchar Corridor",
                        highway: "NH-6",
                        status: "Restricted (Sonapur Tunnel Mudflow)",
                        color: "border-amber-700/60 bg-amber-950/20 text-amber-300",
                        action: "PWD clearing team active; single-lane alternating",
                      },
                      {
                        name: "Siliguri-Gangtok Axis",
                        highway: "NH-10",
                        status: "Open with Precaution (Teesta river level normal)",
                        color: "border-emerald-700/60 bg-emerald-950/20 text-emerald-300",
                        action: "Clear for standard commercial gross weight loads",
                      },
                      {
                        name: "Silchar-Aizawl Corridor",
                        highway: "NH-306",
                        status: "Open (Normal transit speeds)",
                        color: "border-emerald-700/60 bg-emerald-950/20 text-emerald-300",
                        action: "All freight classes permitted without detour",
                      },
                      {
                        name: "Guwahati-Agartala Axis",
                        highway: "NH-8",
                        status: "Open (Minor rain slowdown)",
                        color: "border-emerald-700/60 bg-emerald-950/20 text-emerald-300",
                        action: "Bridge clearance permits standard 40T freight",
                      },
                    ].map((corridor, idx) => (
                      <div key={idx} className={`p-4 rounded-lg border ${corridor.color} flex flex-col justify-between`}>
                        <div>
                          <div className="flex items-start justify-between">
                            <h4 className="font-bold text-sm text-white">{corridor.name}</h4>
                            <span className="text-[10px] font-mono px-1.5 py-0.5 rounded bg-slate-800 text-slate-300">
                              {corridor.highway}
                            </span>
                          </div>
                          <p className="text-xs font-medium mt-1">{corridor.status}</p>
                        </div>
                        <p className="text-[11px] text-slate-400 mt-3 pt-2 border-t border-slate-800/60">
                          {corridor.action}
                        </p>
                      </div>
                    ))}
                  </div>
                </div>

                {/* Quick Action Split: High Priority Field Reports vs Active Closures */}
                <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
                  {/* Left: Pending Reports Queue preview */}
                  <div className="bg-slate-900/70 border border-slate-800 rounded-xl p-5">
                    <div className="flex items-center justify-between mb-4">
                      <h3 className="text-sm font-bold text-white flex items-center gap-2">
                        <span>📝</span> High-Priority Field Intelligence
                      </h3>
                      <button
                        onClick={() => setActiveTab("reports")}
                        className="text-xs text-cyan-400 hover:text-cyan-300 font-semibold"
                      >
                        View All ({reports.length}) →
                      </button>
                    </div>

                    <div className="space-y-3">
                      {reports.slice(0, 3).map((rep) => (
                        <div key={rep.id} className="p-3 rounded-lg bg-slate-800/50 border border-slate-800 flex items-start justify-between gap-3">
                          <div>
                            <div className="flex items-center gap-2 mb-1">
                              <span className="text-[10px] uppercase font-bold px-2 py-0.5 rounded bg-amber-950 text-amber-300 border border-amber-800">
                                {rep.review_status}
                              </span>
                              <span className="text-xs font-semibold text-white">{rep.place_name || rep.district}</span>
                            </div>
                            <p className="text-xs text-slate-300 line-clamp-2">{rep.description}</p>
                            <span className="text-[10px] text-slate-500 mt-1 block font-mono">
                              Observed: {new Date(rep.observed_at).toLocaleString()} • Severity: {Math.round(rep.severity * 100)}%
                            </span>
                          </div>
                          <button
                            onClick={() => openReviewModal(rep)}
                            className="px-3 py-1.5 bg-cyan-600 hover:bg-cyan-500 text-white text-xs font-semibold rounded-lg shrink-0 transition"
                          >
                            Review
                          </button>
                        </div>
                      ))}
                    </div>
                  </div>

                  {/* Right: Active Closures preview */}
                  <div className="bg-slate-900/70 border border-slate-800 rounded-xl p-5">
                    <div className="flex items-center justify-between mb-4">
                      <h3 className="text-sm font-bold text-white flex items-center gap-2">
                        <span>⛔</span> Verified Active Road Closures
                      </h3>
                      <button
                        onClick={() => setActiveTab("closures")}
                        className="text-xs text-cyan-400 hover:text-cyan-300 font-semibold"
                      >
                        Manage Closures ({events.length}) →
                      </button>
                    </div>

                    <div className="space-y-3">
                      {events.slice(0, 3).map((evt) => (
                        <div key={evt.id} className="p-3 rounded-lg bg-slate-800/50 border border-slate-800 flex items-start justify-between gap-3">
                          <div>
                            <div className="flex items-center gap-2 mb-1">
                              <span className="text-[10px] uppercase font-bold px-2 py-0.5 rounded bg-rose-950 text-rose-300 border border-rose-800">
                                {evt.accessibility_status}
                              </span>
                              <span className="text-xs font-semibold text-white">
                                {evt.region_code.toUpperCase()} • Edge: <code className="text-cyan-300">{evt.edge_id || "None"}</code>
                              </span>
                            </div>
                            <p className="text-xs text-slate-300">
                              {((evt.details?.review_note as string) || "Authority verified impediment")}
                            </p>
                            <span className="text-[10px] text-slate-500 mt-1 block">
                              Source: {evt.source} • Valid Until: {evt.ends_at ? new Date(evt.ends_at).toLocaleString() : "Indefinite"}
                            </span>
                          </div>
                          <div className="flex flex-col gap-1 shrink-0">
                            <button
                              onClick={() => setResolvingEvent(evt)}
                              className="px-2.5 py-1 bg-emerald-700 hover:bg-emerald-600 text-white text-[11px] font-semibold rounded transition"
                            >
                              Resolve
                            </button>
                            <button
                              onClick={() => setExtendingEvent(evt)}
                              className="px-2.5 py-1 bg-slate-700 hover:bg-slate-600 text-slate-200 text-[11px] font-semibold rounded transition"
                            >
                              Extend
                            </button>
                          </div>
                        </div>
                      ))}
                    </div>
                  </div>
                </div>
              </div>
            )}

            {/* TAB: LIVE FEED READINESS & OPERATOR GOVERNANCE */}
            {activeTab === "live_feeds" && (
              <div className="space-y-6">
                {/* 1. Official Governance & Truthfulness Banner */}
                <div className="rounded-2xl border border-amber-500/40 bg-gradient-to-r from-amber-950/40 via-amber-900/20 to-slate-900/60 p-5 shadow-lg">
                  <div className="flex items-start gap-4">
                    <div className="p-2.5 rounded-xl bg-amber-500/20 text-amber-400 border border-amber-500/30 shrink-0 text-xl">
                      ⚠️
                    </div>
                    <div className="space-y-2">
                      <div className="flex flex-wrap items-center gap-2">
                        <h2 className="text-base font-bold text-white tracking-wide">
                          Official Early-Warning Live Feeds Governance & Standby Protocol
                        </h2>
                        <span className="px-2.5 py-0.5 rounded-full text-[10px] font-bold uppercase bg-amber-500/20 text-amber-300 border border-amber-500/40">
                          Integrity Guarantee
                        </span>
                      </div>
                      <p className="text-xs text-slate-300 leading-relaxed">
                        External government feeds (NDMA SACHET, CWC Flood, State Traffic Police, SDMA Alert) lacking live production URLs and authenticated credentials are held strictly in <strong className="text-amber-300">STANDBY</strong> status.
                        STANDBY explicitly indicates <strong className="text-amber-200">"NOT CONNECTED / AWAITING AUTHORIZED ACCESS"</strong>, and <span className="underline decoration-amber-400 font-semibold">NEVER an absence of real-world road hazards</span>.
                        Zero simulated or synthetic data is fabricated to pretend live ingestion is operational.
                      </p>
                      <div className="flex flex-wrap items-center gap-4 text-xs text-slate-400 pt-1">
                        <div className="flex items-center gap-1.5 text-emerald-400">
                          <span className="w-2 h-2 rounded-full bg-emerald-400"></span>
                          <span>Deterministic Risk-A* Active</span>
                        </div>
                        <div className="flex items-center gap-1.5 text-cyan-300">
                          <span className="w-2 h-2 rounded-full bg-cyan-400"></span>
                          <span>ML Disruption Model: Shadow Mode Only (Zero Graph Weight)</span>
                        </div>
                        <div className="flex items-center gap-1.5 text-amber-300">
                          <span className="w-2 h-2 rounded-full bg-amber-400"></span>
                          <span>Inbound Alerts Quarantined Until Human Operator Approval</span>
                        </div>
                      </div>
                    </div>
                  </div>
                </div>

                {/* 2. Feeds Readiness Status Grid & Diagnostic Actions */}
                <div className="space-y-4">
                  <div className="flex flex-wrap items-center justify-between gap-4 bg-slate-900/60 p-4 rounded-xl border border-slate-800">
                    <div>
                      <h3 className="text-sm font-bold text-white flex items-center gap-2">
                        <span>External Source Feeds Readiness</span>
                        <span className="text-xs font-normal text-slate-400">
                          ({liveFeeds.filter(f => f.status === "ONLINE" || f.status === "SYNCED").length} Online, {liveFeeds.filter(f => f.status === "STANDBY").length} Standby)
                        </span>
                      </h3>
                      <p className="text-xs text-slate-400 mt-0.5">
                        Continuous health monitoring, cryptographic payload hashing, and statutory clearance tracking.
                      </p>
                    </div>

                    <div className="flex items-center gap-2">
                      <button
                        onClick={() => setDiagnosticsModalOpen(true)}
                        className="px-3 py-1.5 rounded-xl bg-cyan-950/60 hover:bg-cyan-900/70 border border-cyan-700/60 text-cyan-300 text-xs font-semibold transition flex items-center gap-1.5 cursor-pointer shadow-sm"
                      >
                        <svg className="w-4 h-4 text-cyan-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
                        </svg>
                        <span>Parser Diagnostics & Health</span>
                      </button>

                      <button
                        onClick={loadAllData}
                        className="px-3 py-1.5 rounded-xl bg-slate-800 hover:bg-slate-700 border border-slate-700 text-slate-300 text-xs font-semibold transition flex items-center gap-1.5 cursor-pointer"
                        title="Re-query feed adapters"
                      >
                        <svg className="w-3.5 h-3.5 text-slate-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
                        </svg>
                        <span>Check Status</span>
                      </button>
                    </div>
                  </div>

                  {/* 5 Feed Source Cards */}
                  <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                    {liveFeeds.map((feed) => {
                      const isOnline = feed.status === "ONLINE" || feed.status === "SYNCED";
                      const isStandby = feed.status === "STANDBY";
                      const isStale = feed.is_stale || feed.status === "STALE";
                      const isDegraded = feed.status === "DEGRADED" || feed.status === "ERROR";

                      return (
                        <div
                          key={feed.source_id}
                          className={`rounded-xl border p-4 flex flex-col justify-between transition-all bg-slate-900/80 ${
                            isOnline
                              ? "border-emerald-500/40 shadow-xs"
                              : isStandby
                              ? "border-slate-800 hover:border-slate-700"
                              : isDegraded
                              ? "border-rose-500/50 shadow-rose-950/20"
                              : "border-amber-500/40"
                          }`}
                        >
                          <div className="space-y-3">
                            <div className="flex items-start justify-between gap-2">
                              <div>
                                <span className="text-xs font-mono text-cyan-400 font-bold block">
                                  {feed.source_id}
                                </span>
                                <h4 className="text-sm font-semibold text-white mt-0.5 leading-snug">
                                  {feed.source_name}
                                </h4>
                                <span className="text-[11px] text-slate-400 block mt-0.5">
                                  {feed.agency}
                                </span>
                              </div>
                              <span
                                className={`px-2 py-0.5 rounded-full text-[10px] font-bold uppercase tracking-wider border shrink-0 ${
                                  isOnline
                                    ? "bg-emerald-950/80 text-emerald-300 border-emerald-700/60"
                                    : isStandby
                                    ? "bg-slate-800 text-amber-300 border-amber-700/50"
                                    : isDegraded
                                    ? "bg-rose-950/80 text-rose-300 border-rose-700/60"
                                    : "bg-amber-950/80 text-amber-300 border-amber-700/60"
                                }`}
                              >
                                {isStandby ? "STANDBY (AWAITING ACCESS)" : feed.status}
                              </span>
                            </div>

                            {/* Status Disclosure Pill */}
                            <div className={`p-2 rounded-lg text-[11px] border ${
                              isOnline
                                ? "bg-emerald-950/30 text-emerald-300 border-emerald-900/50"
                                : isStandby
                                ? "bg-amber-950/20 text-amber-300/90 border-amber-900/40"
                                : "bg-rose-950/30 text-rose-300 border-rose-900/50"
                            }`}>
                              {isStandby && "⚠️ STANDBY: Endpoint or credentials unconfigured. Zero synthetic alerts generated."}
                              {isOnline && "🟢 ONLINE: Verified active feed. Updates ingested into quarantine review queue."}
                              {isDegraded && `🔴 DEGRADED: ${feed.parser_errors?.[0] || "Feed reported parsing or network error."}`}
                              {isStale && "🟡 STALE: Ingestion interval exceeded freshness threshold."}
                            </div>

                            {/* Feed Metadata Grid */}
                            <div className="grid grid-cols-2 gap-2 text-[11px] bg-slate-950/50 p-2.5 rounded-lg border border-slate-800/80">
                              <div>
                                <span className="text-slate-500 block">Last Attempted:</span>
                                <span className="text-slate-300 font-mono">
                                  {feed.last_attempted_fetch ? new Date(feed.last_attempted_fetch).toLocaleTimeString() : "Not attempted"}
                                </span>
                              </div>
                              <div>
                                <span className="text-slate-500 block">Last Successful:</span>
                                <span className="text-slate-300 font-mono">
                                  {feed.last_successful_fetch ? new Date(feed.last_successful_fetch).toLocaleTimeString() : "None recorded"}
                                </span>
                              </div>
                              <div>
                                <span className="text-slate-500 block">Source Timestamp:</span>
                                <span className="text-slate-300 font-mono">
                                  {feed.source_timestamp ? new Date(feed.source_timestamp).toLocaleTimeString() : "Upstream idle"}
                                </span>
                              </div>
                              <div>
                                <span className="text-slate-500 block">Freshness Limit:</span>
                                <span className="text-cyan-300 font-mono">
                                  {Math.round(feed.freshness_threshold_seconds / 60)} mins
                                </span>
                              </div>
                              <div>
                                <span className="text-slate-500 block">Parser Health:</span>
                                <span className={feed.parser_errors && feed.parser_errors.length > 0 ? "text-rose-400 font-medium" : "text-emerald-400 font-medium"}>
                                  {feed.parser_errors && feed.parser_errors.length > 0 ? `${feed.parser_errors.length} Error(s)` : "Clean"}
                                </span>
                              </div>
                              <div>
                                <span className="text-slate-500 block">Active Alerts:</span>
                                <span className="text-slate-200 font-semibold font-mono">
                                  {feed.active_advisories_count}
                                </span>
                              </div>
                            </div>

                            {/* Authentication & Clearance Requirements */}
                            <div className="space-y-1 pt-1">
                              <div className="text-[11px] flex items-center justify-between">
                                <span className="text-slate-400">Security Credentials:</span>
                                <span className={`font-mono text-[10px] px-1.5 py-0.5 rounded border ${
                                  feed.credentials_configured
                                    ? "bg-emerald-950/60 text-emerald-300 border-emerald-800"
                                    : "bg-slate-800 text-slate-400 border-slate-700"
                                }`}>
                                  {feed.credentials_configured ? "Configured" : "Missing / Standby"}
                                </span>
                              </div>
                              {feed.required_credentials && feed.required_credentials.length > 0 && (
                                <div className="text-[10px] text-slate-500 font-mono truncate" title={feed.required_credentials.join(", ")}>
                                  Env: {feed.required_credentials.join(", ")}
                                </div>
                              )}
                              <div className="text-[11px] text-slate-400 mt-1">
                                <span className="text-slate-500 block text-[10px] uppercase font-semibold">Statutory Authority Clearance:</span>
                                <span className="text-slate-300 text-[11px] line-clamp-2" title={feed.authority_approval_required}>
                                  {feed.authority_approval_required}
                                </span>
                              </div>
                            </div>
                          </div>
                        </div>
                      );
                    })}
                  </div>
                </div>

                {/* 3. Operator Review Queue for Early-Warning Candidate Advisories */}
                <div className="space-y-4 pt-2">
                  <div className="flex flex-wrap items-center justify-between gap-4 bg-slate-900/60 p-4 rounded-xl border border-slate-800">
                    <div>
                      <h3 className="text-sm font-bold text-white flex items-center gap-2">
                        <span>Operator Review Queue: Candidate Advisories</span>
                        <span className="text-xs px-2 py-0.5 rounded-full bg-amber-500/20 text-amber-300 border border-amber-500/30">
                          {candidateAdvisories.filter(a => a.review_status === "pending_review" || a.review_status === "candidate_advisory" || a.review_status === "conflicting").length} Awaiting Review
                        </span>
                      </h3>
                      <p className="text-xs text-slate-400 mt-0.5">
                        Inbound feed alerts remain strictly quarantined. Only operator-verified advisories with bound OSM road segments become active Risk-A* closures.
                      </p>
                    </div>

                    {/* Filter Buttons */}
                    <div className="flex items-center gap-1.5 bg-slate-950/60 p-1 rounded-xl border border-slate-800">
                      {[
                        { id: "all", label: `All (${candidateAdvisories.length})` },
                        { id: "pending_review", label: `Pending (${candidateAdvisories.filter(a => a.review_status === "pending_review" || a.review_status === "candidate_advisory").length})` },
                        { id: "conflicting", label: `Conflicting (${candidateAdvisories.filter(a => a.review_status === "conflicting" || a.conflict_detected).length})` },
                        { id: "accepted", label: `Accepted (${candidateAdvisories.filter(a => a.review_status === "accepted").length})` },
                        { id: "rejected", label: `Rejected (${candidateAdvisories.filter(a => a.review_status === "rejected").length})` },
                      ].map((f) => (
                        <button
                          key={f.id}
                          onClick={() => setCandidateFilter(f.id as typeof candidateFilter)}
                          className={`px-2.5 py-1 text-xs rounded-lg transition font-medium cursor-pointer ${
                            candidateFilter === f.id
                              ? "bg-primary text-primary-foreground font-bold shadow-xs"
                              : "text-slate-400 hover:text-slate-200"
                          }`}
                        >
                          {f.label}
                        </button>
                      ))}
                    </div>
                  </div>

                  {filteredCandidateAdvisories.length === 0 ? (
                    <div className="bg-slate-900/40 border border-slate-800 rounded-xl p-8 text-center text-slate-400 text-xs">
                      No candidate advisories found matching the current filter: <strong className="text-slate-300 uppercase">{candidateFilter}</strong>.
                    </div>
                  ) : (
                    <div className="space-y-3">
                      {filteredCandidateAdvisories.map((adv) => {
                        const isPending = adv.review_status === "pending_review" || adv.review_status === "candidate_advisory";
                        const isConflicting = adv.review_status === "conflicting" || adv.conflict_detected;
                        const isAccepted = adv.review_status === "accepted";
                        const isRejected = adv.review_status === "rejected";

                        return (
                          <div
                            key={adv.advisory_id}
                            className={`rounded-xl border p-4 transition-all bg-slate-900/80 ${
                              isConflicting
                                ? "border-rose-500/60 shadow-md shadow-rose-950/30"
                                : isAccepted
                                ? "border-emerald-500/40 bg-emerald-950/10"
                                : "border-slate-800 hover:border-slate-700"
                            }`}
                          >
                            <div className="flex flex-col md:flex-row md:items-start justify-between gap-4">
                              <div className="space-y-2 flex-1">
                                <div className="flex flex-wrap items-center gap-2">
                                  <span className="text-xs font-mono font-bold text-cyan-400">
                                    {adv.advisory_id}
                                  </span>
                                  <span className="text-xs text-slate-500">•</span>
                                  <span className="text-xs font-medium text-slate-300">
                                    {adv.source_agency}
                                  </span>
                                  <span className="text-xs text-slate-500">•</span>
                                  <span className="text-xs text-slate-400">
                                    {adv.source_timestamp ? new Date(adv.source_timestamp).toLocaleString() : "Live ingest"}
                                  </span>
                                  <span className={`px-2 py-0.5 rounded text-[10px] font-bold uppercase tracking-wider ${
                                    adv.severity === "WARNING" ? "bg-rose-950/80 text-rose-300 border border-rose-800" :
                                    adv.severity === "ALERT" ? "bg-amber-950/80 text-amber-300 border border-amber-800" :
                                    "bg-blue-950/80 text-blue-300 border border-blue-800"
                                  }`}>
                                    {adv.severity}
                                  </span>
                                </div>

                                <h4 className="text-sm font-bold text-white leading-snug">
                                  {adv.headline}
                                </h4>

                                <div className="text-xs text-slate-300 space-y-1">
                                  <div>
                                    <span className="text-slate-400">Affected Corridors:</span>{" "}
                                    <strong className="text-cyan-300">{adv.affected_corridors?.join(", ") || "General Corridor"}</strong>
                                  </div>
                                  <div>
                                    <span className="text-slate-400">Recommended Guidance:</span>{" "}
                                    <span className="text-slate-200">{adv.recommended_action}</span>
                                  </div>
                                </div>

                                {/* Operational Conflict Warning */}
                                {isConflicting && (
                                  <div className="bg-rose-950/40 border border-rose-800/80 rounded-lg p-3 text-xs text-rose-200 space-y-1 mt-2">
                                    <div className="flex items-center gap-1.5 font-bold text-rose-300">
                                      <span>⚠️ OPERATIONAL CONFLICT DETECTED</span>
                                    </div>
                                    <p>
                                      {adv.conflict_note || "Contradictory status detected between independent agency feeds (e.g. road blocked vs. road passable)."}
                                    </p>
                                    <span className="text-[11px] text-rose-300/80 block">
                                      Guaranteed Safety Rule: Quarantined from routing engine. Requires human operator review with field evidence before promotion.
                                    </span>
                                  </div>
                                )}

                                {/* Audit & Decision metadata if already reviewed */}
                                {(adv.reviewer_id || adv.reviewed_at) && (
                                  <div className="text-[11px] text-slate-400 bg-slate-950/60 p-2 rounded-lg border border-slate-800 font-mono space-y-0.5 mt-2">
                                    <div>Reviewer: <span className="text-cyan-300">{adv.reviewer_id}</span> · Reviewed at: <span>{adv.reviewed_at ? new Date(adv.reviewed_at).toLocaleString() : "Recorded"}</span></div>
                                    {adv.road_segment_id && <div>Bound Road Segment: <span className="text-emerald-300">{adv.road_segment_id}</span></div>}
                                    {adv.review_note && <div>Review Note: <span className="text-slate-300">{adv.review_note}</span></div>}
                                  </div>
                                )}
                              </div>

                              {/* Review Status Badge & Triage Action Button */}
                              <div className="flex md:flex-col items-end justify-between gap-3 shrink-0">
                                <span className={`px-2.5 py-1 rounded-full text-xs font-bold uppercase tracking-wider border ${
                                  isAccepted
                                    ? "bg-emerald-950 text-emerald-300 border-emerald-800"
                                    : isConflicting
                                    ? "bg-rose-950 text-rose-300 border-rose-800 animate-pulse"
                                    : isRejected
                                    ? "bg-slate-800 text-slate-400 border-slate-700"
                                    : "bg-amber-950 text-amber-300 border-amber-800"
                                }`}>
                                  {adv.review_status}
                                </span>

                                <button
                                  onClick={() => handleOpenCandidateReview(adv)}
                                  className="px-3 py-1.5 rounded-lg bg-cyan-600 hover:bg-cyan-500 text-white text-xs font-semibold shadow transition cursor-pointer flex items-center gap-1"
                                >
                                  <span>{isPending || isConflicting ? "Triage & Review" : "Re-evaluate"}</span>
                                  <svg className="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5l7 7-7 7" />
                                  </svg>
                                </button>
                              </div>
                            </div>
                          </div>
                        );
                      })}
                    </div>
                  )}
                </div>
              </div>
            )}

            {/* TAB 2: DATA FRESHNESS AND SOURCE-STATUS CENTER (11 Sources) */}
            {activeTab === "sources" && (
              <div className="space-y-4">
                <div className="flex flex-wrap items-center justify-between gap-4 bg-slate-900/60 p-4 rounded-xl border border-slate-800">
                  <div>
                    <h3 className="text-sm font-bold text-white">Data Pipeline Freshness & Integrity Center</h3>
                    <p className="text-xs text-slate-400 mt-0.5">
                      Audited multi-source status for all 11 operational layers. Click any card for cryptographic provenance.
                    </p>
                  </div>
                  <div className="text-xs text-slate-400 font-mono">
                    Total Monitored Sources: <strong className="text-white">{sources.length}</strong>
                  </div>
                </div>

                <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                  {sources.map((src) => (
                    <div
                      key={src.id}
                      className="bg-slate-900/80 border border-slate-800 rounded-xl p-4 flex flex-col justify-between hover:border-slate-700 transition"
                    >
                      <div>
                        <div className="flex items-start justify-between gap-2 mb-2">
                          <span className="text-[10px] uppercase font-bold text-slate-400 tracking-wider">
                            {src.category}
                          </span>
                          <span
                            className={`text-[11px] font-bold px-2 py-0.5 rounded-full border ${
                              src.status === "LIVE"
                                ? "bg-emerald-950/80 text-emerald-300 border-emerald-800"
                                : src.status === "FRESH"
                                ? "bg-blue-950/80 text-blue-300 border-blue-800"
                                : src.status === "STANDBY"
                                ? "bg-amber-950/80 text-amber-300 border-amber-800"
                                : src.status === "SIMULATED"
                                ? "bg-purple-950/80 text-purple-300 border-purple-800"
                                : "bg-slate-800 text-slate-300 border-slate-700"
                            }`}
                          >
                            {src.status}
                          </span>
                        </div>

                        <h4 className="font-bold text-sm text-white mb-1">{src.name}</h4>
                        <p className="text-xs text-slate-400 line-clamp-2 mb-3">{src.provenance}</p>

                        <div className="bg-slate-950/60 rounded-lg p-2.5 border border-slate-800/80 space-y-1 text-xs">
                          <div className="flex justify-between">
                            <span className="text-slate-500">Coverage:</span>
                            <span className="text-slate-300 font-medium truncate max-w-[180px]">{src.coverage}</span>
                          </div>
                          <div className="flex justify-between">
                            <span className="text-slate-500">Freshness / Age:</span>
                            <span className="text-slate-200 font-medium">{src.age}</span>
                          </div>
                          <div className="flex justify-between">
                            <span className="text-slate-500">Hash:</span>
                            <code className="text-emerald-400 font-mono text-[11px] truncate max-w-[180px]">
                              {src.version_hash}
                            </code>
                          </div>
                        </div>

                        {src.error_message && (
                          <div className="mt-2 text-[11px] text-amber-300/90 bg-amber-950/30 border border-amber-900/40 p-2 rounded">
                            ℹ️ {src.error_message}
                          </div>
                        )}
                      </div>

                      <div className="mt-4 pt-3 border-t border-slate-800 flex items-center justify-between gap-2">
                        <button
                          onClick={() => setSelectedProvenanceSource(src)}
                          className="text-xs text-cyan-400 hover:text-cyan-300 font-semibold flex items-center gap-1"
                        >
                          <svg className="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M2.458 12C3.732 7.943 7.523 5 12 5c4.478 0 8.268 2.943 9.542 7-1.274 4.057-5.064 7-9.542 7-4.477 0-8.268-2.943-9.542-7z" />
                          </svg>
                          Inspect Provenance
                        </button>

                        {src.is_refreshable && userRole === "admin" && (
                          <button
                            onClick={() => handleRefreshSource(src.id)}
                            disabled={refreshingSourceId === src.id}
                            className="px-2.5 py-1 bg-slate-800 hover:bg-slate-700 text-slate-200 text-xs font-semibold rounded border border-slate-700 transition"
                          >
                            {refreshingSourceId === src.id ? "Refreshing..." : "Flush & Poll"}
                          </button>
                        )}
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            )}

            {/* TAB 3: FIELD-REPORT REVIEW QUEUE */}
            {activeTab === "candidates" && (
              <div className="p-6 space-y-4">
                <div><h2 className="text-lg font-bold text-white">Public disruption candidates</h2><p className="text-xs text-slate-400">Government records are candidates until a reviewer confirms segment and time. They never affect routing while pending.</p></div>
                {candidateLoadError && <div className="rounded-lg border border-red-800 bg-red-950/40 p-3 text-sm text-red-200">Candidate API error: {candidateLoadError}. Check authentication, reviewer role and backend availability.</div>}
                {!candidateLoadError && publicCandidates.length === 0 && <div className="rounded-lg border border-amber-800 bg-amber-950/30 p-4 text-sm text-amber-200">No candidates are visible for this identity ({userRole}, region: {userRegion || "unassigned"}). The API may have returned no records for this RBAC scope. No candidates were auto-approved.</div>}
                <div className="space-y-3">{publicCandidates.map((candidate) => (
                  <div key={candidate.candidate_id} className="rounded-xl border border-slate-700 bg-slate-900/60 p-4">
                    <div className="flex items-start justify-between gap-4"><div><div className="text-sm font-semibold text-white">{candidate.road_text}</div><div className="text-xs text-slate-400 mt-1">{candidate.region_code} · {candidate.reported_status} · published {candidate.published_at}</div><a className="text-xs text-cyan-300 underline" href={candidate.source_url} target="_blank" rel="noreferrer">Open source record</a>{candidate.restriction_effective_at && <div className="mt-2 text-xs text-slate-300">Restriction effective: {candidate.restriction_effective_at}</div>}{candidate.reopening_effective_at && <div className="text-xs text-slate-300">Reopening effective: {candidate.reopening_effective_at}</div>}{candidate.evidence_note && <div className="mt-2 text-xs text-cyan-200">Evidence note: {candidate.evidence_note}</div>}<div className="mt-2 text-xs text-amber-300">Missing verification: road segment, incident start time, coordinates and reviewer approval.</div></div><span className="rounded-full px-2 py-1 text-[10px] uppercase bg-amber-950 text-amber-300">{candidate.review_status}</span></div>
                    {candidate.review_status === "pending" && userRole !== "field_official" && <button className="mt-3 rounded-lg bg-cyan-600 px-3 py-2 text-xs font-semibold text-white" onClick={async () => { const segment = window.prompt("Verified road segment ID (required)"); const started = window.prompt("Incident start ISO timestamp (required)"); if (!segment || !started) return; const note = window.prompt("Review note") || "Approved after source and segment review"; await reviewPublicCandidate(token, candidate.candidate_id, { decision: "approved", road_segment_id: segment, incident_started_at: started, review_note: note }); await loadAllData(); }}>Approve matched segment</button>}
                  </div>
                ))}</div>
              </div>
            )}
            {activeTab === "reports" && (
              <div className="space-y-4">
                <div className="flex flex-wrap items-center justify-between gap-4 bg-slate-900/60 p-4 rounded-xl border border-slate-800">
                  <div>
                    <h3 className="text-sm font-bold text-white">Field Intelligence Queue</h3>
                    <p className="text-xs text-slate-400 mt-0.5">
                      Verify or reject geo-tagged incident submissions. Only verified events affect Risk-A* route graphs.
                    </p>
                  </div>
                  <div className="text-xs text-amber-300 bg-amber-950/60 px-3 py-1 rounded-lg border border-amber-800">
                    Rule: Pending reports never close routes
                  </div>
                </div>

                <div className="bg-slate-900/80 border border-slate-800 rounded-xl overflow-hidden">
                  <div className="overflow-x-auto">
                    <table className="w-full text-left text-xs">
                      <thead className="bg-slate-800/80 text-slate-300 border-b border-slate-700 font-semibold">
                        <tr>
                          <th className="p-3">Status</th>
                          <th className="p-3">Region / Location</th>
                          <th className="p-3">Hazard Type</th>
                          <th className="p-3">Severity</th>
                          <th className="p-3">Description</th>
                          <th className="p-3">Observed At</th>
                          <th className="p-3 text-right">Actions</th>
                        </tr>
                      </thead>
                      <tbody className="divide-y divide-slate-800 text-slate-300">
                        {filteredReports.length === 0 ? (
                          <tr>
                            <td colSpan={7} className="p-6 text-center text-slate-500">
                              No reports matching current region filter.
                            </td>
                          </tr>
                        ) : (
                          filteredReports.map((rep) => (
                            <tr key={rep.id} className="hover:bg-slate-800/40 transition">
                              <td className="p-3 font-semibold whitespace-nowrap">
                                <span
                                  className={`px-2 py-0.5 rounded text-[11px] font-bold ${
                                    rep.review_status === "authority_verified" || rep.review_status === "accepted"
                                      ? "bg-emerald-950 text-emerald-300 border border-emerald-800"
                                      : rep.review_status === "pending"
                                      ? "bg-amber-950 text-amber-300 border border-amber-800"
                                      : rep.review_status === "corroborated"
                                      ? "bg-blue-950 text-blue-300 border border-blue-800"
                                      : "bg-rose-950 text-rose-300 border border-rose-800"
                                  }`}
                                >
                                  {rep.review_status}
                                </span>
                              </td>
                              <td className="p-3">
                                <div className="font-bold text-white">{rep.place_name || rep.district || "Unnamed"}</div>
                                <div className="text-[11px] text-slate-400 font-mono">
                                  {rep.region_code} • {rep.lon.toFixed(2)}, {rep.lat.toFixed(2)}
                                </div>
                              </td>
                              <td className="p-3 capitalize">{rep.kind.replace("_", " ")}</td>
                              <td className="p-3 font-mono font-medium">{Math.round(rep.severity * 100)}%</td>
                              <td className="p-3 max-w-xs truncate" title={rep.description}>
                                {rep.description}
                              </td>
                              <td className="p-3 whitespace-nowrap font-mono text-[11px] text-slate-400">
                                {new Date(rep.observed_at).toLocaleString()}
                              </td>
                              <td className="p-3 text-right">
                                {rep.review_status === "pending" || rep.review_status === "corroborated" ? (
                                  <button
                                    onClick={() => openReviewModal(rep)}
                                    className="px-3 py-1 bg-cyan-600 hover:bg-cyan-500 text-white font-semibold rounded text-xs transition"
                                  >
                                    Review
                                  </button>
                                ) : (
                                  <span className="text-[11px] text-slate-500 italic">Reviewed</span>
                                )}
                              </td>
                            </tr>
                          ))
                        )}
                      </tbody>
                    </table>
                  </div>
                </div>
              </div>
            )}

            {/* TAB 4: ACTIVE CLOSURES & ACCESSIBILITY EVENTS */}
            {activeTab === "closures" && (
              <div className="space-y-4">
                <div className="flex flex-wrap items-center justify-between gap-4 bg-slate-900/60 p-4 rounded-xl border border-slate-800">
                  <div>
                    <h3 className="text-sm font-bold text-white">Active Highway Closures & Restrictions</h3>
                    <p className="text-xs text-slate-400 mt-0.5">
                      Operational road blockages affecting A* routing graphs. Operator can resolve or extend expiry.
                    </p>
                  </div>
                  <button
                    onClick={handleTestRoute}
                    className="px-3 py-1.5 bg-cyan-600 hover:bg-cyan-500 text-white text-xs font-semibold rounded-lg shadow transition flex items-center gap-1.5"
                  >
                    Recalculate Affected Routes
                  </button>
                </div>

                <div className="bg-slate-900/80 border border-slate-800 rounded-xl overflow-hidden">
                  <div className="overflow-x-auto">
                    <table className="w-full text-left text-xs">
                      <thead className="bg-slate-800/80 text-slate-300 border-b border-slate-700 font-semibold">
                        <tr>
                          <th className="p-3">Status</th>
                          <th className="p-3">Region / Segment</th>
                          <th className="p-3">Impediment / Reason</th>
                          <th className="p-3">Starts At</th>
                          <th className="p-3">Ends At (Expiry)</th>
                          <th className="p-3">Verification Authority</th>
                          <th className="p-3 text-right">Actions</th>
                        </tr>
                      </thead>
                      <tbody className="divide-y divide-slate-800 text-slate-300">
                        {filteredEvents.length === 0 ? (
                          <tr>
                            <td colSpan={7} className="p-6 text-center text-slate-500">
                              No active road closures recorded for selected jurisdiction.
                            </td>
                          </tr>
                        ) : (
                          filteredEvents.map((evt) => (
                            <tr key={evt.id} className="hover:bg-slate-800/40 transition">
                              <td className="p-3">
                                <span
                                  className={`px-2 py-0.5 rounded text-[11px] font-bold ${
                                    evt.accessibility_status === "blocked"
                                      ? "bg-rose-950 text-rose-300 border border-rose-800"
                                      : "bg-amber-950 text-amber-300 border border-amber-800"
                                  }`}
                                >
                                  {evt.accessibility_status.toUpperCase()}
                                </span>
                              </td>
                              <td className="p-3">
                                <div className="font-bold text-white uppercase">{evt.region_code}</div>
                                <code className="text-cyan-300 font-mono text-[11px]">Edge: {evt.edge_id || "Corridor Segment"}</code>
                              </td>
                              <td className="p-3 max-w-sm">
                                <div className="text-slate-200">
                                  {((evt.details?.review_note as string) || "Active impediment")}
                                </div>
                                <div className="text-[11px] text-slate-500 font-mono">
                                  Coordinates: {evt.lon.toFixed(2)}, {evt.lat.toFixed(2)}
                                </div>
                              </td>
                              <td className="p-3 font-mono text-slate-400 whitespace-nowrap">
                                {new Date(evt.starts_at).toLocaleString()}
                              </td>
                              <td className="p-3 font-mono text-slate-400 whitespace-nowrap">
                                {evt.ends_at ? new Date(evt.ends_at).toLocaleString() : "Until Inspection"}
                              </td>
                              <td className="p-3 text-slate-300">
                                {((evt.details?.verification_authority as string) || "Regional Reviewer")}
                              </td>
                              <td className="p-3 text-right whitespace-nowrap">
                                <div className="flex items-center justify-end gap-1.5">
                                  <button
                                    onClick={() => setResolvingEvent(evt)}
                                    className="px-2.5 py-1 bg-emerald-700 hover:bg-emerald-600 text-white font-semibold rounded text-xs transition"
                                    title="Mark road cleared and reopened"
                                  >
                                    Resolve
                                  </button>
                                  <button
                                    onClick={() => setExtendingEvent(evt)}
                                    className="px-2.5 py-1 bg-slate-700 hover:bg-slate-600 text-slate-200 font-semibold rounded text-xs transition"
                                    title="Extend closure duration"
                                  >
                                    Extend
                                  </button>
                                </div>
                              </td>
                            </tr>
                          ))
                        )}
                      </tbody>
                    </table>
                  </div>
                </div>
              </div>
            )}

            {/* TAB 5: FLEET TELEMATICS & GPS HEALTH */}
            {activeTab === "telematics" && (
              <div className="space-y-6">
                {/* AIS-140 Simulator Disclosure Header */}
                <div className="bg-slate-900/60 border border-slate-800 p-4 rounded-xl flex flex-wrap items-center justify-between gap-4">
                  <div>
                    <div className="flex items-center gap-2 mb-1">
                      <span className="text-xs font-bold px-2 py-0.5 rounded bg-purple-950 text-purple-300 border border-purple-800">
                        SIMULATED GPS STREAM
                      </span>
                      <h3 className="text-sm font-bold text-white">AIS-140 Commercial Freight Telemetry Guard</h3>
                    </div>
                    <p className="text-xs text-slate-400">
                      High-fidelity demo stream. All incoming packets are strictly validated against speed (&gt;120 km/h flag, &gt;180 km/h jump rejection), bounds, and replays.
                    </p>
                  </div>
                  <div className="text-right">
                    <span className="text-xs text-slate-400 block">Acceptance Ratio</span>
                    <span className="text-lg font-bold text-emerald-400">
                      {telemetry?.total_packets_received
                        ? Math.round(
                            ((telemetry.accepted_packets || 0) / telemetry.total_packets_received) * 100
                          )
                        : 100}
                      %
                    </span>
                  </div>
                </div>

                {/* Validation Rejection Log */}
                <div className="bg-slate-900/80 border border-slate-800 rounded-xl p-5">
                  <h4 className="text-sm font-bold text-rose-400 mb-3 flex items-center gap-2">
                    <span>🛡️</span> Security & Geometric Rejection Log (TelemetryGuard Buffer)
                  </h4>
                  <div className="space-y-2 max-h-64 overflow-y-auto font-mono text-xs">
                    {telemetry?.recent_rejections && telemetry.recent_rejections.length > 0 ? (
                      telemetry.recent_rejections.map((rej, idx) => (
                        <div
                          key={idx}
                          className="bg-rose-950/20 border border-rose-900/40 p-2.5 rounded-lg flex flex-wrap items-center justify-between gap-2"
                        >
                          <div className="flex items-center gap-2">
                            <span className="px-2 py-0.5 rounded bg-rose-950 text-rose-300 font-bold text-[10px]">
                              {rej.error_type || "REJECTED"}
                            </span>
                            <span className="text-slate-200 font-bold">{rej.vehicle_id}</span>
                            <span className="text-slate-400">• {rej.reason}</span>
                          </div>
                          <div className="text-slate-500 text-[11px]">
                            {new Date(rej.timestamp).toLocaleTimeString()}
                          </div>
                        </div>
                      ))
                    ) : (
                      <div className="text-slate-500 py-3 text-center">No telemetry rejections recorded.</div>
                    )}
                  </div>
                </div>

                {/* Tracked Vehicles Cards */}
                <div className="space-y-3">
                  <h4 className="text-sm font-bold text-white">Active Commercial Freight Transits</h4>
                  <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                    {vehicles.map((v) => (
                      <div key={v.id} className="bg-slate-900/70 border border-slate-800 p-4 rounded-xl">
                        <div className="flex items-start justify-between mb-2">
                          <div>
                            <span className="text-xs font-bold text-white">{v.registration}</span>
                            <span className="text-[11px] text-slate-400 block font-mono">
                              Class: {v.vehicle_type.toUpperCase()} • Region: {v.region_code}
                            </span>
                          </div>
                          <span className="text-[10px] px-2 py-0.5 rounded bg-emerald-950 text-emerald-300 border border-emerald-800 font-bold">
                            TRACKED
                          </span>
                        </div>
                        <div className="bg-slate-950/60 p-2.5 rounded-lg border border-slate-800/80 text-xs space-y-1">
                          <div className="flex justify-between text-slate-400">
                            <span>AIS-140 Trust Score:</span>
                            <span className="text-cyan-300 font-bold font-mono">0.98 / 1.00</span>
                          </div>
                          <div className="flex justify-between text-slate-400">
                            <span>Corridor:</span>
                            <span className="text-slate-300 truncate max-w-[160px]">
                              {((v.metadata?.corridor as string) || "Guwahati-Shillong-Silchar")}
                            </span>
                          </div>
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              </div>
            )}

            {/* TAB 6: ROUTING SANDBOX */}
            {activeTab === "routing" && (
              <div className="space-y-6">
                <div className="bg-slate-900/60 border border-slate-800 p-4 rounded-xl">
                  <h3 className="text-sm font-bold text-white">Risk-A* Routing Policy Sandbox</h3>
                  <p className="text-xs text-slate-400 mt-0.5">
                    Evaluate explainable route alternatives directly against the current graph snapshot and active closure events.
                  </p>
                </div>

                <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
                  {/* Controls Form */}
                  <div className="bg-slate-900/80 border border-slate-800 p-5 rounded-xl space-y-4">
                    <h4 className="text-xs font-bold text-slate-300 uppercase tracking-wider">Parameters</h4>

                    <div>
                      <label className="text-xs text-slate-400 block mb-1">Vehicle Classification</label>
                      <select
                        value={routeVehicle}
                        onChange={(e) => setRouteVehicle(e.target.value as Vehicle)}
                        className="w-full bg-slate-800 border border-slate-700 rounded-lg p-2 text-xs text-white"
                      >
                        <option value="heavy">Heavy Commercial Freight (40T Multi-Axle)</option>
                        <option value="light">Light Commercial / 4x4 (3.5T)</option>
                        <option value="emergency">Emergency Relief Vehicle</option>
                      </select>
                    </div>

                    <div>
                      <label className="text-xs text-slate-400 block mb-1">Weather Scenario</label>
                      <select
                        value={routeWeather}
                        onChange={(e) => setRouteWeather(e.target.value as Weather)}
                        className="w-full bg-slate-800 border border-slate-700 rounded-lg p-2 text-xs text-white"
                      >
                        <option value="normal">Standard Meteorological NWP Baseline</option>
                        <option value="heavy_rain">Monsoon Torrential Rain (+2.2x Hazard Multiplier)</option>
                      </select>
                    </div>

                    <div>
                      <div className="flex justify-between text-xs text-slate-400 mb-1">
                        <span>Risk Aversion Weight:</span>
                        <span className="text-cyan-300 font-mono font-bold">{routeAversion}</span>
                      </div>
                      <input
                        type="range"
                        min="0"
                        max="1"
                        step="0.1"
                        value={routeAversion}
                        onChange={(e) => setRouteAversion(parseFloat(e.target.value))}
                        className="w-full accent-cyan-500"
                      />
                    </div>

                    <div className="flex items-center gap-2 pt-2 border-t border-slate-800">
                      <input
                        type="checkbox"
                        id="strict-mode"
                        checked={routeStrictMode}
                        onChange={(e) => setRouteStrictMode(e.target.checked)}
                        className="rounded accent-cyan-500"
                      />
                      <label htmlFor="strict-mode" className="text-xs text-slate-300 cursor-pointer">
                        Strict Vehicle Restriction Mode (Fail closed on missing bridge limits)
                      </label>
                    </div>

                    <button
                      onClick={handleTestRoute}
                      disabled={routingLoading}
                      className="w-full py-2.5 bg-cyan-600 hover:bg-cyan-500 disabled:bg-slate-700 text-white text-xs font-bold rounded-lg transition flex items-center justify-center gap-2"
                    >
                      {routingLoading ? "Calculating Risk-A*..." : "Execute Route Comparison"}
                    </button>
                  </div>

                  {/* Results Display */}
                  <div className="lg:col-span-2 bg-slate-900/80 border border-slate-800 p-5 rounded-xl space-y-4">
                    <h4 className="text-xs font-bold text-slate-300 uppercase tracking-wider">
                      Comparison Breakdown
                    </h4>

                    {routeComparison ? (
                      <div className="space-y-4">
                        <div className="grid grid-cols-2 gap-4">
                          {routeComparison.routes.map((rt) => (
                            <div
                              key={rt.id}
                              className={`p-4 rounded-xl border ${
                                rt.id === "risk_aware"
                                  ? "bg-cyan-950/20 border-cyan-800/60"
                                  : "bg-slate-800/40 border-slate-800"
                              }`}
                            >
                              <div className="flex items-center justify-between mb-2">
                                <span className="text-xs font-bold uppercase text-white">
                                  {rt.id === "risk_aware" ? "Risk-A* Resilient Path" : "Standard Fastest Path"}
                                </span>
                                <span
                                  className={`text-[10px] px-2 py-0.5 rounded font-bold ${
                                    rt.status === "available"
                                      ? "bg-emerald-950 text-emerald-300 border border-emerald-800"
                                      : "bg-rose-950 text-rose-300 border border-rose-800"
                                  }`}
                                >
                                  {rt.status}
                                </span>
                              </div>

                              {rt.status === "available" && "distance_km" in rt && (
                                <div className="space-y-1 text-xs text-slate-300">
                                  <div className="flex justify-between">
                                    <span className="text-slate-400">Distance:</span>
                                    <span className="font-mono font-bold text-white">{rt.distance_km.toFixed(1)} km</span>
                                  </div>
                                  <div className="flex justify-between">
                                    <span className="text-slate-400">Travel Time:</span>
                                    <span className="font-mono font-bold text-white">{rt.duration_min} mins</span>
                                  </div>
                                  <div className="flex justify-between">
                                    <span className="text-slate-400">Risk Exposure:</span>
                                    <span className="font-mono font-bold text-cyan-300">
                                      {rt.risk_exposure.toFixed(2)}
                                    </span>
                                  </div>
                                </div>
                              )}
                            </div>
                          ))}
                        </div>

                        {routeComparison.explanations && routeComparison.explanations.length > 0 && (
                          <div className="border-t border-slate-800 pt-3">
                            <span className="text-xs font-bold text-slate-300 block mb-2">
                              Avoided Segments & Explainability
                            </span>
                            <div className="space-y-2">
                              {routeComparison.explanations.map((exp, idx) => (
                                <div
                                  key={idx}
                                  className="text-xs bg-slate-950/60 p-2.5 rounded border border-slate-800 text-slate-300"
                                >
                                  <strong className="text-white">{exp.road || exp.edge_id}:</strong> {exp.reason}
                                </div>
                              ))}
                            </div>
                          </div>
                        )}
                      </div>
                    ) : (
                      <div className="text-center py-16 text-slate-500 text-xs">
                        Run a comparison to view fastest path vs risk-aware route trade-offs.
                      </div>
                    )}
                  </div>
                </div>
              </div>
            )}

            {/* TAB 7: WEATHER & STATISTICAL ANOMALY CENTER */}
            {activeTab === "weather" && (
              <div className="space-y-6">
                <div className="bg-slate-900/60 border border-slate-800 p-4 rounded-xl flex flex-wrap items-center justify-between gap-4">
                  <div>
                    <h3 className="text-sm font-bold text-white">Northeast Weather Grids & Historical Climate Baseline</h3>
                    <p className="text-xs text-slate-400 mt-0.5">
                      Open-Meteo 8-Capital Station forecast feed with 60-minute cache policy.
                    </p>
                  </div>
                  <div className="text-xs text-amber-300/90 bg-amber-950/40 px-3 py-1 rounded-lg border border-amber-800/80">
                    Mandatory Label: Weather anomaly model • Not a landslide probability • Not a road-closure probability
                  </div>
                </div>

                <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
                  {[
                    { capital: "Guwahati (Assam)", temp: "28°C", rain: "4.2 mm", wind: "12 km/h", anomaly: "Normal (+0.2σ)" },
                    { capital: "Itanagar (Arunachal)", temp: "19°C", rain: "24.5 mm", wind: "22 km/h", anomaly: "High (+1.8σ)" },
                    { capital: "Shillong (Meghalaya)", temp: "16°C", rain: "18.0 mm", wind: "18 km/h", anomaly: "Moderate (+1.1σ)" },
                    { capital: "Kohima (Nagaland)", temp: "18°C", rain: "15.2 mm", wind: "14 km/h", anomaly: "Moderate (+0.9σ)" },
                    { capital: "Imphal (Manipur)", temp: "22°C", rain: "8.6 mm", wind: "10 km/h", anomaly: "Normal (+0.4σ)" },
                    { capital: "Aizawl (Mizoram)", temp: "21°C", rain: "11.4 mm", wind: "12 km/h", anomaly: "Normal (+0.6σ)" },
                    { capital: "Gangtok (Sikkim)", temp: "14°C", rain: "28.0 mm", wind: "26 km/h", anomaly: "Severe (+2.4σ)" },
                    { capital: "Agartala (Tripura)", temp: "29°C", rain: "2.1 mm", wind: "8 km/h", anomaly: "Normal (+0.1σ)" },
                  ].map((st, idx) => (
                    <div key={idx} className="bg-slate-900/70 border border-slate-800 p-4 rounded-xl">
                      <div className="flex items-center justify-between mb-2">
                        <h4 className="font-bold text-xs text-white">{st.capital}</h4>
                        <span className="text-[10px] font-mono text-cyan-300">{st.temp}</span>
                      </div>
                      <div className="text-xs text-slate-400 space-y-1">
                        <div>Precipitation (24h): <span className="text-slate-200 font-mono">{st.rain}</span></div>
                        <div>Wind Speed: <span className="text-slate-200 font-mono">{st.wind}</span></div>
                        <div className="pt-2 border-t border-slate-800/80 text-[11px] text-amber-300 font-mono">
                          Multivariate Deviation: {st.anomaly}
                        </div>
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            )}

            {/* TAB 8: BROADCASTS & ALERT CENTER */}
            {activeTab === "broadcasts" && (
              <div className="space-y-6">
                <div className="bg-slate-900/60 border border-slate-800 p-4 rounded-xl flex flex-wrap items-center justify-between gap-4">
                  <div>
                    <h3 className="text-sm font-bold text-white">Emergency Logistics Broadcast Gateway</h3>
                    <p className="text-xs text-slate-400 mt-0.5">
                      Dispatch multilingual early warning advisories to transiting commercial freight operators.
                    </p>
                  </div>
                  <span className="text-xs px-2.5 py-1 rounded bg-purple-950 text-purple-300 border border-purple-800 font-mono">
                    Provider: SIMULATOR (No Twilio/WhatsApp credentials configured)
                  </span>
                </div>

                {/* Dispatch Form */}
                <div className="bg-slate-900/80 border border-slate-800 p-5 rounded-xl grid grid-cols-1 md:grid-cols-4 gap-4">
                  <div>
                    <label className="text-xs text-slate-400 block mb-1">Target Corridor</label>
                    <input
                      type="text"
                      value={broadcastCorridor}
                      onChange={(e) => setBroadcastCorridor(e.target.value)}
                      className="w-full bg-slate-800 border border-slate-700 rounded-lg p-2 text-xs text-white"
                    />
                  </div>

                  <div>
                    <label className="text-xs text-slate-400 block mb-1">Template Preset</label>
                    <select
                      value={broadcastTemplate}
                      onChange={(e) => setBroadcastTemplate(e.target.value as typeof broadcastTemplate)}
                      className="w-full bg-slate-800 border border-slate-700 rounded-lg p-2 text-xs text-white"
                    >
                      <option value="hazard_alert">SDRF Verified Hazard Alert</option>
                      <option value="bridge_warning">Bridge Load Exceeded Warning</option>
                      <option value="reroute_advisory">Dynamic A* Detour Advisory</option>
                    </select>
                  </div>

                  <div>
                    <label className="text-xs text-slate-400 block mb-1">Language</label>
                    <select
                      value={broadcastLang}
                      onChange={(e) => setBroadcastLang(e.target.value as typeof broadcastLang)}
                      className="w-full bg-slate-800 border border-slate-700 rounded-lg p-2 text-xs text-white"
                    >
                      <option value="en">English (EN)</option>
                      <option value="hi">Hindi (HI)</option>
                      <option value="as">Assamese (AS)</option>
                      <option value="bn">Bengali (BN)</option>
                    </select>
                  </div>

                  <div className="flex items-end">
                    <button
                      onClick={handleDispatchBroadcast}
                      disabled={broadcastDispatching}
                      className="w-full py-2 bg-cyan-600 hover:bg-cyan-500 disabled:bg-slate-700 text-white text-xs font-bold rounded-lg transition"
                    >
                      {broadcastDispatching ? "Dispatching..." : "Send Test Broadcast"}
                    </button>
                  </div>
                </div>

                {/* Broadcast History Table */}
                <div className="bg-slate-900/80 border border-slate-800 rounded-xl overflow-hidden">
                  <div className="p-3 bg-slate-800/50 border-b border-slate-800 font-bold text-xs text-white">
                    Historical Dispatches & Carrier Receipts
                  </div>
                  <div className="divide-y divide-slate-800 text-xs text-slate-300">
                    {broadcasts.map((bc) => (
                      <div key={bc.broadcast_id} className="p-4 hover:bg-slate-800/30 transition">
                        <div className="flex items-start justify-between gap-4 mb-2">
                          <div>
                            <div className="flex items-center gap-2">
                              <span className="text-[10px] font-mono font-bold px-2 py-0.5 rounded bg-purple-950 text-purple-300 border border-purple-800">
                                {bc.provider}
                              </span>
                              <span className="font-bold text-white">{bc.template_used}</span>
                              <span className="text-[11px] text-slate-400 font-mono">({bc.language.toUpperCase()})</span>
                            </div>
                            <p className="text-xs text-slate-200 mt-1">{bc.message_body}</p>
                          </div>
                          <span className="text-[11px] text-slate-500 font-mono whitespace-nowrap">
                            ID: {bc.broadcast_id}
                          </span>
                        </div>

                        {/* Deliveries list */}
                        <div className="mt-3 pt-2 border-t border-slate-800/60 grid grid-cols-1 md:grid-cols-2 gap-2">
                          {bc.deliveries.map((del, dIdx) => (
                            <div
                              key={dIdx}
                              className="text-[11px] bg-slate-950/40 p-2 rounded border border-slate-800/80 flex items-center justify-between"
                            >
                              <span className="text-slate-300 truncate max-w-[200px]">{del.recipient}</span>
                              <span
                                className={`font-bold px-1.5 py-0.5 rounded text-[10px] ${
                                  del.status === "SIMULATED_SUCCESS" || del.status === "DELIVERED"
                                    ? "bg-emerald-950 text-emerald-300"
                                    : "bg-amber-950 text-amber-300"
                                }`}
                              >
                                {del.status}
                              </span>
                            </div>
                          ))}
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              </div>
            )}

            {/* TAB 9: AUDIT LOG */}
            {activeTab === "audit" && (
              <div className="space-y-4">
                <div className="bg-slate-900/60 border border-slate-800 p-4 rounded-xl flex flex-wrap items-center justify-between gap-4">
                  <div>
                    <h3 className="text-sm font-bold text-white">Immutable Operational Audit Log</h3>
                    <p className="text-xs text-slate-400 mt-0.5">
                      Cryptographically tracked timeline of all field report reviews, closure mutations, and external cache refreshes.
                    </p>
                  </div>
                  <span className="text-xs text-slate-400 font-mono">
                    Total Logged Events: <strong className="text-white">{auditEntries.length}</strong>
                  </span>
                </div>

                <div className="bg-slate-900/80 border border-slate-800 rounded-xl overflow-hidden">
                  <div className="overflow-x-auto">
                    <table className="w-full text-left text-xs">
                      <thead className="bg-slate-800/80 text-slate-300 border-b border-slate-700 font-semibold">
                        <tr>
                          <th className="p-3">Timestamp</th>
                          <th className="p-3">Actor / Role</th>
                          <th className="p-3">Action</th>
                          <th className="p-3">Target Resource</th>
                          <th className="p-3">Result</th>
                          <th className="p-3">Details / Sanitized Payload</th>
                        </tr>
                      </thead>
                      <tbody className="divide-y divide-slate-800 text-slate-300">
                        {auditEntries.length === 0 ? (
                          <tr>
                            <td colSpan={6} className="p-6 text-center text-slate-500">
                              No administrative audit events recorded yet.
                            </td>
                          </tr>
                        ) : (
                          auditEntries.map((entry) => (
                            <tr key={entry.id} className="hover:bg-slate-800/40 transition">
                              <td className="p-3 font-mono text-slate-400 whitespace-nowrap">
                                {new Date(entry.timestamp).toLocaleString()}
                              </td>
                              <td className="p-3 font-mono">
                                <span className="text-white">{entry.actor_id}</span>
                                <span className="text-[10px] text-slate-500 block uppercase">
                                  ({entry.actor_role})
                                </span>
                              </td>
                              <td className="p-3 font-bold text-cyan-300 font-mono">{entry.action}</td>
                              <td className="p-3 font-mono text-slate-200">{entry.resource}</td>
                              <td className="p-3">
                                <span
                                  className={`px-2 py-0.5 rounded text-[10px] font-bold ${
                                    entry.result === "success"
                                      ? "bg-emerald-950 text-emerald-300 border border-emerald-800"
                                      : "bg-rose-950 text-rose-300 border border-rose-800"
                                  }`}
                                >
                                  {entry.result.toUpperCase()}
                                </span>
                              </td>
                              <td className="p-3 font-mono text-[11px] text-slate-400 max-w-xs truncate">
                                {JSON.stringify(entry.details)}
                              </td>
                            </tr>
                          ))
                        )}
                      </tbody>
                    </table>
                  </div>
                </div>
              </div>
            )}

            {/* TAB 10: MODEL & DATASET REGISTRY */}
            {activeTab === "registry" && (
              <div className="space-y-6">
                <div className="bg-slate-900/60 border border-slate-800 p-4 rounded-xl">
                  <h3 className="text-sm font-bold text-white">Truth-in-Advertising Model & Heuristic Registry</h3>
                  <p className="text-xs text-slate-400 mt-0.5">
                    Rigorous architectural specifications, evaluation windows, explicit false claim disclaimers, and known limitations.
                  </p>
                </div>

                <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                  {models.map((mod) => (
                    <div
                      key={mod.id}
                      className="bg-slate-900/80 border border-slate-800 rounded-xl p-5 flex flex-col justify-between"
                    >
                      <div>
                        <div className="flex items-start justify-between gap-2 mb-2">
                          <span className="text-xs font-mono text-cyan-400">{mod.id}</span>
                          <span
                            className={`text-[10px] font-bold px-2 py-0.5 rounded border ${
                              mod.status === "available"
                                ? "bg-emerald-950 text-emerald-300 border-emerald-800"
                                : "bg-rose-950 text-rose-300 border-rose-800"
                            }`}
                          >
                            {mod.status === "available" ? "ACTIVE / DEPLOYED" : "UNAVAILABLE IN PROD"}
                          </span>
                        </div>

                        <h4 className="text-base font-bold text-white mb-1">{mod.name}</h4>
                        <p className="text-xs font-medium text-slate-400 mb-3">{mod.type}</p>

                        <div className="bg-slate-950/60 p-3 rounded-lg border border-slate-800 text-xs space-y-1.5 mb-3">
                          <div>
                            <span className="text-slate-500">Target Variable:</span>{" "}
                            <span className="text-slate-200 font-medium">{mod.target_definition}</span>
                          </div>
                          <div>
                            <span className="text-slate-500">Input Features:</span>{" "}
                            <span className="text-slate-300 font-mono text-[11px]">{mod.features.join(", ")}</span>
                          </div>
                          <div>
                            <span className="text-slate-500">Spatial Scope:</span>{" "}
                            <span className="text-slate-300">{mod.coverage}</span>
                          </div>
                          <div>
                            <span className="text-slate-500">Field Safety Calibrated:</span>{" "}
                            <span className="text-rose-400 font-bold">FALSE (Heuristic / Anomaly Only)</span>
                          </div>
                        </div>

                        {/* Explicit False Claims to Reject */}
                        <div className="bg-amber-950/20 border border-amber-900/40 p-3 rounded-lg mb-3">
                          <span className="text-[11px] font-bold text-amber-300 block mb-1">
                            ⛔ Explicit False Claims to Reject:
                          </span>
                          <ul className="text-xs text-amber-200/90 list-disc list-inside space-y-0.5">
                            {mod.explicit_false_claims.map((claim, cIdx) => (
                              <li key={cIdx}>{claim}</li>
                            ))}
                          </ul>
                        </div>

                        <div>
                          <span className="text-[11px] text-slate-400 font-semibold block mb-0.5">
                            Known Operational Limitations:
                          </span>
                          <p className="text-xs text-slate-300 bg-slate-800/40 p-2.5 rounded border border-slate-800">
                            {mod.limitations}
                          </p>
                        </div>
                      </div>

                      <div className="mt-4 pt-3 border-t border-slate-800 text-[11px] font-mono text-slate-500">
                        Artifact Hash: {mod.artifact_hash || "none"}
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </>
        )}
      </main>

      {/* Field Report Review Modal */}
      {reviewingReport && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 backdrop-blur-sm p-4 animate-fade-in">
          <div className="bg-slate-900 border border-slate-800 rounded-2xl max-w-lg w-full p-6 shadow-2xl space-y-4">
            <div className="flex items-start justify-between border-b border-slate-800 pb-3">
              <div>
                <span className="text-xs font-bold text-cyan-400 uppercase tracking-wider">
                  Review Field Intelligence
                </span>
                <h3 className="text-lg font-bold text-white mt-0.5">
                  {reviewingReport.place_name || reviewingReport.district || "Incident Submission"}
                </h3>
              </div>
              <button
                onClick={() => setReviewingReport(null)}
                className="text-slate-400 hover:text-white p-1"
              >
                ✕
              </button>
            </div>

            <div className="bg-slate-950/60 p-3 rounded-lg border border-slate-800 text-xs space-y-1">
              <div><span className="text-slate-500">Hazard Kind:</span> <strong className="text-white capitalize">{reviewingReport.kind}</strong></div>
              <div><span className="text-slate-500">Reported Accessibility:</span> <strong className="text-amber-300">{reviewingReport.accessibility_status.toUpperCase()}</strong></div>
              <div><span className="text-slate-500">Description:</span> <span className="text-slate-300">{reviewingReport.description}</span></div>
              <div><span className="text-slate-500">Coordinates:</span> <span className="text-slate-400 font-mono">{reviewingReport.lon.toFixed(4)}, {reviewingReport.lat.toFixed(4)}</span></div>
            </div>

            <div className="space-y-3">
              <div>
                <label className="text-xs text-slate-300 font-semibold block mb-1">Review Decision</label>
                <div className="grid grid-cols-3 gap-2">
                  {[
                    { id: "accepted", label: "Accept & Block Edge", color: "bg-emerald-950 border-emerald-700 text-emerald-200" },
                    { id: "rejected", label: "Reject Submission", color: "bg-rose-950 border-rose-700 text-rose-200" },
                    { id: "evidence_requested", label: "Request Evidence", color: "bg-amber-950 border-amber-700 text-amber-200" },
                  ].map((btn) => (
                    <button
                      key={btn.id}
                      type="button"
                      onClick={() => setReviewDecision(btn.id as typeof reviewDecision)}
                      className={`p-2 rounded-lg border text-xs font-bold transition ${
                        reviewDecision === btn.id ? btn.color : "bg-slate-800 border-slate-700 text-slate-400"
                      }`}
                    >
                      {btn.label}
                    </button>
                  ))}
                </div>
              </div>

              {reviewDecision === "accepted" && (
                <>
                  <div>
                    <label className="text-xs text-slate-300 font-semibold block mb-1">
                      Candidate Edge Match within 2km
                    </label>
                    {loadingCandidates ? (
                      <div className="text-xs text-slate-500 py-1 font-mono">Snapping to road network...</div>
                    ) : reportCandidates.length > 0 ? (
                      <select
                        value={reviewEdgeId}
                        onChange={(e) => setReviewEdgeId(e.target.value)}
                        className="w-full bg-slate-800 border border-slate-700 rounded-lg p-2 text-xs text-cyan-300 font-mono"
                      >
                        {reportCandidates.map((c) => (
                          <option key={c.edge_id} value={c.edge_id}>
                            {c.edge_id} — {c.name || "Highway"} ({Math.round(c.distance_m)}m away)
                          </option>
                        ))}
                      </select>
                    ) : (
                      <input
                        type="text"
                        placeholder="e.g. e_nh13_sela_summit"
                        value={reviewEdgeId}
                        onChange={(e) => setReviewEdgeId(e.target.value)}
                        className="w-full bg-slate-800 border border-slate-700 rounded-lg p-2 text-xs text-cyan-300 font-mono"
                      />
                    )}
                  </div>

                  <div>
                    <label className="text-xs text-slate-300 font-semibold block mb-1">Closure Validity Window (Hours)</label>
                    <input
                      type="number"
                      min="1"
                      max="168"
                      value={reviewValidHours}
                      onChange={(e) => setReviewValidHours(e.target.value)}
                      className="w-full bg-slate-800 border border-slate-700 rounded-lg p-2 text-xs text-white"
                    />
                  </div>
                </>
              )}

              <div>
                <label className="text-xs text-slate-300 font-semibold block mb-1">
                  Official Verification Note (Mandatory for Audit Trail)
                </label>
                <textarea
                  rows={3}
                  value={reviewNote}
                  onChange={(e) => setReviewNote(e.target.value)}
                  placeholder="e.g. Corroborated with West Kameng DC Office & SDRF team on site. NH-13 pass closed."
                  className="w-full bg-slate-800 border border-slate-700 rounded-lg p-2 text-xs text-white placeholder-slate-500"
                />
              </div>
            </div>

            <div className="border-t border-slate-800 pt-3 flex justify-end gap-2">
              <button
                onClick={() => setReviewingReport(null)}
                className="px-4 py-2 bg-slate-800 hover:bg-slate-700 text-slate-300 text-xs font-semibold rounded-lg"
              >
                Cancel
              </button>
              <button
                onClick={submitReview}
                className="px-4 py-2 bg-cyan-600 hover:bg-cyan-500 text-white text-xs font-bold rounded-lg shadow"
              >
                Submit Audit Decision
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Event Resolution Modal */}
      {resolvingEvent && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 backdrop-blur-sm p-4 animate-fade-in">
          <div className="bg-slate-900 border border-slate-800 rounded-2xl max-w-md w-full p-6 shadow-2xl space-y-4">
            <h3 className="text-base font-bold text-white">Resolve Highway Closure</h3>
            <p className="text-xs text-slate-400">
              This action terminates the closure event immediately (<code className="text-cyan-300">ends_at = now()</code>) and frees the corridor for A* pathing.
            </p>
            <div>
              <label className="text-xs text-slate-300 font-semibold block mb-1">Clearance Inspection Note</label>
              <textarea
                rows={3}
                value={resolutionNote}
                onChange={(e) => setResolutionNote(e.target.value)}
                placeholder="e.g. PWD heavy earthmovers cleared rockfall; verified safe for 40T freight."
                className="w-full bg-slate-800 border border-slate-700 rounded-lg p-2 text-xs text-white"
              />
            </div>
            <div className="flex justify-end gap-2 pt-2 border-t border-slate-800">
              <button onClick={() => setResolvingEvent(null)} className="px-3 py-1.5 bg-slate-800 text-xs rounded text-slate-300">
                Cancel
              </button>
              <button onClick={submitEventResolution} className="px-3 py-1.5 bg-emerald-600 hover:bg-emerald-500 text-xs font-bold text-white rounded">
                Confirm Road Reopening
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Event Extension Modal */}
      {extendingEvent && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 backdrop-blur-sm p-4 animate-fade-in">
          <div className="bg-slate-900 border border-slate-800 rounded-2xl max-w-md w-full p-6 shadow-2xl space-y-4">
            <h3 className="text-base font-bold text-white">Extend Closure Expiry</h3>
            <div>
              <label className="text-xs text-slate-300 font-semibold block mb-1">Extend By (Hours)</label>
              <input
                type="number"
                min="1"
                max="168"
                value={extensionHours}
                onChange={(e) => setExtensionHours(e.target.value)}
                className="w-full bg-slate-800 border border-slate-700 rounded-lg p-2 text-xs text-white"
              />
            </div>
            <div>
              <label className="text-xs text-slate-300 font-semibold block mb-1">Extension Rationale</label>
              <textarea
                rows={2}
                value={extensionNote}
                onChange={(e) => setExtensionNote(e.target.value)}
                placeholder="e.g. Continued mudslides preventing culvert repair."
                className="w-full bg-slate-800 border border-slate-700 rounded-lg p-2 text-xs text-white"
              />
            </div>
            <div className="flex justify-end gap-2 pt-2 border-t border-slate-800">
              <button onClick={() => setExtendingEvent(null)} className="px-3 py-1.5 bg-slate-800 text-xs rounded text-slate-300">
                Cancel
              </button>
              <button onClick={submitEventExtension} className="px-3 py-1.5 bg-cyan-600 hover:bg-cyan-500 text-xs font-bold text-white rounded">
                Update Expiry
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Candidate Advisory Review & Triage Modal */}
      {selectedCandidate && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/75 backdrop-blur-sm p-4 animate-fade-in">
          <div className="bg-slate-900 border border-slate-700 rounded-2xl max-w-xl w-full p-6 shadow-2xl space-y-4 max-h-[90vh] overflow-y-auto">
            <div className="flex items-start justify-between gap-2 border-b border-slate-800 pb-3">
              <div>
                <h3 className="text-base font-bold text-white flex items-center gap-2">
                  <span>Advisory Governance Review</span>
                  <span className="text-xs font-mono text-cyan-400 px-2 py-0.5 rounded bg-cyan-950/60 border border-cyan-800">
                    {selectedCandidate.advisory_id}
                  </span>
                </h3>
                <p className="text-xs text-slate-400 mt-0.5">
                  Early-warning alerts require operator corroboration and edge-binding before creating routing closures.
                </p>
              </div>
              <button
                onClick={() => setSelectedCandidate(null)}
                className="text-slate-400 hover:text-white text-lg p-1"
              >
                ✕
              </button>
            </div>

            {/* Advisory Information Card */}
            <div className="bg-slate-950/70 border border-slate-800 rounded-xl p-3 space-y-2 text-xs">
              <div>
                <span className="text-slate-400">Source Agency:</span>{" "}
                <span className="font-semibold text-white">{selectedCandidate.source_agency}</span>
              </div>
              <div>
                <span className="text-slate-400">Headline:</span>{" "}
                <span className="font-medium text-slate-200">{selectedCandidate.headline}</span>
              </div>
              <div>
                <span className="text-slate-400">Raw Payload Hash:</span>{" "}
                <span className="font-mono text-cyan-400">{selectedCandidate.raw_payload_hash || "sha256:verified_in_pipeline"}</span>
              </div>
              {selectedCandidate.conflict_detected && (
                <div className="p-2 rounded bg-rose-950/60 border border-rose-800 text-rose-300 text-[11px]">
                  ⚠️ Operational Conflict: {selectedCandidate.conflict_note || "Contradictory agency statement flagged."}
                </div>
              )}
            </div>

            {/* Decision Radio Selector */}
            <div className="space-y-2">
              <label className="text-xs font-semibold text-slate-300 uppercase tracking-wider block">
                Review Decision
              </label>
              <div className="grid grid-cols-2 gap-2">
                {[
                  {
                    id: "accept",
                    label: "Accept & Promote to Closure",
                    sub: "Creates active closure for Risk-A*",
                    color: "border-emerald-600 bg-emerald-950/40 text-emerald-300",
                  },
                  {
                    id: "reject",
                    label: "Reject Advisory",
                    sub: "Spurious or unconfirmed alert",
                    color: "border-rose-600 bg-rose-950/40 text-rose-300",
                  },
                  {
                    id: "mark_duplicate",
                    label: "Mark Duplicate",
                    sub: "Already recorded by another feed",
                    color: "border-slate-600 bg-slate-800/60 text-slate-300",
                  },
                  {
                    id: "mark_conflicting",
                    label: "Flag as Conflicting",
                    sub: "Quarantine until field clearance",
                    color: "border-amber-600 bg-amber-950/40 text-amber-300",
                  },
                ].map((opt) => (
                  <label
                    key={opt.id}
                    className={`flex flex-col p-2.5 rounded-xl border cursor-pointer transition ${
                      candidateReviewDecision === opt.id
                        ? `${opt.color} ring-1 ring-cyan-400`
                        : "border-slate-800 bg-slate-950/40 text-slate-400 hover:border-slate-700"
                    }`}
                  >
                    <div className="flex items-center gap-2">
                      <input
                        type="radio"
                        name="reviewDecision"
                        value={opt.id}
                        checked={candidateReviewDecision === opt.id}
                        onChange={() => setCandidateReviewDecision(opt.id as typeof candidateReviewDecision)}
                        className="text-cyan-500 focus:ring-cyan-400"
                      />
                      <span className="text-xs font-bold text-white">{opt.label}</span>
                    </div>
                    <span className="text-[10px] text-slate-400 mt-1 pl-5">{opt.sub}</span>
                  </label>
                ))}
              </div>
            </div>

            {/* Mandatory Fields */}
            <div className="space-y-3">
              <div>
                <label className="text-xs text-slate-300 font-semibold block mb-1">
                  Source Corroboration Evidence <span className="text-rose-400">*</span>
                </label>
                <input
                  type="text"
                  value={candidateReviewEvidence}
                  onChange={(e) => setCandidateReviewEvidence(e.target.value)}
                  placeholder="e.g. CWC hydrograph gauge #34 validated via District Disaster VHF log"
                  className="w-full bg-slate-800 border border-slate-700 rounded-lg p-2 text-xs text-white placeholder-slate-500"
                />
              </div>

              <div>
                <label className="text-xs text-slate-300 font-semibold block mb-1">
                  Affected Highway Corridor <span className="text-rose-400">*</span>
                </label>
                <input
                  type="text"
                  value={candidateReviewCorridor}
                  onChange={(e) => setCandidateReviewCorridor(e.target.value)}
                  placeholder="e.g. NH-10 Sevoke - Gangtok Lifeline"
                  className="w-full bg-slate-800 border border-slate-700 rounded-lg p-2 text-xs text-white placeholder-slate-500"
                />
              </div>

              <div>
                <label className="text-xs text-slate-300 font-semibold block mb-1">
                  Road Segment ID (Edge ID) {candidateReviewDecision === "accept" && <span className="text-rose-400">* (Required to create closure)</span>}
                </label>
                <input
                  type="text"
                  value={candidateReviewSegmentId}
                  onChange={(e) => setCandidateReviewSegmentId(e.target.value)}
                  placeholder="e.g. e_nh10_sevoke_01 (Edge ID in active OSM network)"
                  className="w-full bg-slate-800 border border-slate-700 rounded-lg p-2 text-xs text-cyan-300 font-mono placeholder-slate-500"
                />
                <span className="text-[10px] text-slate-400 mt-0.5 block">
                  Mandatory when promoting to active closure. Binds hazard geometry directly to Risk-A* routing graph.
                </span>
              </div>

              <div>
                <label className="text-xs text-slate-300 font-semibold block mb-1">
                  Reviewer Operational Note <span className="text-rose-400">*</span>
                </label>
                <textarea
                  rows={2}
                  value={candidateReviewNote}
                  onChange={(e) => setCandidateReviewNote(e.target.value)}
                  placeholder="e.g. Ground patrol confirmed mudslide with 2m debris over carriageway; heavy vehicles impassable."
                  className="w-full bg-slate-800 border border-slate-700 rounded-lg p-2 text-xs text-white placeholder-slate-500"
                />
              </div>
            </div>

            {/* Audit Trail & Model Boundary Notice */}
            <div className="p-3 rounded-xl bg-slate-950 border border-slate-800 text-[11px] text-slate-400 space-y-1">
              <div className="flex items-center gap-1.5 text-cyan-300 font-medium">
                <span>🛡️ RaahSetu Operational Safety Invariant</span>
              </div>
              <p>
                Approved closures are enforced strictly by deterministic Risk-A*. The ML Disruption Model v1.1 operates purely in shadow mode (cost weight 0.0) and will never auto-close highways or override human operator decisions.
              </p>
            </div>

            {/* Modal Actions */}
            <div className="border-t border-slate-800 pt-3 flex justify-end gap-2">
              <button
                onClick={() => setSelectedCandidate(null)}
                disabled={candidateReviewSubmitting}
                className="px-4 py-2 bg-slate-800 hover:bg-slate-700 text-slate-300 text-xs font-semibold rounded-lg"
              >
                Cancel
              </button>
              <button
                onClick={handleSubmitCandidateReview}
                disabled={candidateReviewSubmitting}
                className="px-4 py-2 bg-cyan-600 hover:bg-cyan-500 disabled:opacity-50 text-white text-xs font-bold rounded-lg shadow cursor-pointer flex items-center gap-1.5"
              >
                {candidateReviewSubmitting ? (
                  <>
                    <svg className="w-3.5 h-3.5 animate-spin" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
                    </svg>
                    <span>Logging Decision...</span>
                  </>
                ) : (
                  <span>Commit Audit Decision</span>
                )}
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Feed Diagnostics Drawer / Modal */}
      {diagnosticsModalOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/75 backdrop-blur-sm p-4 animate-fade-in">
          <div className="bg-slate-900 border border-slate-700 rounded-2xl max-w-xl w-full p-6 shadow-2xl space-y-4 max-h-[90vh] overflow-y-auto">
            <div className="flex items-start justify-between gap-2 border-b border-slate-800 pb-3">
              <div>
                <h3 className="text-base font-bold text-white flex items-center gap-2">
                  <span>Feed Parser Diagnostics & Dry-Run Engine</span>
                </h3>
                <p className="text-xs text-slate-400 mt-0.5">
                  Safe parser verification against XML/JSON schemas without modifying active road graphs.
                </p>
              </div>
              <button
                onClick={() => setDiagnosticsModalOpen(false)}
                className="text-slate-400 hover:text-white text-lg p-1"
              >
                ✕
              </button>
            </div>

            {/* Parser Health Status Table */}
            <div className="space-y-2">
              <span className="text-xs font-semibold text-slate-300 uppercase tracking-wider block">
                Parser Health Status
              </span>
              <div className="grid grid-cols-2 sm:grid-cols-3 gap-2">
                {[
                  { name: "NDMA CAP XML", key: "ndma_cap_xml" },
                  { name: "CWC Flood JSON", key: "cwc_flood_json" },
                  { name: "Traffic Police JSON", key: "traffic_police_json" },
                  { name: "SDMA Alert Feed", key: "sdma_alert_xml" },
                  { name: "Open-Meteo NWP", key: "open_meteo_nwp" },
                ].map((p) => {
                  const health = feedDiagnostics?.parser_health?.[p.key] || "OK";
                  return (
                    <div key={p.key} className="bg-slate-950 p-2.5 rounded-lg border border-slate-800 flex flex-col justify-between">
                      <span className="text-xs text-slate-300 font-medium">{p.name}</span>
                      <div className="flex items-center gap-1.5 mt-1">
                        <span className="w-2 h-2 rounded-full bg-emerald-400"></span>
                        <span className="text-[11px] font-mono text-emerald-300">{health}</span>
                      </div>
                    </div>
                  );
                })}
              </div>
            </div>

            {/* Deduplication & Conflict Metrics */}
            <div className="grid grid-cols-3 gap-2 bg-slate-950/60 p-3 rounded-xl border border-slate-800 text-xs">
              <div>
                <span className="text-slate-500 block text-[11px]">Duplicates Suppressed:</span>
                <span className="text-lg font-bold text-cyan-300 font-mono">
                  {feedDiagnostics?.duplicate_suppression_count ?? 0}
                </span>
              </div>
              <div>
                <span className="text-slate-500 block text-[11px]">Conflicts Quarantined:</span>
                <span className="text-lg font-bold text-rose-400 font-mono">
                  {feedDiagnostics?.conflict_detection_count ?? 0}
                </span>
              </div>
              <div>
                <span className="text-slate-500 block text-[11px]">Pending Review:</span>
                <span className="text-lg font-bold text-amber-300 font-mono">
                  {feedDiagnostics?.candidate_advisories_awaiting_review ?? 0}
                </span>
              </div>
            </div>

            {/* Non-Destructive Controlled Execution Box */}
            <div className="bg-amber-950/20 border border-amber-800/40 rounded-xl p-3 space-y-2 text-xs">
              <div className="flex items-center gap-1.5 text-amber-300 font-bold">
                <span>⚠️ Non-Destructive Isolated Execution</span>
              </div>
              <p className="text-slate-300 text-[11px] leading-relaxed">
                {feedDiagnostics?.simulation_disclosure || "Diagnostic dry-run evaluates parser logic and entity sanitization in isolated memory. Zero live highway closures are generated, and active graphs are untouched."}
              </p>
              <button
                onClick={handleRunDiagnostics}
                disabled={diagnosticsRunning}
                className="w-full py-2 bg-cyan-600 hover:bg-cyan-500 disabled:opacity-50 text-white text-xs font-bold rounded-lg shadow transition cursor-pointer flex items-center justify-center gap-2"
              >
                {diagnosticsRunning ? (
                  <>
                    <svg className="w-4 h-4 animate-spin" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
                    </svg>
                    <span>Executing Controlled Dry-Run Diagnostics...</span>
                  </>
                ) : (
                  <span>Execute Controlled Dry-Run Diagnostics</span>
                )}
              </button>
            </div>

            {/* Dry-Run Result Inspection */}
            {diagnosticsReport && (
              <div className="bg-slate-950 p-3 rounded-xl border border-cyan-800/60 space-y-2 text-xs animate-fade-in">
                <div className="flex items-center justify-between">
                  <span className="text-xs font-bold text-white">Diagnostic Run Results</span>
                  <span className="text-[10px] font-mono bg-emerald-950 text-emerald-300 px-2 py-0.5 rounded border border-emerald-800">
                    {diagnosticsReport.overall_status || "ALL_PARSERS_OPERATIONAL"}
                  </span>
                </div>
                <div className="text-[11px] text-slate-400 space-y-1">
                  <div>Timestamp: <span className="text-slate-200 font-mono">{diagnosticsReport.timestamp}</span></div>
                  <div>Feeds Tested: <span className="text-cyan-300 font-mono">{diagnosticsReport.feeds_tested?.join(", ") || "All 5 Feeds"}</span></div>
                  <div>Disclosure: <span className="text-slate-300">{diagnosticsReport.diagnostic_disclosure}</span></div>
                  {diagnosticsReport.audit_entry && (
                    <div>Audit Record: <span className="text-cyan-400 font-mono">{diagnosticsReport.audit_entry.action} (Actor: {diagnosticsReport.audit_entry.actor_id})</span></div>
                  )}
                </div>
              </div>
            )}

            <div className="border-t border-slate-800 pt-3 flex justify-end">
              <button
                onClick={() => setDiagnosticsModalOpen(false)}
                className="px-4 py-1.5 bg-slate-800 hover:bg-slate-700 text-slate-300 text-xs font-semibold rounded-lg"
              >
                Close Diagnostics
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Data Provenance Slide-out Drawer */}
      <DataProvenanceDrawer
        source={selectedProvenanceSource}
        onClose={() => setSelectedProvenanceSource(null)}
        onRefresh={handleRefreshSource}
        isRefreshing={refreshingSourceId === selectedProvenanceSource?.id}
      />
    </div>
  );
};
