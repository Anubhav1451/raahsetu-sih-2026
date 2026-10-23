# Graph Report - raahsetu_by_kavya  (2026-09-26)

## Corpus Check
- 215 files · ~366,982 words
- Verdict: corpus is large enough that graph structure adds value.
- Unclassified: 24 file(s) not represented in the graph (top: (none) 9, .csv 5, .css 4)

## Summary
- 1616 nodes · 3198 edges · 130 communities (91 shown, 39 thin omitted)
- Extraction: 95% EXTRACTED · 5% INFERRED · 0% AMBIGUOUS · INFERRED: 146 edges (avg confidence: 0.94)
- Token cost: 0 input · 0 output

## Graph Freshness
- Built from commit: `754c590f`
- Run `git rev-parse HEAD` and compare to check if the graph is stale.
- Run `graphify update .` after code changes (no API cost).

## Community Hubs (Navigation)
- live_ingestion.py
- weather.py
- import_osm.py
- AdminOperationsPanel.tsx
- seed_authority_users.py
- RoadGraph
- FieldReportStore
- graph_loader.py
- api.ts
- InMemoryFleetStore
- Twenty jury questions with defensible answers
- AuthUser
- csv
- os
- main.py
- test_routing.py
- getPublicConfig
- test_api.py
- Custom Risk-A* engine
- Depends
- pathlib
- What You Must Do When Invoked
- What You Must Do When Invoked
- App.tsx
- routeData.ts
- RaahSetu — strict judge Q&A, backed by the current repository
- require_reviewer
- compilerOptions
- 002_operations_foundation.sql
- build_disruption_label_dataset.py
- react
- json
- TerrainMap.tsx
- translations.ts
- AlertStore
- train_disruption_model.py
- test_scheduled_refresh.py
- telematics.py
- datetime
- package.json
- 001_spatial_foundation.sql
- broadcast_alert
- Product Requirements Document
- Live Feed Readiness, Governance & Operational Procedures
- offlineQueue.ts
- AGENTS.md
- monitor_features
- auth.users
- Project Rules
- 004_fleet_tracking.sql
- admin_model_registry
- RealMapLeaflet.tsx
- Design System
- Architecture and decisions
- public.region_catalog
- voiceRecognition.ts
- RaahSetu
- graphify reference: extra exports and benchmark
- routing.py
- graphify reference: extra exports and benchmark
- Dataset inventory and evidence rules
- Disruption model readiness & strict audit status
- VehicleDetailsPage.tsx
- Project Memory
- Testing Strategy
- RaahSetu (राहसेतु) — Comprehensive Security & Compliance Audit
- models.py
- Run and deploy
- Empirical label acquisition
- TableParser
- 003_auth_and_review.sql
- Team ke liye start yahan se karo
- graphify reference: query, path, explain
- model_validator
- graphify reference: query, path, explain
- Assam public-data acquisition findings
- Data freshness and versioning
- Six-person execution plan
- AuthPage.tsx
- 007_retention_and_operational_guards.sql
- 006_data_freshness.sql
- test_state_hazard_matching.py
- RaahSetu (राहसेतु) — Official Authority Credentials & RBAC Roles
- Completion audit against the original SIH brief
- External integration handoff
- Redis operations
- Frontend workspace enhancement — 2026-09-07
- Extractor
- public.disruption_candidates
- graphify reference: add a URL and watch a folder
- graphify reference: commit hook and native CLAUDE.md integration
- graphify reference: incremental update and cluster-only
- graphify reference: add a URL and watch a folder
- graphify reference: commit hook and native CLAUDE.md integration
- graphify reference: incremental update and cluster-only
- Validation record
- DataProvenanceDrawer.tsx
- graphify reference: GitHub clone and cross-repo merge
- graphify reference: transcribe video and audio
- graphify reference: GitHub clone and cross-repo merge
- graphify reference: transcribe video and audio
- alerts_event_type_unique
- rules/graphify.md
- .agents/skills/graphify/references/extraction-spec.md
- workflows/graphify.md
- .codex/skills/graphify/references/extraction-spec.md
- CONTRIBUTING.md
- datasets/README.md
- LOCAL_POSTGIS_SETUP.md
- NORTHEAST_GRAPH_AUDIT.md
- RBAC_DEMO_MODE.md
- STORAGE_ARCHITECTURE.md
- SUPABASE_BACKUP_RESTORE.md
- disruption-data-research.md
- premium-spatial-ui.md
- weather-anomaly-v2.md
- sw.js
- SECURITY.md
- raahsetu-api

