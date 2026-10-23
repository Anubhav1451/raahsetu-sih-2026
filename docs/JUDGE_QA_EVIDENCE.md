# RaahSetu — strict judge Q&A, backed by the current repository

This file is the claim boundary for demonstrations. A claim is allowed only when the cited artifact exists in this checkout. `working` means executable locally, `controlled` means a synthetic or scenario benchmark, and `external` means credentials, authoritative data or a field pilot are still required.

## 1. “AI-Based” kahan hai?

**Answer:** The current trained component is `weather-anomaly-v1`: a state-wise anomaly detector trained on 2021–2024 daily weather and checked on a 2025 temporal holdout. It has 1,461 training days per state and uses precipitation, wind and temperature range. Its output is a weather-anomaly score, feature contributions and model/data version. It is not represented as a landslide or road-closure probability. Risk-A* remains a deterministic routing component.

**Evidence:** `backend/scripts/train_weather_anomaly.py`, `backend/data/weather_anomaly_model.json`, `backend/app/weather_anomaly.py`.

## 2. A* ko AI kyun kahoge?

**Answer:** We will not call A* a trained AI model. A* is informed search. The platform combines an ML weather-anomaly signal, rule-based risk fusion, and an explainable A* optimizer. This separation makes the claim technically precise.

## 3. Google Maps/OSRM/GraphHopper se quantitatively better?

**Answer:** We do not claim universal route superiority without a reproducible third-party benchmark. Our controlled same-graph benchmark solved 56/56 journeys and produced a lower modelled exposure alternative in 34 cases. That demonstrates an auditable time-versus-risk objective, not superiority over Google. Our functional difference is support for reviewed closures, vehicle constraints, risk evidence and versioned local graphs.

**Evidence:** `docs/validation/evaluation-summary.json`, `docs/validation/route-evaluation.csv`.

## 4. Edge-cost formula?

**Answer:** Base risk is `0.5 × accident_score + 0.3 × surface_score + 0.2 × weather_score`. Heavy rain additionally raises weather exposure by the edge flood-susceptibility term before clamping risk to `[0,1]`. Fastest cost is estimated travel seconds. Risk-aware cost is `travel_seconds × (1 + 4 × risk_aversion × risk)`. Closures and incompatible vehicle constraints remove an edge from the search space.

**Evidence:** `backend/app/routing.py`.

## 5. Weights learned hain?

**Answer:** The routing weights are documented, manually configured policy weights; they are not fitted coefficients. The separate weather anomaly baseline is trained from real historical weather. Learned routing weights require labelled, authority-reviewed road outcomes and geographic/temporal validation, which we do not currently possess.

## 6. Live government feed proof?

**Answer:** CAP, CWC and traffic payload parsers, freshness metadata, scheduled refresh and auditable import runs work. In the absence of an authorised production feed URL, the connector reports `STANDBY`; we do not label cached or simulated data as live government data.

**Evidence:** `backend/app/live_ingestion.py`, `backend/app/scheduled_refresh.py`, parser tests.

## 7. Stale hazard se unsafe route kaise rokte ho?

**Answer:** Every source has freshness metadata. Operational events without a valid end time stop affecting routing after `OPERATIONAL_EVENT_MAX_AGE_HOURS` (24 hours by default). Stale live weather falls back with an explicit stale/unavailable status and does not manufacture an ML score. Unknown evidence is reported as unknown; strict vehicle mode fails closed.

## 8. Bridge limit coverage?

**Answer:** Constraint enforcement is implemented for gross weight, height, width, axle load, HGV access and allowed vehicle type. The current eight real OSM state snapshots have 0% authoritative restriction-tag coverage in the fresh audit, so we cannot claim state-wide bridge-limit coverage. Known limits are enforced; in strict mode, missing limits make an edge ineligible. A PWD/bridge-asset registry is required for operational coverage.

**Evidence:** `docs/validation/northeast-graph-audit.json`, `backend/app/routing.py`.

## 9. False citizen report?

**Answer:** A citizen/field submission is pending evidence and cannot directly close a road. A reviewer/admin accepts it before an accessibility event is created. The server is idempotent by `client_report_id`; review actions are tied to authenticated users.

## 10. Offline duplicate/conflict/replay?

