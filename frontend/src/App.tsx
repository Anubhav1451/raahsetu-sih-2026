import { type FormEvent, lazy, Suspense, useEffect, useRef, useState } from "react";
import {
  Activity,
  ArrowDownUp,
  ArrowRight,
  ArrowUpRight,
  Check,
  ChevronRight,
  CloudRain,
  Compass,
  Database,
  Download,
  Focus,
  Info,
  Layers3,
  LoaderCircle,
  MapPinned,
  Navigation,
  Route as RouteIcon,
  ShieldCheck,
  SlidersHorizontal,
  Truck,
  X,
  AlertTriangle,
} from "lucide-react";
import {
  compareRoutes,
  createFieldReport,
  getBootstrap,
  getFieldReports,
  getAccessibilityEvents,
  getAlerts,
  getConnectivity,
  getFleetVehicles,
  getDeliveries,
  createDelivery,
  updateDelivery,
  sendFleetPosition,
  getNetwork,
  getTerrain,
  getLiveWeather,
  searchPlaces,
  signIn,
  signUp,
  getProfile,
  reviewFieldReport,
  uploadFieldReportAttachment,
  getRoadCandidates,
  refreshSession,
  AuthError,
} from "./api";
const TerrainMap = lazy(() => import("./TerrainMap"));
import type {
  Bootstrap,
  AuthSession,
  Comparison,
  ElevationGrid,
  FieldReport,
  AccessibilityEvent,
  Alert as AlertItem,
  ConnectivitySummary,
  VehicleAsset,
  DeliveryJob,
  RoadCandidate,
  Network,
  Route,
  RouteInput,
  Vehicle,
  Weather,
} from "./types";
import { dataUrlToFile, fileToDataUrl, listQueuedReports, queueReport, removeQueuedReport } from "./offlineQueue";

function RouteCard({
  route,
  selected,
  onSelect,
}: {
  route: Route;
  selected: boolean;
  onSelect: () => void;
}) {
  const safe = route.id === "risk_aware";
  return (
    <button
      className={`route-card ${safe ? "safe" : ""} ${selected ? "selected" : ""}`}
      onClick={onSelect}
    >
      <div className="route-card-heading">
        <span className="route-type">
          {safe ? <ShieldCheck size={18} /> : <Navigation size={17} />}
          {safe ? "Risk-aware route" : "Fastest estimate"}
        </span>
        <span className="radio-dot">{selected && <span />}</span>
      </div>
      {route.status === "available" ? (
        <>
          <div className="route-metrics">
            <strong>
              {route.duration_min.toFixed(1)}
              <small> min</small>
            </strong>
            <span>{route.distance_km.toFixed(1)} km</span>
          </div>
          <div className="risk-line">
            <span>Risk exposure</span>
            <b>
              {route.unknown_risk_segments ? (
                "Incomplete data"
              ) : (
                <>
                  {route.risk_exposure.toFixed(2)} <small>risk-km</small>
                </>
              )}
            </b>
          </div>
          <div className="risk-meter">
            <i style={{ width: `${route.mean_risk_score * 100}%` }} />
          </div>
          <div className="route-card-foot">
            <span>{route.high_risk_segments} high-risk segments</span>
            {safe && <span className="tiny-tag">A* route</span>}
          </div>
        </>
      ) : (
        <div className="unreachable">
          <AlertTriangle size={19} />
          <strong>No feasible route</strong>
          <span>Review closures or vehicle restrictions.</span>
        </div>
      )}
    </button>
  );
}