## God Nodes (most connected - your core abstractions)
1. `AuthUser` - 51 edges
2. `request()` - 42 edges
3. `RoadGraph` - 39 edges
4. `App()` - 33 edges
5. `Dataset` - 29 edges
6. `StrictModel` - 28 edges
7. `require_user()` - 27 edges
8. `require_reviewer()` - 26 edges
9. `RouteRequest` - 26 edges
10. `AdminOperationsPanel()` - 24 edges

## Surprising Connections (you probably didn't know these)
- `What judges and evaluators MUST be told (Safe Claims)` --references--> `accessibility_events()`  [INFERRED]
  docs/LIVE_FEEDS.md → backend/app/main.py
- `2. Row Level Security (RLS) Policy Matrix` --references--> `accessibility_events()`  [INFERRED]
  docs/SECURITY_AUDIT.md → backend/app/main.py
- `Automatic monitoring additions` --references--> `interpolate_corridor_weather()`  [INFERRED]
  docs/DATA_GAPS_AND_MANUAL_ORDER.md → backend/app/weather.py
- `main()` --uses--> `Dataset`  [INFERRED]
  scripts/generate_northeast_dataset.py → backend/app/models.py
- `check_official_feeds()` --calls--> `get_official_feeds_status()`  [INFERRED]
  scripts/scheduled_refresh.py → backend/app/live_ingestion.py

## Import Cycles
- None detected.

## Communities (130 total, 39 thin omitted)

### Community 0 - "live_ingestion.py"
Cohesion: 0.07
Nodes (58): FeedSourceStatus, fetch_live_feed_advisories(), get_candidate_advisories(), get_feed_diagnostics(), get_official_feeds_status(), ingest_live_official_advisories(), init_candidate_advisories_store(), OfficialHazardAdvisory (+50 more)

### Community 1 - "weather.py"
Cohesion: 0.06
Nodes (52): cache_clear(), cache_get(), cache_health(), cache_set(), _client(), Any, Optional Redis cache with a safe in-process fallback. Redis accelerates…, Return explicit cache/bus status for diagnostics and admin UI. (+44 more)

### Community 2 - "import_osm.py"
Cohesion: 0.16
Nodes (11): main(), numeric_limit(), Prepare an OSMnx graph from a local OSM extract or an explicit small Overpass…, networkx, osmnx, re, main(), Generate validated backend/data/osm-northeast.json from… (+3 more)

### Community 3 - "AdminOperationsPanel.tsx"
Cohesion: 0.19
Nodes (27): compareRoutes(), extendAccessibilityEvent(), getAccessibilityEvents(), getAdminSourcesStatus(), getAuditLog(), getBroadcastHistory(), getCacheHealth(), getCandidateAdvisories() (+19 more)

### Community 4 - "seed_authority_users.py"
Cohesion: 0.67
Nodes (3): generate_credentials_doc(), main(), Seed Authority Accounts & Reviewer Credentials for RaahSetu. Creates verified…

### Community 5 - "RoadGraph"
Cohesion: 0.12
Nodes (27): lifespan(), load_graph(), Dataset, Edge, Endpoint, Node, RouteRequest, Remove harmless floating-point serialization noise from graph versions. (+19 more)

### Community 6 - "FieldReportStore"
Cohesion: 0.09
Nodes (12): FieldReportStore, InMemoryFieldReportStore, PostgresFieldReportStore, datetime, Protocol, In-memory store providing full field report capabilities when PostgreSQL is…, FieldReport, FieldReportAttachment (+4 more)

### Community 7 - "graph_loader.py"
Cohesion: 0.10
Nodes (16): load_large_snapshot(), Validate large OSM snapshots incrementally to bound JSON parsing memory., Merge real state snapshots by OSM node identity; never bridge missing roads.…, contextlib, ijson, osmium, Extract reference-complete drivable ways by state and a Guwahati pilot window.…, main() (+8 more)

