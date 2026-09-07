# Project Memory

## Current Status

RaahSetu is a working local SIH26002 MVP in `D:\FORSIH`. FastAPI runs on port 8000 and the React/R3F dashboard on port 5173. The dashboard supports synthetic, Guwahati OSM and provisional reviewed Guwahati corridor datasets, road/place search, route comparison, scenarios and an OSM SVG fallback when WebGL is unavailable.

## Recently Completed

- Eight Northeast state OSM road extracts and facility files acquired.
- Northeast coverage catalog with all eight states and capitals generated.
- Guwahati corridor snapshot created from two historical 1 km observations.
- Custom Risk-A* and 27-test verification suite established.
- Supabase/PostGIS schema, CSV imports and deployment manifests prepared.

## Known Problems and Limits

Supabase cloud credentials and live round-trip are not configured. Verified coordinate-level blackspot coverage is incomplete. Weather is reference-point data. Historical hazards are not current closures. Docker/Kubernetes execution and field validation remain pending.

## Recent Decisions

Risk belongs in edge cost; heuristic remains an admissible lower bound. Missing evidence is unknown. OSM graphs are prepared and loaded region-wise rather than all at once in the browser.

## Next Steps

1. Connect the team's Supabase project and run transactional pilot import.
2. Review hazard-to-road candidates with a domain reviewer.
3. Create state-wise runtime graph snapshots and a Northeast selector.
4. Continue frontend search/map/performance enhancement.
5. Validate one fixed corridor and rehearse the demo.

## Session Handoff

Read `PRD.md`, `AGENTS.md`, `docs/ARCHITECTURE.md`, `docs/DATA.md`, `docs/COMPLETION-AUDIT.md` and `TESTING.md` before making a major change. Run `scripts\verify.ps1` after meaningful changes.
