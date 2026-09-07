# Completion audit against the original SIH brief

Audit date: 2026-09-07

This file separates implemented work from work that needs accounts, restricted data, field review or a final team decision. A prepared configuration is not described as a live deployment.

## Requirement matrix

| Original requirement | Status | Evidence |
|---|---|---|
| Custom risk-aware A* routing | Complete for the prototype | `backend/app/routing.py`; directed keyed edges, request-scoped costs and explicit path reconstruction |
| Distance plus accident, road-condition and weather risk | Complete for the prototype | Documented edge-cost formula; synthetic scores are clearly labelled and real missing evidence remains unknown |
| Correctness baseline | Complete for tested prototype behavior | 41 backend tests, including 300 randomized A* versus independent NetworkX Dijkstra cost comparisons and reviewer-region access regressions |
| Python 3.12 and FastAPI | Complete | Version-pinned backend, validation models, health/bootstrap/network/terrain/route endpoints and generated OpenAPI contract |
| OSMnx graph processing | Complete | Local PBF/XML import pipeline, directed multigraph conversion and a real Guwahati runtime snapshot |
| React, TypeScript and React Three Fiber | Complete | Interactive 3D terrain dashboard, two-route comparison, scenarios, vehicle profiles and JSON evidence export |
| Supabase PostgreSQL/PostGIS | Live and verified | Three migrations, eight-state catalog, demo and Guwahati graphs, two hazard observations, canonical version reconciliation, private evidence bucket and auth profile trigger are verified; database uses about 35.1 MB |
| Field accessibility reporting | Authenticated reporting, evidence upload, reviewed edge closures and browser offline queue implemented | Dashboard supports sign-in/signup, mapped reports, private photo upload and explicit candidate-edge review. Accepted blocked events affect request-time routing. Candidate lookup enforces assigned reviewer regions. Report payloads and optional evidence are queued in IndexedDB and retried after connectivity returns. |
| GPS fleet tracking and delivery visibility | Secure backend and operator workflow complete | Migration `004_fleet_tracking.sql` adds vehicle assets, position history and delivery jobs. Authenticated API scopes reads by reviewer region, lists assigned vehicles, accepts operator-owned GPS updates, and supports delivery create/status updates with delivered timestamps. The dashboard includes a browser GPS sharing panel; a packaged mobile client remains pending. |
| Disruption alerts and connectivity dashboard | Alert generation and read APIs complete | Accepted field reports now create one blocked-route or restricted-access alert with a stable translation key and expiry. Authenticated `/api/v1/alerts` returns active region-scoped alerts and `/api/v1/connectivity` summarizes open, restricted and blocked events by state. Push/SMS delivery channels remain pending. |
| Docker | Ready for runtime verification | Non-root backend/frontend images and Compose file are present; Docker was unavailable on this machine |
| Kubernetes on cloud VMs | Ready for environment configuration | Two-replica manifests, probes, resource limits and ingress example are present; registry, domain, cluster and TLS belong to the team environment |
| Northeast public data and OSM | Complete for the documented public-source acquisition scope | Eight state OSM extracts and eight validated runtime graph snapshots, 45 terrain tiles, boundaries, 467 historical landslide records, 14,608 weather point-days and road-safety source documents |
| Verified blackspots on every Northeast road | Blocked by evidence availability and human review | Public coordinate-level coverage for all eight states was not found; unreviewed records are deliberately not mapped as facts |
| AI/ML claim | Architecture defined; training not yet defensible | Current scoring is rule-based. A labelled target, reviewed road matches and held-out evaluation are required before training or claiming prediction performance |
| Presentation and six-person execution plan | Complete | Editable 10-slide deck, architecture, evidence boundaries and six ownership tracks |
| Local reproducible demo | Complete | Synthetic decision scenario plus real Guwahati OSM/elevation view; start/stop/setup scripts included |
| One versioned corridor comparison | Complete as a provisional pilot | `backend/scripts/build_guwahati_corridor.py` produces `osm-guwahati-corridor-reviewed-v1`; API loads it and returns available fastest/Risk-A* responses |
| Large-state browser delivery | Complete for bounded GeoJSON MVP | State graphs load on demand; map responses use a focused radius and feature cap while full-graph routing remains server-side |
| Local place and facility search | Complete for OSM-derived coverage | State-wise gazetteers support cities, towns, villages and facilities with nearest-road snapping; all eight capitals verified through the live API |

## Fresh verification result

- Backend tests: 43 passed. Two dependency deprecation warnings do not affect results. Candidate-access and fleet validation cases use mocked or local dependencies; they do not constitute a fresh live Supabase authorization test.
- Frontend production build: passed after the fleet and alert API foundation changes.
- Frontend production build: passed after adding the IndexedDB offline report queue and retry flow.
- Algorithm oracle checks: 300 randomized comparisons passed.
- Synthetic evaluation: 56 journeys available; 34 had lower modelled exposure at the default preference.
- Data audit: 61 source downloads and all 45 planned HGT tiles verified; no terrain tile is missing.
- Frontend: TypeScript and production build passed. The large Three.js bundle produces a performance advisory, not a build failure.
- Local HTTP: frontend and API responded successfully for the prepared runtime.
- Guwahati corridor pilot: two historical 1 km observations matched to OSM candidate edges at 308.0 m and 26.3 m; versioned snapshot loaded by API and route comparison returned available results.
- Eight state runtime graphs: every snapshot passed model/reference validation and fastest plus Risk-A* smoke routing; API discovery and bounded on-demand loading were verified with Sikkim.
- Live browser checks: Sikkim and the 555,819-edge Assam dataset both loaded, rendered focused roads and returned fastest/Risk-A* comparisons without sending the full graph to the browser.
- Named endpoint checks: Itanagar, Dispur, Imphal, Shillong, Aizawl, Kohima, Gangtok and Agartala all resolved in their state datasets; Sikkim city and hospital search were verified in the browser.
- Presentation: 10 slides rendered and visually reviewed; package and layout validation passed.

Run the complete local verification again with:

```powershell
.\scripts\verify.ps1
```

## Honest remaining dependencies

The following still need external access or team decisions: a container registry,
VM/Kubernetes access, TLS/domain ownership, restricted eDAR access, final SIH wording,
team member names and domain-expert acceptance of hazard-to-road matches. Guwahati is the
versioned comparison corridor; all eight state road snapshots remain selectable locally.

After those inputs arrive, the next implementation release should apply the migration, import reviewed observations, publish a versioned graph snapshot, deploy the two images and record latency plus route-quality evidence on a fixed corridor test set.