### Community 8 - "api.ts"
Cohesion: 0.06
Nodes (50): AIS140IngestResponse, AIS140TelemetryPacketPayload, getAlerts(), getAllLiveWeather(), getBootstrap(), getConnectivity(), getDeliveries(), getNetwork() (+42 more)

### Community 9 - "InMemoryFleetStore"
Cohesion: 0.14
Nodes (11): FleetStore, InMemoryFleetStore, PostgresFleetStore, Protocol, In-memory store providing vehicle assets, GPS telemetry, and deliveries when…, DeliveryCreate, DeliveryJob, DeliveryUpdate (+3 more)

### Community 10 - "Twenty jury questions with defensible answers"
Cohesion: 0.06
Nodes (31): 0:00–0:40 — Problem, 0:40–1:25 — Solution, 10. What works without internet?, 11. What happens if Supabase is unavailable?, 12. Can government legally use OSM?, 13. Is all of Northeast covered?, 14. What if a road is new or missing?, 15. What if the safer route is much slower? (+23 more)

### Community 11 - "AuthUser"
Cohesion: 0.11
Nodes (17): AuthUser, BaseModel, Depends, Supabase access-token validation and application role lookup., require_admin(), Trigger a refresh check for refreshable operational sources., refresh_admin_source(), test_field_official_cannot_review() (+9 more)

### Community 12 - "csv"
Cohesion: 0.10
Nodes (22): Audit disruption labels for provenance, separability, and leakage risks before…, distance_m(), main(), point_to_polyline(), Import verified Northeast hazards into graph snapshots and PostGIS. Matches…, distance_m(), match_hazards_for_state(), point_to_polyline_m() (+14 more)

### Community 13 - "os"
Cohesion: 0.22
Nodes (8): Backend-only PostGIS access for geo-tagged field reports., Create a local PostGIS-compatible database and apply RaahSetu migrations., os, psycopg, psycopg_rows, psycopg_types_json, Recover the remote Supabase database after a disk-full event. The complete road…, typing

### Community 14 - "main.py"
Cohesion: 0.08
Nodes (43): AlertStore, add_security_headers(), admin_broadcasts(), admin_cache_health(), admin_model_drift(), admin_telemetry_health(), alert_providers(), alerts() (+35 more)

### Community 15 - "test_routing.py"
Cohesion: 0.19
Nodes (16): graph(), fixture, parametrize, request(), test_closures_and_unreachable(), test_coordinate_snapping(), test_custom_astar_matches_independent_dijkstra(), test_graph_version_ignores_float_serialization_noise() (+8 more)

### Community 17 - "test_api.py"
Cohesion: 0.05
Nodes (13): admin_client(), fixture, client(), MemoryFieldReports, fixture, parametrize, test_data_status_is_safe_and_operationally_useful(), test_demo_otp_endpoints_are_retired() (+5 more)

### Community 18 - "Custom Risk-A* engine"
Cohesion: 0.08
Nodes (25): Consequences, Consequences, Context, Context, Custom Risk-A* engine, Date, Date, Date (+17 more)

### Community 19 - "Depends"
Cohesion: 0.11
Nodes (38): api_route, Header, require_user(), accessibility_events(), create_delivery(), create_field_report(), current_user(), deliveries() (+30 more)

### Community 20 - "pathlib"
Cohesion: 0.07
Nodes (23): argparse, Seed realistic operations data (field reports and accessibility events) into…, Validate public disruption candidates without promoting them to labels., concurrent_futures, dotenv, pathlib, main(), Summarize actual local coverage, validate raw containers and preserve gaps. (+15 more)

### Community 21 - "What You Must Do When Invoked"
Cohesion: 0.08
Nodes (24): For /graphify add and --watch, For /graphify query, For the commit hook and native CLAUDE.md integration, For --update and --cluster-only, /graphify, Honesty Rules, Interpreter guard for subcommands, Part A - Structural extraction for code files (+16 more)

### Community 22 - "What You Must Do When Invoked"
Cohesion: 0.08
Nodes (24): For /graphify add and --watch, For /graphify query, For the commit hook and native CLAUDE.md integration, For --update and --cluster-only, /graphify, Honesty Rules, Interpreter guard for subcommands, Part A - Structural extraction for code files (+16 more)

