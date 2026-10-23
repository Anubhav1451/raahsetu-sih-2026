# AGENTS.md

## Project Overview

RaahSetu is an SIH26002 prototype for explainable logistics routing. The working code is in `backend`, `frontend`, `supabase`, `datasets`, `deploy` and `scripts`.

## Architecture Overview

FastAPI loads immutable graph snapshots into a read-only routing engine. The React/R3F client calls the API; it never receives database credentials. OSM PBF/XML input is prepared offline with Pyosmium and OSMnx. PostGIS stores versioned graph metadata, hazard observations and review decisions.

## Commands

```powershell
.\scripts\setup.ps1
.\scripts\start.ps1
.\scripts\verify.ps1
```

Dashboard: `http://127.0.0.1:5173/`. API docs: `http://127.0.0.1:8000/docs`.

## Repository Structure

- `backend/app`: models, API and routing engine.
- `backend/tests`: algorithm and API tests.
- `frontend/src`: React dashboard and R3F map.
- `supabase`: migrations and import CSVs.
- `datasets`: manifests, receipts and processed public data.
- `docs`: architecture, data, deployment, validation and presentation.
- `scripts`: setup, verification and data preparation.

## Working Rules

- Preserve the prescribed stack unless the team explicitly changes it.
- Keep graph snapshots immutable and versioned.
- Keep route calculations request-scoped and read-only.
- Preserve directed edge IDs and parallel edges.
- Treat missing hazard and vehicle evidence as unknown.
- Do not invent government data, coordinates, traffic, closures or safety improvements.
- Keep secrets in `.env` or a secret manager; never in frontend code, Git or slides.
- Do not commit raw large datasets or generated OSM graphs.

## API and Data Conventions

GeoJSON coordinates are `[longitude, latitude]`. Internal lengths are metres and times are seconds. PostGIS distances use geography metres. Hazard proximity creates review candidates; only accepted reviews may affect a future scoring snapshot.

## Verification Checklist

Run `scripts\verify.ps1` after meaningful changes. For frontend work, also test search, dataset switching, route recalculation, reduced motion and WebGL fallback in a browser.

## Additional Documentation

Read `PRD.md`, `docs/ARCHITECTURE.md`, `DESIGN.md`, `RULES.md`, `DECISIONS.md`, `TESTING.md`, `docs/DATA.md` and `docs/DEPLOYMENT.md` as applicable.

## graphify

This project has a knowledge graph at graphify-out/ with god nodes, community structure, and cross-file relationships.

When the user types `/graphify`, use the installed graphify skill or instructions before doing anything else.

Rules:
- For codebase questions, first run `graphify query "<question>"` when graphify-out/graph.json exists. Use `graphify path "<A>" "<B>"` for relationships and `graphify explain "<concept>"` for focused concepts. These return a scoped subgraph, usually much smaller than GRAPH_REPORT.md or raw grep output.
- Dirty graphify-out/ files are expected after hooks or incremental updates; dirty graph files are not a reason to skip graphify. Only skip graphify if the task is about stale or incorrect graph output, or the user explicitly says not to use it.
- If graphify-out/wiki/index.md exists, use it for broad navigation instead of raw source browsing.
- Read graphify-out/GRAPH_REPORT.md only for broad architecture review or when query/path/explain do not surface enough context.
- After modifying code, run `graphify update .` to keep the graph current (AST-only, no API cost).
