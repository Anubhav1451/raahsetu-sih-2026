# Testing Strategy

## Philosophy

Verify route correctness, request isolation, provenance and user-visible uncertainty. Synthetic evaluation demonstrates behavior; it is not a field safety study.

## Current Test Stack

- Python `pytest` with FastAPI test client.
- NetworkX as an independent shortest-path oracle.
- Ruff for Python quality checks.
- TypeScript compiler and Vite production build.
- Live HTTP and browser checks for integrated UI behavior.

## Required Coverage

- A* and Dijkstra cost agreement across vehicles, weather and journeys.
- Parallel directed edges, closures, vehicle limits, unreachable routes and zero-length endpoint behavior.
- Pydantic coordinate and request validation.
- API CORS, unknown dataset and unsupported scenario errors.
- Search result selection updates endpoint state and route input.
- Synthetic and real OSM dataset loading.
- WebGL fallback, reduced motion and visible loading/error states.

## Test Data

The deterministic synthetic graph supports controlled route-cost experiments. The Guwahati OSM graph supports integration checks with unknown-risk warnings. The provisional corridor snapshot uses two historical observations and must not be treated as live safety ground truth.

## Commands

```powershell
.\scripts\verify.ps1
```

This runs backend tests, Ruff, the 56-journey evaluation, data integrity audit and frontend production build.

## Definition of Done

A change is complete when relevant tests pass, the production build passes, API contracts remain valid, provenance and uncertainty are preserved, and the affected browser flow has been checked. Docker/Kubernetes and Supabase round-trip checks are required once those environments are available.

## Known Boundaries

Live traffic freshness, ETA accuracy, operational blackspot completeness, trained ML performance, cloud deployment and field safety outcomes are not validated by the current test suite.