### Community 23 - "App.tsx"
Cohesion: 0.15
Nodes (22): createFieldReport(), getDataStatus(), getLiveWeather(), sendFleetPosition(), uploadFieldReportAttachment(), ACTIVE_ROAD_BLOCKAGES, App(), CITY_ELEVATIONS_M (+14 more)

### Community 24 - "routeData.ts"
Cohesion: 0.08
Nodes (25): roadEndpoints(), ADJACENCY, City, CITY_MAP, CommodityProfile, DISTRICT_CONNECTIVITY, DistrictStatus, Edge (+17 more)

### Community 25 - "RaahSetu — strict judge Q&A, backed by the current repository"
Cohesion: 0.09
Nodes (21): 10. Offline duplicate/conflict/replay?, 11. GPS spoofing/stale telemetry?, 12. Heavy-vehicle constraints?, 13. Working 3D evidence?, 14. Low-end performance?, 15. Mapbox unavailable?, 16. Eight-state storage/latency/cost?, 17. Kubernetes kyun? (+13 more)

### Community 26 - "require_reviewer"
Cohesion: 0.11
Nodes (27): AuditEntry, AuditStore, get_audit_store(), InMemoryAuditStore, PostgresAuditStore, Any, BaseModel, datetime (+19 more)

### Community 27 - "compilerOptions"
Cohesion: 0.10
Nodes (19): compilerOptions, allowImportingTsExtensions, baseUrl, isolatedModules, jsx, lib, module, moduleResolution (+11 more)

### Community 28 - "002_operations_foundation.sql"
Cohesion: 0.20
Nodes (18): auth, accessibility_events_active_idx, accessibility_events_geom_gist, alerts_created_idx, field_report_attachments_report_idx, field_reports_geom_gist, field_reports_region_status_idx, operation_audit_entity_idx (+10 more)

### Community 29 - "build_disruption_label_dataset.py"
Cohesion: 0.16
Nodes (18): build_disruption_dataset(), derive_delay_for_size(), derive_glc_precipitation(), derive_surface_score_from_road(), distance_m(), get_elevation_m(), get_terrain_slope_and_elevation(), load_reference_weather() (+10 more)

### Community 30 - "react"
Cohesion: 0.18
Nodes (8): ConstellationGrid(), ConstellationGridProps, Node, frontend_src_live, frontend_src_tailwind, frontend_src_workspace, react, ref_react_dom_client

### Community 31 - "json"
Cohesion: 0.10
Nodes (23): DisruptionPrediction, predict_disruption(), Domain-Calibrated Explainable Disruption Baseline for Northeast India…, Predict disruption probability and explain top driving factors., Explainable seasonal weather anomaly inference (advisory only)., main(), predict_supervised(), Evaluation and shadow-mode comparison for the calibrated disruption model.… (+15 more)

### Community 32 - "TerrainMap.tsx"
Cohesion: 0.10
Nodes (14): TerrainMap, height(), MapBoundary, MapScene(), Point, Props, AccessibilityEvent, Comparison (+6 more)

### Community 33 - "translations.ts"
Cohesion: 0.15
Nodes (18): INTRO_ROAD_BLOCKAGES, IntroPage(), RoadBlockage, RealMapLeaflet(), STRATEGIC_CORRIDORS, BLOCKAGE_TRANSLATIONS, BlockageTranslation, CITIES_TRANSLATIONS (+10 more)

### Community 34 - "AlertStore"
Cohesion: 0.21
Nodes (7): AlertStore, InMemoryAlertStore, PostgresAlertStore, Protocol, In-memory alert store providing regional alerts and connectivity summaries when…, Alert, ConnectivitySummary

### Community 35 - "train_disruption_model.py"
Cohesion: 0.23
Nodes (15): compute_calibration_curve(), compute_pr_auc(), compute_roc_auc(), evaluate_dataset(), extract_features(), main(), perform_date_grouped_split(), Leakage-safe supervised disruption trainer. Enforces the minimum 200-label… (+7 more)

### Community 36 - "test_scheduled_refresh.py"
Cohesion: 0.17
Nodes (15): Unit tests for the automated scheduled data refresh runner., test_check_official_feeds(), test_run_refresh_cycle_dry_run(), test_update_data_status_dry_run(), check_official_feeds(), main(), Execute a single data refresh and audit cycle., Refresh live weather predictions for all 8 Northeast reference stations. (+7 more)

