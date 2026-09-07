# Decision Log

## Custom Risk-A* engine

### Date
2026-09-06

### Status
Accepted for MVP

### Context
The project must compare fastest and safer logistics routes using a custom algorithm.

### Options Considered
Third-party directions API, Dijkstra, and custom A*.

### Decision
Use custom directed A* with an admissible lower-bound heuristic. Put risk in edge cost, not in an unsafe heuristic.

### Reasoning
This keeps the route decision explainable, preserves parallel roads and supports vehicle, weather and closure constraints.

### Trade-offs
More engineering and data preparation than an API wrapper; no live traffic by default.

## Northeast-first, region-wise graphs

### Date
2026-09-06

### Status
Accepted

### Context
All-India OSM geometry is too large for one browser payload and the hackathon demo needs a bounded reliable pilot.

### Decision
Acquire all eight Northeast states, prepare state/region snapshots and load the selected graph at runtime. Keep Guwahati as the first pilot.

### Consequences
The UI needs dataset/region selection and graph version provenance. Cross-region routing requires a later connected snapshot strategy.

## PostGIS review boundary

### Date
2026-09-06

### Status
Accepted

### Decision
PostGIS proximity creates hazard-to-road candidates. A human review decision is required before evidence affects routing risk.

### Reasoning
Historical coordinates, parallel roads, bridges and stale incidents make automatic snapping unsafe.

## Unknown risk semantics

### Date
2026-09-06

### Status
Accepted

### Decision
Missing risk data is displayed as unknown and never as safe.

### Consequences
Real OSM route comparisons may remain incomplete until reviewed evidence is available.
