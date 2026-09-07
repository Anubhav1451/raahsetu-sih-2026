# Validation record

## Completed locally

- 27 backend tests passed on Python 3.12, including 300 randomized cost comparisons with independent NetworkX Dijkstra.
- 56 ordered synthetic journeys evaluated. 34 produced lower modelled exposure under the default risk preference.
- Frontend TypeScript check and production build passed.
- HTTP checks passed for both the synthetic and Guwahati OSM networks through the running API.
- The real OSM default route returned available status and correctly warned about missing risk data.
- Docker Compose, K8s manifests and CI YAML parsed successfully.
- Raw source files carry SHA-256 receipts. The data audit checks them and verifies HGT gzip/grid integrity.

## Not verified in this environment

- Browser interaction and visual QA of the dashboard were not performed. The preview was opened after a successful HTTP check.
- Docker image execution and Kubernetes deployment were not performed because Docker and kubectl were unavailable.
- Supabase migrations and database round-trips are verified. Hazard-to-edge acceptance
  still requires a domain reviewer before risk scores are promoted into a route snapshot.
- Real-world safety, ETA accuracy, current closure freshness and predictive ML performance remain unvalidated.

Two warnings in the test run originate from installed FastAPI/Starlette dependencies regarding future client API deprecations. They did not fail the tests.

The CSV and JSON evaluation outputs identify the fixture/version. Do not present their exposure reductions as reductions in accident probability.