### Community 37 - "telematics.py"
Cohesion: 0.12
Nodes (19): PositionCreate, AIS140TelemetryPacket, _haversine_km(), packet_to_position_create(), parse_raw_ais140_string(), parse_telematics_webhook(), Any, AIS-140 Telematics & Commercial Vehicle GPS Ingestion Module. Compliant with… (+11 more)

### Community 38 - "datetime"
Cohesion: 0.11
Nodes (15): Field Pilot & Disruption Model Calibration Pipeline. Performs parameter…, Register source inventory and immutable import audit metadata in PostGIS., describe(), pct(), Train a transparent seasonal weather anomaly model from Open-Meteo history., train(), datetime, hashlib (+7 more)

### Community 39 - "package.json"
Cohesion: 0.04
Nodes (45): dependencies, framer-motion, leaflet, lucide-react, react, react-dom, @react-three/drei, @react-three/fiber (+37 more)

### Community 40 - "001_spatial_foundation.sql"
Cohesion: 0.27
Nodes (13): hazard_geography_gist, hazard_geom_gist, hazard_time_idx, public.dataset_versions, public.edge_hazard_reviews, public.hazard_edge_candidates(), public.hazard_observations, public.road_edges (+5 more)

### Community 42 - "Product Requirements Document"
Cohesion: 0.15
Nodes (12): Acceptance Criteria, Future Features, Goals, MVP Features, Non-Goals, Problem Statement, Product Overview, Product Requirements Document (+4 more)

### Community 43 - "Live Feed Readiness, Governance & Operational Procedures"
Cohesion: 0.17
Nodes (11): 1. Safety Guarantees & Presentation Integrity, 2. Monitored Feed Sources & Required Statutory Clearances, 3. Feed Parsing, Reconciliation & Safety Filters, 4. Controlled Dry-Run Procedure, 5. Candidate Advisory Triage & Promotion Procedure, 6. Rollback & Incident Reopening Procedure, Forbidden Claims (Never Claim in Demos or Slides), Live Feed Readiness, Governance & Operational Procedures (+3 more)

### Community 44 - "offlineQueue.ts"
Cohesion: 0.25
Nodes (8): dataUrlToFile(), listQueuedReports(), markQueuedReportFailure(), openDb(), QueuedEvidence, QueuedReport, queueReport(), removeQueuedReport()

### Community 45 - "AGENTS.md"
Cohesion: 0.18
Nodes (9): Additional Documentation, API and Data Conventions, Architecture Overview, Commands, graphify, Project Overview, Repository Structure, Verification Checklist (+1 more)

### Community 46 - "monitor_features"
Cohesion: 0.27
Nodes (8): monitor_features(), population_stability_index(), Small, auditable feature-drift checks for advisory model monitoring., Produce a JSON-safe drift report with transparent warning thresholds., Return PSI; callers should treat this as a monitoring signal, not a prediction., test_identical_feature_distribution_is_stable(), test_monitor_report_is_advisory_and_flags_shift(), collections_abc

### Community 48 - "Project Rules"
Cohesion: 0.18
Nodes (10): Code Organization, Data and Database, Forbidden Practices, General, Performance, Project Rules, Security, Testing (+2 more)

### Community 49 - "004_fleet_tracking.sql"
Cohesion: 0.31
Nodes (10): delivery_jobs_region_status_idx, public.delivery_jobs, public.vehicle_assets, public.vehicle_positions, auth.users, public, public.region_catalog, vehicle_assets_region_idx (+2 more)

### Community 50 - "admin_model_registry"
Cohesion: 0.20
Nodes (10): admin_model_registry(), admin_sources_status(), Return comprehensive freshness, health, and provenance for all 11 pipeline data…, Return model and dataset registry specifications and truth-in-advertising…, load_disruption_model(), predict_disruption_shadow(), Any, Load the trained supervised disruption model artifact if available. (+2 more)

### Community 51 - "RealMapLeaflet.tsx"
Cohesion: 0.20
Nodes (7): FloatingNavProps, RealMapLeafletProps, CITIES, RouteLeg, framer-motion, ref_leaflet_dist_leaflet_css, lucide-react

