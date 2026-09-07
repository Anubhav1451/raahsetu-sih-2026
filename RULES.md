# Project Rules

## General

Make the smallest coherent change that preserves the existing architecture. Keep behavior explicit and testable. Mark assumptions and provisional evidence in user-visible copy and documentation.

## Code Organization

Routing logic belongs in `backend/app/routing.py`; API translation belongs in `backend/app/main.py`; UI behavior belongs in `frontend/src`; data preparation belongs in `scripts` or `backend/scripts`.

## Type Safety and Errors

Use the existing strict Pydantic models and TypeScript types. Reject invalid coordinates, unknown datasets, unsupported scenarios and unknown edge closures. Return actionable errors without exposing secrets.

## Data and Database

Use WGS84 GeoJSON `[lon, lat]`. Keep source IDs, timestamps, accuracy and provenance. Never convert proximity into accepted road evidence automatically. Use immutable dataset versions and transactional imports.

## UI and State

Keep endpoint selection, search selection and route input synchronized. Abort stale route requests. Provide loading, empty, error, unreachable and reduced-motion states. Keep the OSM fallback functional when WebGL is unavailable.

## Security

No database credentials in the browser. Keep RLS enabled and privileged imports server-side. Do not commit `.env`, service keys or raw personal data.

## Performance

Avoid per-frame React state updates. Reuse Three.js geometry, cap device pixel ratio, limit rendered road detail and lazy-load large visual modules when useful. Measure before optimizing.

## Testing

Run `scripts\verify.ps1`. Routing changes require algorithm tests and an independent baseline comparison. UI changes require a production build and live browser checks for the affected flow.

## Forbidden Practices

Do not claim real-world safety improvement from synthetic exposure. Do not silently apply unreviewed hazards. Do not replace the custom routing engine with a third-party route API. Do not load all India geometry into one browser payload.
