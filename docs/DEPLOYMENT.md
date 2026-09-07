# Run and deploy

## Local development

Use `scripts/setup.ps1` on a new machine, then `scripts/start.ps1`. The dashboard uses Vite's same-origin proxy to reach FastAPI. No cloud account is needed for the demo.

## Supabase

1. Create or select the team's Supabase project in Mumbai and enable PostGIS.
2. Apply migrations `001`, `002` and `003`. They add spatial routing data,
   eight-state operations, authenticated roles, the profile trigger and private evidence bucket.
3. Copy `.env.example` to `.env`. Set `DATABASE_URL`, `SUPABASE_URL` and
   `SUPABASE_PUBLISHABLE_KEY`. The publishable key reaches the browser through the backend;
   database credentials never do.
4. Run:

```powershell
.\scripts\setup_supabase.ps1
.\.venv\Scripts\python.exe backend/scripts/supabase_io.py import-graph backend/data/demo-network.json
.\.venv\Scripts\python.exe backend/scripts/supabase_io.py import-hazards supabase/hazards.example.csv
.\.venv\Scripts\python.exe backend/scripts/supabase_io.py export-graph work/roundtrip.json --dataset-id ner-synthetic-v1
```

`setup_supabase.ps1` applies all idempotent migrations, imports all eight region records with boundaries and prints database/table byte usage. Keep the database below the project's quota with operating headroom. Full state graph snapshots stay in versioned object storage or VM volumes rather than the 500 MB database.

The example hazard is explicitly synthetic. Real CSV imports need the same headers with verified coordinates and timestamps. The script preserves duplicate source IDs idempotently. A changed graph requires a new dataset version ID.

For the provisional Guwahati pilot, use `supabase/hazards-guwahati-reviewed.csv`. It contains the two historical observations documented in `datasets/processed/road_safety/guwahati-corridor-review.json`. Importing them stores observations only; the SQL candidate function and `edge_hazard_reviews` workflow still require a human reviewer before operational risk scoring.

`hazard_edge_candidates` returns nearby roads using metre distances. It does not accept a match. Record accepted/rejected decisions in `edge_hazard_reviews`, then implement a reviewed snapshot-scoring job before feeding these observations into runtime routing.

`GET /api/v1/accessibility-events` exposes only currently active reviewer-approved field events for map overlays. It does not close a road automatically; an explicit dataset and road-edge match is required before routing changes.

Reviewers can request `/api/v1/field-reports/{id}/road-candidates` and must submit the selected `dataset_id` and `edge_id` with an acceptance decision. The backend verifies that edge remains within 2 km of the report before creating the accessibility event.

The app uses immutable local graph snapshots for repeatable routing. The live Supabase
project has been verified with eight region records, versioned demo and Guwahati graphs,
hazard candidate queries, and a temporary field-report API round-trip. Keep bulk eight-state
OSM graphs outside the 500 MB database; import compact operational data and selected
versioned corridors instead.

## Docker

```powershell
docker compose up --build
```

Open http://127.0.0.1:8080/. The API image includes only the small demo network. The `.dockerignore` excludes large source datasets. To serve the real OSM pilot, mount `backend/data/osm-guwahati.json` and its terrain JSON into `/app/backend/data/` as read-only files before starting the API. All replicas must use the same graph version.

The Python runtime dependency lock includes platform markers. Node dependencies use `package-lock.json`.

## Kubernetes on cloud VMs

The manifests assume the team has already provisioned a Kubernetes cluster on VMs. They do not create VMs, provision billing resources or install an ingress controller.

1. Build backend and frontend images and push them to the team's container registry.
2. Replace image references in `deploy/k8s/base.yaml` with actual immutable release tags/digests.
3. Replace the example CORS domain. Attach versioned graph storage if serving a real region.
4. Apply `deploy/k8s/base.yaml` and verify readiness.
5. Provision an ingress controller and TLS certificate. Replace the example domain/secret in `ingress.example.yaml`, then apply it.

```text
kubectl apply -f deploy/k8s/base.yaml
kubectl -n raahsetu rollout status deployment/backend
kubectl -n raahsetu rollout status deployment/frontend
kubectl -n raahsetu port-forward service/frontend 8080:80
```

Both workloads run without root and without Kubernetes API tokens. CPU/memory values are starter estimates for the small pilot. Measure memory and latency before loading state-sized graphs or increasing replica counts.

Docker and kubectl were unavailable in the initial environment. YAML structure can be checked locally, but successful cloud deployment must be verified on the team's cluster. Do not describe the prepared manifests as an already deployed service.

## Before external use

Add operator authentication, authorization, rate limits and request limits at the ingress. Define retention and consent for any future GPS or image uploads. Use health checks, central logs and versioned snapshot rollback. These are deployment requirements for the planned external service, not features claimed by the current local prototype.