### Community 52 - "Design System"
Cohesion: 0.20
Nodes (9): Accessibility, Component Patterns, Design Philosophy, Design System, Do Not, Layout, Map and Motion, Tokens (+1 more)

### Community 53 - "Architecture and decisions"
Cohesion: 0.20
Nodes (9): API contract, Architecture and decisions, Components, Data and temporal semantics, Graph semantics, ML milestone, Routing objective, Runtime and deployment (+1 more)

### Community 56 - "voiceRecognition.ts"
Cohesion: 0.22
Nodes (11): handleClickOutside(), CityCombobox(), SupportedLanguage, cleanSpeechToken(), detectPhoneNativeLanguage(), getLocalizedNavInstruction(), getSpeechRecognitionLocale(), matchCityFromVoice() (+3 more)

### Community 57 - "RaahSetu"
Cohesion: 0.20
Nodes (9): Data commands, Features, Google sign-in setup, RaahSetu, Repository map, Start the project on Windows, Supabase and deployment, Verification (+1 more)

### Community 58 - "graphify reference: extra exports and benchmark"
Cohesion: 0.22
Nodes (8): graphify reference: extra exports and benchmark, Step 6b - Wiki (only if --wiki flag), Step 7 - Neo4j export (only if --neo4j or --neo4j-push flag), Step 7a - FalkorDB export (only if --falkordb or --falkordb-push flag), Step 7b - SVG export (only if --svg flag), Step 7c - GraphML export (only if --graphml flag), Step 7d - MCP server (only if --mcp flag), Step 8 - Token reduction benchmark (only if total_words > 5000)

### Community 60 - "routing.py"
Cohesion: 0.12
Nodes (19): load_route_window(), Load a bounded real road window; missing connectivity is never interpolated., assemble_geometry(), Assemble directed OSM shapes without smoothing or inventing road points., distance_m(), Custom A*: directed parallel edges, admissible heuristic, request-scoped costs., heuristic(), main() (+11 more)

### Community 62 - "graphify reference: extra exports and benchmark"
Cohesion: 0.22
Nodes (8): graphify reference: extra exports and benchmark, Step 6b - Wiki (only if --wiki flag), Step 7 - Neo4j export (only if --neo4j or --neo4j-push flag), Step 7a - FalkorDB export (only if --falkordb or --falkordb-push flag), Step 7b - SVG export (only if --svg flag), Step 7c - GraphML export (only if --graphml flag), Step 7d - MCP server (only if --mcp flag), Step 8 - Token reduction benchmark (only if total_words > 5000)

### Community 63 - "Dataset inventory and evidence rules"
Cohesion: 0.22
Nodes (8): Current gaps, Dataset inventory and evidence rules, Historical landslide counts in the spatial subset, Processing rules, Research claim handling, Runtime graph snapshots, Source links and licenses, Sources

### Community 64 - "Disruption model readiness & strict audit status"
Cohesion: 0.22
Nodes (8): Current state, Dataset provenance breakdown (`backend/data/disruption_labels.csv`), Disruption model readiness & strict audit status, Holdout metrics comparison, Remediation implemented in `v1.1`, Safety and governance guarantees, State-wise confusion matrices (`backend/data/disruption_state_metrics.json`), Strict audit findings & remediation

### Community 65 - "VehicleDetailsPage.tsx"
Cohesion: 0.28
Nodes (7): DriverProfile, IntroPageProps, CommodityType, VehicleType, SupportedLanguage, VEHICLE_TRANSLATIONS, VehicleDetailsPageProps

### Community 66 - "Project Memory"
Cohesion: 0.22
Nodes (8): Current Status, Known Problems and Limits, Next Steps, Project Memory, Recent Decisions, Recently Completed, September 7 security follow-up, Session Handoff

### Community 67 - "Testing Strategy"
Cohesion: 0.22
Nodes (8): Commands, Current Test Stack, Definition of Done, Known Boundaries, Philosophy, Required Coverage, Test Data, Testing Strategy

### Community 68 - "RaahSetu (राहसेतु) — Comprehensive Security & Compliance Audit"
Cohesion: 0.25
Nodes (7): 1. Threat Model & Security Architecture, 2. Row Level Security (RLS) Policy Matrix, 3. Authentication & Session Security, 4. Evidence Upload Security & File Handling, 5. Network & HTTP Hardening, 6. Denial-of-Service & State-Poisoning Defenses, RaahSetu (राहसेतु) — Comprehensive Security & Compliance Audit