**Answer:** IndexedDB stores a stable client report ID. Server inserts are idempotent; duplicate IDs return the existing report. The queue uses retry count, last/next attempt, error state and exponential backoff. Review status is server-authoritative, so a delayed client replay cannot overwrite an authority decision.

**Evidence:** `frontend/src/offlineQueue.ts`, `backend/app/field_reports.py`.

## 11. GPS spoofing/stale telemetry?

**Answer:** Production gateways can require HMAC-SHA256. The guard rejects missing-timezone, stale, future, replayed/out-of-order, outside-NER and physically impossible jump packets. Missing/poor accuracy lowers trust and is stored with quality flags. This is anomaly filtering, not cryptographic proof of satellite location; AIS-140 device identity and carrier/device attestation remain pilot integrations.

## 12. Heavy-vehicle constraints?

**Answer:** The engine checks effective gross weight (vehicle plus optional cargo override), height, width, axle load, HGV permission, road class/vehicle allow-list and active closures. Unknown restrictions are surfaced; strict mode rejects them.

## 13. Working 3D evidence?

**Answer:** `TerrainMap.tsx` renders terrain, routes, hazards and events with React Three Fiber. The production build contains separately loaded R3F and Three.js chunks. A deterministic SVG map is the fallback. Demo evidence must be shown live or recorded; the PPT alone is not proof.

## 14. Low-end performance?

**Answer:** Reduced-motion, hidden/offscreen frame suspension, demand rendering and automatic fallback for four-or-fewer CPU threads or up-to-4-GB reported device memory are implemented. We do not claim a measured FPS on a ten-year-old control-room PC until the physical-device benchmark is run.

## 15. Mapbox unavailable?

**Answer:** The current frontend does not depend on Mapbox. It uses local/versioned routing graphs, a custom WebGL/R3F view and Leaflet/OSM for geographic display. Replacing the visual tile provider does not change the routing API, but it is a provider adapter/configuration change rather than a dishonest “one-line” guarantee.

## 16. Eight-state storage/latency/cost?

**Answer:** Eight immutable graphs are kept locally, not uploaded wholesale to the free Supabase database. The audit covers 431,931 nodes and 1,013,565 directed edges; each state route smoke test passed. Supabase stores small operational metadata, reports, events and auth. Exact monthly production cost depends on request volume, retention and provider plan and must be load-tested; we will not invent a rupee figure.

## 17. Kubernetes kyun?

**Answer:** Kubernetes is optional scale/deployment documentation, not required for a pilot. A single FastAPI process plus local graph snapshots/PostgreSQL is the pilot architecture. Kubernetes becomes useful only for multiple replicas, rolling updates and health-managed production workloads; its overhead is unjustified for the present local demo.

## 18. Security/privacy?

**Answer:** Supabase Auth JWT plus backend RBAC protects reviewer/admin actions. Tables enable RLS and revoke browser roles; server credentials remain backend-only. HTTPS/TLS is a deployment requirement. GPS integrity metadata is retained, and migration 007 supplies an admin-only purge function with 90-day position and 365-day completed-job defaults. A deployment must approve consent/retention and run policy tests before production.

## 19. Success metrics?

**Answer:** Pilot baselines are: existing dispatcher route/time, actual arrival delay, blocked-route encounters and kilometres travelled. Compare them against frozen-version RaahSetu recommendations using median/P90 delay, reroute response time, false-alert rate, missed disruption rate, detour kilometres and delivery completion. Current 56 journeys are only a controlled algorithmic benchmark, not measured field impact.

## 20. Aaj exactly kya working hai?

**Working:** eight real OSM graph snapshots and route solving; Risk-A* and constraint filtering; real historical weather anomaly training/inference; Open-Meteo ingestion with freshness; reviewed field reports; offline queue; RBAC; AIS-140/mobile webhook adapters with integrity checks; 2D/3D dashboard and fallback; notification simulator/provider adapters; scheduled refresh.

**Controlled:** 56-journey route benchmark, demo incidents, simulator delivery and any synthetic hazard toggle.

**External before operational deployment:** authorised NDMA/CWC/traffic endpoints, authoritative bridge/restriction registry, messaging credentials, physical AIS-140 pilot, old-PC FPS test, labelled disruption outcomes, security/load review and cloud deployment.