export default function App() {
  const [bootstrap, setBootstrap] = useState<Bootstrap | null>(null);
  const [datasetId, setDatasetId] = useState("demo");
  const [network, setNetwork] = useState<Network | null>(null);
  const [terrain, setTerrain] = useState<ElevationGrid | null>(null);
  const [origin, setOrigin] = useState("");
  const [destination, setDestination] = useState("");
  const [vehicle, setVehicle] = useState<Vehicle>("heavy");
  const [weather, setWeather] = useState<Weather>("normal");
  const [liveWeather, setLiveWeather] = useState<import("./types").LiveWeather | null>(null);
  const [aversion, setAversion] = useState(1.5);
  const [strict, setStrict] = useState(false);
  const [scenarioId, setScenarioId] = useState("none");
  const [result, setResult] = useState<Comparison | null>(null);
  const [busy, setBusy] = useState(true);
  const [error, setError] = useState("");
  const [selected, setSelected] = useState("risk_aware");
  const [mode, setMode] = useState<"3d" | "flat">("3d");
  const [reset, setReset] = useState(0);
  const [showRisk, setShowRisk] = useState(true);
  const [retry, setRetry] = useState(0);
  const [search, setSearch] = useState("");
  const [searchMessage, setSearchMessage] = useState("");
  const [searchResults, setSearchResults] = useState<
    import("./types").SearchResult[]
  >([]);
  const dialog = useRef<HTMLDialogElement>(null);
  const reportDialog = useRef<HTMLDialogElement>(null);
  const [reports, setReports] = useState<FieldReport[]>([]);
  const [events, setEvents] = useState<AccessibilityEvent[]>([]);
  const [alerts, setAlerts] = useState<AlertItem[]>([]);
  const [connectivity, setConnectivity] = useState<ConnectivitySummary[]>([]);
  const [showOperations, setShowOperations] = useState(false);
  const [operationsBusy, setOperationsBusy] = useState(false);
  const [operationsErrors, setOperationsErrors] = useState<Record<string, string>>({});
  const [operationsRefresh, setOperationsRefresh] = useState(0);
  const [operationsUpdated, setOperationsUpdated] = useState<string | null>(null);
  const [fleetVehicles, setFleetVehicles] = useState<VehicleAsset[]>([]);
  const [deliveries, setDeliveries] = useState<DeliveryJob[]>([]);
  const [deliveryStatusDraft, setDeliveryStatusDraft] = useState<Record<string, DeliveryJob["status"]>>({});
  const [deliveryBusy, setDeliveryBusy] = useState<string | null>(null);
  const [deliveryMessage, setDeliveryMessage] = useState("");
  const [operatorRegion, setOperatorRegion] = useState("");
  const [showDeliveryForm, setShowDeliveryForm] = useState(false);
  const [deliveryCreateBusy, setDeliveryCreateBusy] = useState(false);
  const [deliveryCreateMessage, setDeliveryCreateMessage] = useState("");
  const [deliveryForm, setDeliveryForm] = useState({ vehicle_id: "", commodity: "", origin_name: "", destination_name: "", eta_at: "" });
  const [fleetSelectedVehicle, setFleetSelectedVehicle] = useState("");
  const [locationMessage, setLocationMessage] = useState("");
  const [locationBusy, setLocationBusy] = useState(false);
  const [liveTracking, setLiveTracking] = useState(false);
  const gpsWatch = useRef<number | null>(null);
  const currentAccount = useRef<string | undefined>(undefined);
  const [alertLanguage, setAlertLanguage] = useState<"en" | "hi" | "as">("en");
  const [notificationMessage, setNotificationMessage] = useState("");
  const [reportBusy, setReportBusy] = useState(false);
  const [reportMessage, setReportMessage] = useState("");
  const [evidenceFile, setEvidenceFile] = useState<File | null>(null);
  const [queuedReports, setQueuedReports] = useState(0);
  const [session, setSession] = useState<AuthSession | null>(() => {
    try {
      return JSON.parse(localStorage.getItem("raahsetu-session") || "null");
    } catch {
      return null;
    }
  });
  const [authForm, setAuthForm] = useState({ displayName: "", email: "", password: "" });
  currentAccount.current = session?.user?.id;
  const [authMode, setAuthMode] = useState<"signin" | "signup">("signin");
  const [authBusy, setAuthBusy] = useState(false);
  const [authMessage, setAuthMessage] = useState("");
  const regionCode = datasetId.startsWith("osm-guwahati")
    ? "assam"
    : datasetId === "demo"
      ? "assam"
      : datasetId.replace(/^osm-/, "");
  useEffect(() => {
    if (!session?.refresh_token) return;
    let cancelled = false;
    let timer: ReturnType<typeof setTimeout>;
    const renew = async () => {
      try {
        const fresh = await refreshSession(session.refresh_token);
        if (cancelled) return;
        if (!fresh.access_token || !fresh.refresh_token) throw new Error("Session renewal failed");
        fresh.expires_at ??= Math.floor(Date.now() / 1000) + fresh.expires_in;
        localStorage.setItem("raahsetu-session", JSON.stringify(fresh));
        setSession(fresh);
      } catch (error) {
        if (cancelled) return;
        if (error instanceof AuthError && [400, 401, 403].includes(error.status)) {
          localStorage.removeItem("raahsetu-session");
          setSession(null);
          setReports([]);
          setAuthMessage("Session expired. Please sign in again.");
          return;
        }
        setReportMessage("Session renewal failed. Check your connection or sign in again.");
        timer = setTimeout(renew, 30000);
      }
    };
    const remaining = (session.expires_at || 0) * 1000 - Date.now() - 60000;
    timer = setTimeout(renew, Math.max(0, Math.min(remaining, 2147483647)));
    return () => { cancelled = true; clearTimeout(timer); };
  }, [session]);

  useEffect(() => {
    getAccessibilityEvents(regionCode).then((payload) => setEvents(payload.events)).catch(() => setEvents([]));
  }, [regionCode]);
  useEffect(() => {
    const point = bootstrap?.locations.find((location) => location.id === bootstrap.dataset.default_origin) || bootstrap?.locations[0];
    if (!point) return;
    getLiveWeather(point.lat, point.lon).then(setLiveWeather).catch(() => setLiveWeather(null));
  }, [bootstrap]);
  useEffect(() => {
    let cancelled = false;
    setAlerts([]); setConnectivity([]); setFleetVehicles([]); setDeliveries([]); setDeliveryStatusDraft({}); setDeliveryMessage(""); setDeliveryCreateMessage(""); setFleetSelectedVehicle("");
    setOperationsErrors({}); setOperationsUpdated(null); setOperationsBusy(false);
    if (!session?.access_token || !showOperations) return;
    setOperationsBusy(true);
    Promise.allSettled([getAlerts(session.access_token), getConnectivity(session.access_token), getFleetVehicles(session.access_token), getDeliveries(session.access_token)])
      .then(([alertResult, stateResult, vehicleResult, deliveryResult]) => {
        if (cancelled) return;
        const errors: Record<string, string> = {};
        if (alertResult.status === "fulfilled") setAlerts(alertResult.value);
        else errors.alerts = "Alerts could not be loaded. Refresh to retry.";
        if (stateResult.status === "fulfilled") setConnectivity(stateResult.value);
        else errors.connectivity = "Regional reports are unavailable. Refresh to retry.";
        if (vehicleResult.status === "fulfilled") {
          setFleetVehicles(vehicleResult.value); setFleetSelectedVehicle(vehicleResult.value[0]?.id || "");
          setDeliveryForm((form) => ({ ...form, vehicle_id: form.vehicle_id || vehicleResult.value[0]?.id || "" }));
        } else errors.fleet = "Assigned vehicles could not be loaded. Refresh to retry.";
        if (deliveryResult.status === "fulfilled") {
          setDeliveries(deliveryResult.value);
          setDeliveryStatusDraft(Object.fromEntries(deliveryResult.value.map((delivery) => [delivery.id, delivery.status])));
        }
        else errors.deliveries = "Delivery status is unavailable. Refresh to retry.";
        setOperationsErrors(errors);
        setOperationsUpdated(new Date().toLocaleTimeString());
        setOperationsBusy(false);
      });
    return () => { cancelled = true; };
  }, [session?.access_token, showOperations, operationsRefresh]);
  const saveDeliveryStatus = async (delivery: DeliveryJob) => {
    if (!session?.access_token || deliveryBusy) return;
    const status = deliveryStatusDraft[delivery.id] || delivery.status;
    if (status === delivery.status) return;
    setDeliveryBusy(delivery.id); setDeliveryMessage("");
    try {
      const updated = await updateDelivery(session.access_token, delivery.id, { status, eta_at: delivery.eta_at });
      setDeliveries((items) => items.map((item) => item.id === updated.id ? updated : item));
      setDeliveryStatusDraft((items) => ({ ...items, [updated.id]: updated.status }));
      setDeliveryMessage("Delivery status updated.");
    } catch (cause) {
      setDeliveryMessage(cause instanceof Error ? cause.message : "Delivery update failed. Please retry.");
    } finally { setDeliveryBusy(null); }
  };
  const submitDelivery = async (event: FormEvent) => {
    event.preventDefault();
    if (!session?.access_token || deliveryCreateBusy) return;
    if (!deliveryForm.vehicle_id || !deliveryForm.commodity.trim() || !deliveryForm.origin_name.trim() || !deliveryForm.destination_name.trim()) {
      setDeliveryCreateMessage("Vehicle, commodity, origin and destination are required.");
      return;
    }
    setDeliveryCreateBusy(true); setDeliveryCreateMessage("");
    try {
      const created = await createDelivery(session.access_token, {
        vehicle_id: deliveryForm.vehicle_id,
        region_code: operatorRegion || fleetVehicles.find((vehicle) => vehicle.id === deliveryForm.vehicle_id)?.region_code || "assam",
        commodity: deliveryForm.commodity.trim(),
        origin_name: deliveryForm.origin_name.trim(),
        destination_name: deliveryForm.destination_name.trim(),
        eta_at: deliveryForm.eta_at ? new Date(deliveryForm.eta_at).toISOString() : null,
      });
      setDeliveries((items) => [created, ...items]);
      setDeliveryStatusDraft((items) => ({ ...items, [created.id]: created.status }));
      setDeliveryForm((form) => ({ ...form, commodity: "", origin_name: "", destination_name: "", eta_at: "" }));
      setDeliveryCreateMessage("Delivery created and added to the operations queue.");
    } catch (cause) {
      setDeliveryCreateMessage(cause instanceof Error ? cause.message : "Delivery creation failed. Please retry.");
    } finally { setDeliveryCreateBusy(false); }
  };
  const shareVehicleLocation = () => {
    if (!session?.access_token || !fleetSelectedVehicle || locationBusy) return;
    if (!navigator.geolocation) { setLocationMessage("Location is unavailable on this device."); return; }
    const accountId = session.user.id;
    setLocationBusy(true);
    setLocationMessage("Requesting GPS…");
    navigator.geolocation.getCurrentPosition(async (position) => {
      try {
        if (currentAccount.current !== accountId) return;
        await sendFleetPosition(session.access_token, { vehicle_id: fleetSelectedVehicle, recorded_at: new Date(position.timestamp).toISOString(), lon: position.coords.longitude, lat: position.coords.latitude, accuracy_m: position.coords.accuracy });
        if (currentAccount.current === accountId) setLocationMessage("Location shared securely.");
      } catch (cause) { if (currentAccount.current === accountId) setLocationMessage(cause instanceof Error ? cause.message : "Location update failed."); }
      finally { setLocationBusy(false); }
    }, () => { setLocationBusy(false); if (currentAccount.current === accountId) setLocationMessage("GPS permission was denied or unavailable."); }, { enableHighAccuracy: true, timeout: 10000, maximumAge: 30000 });
  };
  const stopLiveTracking = () => {
    if (gpsWatch.current !== null) navigator.geolocation.clearWatch(gpsWatch.current);
    gpsWatch.current = null; setLiveTracking(false); setLocationMessage("Live GPS sharing stopped.");
  };
  const enableBrowserNotifications = async () => {
    if (!("Notification" in window)) { setNotificationMessage("Browser notifications are unavailable on this device."); return; }
    const permission = await Notification.requestPermission();
    setNotificationMessage(permission === "granted" ? "Browser alerts enabled for this session." : "Notification permission was not granted.");
  };
  const startLiveTracking = () => {
    if (!session?.access_token || !fleetSelectedVehicle || liveTracking) return;
    if (!navigator.geolocation) { setLocationMessage("Location is unavailable on this device."); return; }
    const accountId = session.user.id;
    setLiveTracking(true); setLocationMessage("Requesting live GPS permission…");
    gpsWatch.current = navigator.geolocation.watchPosition(async (position) => {
      if (currentAccount.current !== accountId || !session?.access_token) return;
      try {
        await sendFleetPosition(session.access_token, { vehicle_id: fleetSelectedVehicle, recorded_at: new Date(position.timestamp).toISOString(), lon: position.coords.longitude, lat: position.coords.latitude, accuracy_m: position.coords.accuracy });
        setLocationMessage(`Live location shared · ±${Math.round(position.coords.accuracy)} m accuracy`);
      } catch (cause) { setLocationMessage(cause instanceof Error ? cause.message : "Live GPS update failed."); }
    }, () => { setLiveTracking(false); setLocationMessage("GPS permission was denied or became unavailable."); }, { enableHighAccuracy: true, timeout: 15000, maximumAge: 15000 });
  };
  useEffect(() => () => { if (gpsWatch.current !== null) navigator.geolocation.clearWatch(gpsWatch.current); }, []);
  const [operatorRole, setOperatorRole] = useState("");
  const [reviewNotes, setReviewNotes] = useState<Record<string, string>>({});
  const [reviewing, setReviewing] = useState<string | null>(null);
  const [candidates, setCandidates] = useState<Record<string, RoadCandidate[]>>({});
  const [selectedEdges, setSelectedEdges] = useState<Record<string, string>>({});
  useEffect(() => {
    let cancelled = false;
    setOperatorRole(""); setOperatorRegion("");
    if (session?.access_token) {
      getProfile(session.access_token)
        .then((profile) => { if (!cancelled) { setOperatorRole(profile.role); setOperatorRegion(profile.region_code || ""); } })
        .catch(() => {
          if (!cancelled) setReportMessage("Session could not be verified. Sign in again.");
        });
    }
    return () => { cancelled = true; };
  }, [session]);

  const moderateReport = async (id: string, decision: "accepted" | "rejected") => {
    if (!session || reviewing) return;
    setReviewing(id);
    try {
      const edgeId = selectedEdges[id];
      const updated = await reviewFieldReport(session.access_token, id, decision, reviewNotes[id]?.trim() || "", datasetId, edgeId);
      setReports((items) => items.map((item) => item.id === id ? updated : item));
      setReportMessage(`Report ${decision}. Road matching is a separate review step.`);
    } catch (cause) {
      setReportMessage(cause instanceof Error ? cause.message : "Review failed. Please retry.");
    } finally {
      setReviewing(null);
    }
  };

  useEffect(() => {
    if (!session?.access_token || !["reviewer", "admin"].includes(operatorRole)) return;
    reports.filter((report) => report.review_status === "pending").forEach((report) => {
      getRoadCandidates(session.access_token, report.id, datasetId)
        .then((payload) => {
          setCandidates((current) => ({ ...current, [report.id]: payload.candidates }));
          if (payload.candidates[0]) setSelectedEdges((current) => ({ ...current, [report.id]: current[report.id] || payload.candidates[0].edge_id }));
        })
        .catch(() => setCandidates((current) => ({ ...current, [report.id]: [] })));
    });
  }, [reports, session, operatorRole, datasetId]);
  const [reportForm, setReportForm] = useState({
    kind: "road_blocked",
    accessibility_status: "blocked",
    severity: 0.8,
    district: "",
    description: "",
  });
  const [runInput, setRunInput] = useState<RouteInput | null>(null);
  const scenario = bootstrap?.scenarios.find((s) => s.id === scenarioId);
  const closedIds = scenario?.closed_edge_ids ?? [];
  const reportLocation = bootstrap?.locations.find(
    (location) => location.id === origin,
  );

  const refreshQueueCount = () => listQueuedReports().then((items) => setQueuedReports(items.length)).catch(() => setQueuedReports(0));
  useEffect(() => { refreshQueueCount(); }, []);

  useEffect(() => {
    if (!session?.access_token || !navigator.onLine) return;
    let cancelled = false;
    const sync = async () => {
      const items = await listQueuedReports().catch(() => []);
      for (const item of items) {
        if (cancelled) return;
        try {
          const created = await createFieldReport(item.payload, session.access_token);
          if (item.evidence) {
            await uploadFieldReportAttachment(
              session.access_token,
              created.id,
              dataUrlToFile(item.evidence.dataUrl, item.evidence.name, item.evidence.type),
            );
          }
          await removeQueuedReport(item.id);
          setReports((current) => [created, ...current]);
        } catch {
          break;
        }
      }
      refreshQueueCount();
    };
    sync();
    window.addEventListener("online", sync);
    return () => { cancelled = true; window.removeEventListener("online", sync); };
  }, [session?.access_token]);

  const openReportDialog = () => {
    setReportMessage("");
    reportDialog.current?.showModal();
    if (session?.access_token) {
      getFieldReports(session.access_token, regionCode)
        .then(setReports)
        .catch((cause) => {
          setReports([]);
          setReportMessage(cause instanceof Error ? cause.message : "Reports unavailable.");
        });
    }
  };

  const submitAuth = async (event: FormEvent) => {
    event.preventDefault();
    setAuthBusy(true);
    setAuthMessage("");
    try {
      const authenticated = authMode === "signin"
        ? await signIn(authForm.email, authForm.password)
        : await signUp(authForm.email, authForm.password, authForm.displayName);
      if (!authenticated.access_token) {
        setAuthMessage("Check your email to confirm the account, then sign in.");
        setAuthMode("signin");
        return;
      }
      localStorage.setItem("raahsetu-session", JSON.stringify(authenticated));
      setSession(authenticated);
      setAuthMessage(`Signed in as ${authenticated.user.email ?? "field official"}.`);
      setReports(await getFieldReports(authenticated.access_token, regionCode));
    } catch (cause) {
      setAuthMessage(cause instanceof Error ? cause.message : "Authentication failed.");
    } finally {
      setAuthBusy(false);
    }
  };

  const signOut = () => {
    localStorage.removeItem("raahsetu-session");
    setSession(null);
    setReports([]);
    setAuthMessage("Signed out.");
  };

  const submitFieldReport = async (event: FormEvent) => {
    event.preventDefault();
    if (!reportLocation) {
      setReportMessage("Select a mapped origin before reporting an incident.");
      return;
    }
    if (!session?.access_token) {
      setReportMessage("Sign in before submitting a field report.");
      return;
    }
    setReportBusy(true);
    setReportMessage("");
    const now = new Date().toISOString();
    try {
      const created = await createFieldReport({
        client_report_id: `web-${crypto.randomUUID()}`,
        region_code: regionCode,
        district: reportForm.district || undefined,
        place_name: reportLocation.label,
        kind: reportForm.kind as import("./types").FieldReportInput["kind"],
        accessibility_status:
          reportForm.accessibility_status as import("./types").FieldReportInput["accessibility_status"],
        severity: reportForm.severity,
        lon: reportLocation.lon,
        lat: reportLocation.lat,
        description: reportForm.description,
        observed_at: now,
        details: { dataset_id: datasetId, source: "dashboard" },
      }, session.access_token);
      setReports((current) => [created, ...current]);
      setReportForm((current) => ({ ...current, description: "" }));
      if (evidenceFile) {
        await uploadFieldReportAttachment(session.access_token, created.id, evidenceFile);
        setEvidenceFile(null);
        setReportMessage("Report and evidence queued for official review.");
      } else {
        setReportMessage("Report queued for official review.");
      }
    } catch (cause) {
      const payload = {
        client_report_id: `web-${crypto.randomUUID()}`,
        region_code: regionCode,
        district: reportForm.district || undefined,
        place_name: reportLocation.label,
        kind: reportForm.kind as import("./types").FieldReportInput["kind"],
        accessibility_status: reportForm.accessibility_status as import("./types").FieldReportInput["accessibility_status"],
        severity: reportForm.severity, lon: reportLocation.lon, lat: reportLocation.lat,
        description: reportForm.description, observed_at: now,
        offline_created_at: now, details: { dataset_id: datasetId, source: "offline-dashboard" },
      };
      const isNetworkFailure = !navigator.onLine || cause instanceof TypeError || (cause instanceof Error && /network|fetch|failed to fetch/i.test(cause.message));
      if (isNetworkFailure) {
        try {
          await queueReport({
            id: payload.client_report_id,
            payload,
            queuedAt: now,
            evidence: evidenceFile ? { name: evidenceFile.name, type: evidenceFile.type, dataUrl: await fileToDataUrl(evidenceFile) } : undefined,
          });
          setQueuedReports((count) => count + 1);
          setReportForm((current) => ({ ...current, description: "" }));
          setEvidenceFile(null);
          setReportMessage("Offline: report saved on this device and will sync automatically.");
        } catch {
          setReportMessage("Offline storage is unavailable. Keep this report open and retry when connected.");
        }
      } else {
        setReportMessage(cause instanceof Error ? cause.message : "Report could not be submitted.");
      }
    } finally {
      setReportBusy(false);
    }
  };

  const chooseSearchResult = (
    item: import("./types").SearchResult,
    endpoint: "origin" | "destination",
  ) => {
    setBootstrap((current) =>
      current && current.locations.some((location) => location.id === item.id)
        ? current
        : current && { ...current, locations: [...current.locations, item] },
    );
    if (endpoint === "origin") setOrigin(item.id);
    else setDestination(item.id);
    setSearch("");
    setSearchResults([]);
  };

  useEffect(() => {
    let cancelled = false;
    setSearchResults([]);
    if (search.trim().length < 2) {
      setSearchMessage("");
      return;
    }
    setSearchMessage("Searching this road network…");
    const timer = window.setTimeout(() => {
      searchPlaces(search, datasetId)
        .then((value) => {
          if (cancelled) return;
          setSearchResults(value.results);
          setSearchMessage(value.results.length ? "Choose A for origin or B for destination." : "No matching places in this dataset. Try a nearby town or road.");
        })
        .catch(() => { if (!cancelled) setSearchMessage("Search unavailable. Edit your search to retry."); });
    }, 240);
    return () => { cancelled = true; window.clearTimeout(timer); };
  }, [search, datasetId]);

  useEffect(() => {
    let cancelled = false;
    setError("");
    setBusy(true);
    getBootstrap(datasetId)
      .then(async (boot) => {
        const [net, grid] = await Promise.all([
          getNetwork("normal", datasetId, boot.dataset.default_origin),
          getTerrain(datasetId),
        ]);
        return { boot, net, grid };
      })
      .then(({ boot, net, grid }) => {
        if (cancelled) return;
        setBootstrap(boot);
        setNetwork(net);
        setTerrain(grid);
        setOrigin(boot.dataset.default_origin);
        setDestination(boot.dataset.default_destination);
      })
      .catch((e) => {
        if (!cancelled) {
          setError(e.message || "Cannot connect to the routing service.");
          setBusy(false);
        }
      });
    return () => {
      cancelled = true;
    };
  }, [retry, datasetId]);

  useEffect(() => {
    if (!bootstrap || !origin || !destination) return;
    const controller = new AbortController();
    setBusy(true);
    setError("");
    setResult(null);
    const input: RouteInput = {
      dataset_id: datasetId,
      origin: { node_id: origin },
      destination: { node_id: destination },
      vehicle,
      weather,
      risk_aversion: aversion,
      strict_vehicle: strict,
      closed_edge_ids:
        bootstrap.scenarios.find((s) => s.id === scenarioId)?.closed_edge_ids ??
        [],
    };
    const timer = window.setTimeout(() => {
      const timeout = window.setTimeout(
        () => controller.abort("timeout"),
        20000,
      );
      Promise.all([
        compareRoutes(input, controller.signal),
        getNetwork(weather, datasetId, origin),
      ])
        .then(([comparison, net]) => {
          if (!controller.signal.aborted) {
            setResult(comparison);
            setNetwork(net);
            setRunInput(input);
          }
        })
        .catch((e) => {
          if (
            !controller.signal.aborted ||
            controller.signal.reason === "timeout"
          )
            setError(
              controller.signal.reason === "timeout"
                ? "Routing timed out. Please retry."
                : e.message || "Routing failed.",
            );
        })
        .finally(() => {
          window.clearTimeout(timeout);
          if (
            !controller.signal.aborted ||
            controller.signal.reason === "timeout"
          )
            setBusy(false);
        });
    }, 180);
    return () => {
      window.clearTimeout(timer);
      controller.abort();
    };
  }, [
    bootstrap,
    origin,
    destination,
    vehicle,
    weather,
    aversion,
    strict,
    scenarioId,
    datasetId,
  ]);

  function downloadComparison() {
    if (!result || !runInput) return;
    const blob = new Blob(
      [
        JSON.stringify(
          {
            exported_at: new Date().toISOString(),
            dataset: bootstrap?.dataset,
            request: runInput,
            result,
          },
          null,
          2,
        ),
      ],
      { type: "application/json" },
    );
    const url = URL.createObjectURL(blob);
    const anchor = document.createElement("a");
    anchor.href = url;
    anchor.download = "raahsetu-route-comparison.json";
    anchor.click();
    window.setTimeout(() => URL.revokeObjectURL(url), 1000);
  }
  const activeRoute = result?.routes.find((r) => r.id === selected);
  const selectedVehicle = bootstrap?.vehicles[vehicle];
  const reduction = result?.comparison?.exposure_reduction_pct;
  const localizedAlert = (alert: AlertItem) => {
    const labels = {
      en: { "route.blocked": "Road blocked", "route.restricted": "Road accessibility restricted" },
      hi: { "route.blocked": "सड़क बंद है", "route.restricted": "सड़क आवागमन सीमित है" },
      as: { "route.blocked": "পথ বন্ধ আছে", "route.restricted": "পথ চলাচল সীমিত" },
    } as const;
    return labels[alertLanguage][alert.message_key as keyof typeof labels.en] ?? alert.title;
  };

  return (
    <div className="app-shell">
      <aside className="rail" aria-label="Workspace navigation">
        <div className="brand-symbol" aria-label="RaahSetu">
          <RouteIcon size={27} strokeWidth={2.4} />
        </div>
        <button
          className="rail-button active"
          aria-label="Route planner"
          title="Route planner"
          onClick={() => document.getElementById("origin")?.focus()}
        >
          <MapPinned size={22} />
        </button>
        <button
          className="rail-button"
          aria-label="Data and evidence"
          title="Data and evidence"
          onClick={() => dialog.current?.showModal()}
        >
          <Database size={21} />
        </button>
        <button
          className="rail-button"
          aria-label="Report road incident"
          title="Report road incident"
          onClick={openReportDialog}
        >
          <AlertTriangle size={21} />
        </button>
        <div className="rail-bottom">
          <span className="team-avatar" title="SIH 2026 team">
            S6
          </span>
        </div>
      </aside>
      <div className="workspace">
        <header className="topbar">
          <a className="wordmark" href="/">
            Raah<span>Setu</span>
            <small>LOGISTICS INTELLIGENCE</small>
          </a>
          <div className="breadcrumb">
            <span>Workspace</span>
            <ChevronRight size={14} />
            <strong>Route planner</strong>
          </div>
          <div className="topbar-right">
            <span className="demo-pill">
              <i />
              {bootstrap?.dataset.is_synthetic === false
                ? "OSM network"
                : "Demo workspace"}
            </span>
            <span className="edition">SIH 2026</span>
          </div>
        </header>
        <main>
          <div className="page-heading">
            <div>
              <div className="eyebrow">NORTH EAST · CORRIDOR INTELLIGENCE</div>
              <h1>Plan with the road ahead in view.</h1>
              <p>Compare routes, inspect road evidence and coordinate essential supplies.</p>
            </div>
            <div className="heading-actions">
              <button className="button secondary" onClick={openReportDialog}>
                <AlertTriangle size={16} />
                Report incident
              </button>
              <button
                className="button secondary export-button"
                onClick={downloadComparison}
                disabled={!result || busy}
              >
                <Download size={16} />
                Export comparison
              </button>
            </div>
          </div>
          <div className="workspace-toolbar">
            <div className="workspace-context"><MapPinned size={19} aria-hidden="true" /><span><strong>{bootstrap?.dataset.title || "Loading road network"}</strong><small>{bootstrap?.dataset.is_synthetic ? "Synthetic sandbox · illustrative roads and hazards" : "OSM snapshot · risk evidence may be incomplete"}</small></span></div>
            <button className="button secondary" aria-expanded={showOperations} aria-controls="operations-panel" onClick={() => setShowOperations((value) => !value)}><Activity size={16} />Operations {showOperations ? "−" : "+"}</button>
          </div>
          {showOperations && <div id="operations-panel" className="operations-workspace">
            <div className="operations-heading"><div><h2>Field operations</h2><p>Account-scoped reports and vehicle sharing. Refresh for a new snapshot.</p></div>{session && <button className="button secondary" disabled={operationsBusy} onClick={() => setOperationsRefresh((value) => value + 1)}>{operationsBusy ? "Loading…" : "Refresh data"}</button>}</div>
            {!session ? <div className="operations-signin"><ShieldCheck size={28} /><div><strong>Your operations workspace</strong><p>Sign in to view reviewed alerts, regional reports and vehicles assigned to you.</p></div><button className="button primary" onClick={openReportDialog}>Sign in to operations</button></div> : <>
            <p className="operations-freshness" role="status">{operationsBusy ? "Loading your account data…" : operationsUpdated ? `Last checked ${operationsUpdated}${Object.keys(operationsErrors).length ? " · Some sources unavailable" : ""}` : "Awaiting data"}</p>
            <section className="operations-strip" aria-label="Operations snapshot" aria-busy={operationsBusy}>
              <div className="operations-alerts">
                <div className="panel-heading"><span><AlertTriangle size={18} /> Live alerts</span><span className="alert-tools"><select aria-label="Alert language" value={alertLanguage} onChange={(event) => setAlertLanguage(event.target.value as typeof alertLanguage)}><option value="en">EN</option><option value="hi">हिं</option><option value="as">অসমীয়া</option></select><button className="button compact" type="button" onClick={enableBrowserNotifications}>Notify</button><span className="step-chip">{alerts.length}</span></span></div>
                {alerts.slice(0, 3).map((alert) => (
                  <div className="operation-alert" key={alert.id}>
                    <i className={alert.severity >= 0.75 ? "critical" : "warning"} />
                    <span><strong>{localizedAlert(alert)}</strong><small>{alert.region_code} · {alert.alert_type.replaceAll("_", " ")}</small></span>
                  </div>
                ))}
                {operationsErrors.alerts ? <p className="source-error" role="alert">{operationsErrors.alerts}</p> : alerts.length === 0 && <small className="muted-copy">{operationsBusy ? "Checking alerts…" : "No active alerts returned for your account scope."}</small>}
                {notificationMessage && <small className="muted-copy" role="status">{notificationMessage}</small>}
              </div>
              <div className="connectivity-summary">
                <div className="panel-heading"><span><Activity size={18} /> Regional road reports</span><span className="step-chip">{connectivity.length}</span></div>
                <div className="connectivity-list">{connectivity.slice(0, 8).map((state) => <span key={state.region_code} className={`connectivity-chip ${state.blocked_events ? "blocked" : state.restricted_events ? "restricted" : "unknown"}`}><strong>{state.state_name}</strong><small>{state.active_events ? `${state.blocked_events} blocked · ${state.restricted_events} restricted` : "No active reports"}</small></span>)}</div>
                {operationsErrors.connectivity && <p className="source-error" role="alert">{operationsErrors.connectivity}</p>}
                <p className="muted-copy">Report counts do not establish whether every road in a state is accessible.</p>
              </div>
              <div className="fleet-share">
                {operationsErrors.fleet && <p className="source-error" role="alert">{operationsErrors.fleet}</p>}
                <div className="panel-heading"><span><Navigation size={18} /> Share vehicle GPS</span></div>
                {fleetVehicles.length > 0 ? <>
                  <select aria-label="Assigned vehicle" disabled={locationBusy} value={fleetSelectedVehicle} onChange={(event) => setFleetSelectedVehicle(event.target.value)}>{fleetVehicles.map((vehicle) => <option key={vehicle.id} value={vehicle.id}>{vehicle.registration} · {vehicle.vehicle_type}</option>)}</select>
                  <button className="button secondary" type="button" disabled={locationBusy} onClick={shareVehicleLocation}>{locationBusy ? "Sharing location…" : "Share current location"}</button>
                  <button className={`button ${liveTracking ? "danger" : "secondary"}`} type="button" disabled={locationBusy} onClick={liveTracking ? stopLiveTracking : startLiveTracking}>{liveTracking ? "Stop live sharing" : "Start live sharing"}</button>
                  <small className="muted-copy" role="status">{locationMessage || "One-shot or operator-controlled live updates. No hidden background tracking."}</small>
                </> : !operationsErrors.fleet && <small className="muted-copy">{operationsBusy ? "Loading assigned vehicles…" : "No assigned vehicle is provisioned for this account."}</small>}
              </div>
              <div className="delivery-status">
                <div className="panel-heading"><span><Truck size={18} /> Delivery status</span><span className="panel-heading-actions"><span className="step-chip">{deliveries.filter((delivery) => !["delivered", "cancelled"].includes(delivery.status)).length}</span><button className="button compact" type="button" onClick={() => { setShowDeliveryForm((value) => !value); setDeliveryCreateMessage(""); }}>{showDeliveryForm ? "Close" : "New delivery"}</button></span></div>
                {showDeliveryForm && <form className="delivery-form" onSubmit={submitDelivery}>
                  <select aria-label="Delivery vehicle" value={deliveryForm.vehicle_id} onChange={(event) => setDeliveryForm((form) => ({ ...form, vehicle_id: event.target.value }))} required>
                    <option value="">Select vehicle</option>
                    {fleetVehicles.map((vehicle) => <option key={vehicle.id} value={vehicle.id}>{vehicle.registration} · {vehicle.vehicle_type}</option>)}
                  </select>
                  <input aria-label="Commodity" placeholder="Commodity" value={deliveryForm.commodity} onChange={(event) => setDeliveryForm((form) => ({ ...form, commodity: event.target.value }))} required />
                  <input aria-label="Origin" placeholder="Origin" value={deliveryForm.origin_name} onChange={(event) => setDeliveryForm((form) => ({ ...form, origin_name: event.target.value }))} required />
                  <input aria-label="Destination" placeholder="Destination" value={deliveryForm.destination_name} onChange={(event) => setDeliveryForm((form) => ({ ...form, destination_name: event.target.value }))} required />
                  <input aria-label="Estimated arrival" type="datetime-local" value={deliveryForm.eta_at} onChange={(event) => setDeliveryForm((form) => ({ ...form, eta_at: event.target.value }))} />
                  <button className="button primary" type="submit" disabled={deliveryCreateBusy || fleetVehicles.length === 0}>{deliveryCreateBusy ? "Creating…" : "Create delivery"}</button>
                  {deliveryCreateMessage && <small className="muted-copy" role="status">{deliveryCreateMessage}</small>}
                </form>}
                {operationsErrors.deliveries ? <p className="source-error" role="alert">{operationsErrors.deliveries}</p> : deliveries.length === 0 ? <small className="muted-copy">{operationsBusy ? "Loading deliveries…" : "No delivery jobs assigned to your account."}</small> : <div className="delivery-list">{deliveries.slice(0, 3).map((delivery) => <article className="delivery-item" key={delivery.id}><div><strong>{delivery.commodity}</strong><small>{delivery.origin_name} → {delivery.destination_name}</small></div><span className={`delivery-badge ${delivery.status}`}>{delivery.status.replaceAll("_", " ")}</span>{delivery.eta_at && <small className="delivery-eta">ETA {new Date(delivery.eta_at).toLocaleString([], { dateStyle: "medium", timeStyle: "short" })}</small>}<div className="delivery-actions"><select aria-label={`Status for ${delivery.commodity}`} value={deliveryStatusDraft[delivery.id] || delivery.status} disabled={deliveryBusy === delivery.id} onChange={(event) => setDeliveryStatusDraft((items) => ({ ...items, [delivery.id]: event.target.value as DeliveryJob["status"] }))}><option value="planned">Planned</option><option value="en_route">En route</option><option value="delayed">Delayed</option><option value="delivered">Delivered</option><option value="cancelled">Cancelled</option></select><button className="button secondary" type="button" disabled={deliveryBusy === delivery.id || (deliveryStatusDraft[delivery.id] || delivery.status) === delivery.status} onClick={() => saveDeliveryStatus(delivery)}>{deliveryBusy === delivery.id ? "Saving…" : "Save"}</button></div></article>)}</div>}
                {deliveryMessage && <small className="muted-copy" role="status">{deliveryMessage}</small>}
              </div>
            </section></>}
          </div>}
          <div className="planner-grid">
            <section className="planner-panel" aria-label="Journey settings">
              <div className="panel-heading">
                <span>
                  <RouteIcon size={19} />
                  Plan a journey
                </span>
                <span className="step-chip">01</span>
              </div>
              <label className="field-label" htmlFor="dataset">
                Road network
              </label>
              <select
                id="dataset"
                className="full-select dataset-select"
                value={datasetId}
                onChange={(e) => {
                  setBootstrap(null);
                  setNetwork(null);
                  setResult(null);
                  setOrigin("");
                  setDestination("");
                  setScenarioId("none");
                  setDatasetId(e.target.value);
                  setReset((r) => r + 1);
                }}
              >
                {(
                  bootstrap?.available_datasets ?? [
                    {
                      id: datasetId,
                      label: "Loading network…",
                      is_synthetic: true,
                    },
                  ]
                ).map((d) => (
                  <option key={d.id} value={d.id}>
                    {d.label}
                  </option>
                ))}
              </select>
              <div className="place-search">
                <label htmlFor="place-search">SEARCH ROAD OR PLACE</label>
                <input
                  id="place-search"
                  value={search}
                  onChange={(e) => setSearch(e.target.value)}
                  placeholder="City, village, hospital or road"
                  aria-describedby="search-feedback"
                />
                <small id="search-feedback" className="search-feedback" role="status">{searchMessage}</small>
                {search.trim().length >= 2 && searchResults.length > 0 && (
                  <div className="search-results">
                    {searchResults.map((item) => (
                      <div
                        className="search-result"
                        key={`${item.kind}-${item.id}`}
                      >
                        <span>
                          <b>{item.label}</b>
                          <small>
                            {item.detail ?? item.kind} · {item.lat.toFixed(4)},{" "}
                            {item.lon.toFixed(4)}
                          </small>
                        </span>
                        <button
                          aria-label={`Set ${item.label} as origin`}
                          onClick={() => chooseSearchResult(item, "origin")}
                        >
                          A
                        </button>
                        <button
                          aria-label={`Set ${item.label} as destination`}
                          onClick={() =>
                            chooseSearchResult(item, "destination")
                          }
                        >
                          B
                        </button>
                      </div>
                    ))}
                  </div>
                )}
              </div>
              <div className="journey-inputs">
                <div className="journey-track">
                  <i>A</i>
                  <span />
                  <i>B</i>
                </div>
                <div className="journey-fields">
                  <label htmlFor="origin">ORIGIN</label>
                  <select
                    id="origin"
                    value={origin}
                    onChange={(e) => setOrigin(e.target.value)}
                    disabled={!bootstrap}
                  >
                    {bootstrap?.locations.map((n) => (
                      <option key={n.id} value={n.id}>
                        {n.label}
                      </option>
                    ))}
                  </select>
                  <div className="input-divider" />
                  <label htmlFor="destination">DESTINATION</label>
                  <select
                    id="destination"
                    value={destination}
                    onChange={(e) => setDestination(e.target.value)}
                    disabled={!bootstrap}
                  >
                    {bootstrap?.locations.map((n) => (
                      <option key={n.id} value={n.id}>
                        {n.label}
                      </option>
                    ))}
                  </select>
                </div>
                <button
                  className="swap-button icon-button"
                  aria-label="Swap origin and destination"
                  disabled={!bootstrap}
                  onClick={() => {
                    setOrigin(destination);
                    setDestination(origin);
                  }}
                >
                  <ArrowDownUp size={15} />
                </button>
              </div>
              <label className="field-label" htmlFor="vehicle">
                <Truck size={16} />
                Vehicle profile
              </label>
              <select
                className="full-select"
                id="vehicle"
                value={vehicle}
                onChange={(e) => setVehicle(e.target.value as Vehicle)}
              >
                {Object.entries(
                  bootstrap?.vehicles ?? {
                    heavy: { label: "Heavy logistics" },
                  },
                ).map(([id, p]) => (
                  <option key={id} value={id}>
                    {p.label}
                  </option>
                ))}
              </select>
              {selectedVehicle && (
                <div className="vehicle-specs">
                  <span>{selectedVehicle.weight_t} t load profile</span>
                  <i />
                  <span>{selectedVehicle.height_m} m height</span>
                </div>
              )}
              <div className="section-rule" />
              <div className="field-heading">
                <label htmlFor="risk-weight">
                  <SlidersHorizontal size={16} />
                  Risk preference
                </label>
                <span>
                  {aversion === 0
                    ? "Time only"
                    : aversion < 2
                      ? "Balanced"
                      : "Risk focused"}
                </span>
              </div>
              <input
                id="risk-weight"
                className="risk-slider"
                type="range"
                min="0"
                max="5"
                step="0.25"
                value={aversion}
                onChange={(e) => setAversion(Number(e.target.value))}
                aria-valuetext={`${aversion}, ${aversion === 0 ? "time only" : "risk weight"}`}
              />
              <div className="range-labels">
                <span>Prioritize time</span>
                <span>Prioritize lower risk</span>
              </div>
              <label className="check-setting">
                <input
                  type="checkbox"
                  checked={strict}
                  onChange={(e) => setStrict(e.target.checked)}
                />
                <span>Require complete vehicle limits</span>
              </label>
              <div className="section-rule" />
              <div className="field-heading">
                <span>
                  <CloudRain size={17} />
                  Scenario controls
                </span>
                <span className="tiny-tag">SIMULATED</span>
              </div>
              <div
                className="weather-toggle"
                role="group"
                aria-label="Weather scenario"
              >
                <button
                  className={weather === "normal" ? "chosen" : ""}
                  onClick={() => setWeather("normal")}
                >
                  Normal weather
                </button>
                <button
                  className={weather === "heavy_rain" ? "chosen" : ""}
                  onClick={() => setWeather("heavy_rain")}
                >
                  <CloudRain size={14} />
                  Heavy rain
                </button>
              </div>
              {liveWeather && <small className="muted-copy live-weather" role="status">Live Open-Meteo · {liveWeather.temperature_c ?? "—"}°C · {liveWeather.rain_mm.toFixed(1)} mm rain · {liveWeather.wind_kph.toFixed(0)} km/h wind · {liveWeather.routing_scenario === "heavy_rain" ? "Risk uplift active" : "Normal conditions"}</small>}
              <label className="field-label compact" htmlFor="closure">
                Road disruption
              </label>
              <select
                className="full-select"
                id="closure"
                value={scenarioId}
                onChange={(e) => setScenarioId(e.target.value)}
              >
                <option value="none">No added closures</option>
                {bootstrap?.scenarios.map((s) => (
                  <option key={s.id} value={s.id}>
                    {s.label}
                  </option>
                ))}
              </select>
              {scenario && (
                <p className="scenario-note">{scenario.description}</p>
              )}
              <div className="auto-status" role="status">
                {busy ? (
                  <>
                    <LoaderCircle size={15} className="spin" />
                    Updating routes…
                  </>
                ) : error ? (
                  <>
                    <AlertTriangle size={15} />
                    Connection needs attention
                  </>
                ) : (
                  <>
                    <Check size={15} />
                    Routes updated automatically
                  </>
                )}
              </div>
            </section>
            <section className="map-panel" aria-label="Interactive route map">
              <div className="map-top">
                <div className="map-title">
                  <span className="map-region-dot" />
                  <div>
                    <strong>{bootstrap?.dataset.region || "North-East road network"}</strong>
                    <span>
                      {bootstrap?.dataset.is_synthetic === false
                        ? "OpenStreetMap road network"
                        : "Illustrative corridor network"}
                    </span>
                  </div>
                </div>
                <div
                  className="view-switch"
                  role="group"
                  aria-label="Map perspective"
                >
                  <button
                    className={mode === "flat" ? "on" : ""}
                    aria-pressed={mode === "flat"}
                    onClick={() => setMode("flat")}
                  >
                    Top view
                  </button>
                  <button
                    className={mode === "3d" ? "on" : ""}
                    aria-pressed={mode === "3d"}
                    onClick={() => setMode("3d")}
                  >
                    <Layers3 size={14} />
                    3D terrain
                  </button>
                </div>
              </div>
              <div className="map-canvas">
                {network && bootstrap ? (
                  <Suspense fallback={<div className="map-loading" role="status"><Compass size={42} /><span>Loading map renderer…</span></div>}><TerrainMap
                    network={network}
                    locations={bootstrap.locations}
                    result={result}
                    origin={origin}
                    destination={destination}
                    closedIds={closedIds}
                    mode={mode}
                    reset={reset}
                    showRisk={showRisk}
                    selected={selected}
                    terrain={terrain}
                    events={events.filter((event) => !event.dataset_id || event.dataset_id === datasetId)}
                  /></Suspense>
                ) : (
                  <div className="map-loading">
                    <Compass size={42} />
                    <span>
                      {error
                        ? "Waiting for the routing service"
                        : "Preparing your workspace…"}
                    </span>
                  </div>
                )}
              </div>
              <div className="map-tools">
                <button
                  className="map-tool"
                  aria-label="Reset map camera"
                  title="Reset view"
                  onClick={() => setReset(reset + 1)}
                >
                  <Focus size={19} />
                </button>
                <button
                  className={`map-tool ${showRisk ? "enabled" : ""}`}
                  aria-label="Show road risk"
                  aria-pressed={showRisk}
                  title="Toggle risk layer"
                  onClick={() => setShowRisk(!showRisk)}
                >
                  <Layers3 size={19} />
                </button>
              </div>
              <div className="north-indicator">
                <Navigation size={18} />
                <span>N</span>
              </div>
              {scenario && (
                <div className="map-alert">
                  <AlertTriangle size={17} />
                  <span>{scenario.label}</span>
                  <b>{closedIds.length} directed segments closed</b>
                </div>
              )}
              <div className="map-bottom">
                <div className="map-legend">
                  <span>
                    <i className="legend-safe" />
                    Risk-aware
                  </span>
                  <span>
                    <i className="legend-fast" />
                    Fastest
                  </span>
                  <span>
                    <i className="legend-risk" />
                    High risk
                  </span>
                </div>
                <span className="terrain-disclaimer">
                  {terrain
                    ? `DEM elevation · 2× vertical scale${terrain.void_samples ? " · gaps present" : ""}`
                    : "Illustrative elevation"}{" "}
                  · drag to explore
                </span>
              </div>
            </section>
            <section
              className="comparison-panel"
              aria-label="Route comparison"
              aria-busy={busy}
            >
              <div className="panel-heading">
                <span>Route comparison</span>
                <span className="step-chip">02</span>
              </div>
              {error ? (
                <div className="error-card" role="alert">
                  <AlertTriangle size={24} />
                  <h3>Couldn’t calculate routes</h3>
                  <p>{error}</p>
                  <button
                    className="button secondary"
                    onClick={() => setRetry(retry + 1)}
                  >
                    Reconnect
                  </button>
                </div>
              ) : result ? (
                <>
                  {result.routes.map((route) => (
                    <RouteCard
                      key={route.id}
                      route={route}
                      selected={selected === route.id}
                      onSelect={() => setSelected(route.id)}
                    />
                  ))}
                  {result.comparison && (
                    <div className="tradeoff-card">
                      <span className="eyebrow">THE TRADEOFF</span>
                      {result.routes.some(
                        (r) =>
                          r.status === "available" &&
                          r.unknown_risk_segments > 0,
                      ) ? (
                        <>
                          <strong>Risk evidence needed.</strong>
                          <p>
                            Routes can be calculated, but missing hazard data
                            prevents a supported risk comparison.
                          </p>
                        </>
                      ) : result.comparison.same_route ? (
                        <>
                          <strong>One route. Both priorities.</strong>
                          <p>
                            Both objectives select the same path with these
                            settings.
                          </p>
                        </>
                      ) : (
                        <>
                          <strong>
                            {reduction !== null && reduction !== undefined
                              ? `${Math.abs(reduction).toFixed(1)}% ${reduction >= 0 ? "lower" : "higher"}`
                              : "Compare"}{" "}
                            <span>risk exposure</span>
                          </strong>
                          <p>
                            for {result.comparison.extra_minutes.toFixed(1)}{" "}
                            extra estimated minutes.
                          </p>
                        </>
                      )}
                      <span className="index-note">
                        Modelled index, not accident probability.
                      </span>
                    </div>
                  )}
                  {!result.comparison && (
                    <div className="accessibility-warning">
                      <AlertTriangle size={18} />
                      <p>
                        This destination is inaccessible under the selected
                        conditions. Try another depot or review the scenario.
                      </p>
                    </div>
                  )}
                </>
              ) : (
                <div className="comparison-placeholder">
                  <Activity size={25} className={busy ? "pulse" : ""} />
                  <strong>
                    {busy ? "Comparing your options" : "Choose your journey"}
                  </strong>
                  <p>
                    Time, risk and vehicle restrictions are evaluated together.
                  </p>
                </div>
              )}
              <button
                className="evidence-link"
                onClick={() => dialog.current?.showModal()}
              >
                <Info size={15} />
                About these estimates
                <ArrowUpRight size={14} />
              </button>
            </section>
          </div>
          <div className="insights-grid">
            <section className="insight-card explanation-card">
              <div className="insight-heading">
                <ShieldCheck size={18} />
                <h2>Why this route?</h2>
                <span>EXPLAINABLE BY DESIGN</span>
              </div>
              {result?.explanations.length ? (
                <div className="explanation-list">
                  {Array.from(
                    new Map(
                      result.explanations.map((e) => [e.road, e]),
                    ).values(),
                  )
                    .slice(0, 2)
                    .map((e) => (
                      <div className="explanation" key={e.edge_id}>
                        <span className="explanation-icon">
                          <ArrowUpRight size={19} />
                        </span>
                        <div>
                          <strong>Bypass {e.road.toLowerCase()}</strong>
                          <p>
                            Higher {e.reason} score on the fastest route.{" "}
                            <span>{e.evidence}.</span>
                          </p>
                        </div>
                      </div>
                    ))}
                </div>
              ) : (
                <p className="insight-empty">
                  {busy
                    ? "Route explanations will appear here."
                    : result?.comparison?.same_route
                      ? "No detour is needed for the selected balance of time and risk."
                      : "Change a scenario to inspect accessibility and route tradeoffs."}
                </p>
              )}
            </section>
            <section className="insight-card">
              <div className="insight-heading">
                <Activity size={18} />
                <h2>Route diagnostics</h2>
              </div>
              <div className="diagnostics">
                <div>
                  <strong>
                    {activeRoute?.status === "available"
                      ? activeRoute.expanded_nodes
                      : "—"}
                  </strong>
                  <span>nodes explored</span>
                </div>
                <div>
                  <strong>
                    {activeRoute?.status === "available"
                      ? `${activeRoute.compute_ms.toFixed(1)}`
                      : "—"}
                    <small> ms</small>
                  </strong>
                  <span>search time</span>
                </div>
                <div>
                  <strong>{bootstrap?.counts.edges ?? "—"}</strong>
                  <span>directed segments</span>
                </div>
              </div>
              {activeRoute?.status === "available" &&
                activeRoute.warnings.map((w) => (
                  <p className="restriction-warning" key={w}>
                    {w}
                  </p>
                ))}
            </section>
          </div>
          <footer>
            <span>
              <span className="footer-dot" />
              {bootstrap?.dataset.source ?? "Connecting"} ·{" "}
              {bootstrap?.dataset.hazard_source ?? "Data source loading"}
            </span>
            <button onClick={() => dialog.current?.showModal()}>
              View provenance
              <ArrowRight size={14} />
            </button>
          </footer>
        </main>
      </div>
      <dialog
        ref={dialog}
        className="evidence-dialog"
        onClick={(e) => {
          if (e.target === e.currentTarget) dialog.current?.close();
        }}
      >
        <div className="dialog-heading">
          <div>
            <div className="eyebrow">DATA & METHODOLOGY</div>
            <h2>Know what powers the route.</h2>
          </div>
          <button
            className="icon-button"
            aria-label="Close data information"
            onClick={() => dialog.current?.close()}
          >
            <X size={21} />
          </button>
        </div>
        <div className="evidence-source">
          <Database size={22} />
          <div>
            <strong>{bootstrap?.dataset.title}</strong>
            <p>{bootstrap?.dataset.region}</p>
          </div>
          <span className="tiny-tag">
            {bootstrap?.dataset.is_synthetic ? "SYNTHETIC" : "OSM"}
          </span>
        </div>
        <dl>
          <dt>Road network</dt>
          <dd>{bootstrap?.dataset.source}</dd>
          <dt>Hazards</dt>
          <dd>{bootstrap?.dataset.hazard_source}</dd>
          <dt>Terrain</dt>
          <dd>
            {terrain
              ? `${terrain.source}; 2× vertical exaggeration`
              : bootstrap?.dataset.terrain_source}
          </dd>
          <dt>Dataset version</dt>
          <dd>{bootstrap?.dataset_version}</dd>
        </dl>
        <h3>How the comparison works</h3>
        <p>
          Both routes respect the same closures and vehicle limits. The fastest
          route minimizes estimated travel time. The risk-aware route adds a
          non-negative risk penalty to each road’s time cost, then uses our
          custom A* search.
        </p>
        <p>
          Risk exposure adds road length × risk score across the route. It is an
          index measured in risk-km, not a measured probability of an accident.
          Lower exposure can require more travel time.
        </p>
        <h3>Current limitations</h3>
        <ul>
          {bootstrap?.dataset.limitations.map((l) => (
            <li key={l}>{l}</li>
          ))}
          <li>
            Turn restrictions and time-dependent departures are not yet
            modelled.
          </li>
          <li>
            Unknown vehicle limits are allowed with a warning unless strict
            checking is enabled.
          </li>
        </ul>
        <div className="dialog-footer">
          <span>Research claims are not presented as prototype results.</span>
          <button
            className="button primary"
            onClick={() => dialog.current?.close()}
          >
            Understood
            <Check size={16} />
          </button>
        </div>
      </dialog>
      <dialog
        ref={reportDialog}
        className="evidence-dialog report-dialog"
        onClick={(event) => {
          if (event.target === event.currentTarget) reportDialog.current?.close();
        }}
      >
        <div className="dialog-heading">
          <div>
            <div className="eyebrow">FIELD ACCESSIBILITY UPDATE</div>
            <h2>Report a road incident.</h2>
          </div>
          <button
            className="icon-button"
            aria-label="Close incident report"
            onClick={() => reportDialog.current?.close()}
          >
            <X size={21} />
          </button>
        </div>
        <div className="report-location">
          <MapPinned size={20} />
          <div>
            <strong>{reportLocation?.label ?? "No mapped origin selected"}</strong>
            <span>
              {reportLocation
                ? `${reportLocation.lat.toFixed(5)}, ${reportLocation.lon.toFixed(5)} · ${regionCode}`
                : "Choose a location from the route planner"}
            </span>
          </div>
        </div>
        <div className="auth-panel">
          {session?.access_token ? (
            <div className="signed-in-row">
              <span><Check size={15} /> Signed in as {session.user.email ?? "field official"}</span>
              <button type="button" onClick={signOut}>Sign out</button>
            </div>
          ) : (
            <form onSubmit={submitAuth}>
              <div className="auth-heading">
                <strong>{authMode === "signin" ? "Field official sign in" : "Create field account"}</strong>
                <button
                  type="button"
                  onClick={() => setAuthMode((mode) => mode === "signin" ? "signup" : "signin")}
                >
                  {authMode === "signin" ? "Create account" : "Use existing account"}
                </button>
              </div>
              {authMode === "signup" && (
                <input
                  required
                  value={authForm.displayName}
                  onChange={(event) => setAuthForm((current) => ({ ...current, displayName: event.target.value }))}
                  placeholder="Official display name"
                />
              )}
              <input
                required
                type="email"
                autoComplete="email"
                value={authForm.email}
                onChange={(event) => setAuthForm((current) => ({ ...current, email: event.target.value }))}
                placeholder="Official email"
              />
              <input
                required
                type="password"
                minLength={8}
                autoComplete={authMode === "signin" ? "current-password" : "new-password"}
                value={authForm.password}
                onChange={(event) => setAuthForm((current) => ({ ...current, password: event.target.value }))}
                placeholder="Password"
              />
              <button className="button primary" disabled={authBusy}>
                {authBusy && <LoaderCircle className="spin" size={15} />}
                {authMode === "signin" ? "Sign in" : "Create account"}
              </button>
              {authMessage && <span className="auth-message">{authMessage}</span>}
            </form>
          )}
        </div>
        <form className="report-form" onSubmit={submitFieldReport}>
          <label>
            Incident type
            <select
              value={reportForm.kind}
              onChange={(event) =>
                setReportForm((current) => ({ ...current, kind: event.target.value }))
              }
            >
              <option value="road_blocked">Road blocked</option>
              <option value="road_damage">Road damage</option>
              <option value="bridge_damage">Bridge damage</option>
              <option value="landslide">Landslide</option>
              <option value="flood">Flood</option>
              <option value="heavy_rain">Heavy rain</option>
              <option value="traffic_congestion">Traffic congestion</option>
              <option value="other">Other</option>
            </select>
          </label>
          <label>
            Accessibility
            <select
              value={reportForm.accessibility_status}
              onChange={(event) =>
                setReportForm((current) => ({
                  ...current,
                  accessibility_status: event.target.value,
                }))
              }
            >
              <option value="blocked">Blocked</option>
              <option value="restricted">Restricted</option>
              <option value="open">Open / restored</option>
              <option value="unknown">Unknown</option>
            </select>
          </label>
          <label>
            District (optional)
            <input
              value={reportForm.district}
              maxLength={120}
              onChange={(event) =>
                setReportForm((current) => ({
                  ...current,
                  district: event.target.value,
                }))
              }
              placeholder="e.g. North Sikkim"
            />
          </label>
          <label>
            Severity <b>{Math.round(reportForm.severity * 100)}%</b>
            <input
              type="range"
              min="0"
              max="1"
              step="0.05"
              value={reportForm.severity}
              onChange={(event) =>
                setReportForm((current) => ({
                  ...current,
                  severity: Number(event.target.value),
                }))
              }
            />
          </label>
          <label className="report-description">
            Field observation
            <textarea
              required
              minLength={5}
              maxLength={2000}
              value={reportForm.description}
              onChange={(event) =>
                setReportForm((current) => ({
                  ...current,
                  description: event.target.value,
                }))
              }
              placeholder="Describe blockage, passable lanes and visible damage…"
            />
          </label>
          <label className="report-description">
            Photo evidence (optional, max 10 MB)
            <input type="file" accept="image/jpeg,image/png,image/webp" onChange={(event) => setEvidenceFile(event.target.files?.[0] || null)} />
            {evidenceFile && <small>{evidenceFile.name} · {(evidenceFile.size / 1024 / 1024).toFixed(2)} MB</small>}
          </label>
          <div className="report-actions">
            <span className={reportMessage.includes("queued") ? "success" : ""}>
              {reportMessage || "New reports remain pending until reviewed."}
              {queuedReports > 0 && <small className="offline-queue-note"> {queuedReports} saved offline · will sync when connected</small>}
            </span>
            <button className="button primary" disabled={reportBusy || !reportLocation || !session}>
              {reportBusy ? <LoaderCircle className="spin" size={16} /> : <AlertTriangle size={16} />}
              Submit report
            </button>
          </div>
        </form>
        <div className="pending-reports">
          <div>
            <strong>Recent regional reports</strong>
            <span>{reports.length} loaded</span>
          </div>
          {reports.slice(0, 4).map((report) => (
            <article key={report.id}>
              <span className={`status-dot ${report.accessibility_status}`} />
              <div>
                <strong>{report.place_name || report.district || report.region_code}</strong>
                <small>{report.kind.replaceAll("_", " ")} · {report.review_status}</small>
                <p>{report.description}</p>
                <small>{report.lat.toFixed(5)}, {report.lon.toFixed(5)} · {new Date(report.observed_at).toLocaleString()}</small>
                {report.review_status === "pending" && ["reviewer", "admin"].includes(operatorRole) && (
                  <div className="review-controls">
                    <label>
                      Reviewed road edge
                      <select
                        aria-label={`Road candidate for ${report.place_name || report.id}`}
                        value={selectedEdges[report.id] || ""}
                        onChange={(event) => setSelectedEdges((edges) => ({ ...edges, [report.id]: event.target.value }))}
                      >
                        <option value="">Select a road edge</option>
                        {(candidates[report.id] || []).map((candidate) => (
                          <option key={candidate.edge_id} value={candidate.edge_id}>{candidate.name} · {candidate.distance_m} m</option>
                        ))}
                      </select>
                    </label>
                    <label>
                      Review evidence and reason
                      <textarea
                        aria-label={`Review note for ${report.place_name || report.id}`}
                        maxLength={1000}
                        value={reviewNotes[report.id] || ""}
                        onChange={(event) => setReviewNotes((notes) => ({ ...notes, [report.id]: event.target.value }))}
                      />
                    </label>
                    <div>
                      <button type="button" className="button secondary" disabled={!!reviewing || (reviewNotes[report.id]?.trim().length || 0) < 5} onClick={() => moderateReport(report.id, "rejected")}>Reject</button>
                      <button type="button" className="button primary" disabled={!!reviewing || report.accessibility_status === "unknown" || !selectedEdges[report.id] || (reviewNotes[report.id]?.trim().length || 0) < 5} onClick={() => moderateReport(report.id, "accepted")}>{reviewing === report.id ? "Saving…" : "Accept report"}</button>
                    </div>
                  </div>
                )}
              </div>
              <b>{Math.round(report.severity * 100)}%</b>
            </article>
          ))}
        </div>
      </dialog>
    </div>
  );
}