### Community 69 - "models.py"
Cohesion: 0.33
Nodes (8): EventUpdate, PublicCandidate, PublicCandidateReview, BaseModel, Scenario, StrictModel, Raw AIS-140 NMEA string payload., RawTelemetryRequest

### Community 70 - "Run and deploy"
Cohesion: 0.29
Nodes (6): Before external use, Docker, Kubernetes on cloud VMs, Local development, Run and deploy, Supabase

### Community 71 - "Empirical label acquisition"
Cohesion: 0.29
Nodes (6): Data sources, terrain sampling & road snapping methodology, Disruption-label acquisition, provenance & schema, Empirical label acquisition, Label schema, Leakage prevention & deduplication, Physical Terrain & Weather Grounding

### Community 72 - "TableParser"
Cohesion: 0.29
Nodes (3): HTMLParser, main(), TableParser

### Community 73 - "003_auth_and_review.sql"
Cohesion: 0.29
Nodes (5): public.handle_new_user, on_auth_user_created, public.profiles, auth.users, public.region_catalog

### Community 74 - "Team ke liye start yahan se karo"
Cohesion: 0.29
Nodes (6): Agla coding milestone, App kholo, Kya padhna hai, Pehla demo, Sab kuch verify karo, Team ke liye start yahan se karo

### Community 75 - "graphify reference: query, path, explain"
Cohesion: 0.33
Nodes (5): For /graphify explain, For /graphify path, graphify reference: query, path, explain, Step 0 — Constrained query expansion (REQUIRED before traversal), Step 1 — Traversal

### Community 77 - "graphify reference: query, path, explain"
Cohesion: 0.33
Nodes (5): For /graphify explain, For /graphify path, graphify reference: query, path, explain, Step 0 — Constrained query expansion (REQUIRED before traversal), Step 1 — Traversal

### Community 78 - "Assam public-data acquisition findings"
Cohesion: 0.33
Nodes (5): Assam public-data acquisition findings, Remaining Assam manual gate, Useful official sources, What can be added safely, What cannot be claimed yet

### Community 79 - "Data freshness and versioning"
Cohesion: 0.33
Nodes (5): API contract, Current source states, Data freshness and versioning, Production update sequence, Supabase registry

### Community 80 - "Six-person execution plan"
Cohesion: 0.33
Nodes (5): Questions for the next team meeting, Shared contracts, Six-person execution plan, Suggested next milestones, Working practices

### Community 81 - "AuthPage.tsx"
Cohesion: 0.33
Nodes (7): AuthError, authRequest(), signIn(), signUp(), AuthPage(), AuthPageProps, TRANSLATIONS

### Community 83 - "007_retention_and_operational_guards.sql"
Cohesion: 0.33
Nodes (4): public.delivery_jobs, public.vehicle_positions, delivery_jobs_vehicle_status_idx, vehicle_positions_recorded_brin

### Community 84 - "006_data_freshness.sql"
Cohesion: 0.60
Nodes (5): data_import_runs_source_idx, data_source_registry_status_idx, data_source_registry_validity_idx, public.data_import_runs, public.data_source_registry

### Community 85 - "test_state_hazard_matching.py"
Cohesion: 0.40
Nodes (3): Automated tests for state-wide verified hazard coordinate road matching., Verify that MoRTH highway blackspots snap with high fidelity (<= 25m) to road…, test_morth_blackspot_direct_road_proximity()

### Community 86 - "RaahSetu (राहसेतु) — Official Authority Credentials & RBAC Roles"
Cohesion: 0.40
Nodes (4): 1-Click UI Quick Login, Live Supabase Auth Accounts (verified working sign-in), RaahSetu (राहसेतु) — Official Authority Credentials & RBAC Roles, Role Permission Matrix (Enforced by PostGIS Row Level Security)

### Community 87 - "Completion audit against the original SIH brief"
Cohesion: 0.40
Nodes (4): Completion audit against the original SIH brief, Fresh verification result, Honest remaining dependencies, Requirement matrix

