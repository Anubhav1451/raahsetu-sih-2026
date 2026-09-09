# Project Memory

## Current Status

RaahSetu is a working local SIH26002 MVP in `D:\FORSIH`. FastAPI runs on port 8000 and the React/R3F dashboard on port 5173. The dashboard supports synthetic, Guwahati OSM and provisional reviewed Guwahati corridor datasets, road/place search, route comparison, scenarios and an OSM SVG fallback when WebGL is unavailable.

## Recently Completed

- Eight Northeast state OSM road extracts and facility files acquired.
- Northeast coverage catalog with all eight states and capitals generated.
- Guwahati corridor snapshot created from two historical 1 km observations.
- Custom Risk-A* and 27-test verification suite established.
- Supabase/PostGIS schema, CSV imports and deployment manifests prepared.
- Fleet foundation added: vehicle assets, GPS position history, delivery jobs and region-scoped FastAPI endpoints.
- Alert and connectivity foundation added: active alert listing and state-wise open/restricted/blocked summaries.
- Delivery workflow added: operators can create jobs for assigned vehicles and update status through delivered/cancelled states.

## Known Problems and Limits

Supabase is connected; prior verification recorded three migrations, eight-state metadata, versioned pilot graphs and private evidence storage. Verified coordinate-level blackspot coverage is incomplete. Weather is reference-point data. Historical hazards are not current closures. Docker/Kubernetes execution and field validation remain pending.

## Recent Decisions

Risk belongs in edge cost; heuristic remains an admissible lower bound. Missing evidence is unknown. OSM graphs are prepared and loaded region-wise rather than all at once in the browser.

## Next Steps

1. Official coordinate-level blackspot/eDAR data and domain review of provisional matches.
2. Public HTTPS deployment (Vercel/Render or team VM) for phone GPS, PWA install and push testing.
3. Physical-device checks: Android PWA install, offline restart, weak-network sync, FPS profiling.
4. Trained ML disruption model only after verified negative road-day samples and held-out evaluation.
5. Rehearse the full field-report-to-rerouting demo with the demo accounts recorded below.

## September 8 milestones

- All five Supabase migrations applied live; fleet, delivery and alert tables verified.
- Full live closure workflow proven: field report (photo evidence) -> reviewer accept + edge bind -> blocked_route alert -> connectivity Assam=blocked -> delivery en_route->delivered.
- Reroute proof: closing Lokhra-Lalganesh Road edge `653996576>653996523:0` changes the u->v journey from 0.99 min/0.645 km to unreachable; reopen restores it.
- Demo accounts (provisioned via `backend/scripts/provision_demo_users.py`, password `DemoSih!2026`):
  officer.demo.0ba846@gmail.com (field_official, assam) and
  reviewer.demo.0ba846@gmail.com (reviewer, assam); vehicles AS01-DEMO-0BA846 (light), AS02-DEMO-0BA846 (heavy).
- Installable PWA (192/512 maskable icons, offline shell v4), mission-control dashboard, Docker/K8s static contract checks in verify pipeline; 44 tests, PWA/SW/deployment checks and frontend build all pass.
- Idea deck rebuilt on the official SIH six-slide format with live prototype screenshots in `docs/presentation/`.

## September 7 security follow-up

Road-candidate lookup now checks the report's region before querying spatial matches.
Assigned reviewers cannot inspect another region; administrators retain cross-region access.
Missing reports return 404. Five API/store regression cases cover these boundaries.
The public GitHub repository is Anubhav1451/raahsetu-sih-2026.

## Session Handoff

Read `PRD.md`, `AGENTS.md`, `docs/ARCHITECTURE.md`, `docs/DATA.md`, `docs/COMPLETION-AUDIT.md` and `TESTING.md` before making a major change. Run `scripts\verify.ps1` after meaningful changes.
