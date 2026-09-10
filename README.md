# RaahSetu

Working name for the SIH26002 team prototype. The final project name is still your team's decision.

An explainable logistics route planner for North-East India. It compares estimated fastest routes with routes that account for road risk, vehicle limits and closures. The stack follows the team blueprint: **React + TypeScript + React Three Fiber, Python 3.12 + FastAPI, OSMnx, Supabase/PostGIS, Docker and Kubernetes on VMs**.

## Start the project on Windows

The environment in `D:\FORSIH` is already installed. From PowerShell in this folder:

```powershell
.\scripts\start.ps1
```

Open http://127.0.0.1:5173/ for the dashboard. API documentation is at http://127.0.0.1:8000/docs.

On a new teammate's computer, install Python 3.12, Node.js 24 and Git, then run:

```powershell
.\scripts\setup.ps1
.\scripts\start.ps1
```

Stop processes created by the helper with `scripts/stop.ps1`. The helper never stops unrelated processes.

Alternatively, use two terminals:

```powershell
# Terminal 1, repository root
.\.venv\Scripts\python.exe -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000

# Terminal 2
cd frontend
npm.cmd run dev
```

## Features

- Custom A* implemented with a priority queue, an admissible heuristic and explicit edge reconstruction.
- Directed parallel roads, known truck limits, strict checking of missing limits, blocked roads and unreachable destinations.
- Fastest and risk-aware route comparison using the same road graph and scenario.
- Interactive R3F terrain, route overlays, vehicle selection, risk preference, scenario changes and JSON export.
- Two local network options when the OSM pilot is prepared: a deterministic synthetic sandbox and a real Guwahati OSM network.
- State-wise road extraction, public facility extraction, historical weather CSVs and Northeast landslide subsets.
- Live Supabase/PostGIS foundation with eight-state metadata, versioned graph snapshots,
  hazard observations, and geo-tagged field-report APIs.
- Responsive field-official incident form with mapped origin coordinates, offline-safe
  client IDs, validation, pending moderation state and recent regional reports.
- Nearby independent reports are counted in a 1 km / 6-hour evidence window; they remain
  warnings until an assigned reviewer or admin confirms the incident and road edge.
- Reviewer-approved accessibility events are exposed as active map markers; evidence
  storage is private and scoped to the submitting user's folder.
- Reviewers explicitly match accepted incidents to nearby versioned road edges; accepted
  blocked events become request-time closures for the custom A* engine.
- JPEG, PNG and WebP field evidence uploads use authenticated private storage with a
  10 MB limit and SHA-256 metadata.
- Container definitions, Kubernetes deployment examples, CI and a six-person delivery plan.

## What the prototype does not claim

The synthetic network has fictional roads and hazards. The real OSM network does not yet have reviewed blackspot/landslide matches, so it explicitly reports missing risk evidence. Weather controls simulate conditions. Travel time is estimated without live traffic. Risk exposure is an index, not an accident probability. The current scoring is rule-based, not a trained predictive ML model.

The app is a hackathon prototype, not operational dispatch or navigation. A packaged
field mobile client, push/SMS alert delivery, turn restrictions, sustained load testing
and live government feeds remain backlog work. Authenticated browser GPS sharing,
delivery status, reviewed alerts, installable PWA assets and an offline field-report queue
are implemented. The team Supabase project is connected; VM/Kubernetes deployment still
requires the team's cloud account.

## Repository map

| Folder | Owner / purpose |
|---|---|
| `backend/app` | API models and custom routing engine |
| `backend/tests` | Algorithm correctness and API tests |
| `backend/scripts` | OSMnx preparation, evaluation and PostGIS import/export |
| `frontend/src` | React dashboard and Three.js terrain |
| `supabase` | Spatial schema and example hazard CSV |
| `datasets/raw` | Original downloaded files plus receipts |
| `datasets/processed` | State subsets, road extracts and analysis-ready tables |
| `scripts` | Setup, startup, downloads and data processing |
| `deploy/k8s` | VM-hosted Kubernetes deployment examples |
| `docs` | Architecture, dataset evidence, team plan and presentation |

Large datasets and generated OSM graphs stay out of Git. Preserve download manifests and source receipts alongside any shared data archive.

## Data commands

```powershell
.\.venv\Scripts\python.exe scripts/download_data.py
.\.venv\Scripts\python.exe scripts/prepare_geography.py
.\.venv\Scripts\python.exe scripts/download_data.py --catalog datasets/catalog-terrain.json
.\.venv\Scripts\python.exe scripts/download_data.py --catalog datasets/catalog-weather-landslides.json
.\.venv\Scripts\python.exe scripts/extract_osm.py
.\.venv\Scripts\python.exe backend/scripts/import_osm.py --xml datasets/processed/osm/guwahati-pilot-roads.osm --name guwahati
.\.venv\Scripts\python.exe scripts/build_terrain.py
.\.venv\Scripts\python.exe scripts/process_evidence.py
.\.venv\Scripts\python.exe backend/scripts/build_guwahati_corridor.py
.\.venv\Scripts\python.exe scripts/build_ne_coverage_catalog.py
```

`prepare_geography.py` needs the India ADM1 boundary download. Its exact pinned URL is in `datasets/catalog-additional.json`; run the downloader with that catalog first on a new machine. Sources can change. Check each manifest for unavailable files and rerun failed sources only when useful.

Read `docs/DATA.md` before using a source in risk scoring. Never treat aggregate state accident counts as road coordinates or historical landslides as current closures.

The corridor builder creates `osm-guwahati-corridor-reviewed-v1` from two 1 km accuracy historical observations near Dispur and Chandmari. It is a reproducible provisional pilot snapshot; run domain review before operational use.

`datasets/processed/ne-coverage-catalog.json` is the explicit Northeast coverage manifest: all eight states, all eight capitals, OSM road extracts and facility files with counts.

## Verification

```powershell
.\scripts\verify.ps1
```

The command above runs the complete local test, evaluation, data-integrity and frontend-build sequence. Individual commands are:

```powershell
.\.venv\Scripts\python.exe -m pytest backend/tests -q
.\.venv\Scripts\ruff.exe check backend scripts
.\.venv\Scripts\python.exe backend/scripts/evaluate.py
cd frontend
npm.cmd run build
```

The tests include 300 randomized A*/independent-Dijkstra cost comparisons across vehicle and weather settings, plus deterministic closure, multigraph, input validation and concurrency checks. The evaluation CSV covers 56 ordered journeys in the synthetic fixture. It is not a real-world safety evaluation.

See `docs/COMPLETION-AUDIT.md` for the requirement-by-requirement completion record and external dependencies.

## Supabase and deployment

The local `.env` contains the backend-only Supabase pooler connection. Use
`scripts/setup_supabase.ps1` for a fresh environment and the commands in
`docs/DEPLOYMENT.md` for controlled imports. No privileged database credential belongs in
the frontend.

Docker and Kubernetes definitions are prepared. Their runtime verification requires Docker/K8s, which were unavailable on the development machine. Read the deployment guide before exposing the app externally.

OpenStreetMap data © OpenStreetMap contributors, available under ODbL 1.0. See `docs/DATA.md` for source-specific attribution and limitations.
