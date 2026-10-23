# Validation record

## Completed locally

- 27 backend tests passed on Python 3.12, including 300 randomized cost comparisons with independent NetworkX Dijkstra.
- 56 ordered synthetic journeys evaluated. 34 produced lower modelled exposure under the default risk preference.
- Frontend TypeScript check and production build passed.
- HTTP checks passed for both the synthetic and Guwahati OSM networks through the running API.
- The real OSM default route returned available status and correctly warned about missing risk data.
- 24 verified Northeast hazard points matched against 8 real state OSM road networks with geodesic perpendicular snapping in `hazard_state_road_matches.json`.
- Automated scheduled data refresh runner verified (`scripts/scheduled_refresh.py`).
- Frontend production bundle size optimized: Three.js core and R3F chunks separated, eliminating the >1000 kB bundle size warning.

## Controlled synthetic benchmark notice

The 56 ordered journeys evaluation is an in-silico algorithmic Pareto trade-off benchmark on the controlled graph fixture. It measures simulated exposure index reduction against detour transit penalty in a mathematical model. It is explicitly NOT an empirical field road safety claim or verified real-world collision reduction study.

The CSV and JSON evaluation outputs identify the fixture/version. Do not present their exposure reductions as reductions in accident probability.

