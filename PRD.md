# Product Requirements Document

## Product Overview

RaahSetu is an explainable logistics route-planning prototype for SIH26002. It compares an estimated fastest route with a custom risk-aware A* route using road-network, vehicle, weather, closure and reviewed hazard evidence.

## Target Users

- Logistics operators planning heavy vehicle journeys.
- Emergency fleet coordinators.
- Reviewers validating road-hazard evidence.
- Hackathon judges evaluating route decisions and provenance.

## Problem Statement

Fastest-route navigation can select roads with known or suspected accident, surface or weather exposure. Heavy logistics and emergency fleets need a route decision that exposes the time-versus-risk tradeoff and respects vehicle constraints.

## Goals

- Produce reproducible fastest and risk-aware route comparisons.
- Make every route result explainable through graph version, assumptions and evidence.
- Cover Northeast India through state-wise OSM data acquisition, with Guwahati as the first runtime pilot.
- Demonstrate the workflow in a clear React/Three.js interface.
- Preserve unknown risk as unknown rather than treating it as safe.

## Non-Goals

- Operational dispatch or navigation guarantees.
- Claiming accident probability reduction from a rule-based index.
- Automatically accepting unverified blackspots or historical incidents.
- Loading all India road geometry into the browser at once.
- Live traffic, GPS tracking, turn restrictions or trained ML prediction in the current MVP.

## MVP Features

- Directed OSM-derived graph and custom admissible A* search.
- Fastest versus risk-aware route comparison.
- Heavy, emergency and light vehicle profiles.
- Weather and closure scenarios.
- Real Guwahati OSM pilot and provisional reviewed corridor snapshot.
- React Three Fiber terrain view with OSM fallback map.
- Road/place search for loaded datasets.
- Supabase/PostGIS schema and transactional import tools.
- Provenance, assumptions, warnings and JSON export.

## User Flow

1. Select a loaded road network.
2. Search or select origin and destination.
3. Choose vehicle profile, risk preference and scenario.
4. Compare fastest and risk-aware routes.
5. Inspect map, explanations, warnings and source provenance.
6. Export the exact comparison input and result.

## Future Features

Reviewed hazard workflows, authenticated field reports, state-wise runtime graph selection, live permitted feeds, turn restrictions, multi-stop routing, offline support, ML after labelled-data validation, and cloud deployment.

## Technical Constraints

React + TypeScript + React Three Fiber, Python 3.12 + FastAPI, OSMnx graph processing, Supabase PostgreSQL/PostGIS, Docker and Kubernetes on VMs. Large raw OSM and terrain files remain outside Git and are loaded through versioned storage or offline preparation.

## Success Metrics

- Supported A* results match an independent shortest-path baseline.
- Route requests return a reproducible dataset version and assumptions.
- Missing evidence is visible in the UI.
- The fixed synthetic evaluation remains reproducible.
- A selected real corridor can be reviewed and versioned before operational claims.

## Acceptance Criteria

- Backend tests, routing oracle checks, lint and frontend build pass.
- Synthetic and real OSM datasets load successfully.
- Search selection updates the route endpoints and recalculates the route.
- No safety claim is made without reviewed evidence and a documented evaluation set.