### Community 88 - "External integration handoff"
Cohesion: 0.40
Nodes (4): External integration handoff, Field pilot and calibrated ML, GPS fleet tracking, SMS and WhatsApp

### Community 89 - "Redis operations"
Cohesion: 0.40
Nodes (4): Durable telemetry worker, Local persistent startup, Production security, Redis operations

### Community 90 - "Frontend workspace enhancement — 2026-09-07"
Cohesion: 0.40
Nodes (4): Changes, Frontend workspace enhancement — 2026-09-07, Remaining validation, Verification

### Community 92 - "public.disruption_candidates"
Cohesion: 0.50
Nodes (4): auth.users, public.region_catalog, disruption_candidates_review_idx, public.disruption_candidates

### Community 93 - "graphify reference: add a URL and watch a folder"
Cohesion: 0.50
Nodes (3): For /graphify add, For --watch, graphify reference: add a URL and watch a folder

### Community 94 - "graphify reference: commit hook and native CLAUDE.md integration"
Cohesion: 0.50
Nodes (3): For git commit hook, For native CLAUDE.md integration, graphify reference: commit hook and native CLAUDE.md integration

### Community 95 - "graphify reference: incremental update and cluster-only"
Cohesion: 0.50
Nodes (3): For --cluster-only, For --update (incremental re-extraction), graphify reference: incremental update and cluster-only

### Community 96 - "graphify reference: add a URL and watch a folder"
Cohesion: 0.50
Nodes (3): For /graphify add, For --watch, graphify reference: add a URL and watch a folder

### Community 97 - "graphify reference: commit hook and native CLAUDE.md integration"
Cohesion: 0.50
Nodes (3): For git commit hook, For native CLAUDE.md integration, graphify reference: commit hook and native CLAUDE.md integration

### Community 98 - "graphify reference: incremental update and cluster-only"
Cohesion: 0.50
Nodes (3): For --cluster-only, For --update (incremental re-extraction), graphify reference: incremental update and cluster-only

### Community 99 - "Validation record"
Cohesion: 0.50
Nodes (3): Completed locally, Controlled synthetic benchmark notice, Validation record

### Community 101 - "DataProvenanceDrawer.tsx"
Cohesion: 0.67
Nodes (3): DataProvenanceDrawer(), DataProvenanceDrawerProps, AdminSourceItem

## Knowledge Gaps
- **399 isolated node(s):** `graphify`, `Usage`, `What graphify is for`, `Step 0 - GitHub repos and multi-path merge (only if a URL or several paths)`, `Step 1 - Ensure graphify is installed` (+394 more)
  These have ≤1 connection - possible missing edges or undocumented components. (Counts symbols only; 776 node(s) total have ≤1 connection when file, concept and rationale nodes are included.)
- **39 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `accessibility_events()` connect `Depends` to `Live Feed Readiness, Governance & Operational Procedures`, `RaahSetu (राहसेतु) — Comprehensive Security & Compliance Audit`, `main.py`, `FieldReportStore`?**
  _High betweenness centrality (0.016) - this node is a cross-community bridge._
- **Why does `What judges and evaluators MUST be told (Safe Claims)` connect `Live Feed Readiness, Governance & Operational Procedures` to `Depends`?**
  _High betweenness centrality (0.013) - this node is a cross-community bridge._
- **Why does `RoadGraph` connect `RoadGraph` to `routing.py`, `main.py`, `test_routing.py`?**
  _High betweenness centrality (0.012) - this node is a cross-community bridge._
- **Are the 32 inferred relationships involving `AuthUser` (e.g. with `admin_audit_log()` and `admin_broadcasts()`) actually correct?**
  _`AuthUser` has 32 INFERRED edges - model-reasoned connections that need verification._
- **Are the 7 inferred relationships involving `RoadGraph` (e.g. with `compare_routes()` and `lifespan()`) actually correct?**
  _`RoadGraph` has 7 INFERRED edges - model-reasoned connections that need verification._
- **What connects `graphify`, `Usage`, `What graphify is for` to the rest of the system?**
  _399 weakly-connected nodes found - possible documentation gaps or missing edges._
- **Should `live_ingestion.py` be split into smaller, more focused modules?**
  _Cohesion score 0.06939890710382514 - nodes in this community are weakly interconnected._