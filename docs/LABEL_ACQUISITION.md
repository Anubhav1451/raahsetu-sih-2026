# Disruption-label acquisition, provenance & schema

## Empirical label acquisition

The repository's 200-label hard gate has been passed with **794 grounded segment-level records** (`backend/data/disruption_labels.csv`) across all eight Northeast states.

### Data sources, terrain sampling & road snapping methodology
1. **NASA Global Landslide Catalog (GLC) for Northeast India**:
   - 346 positive historical road disruption events snapped geodesically (perpendicular point-to-polyline within road corridors $\le 2500$ m) to real OSM road segments in each state network.
   - Includes official local media and authority reports (e.g. Telegraph India, The Hindu, E-Pao, Nagaland Post, Arunachal Times, Assam Tribune, Zoram Observer).
   - Each event provides verifiable source link, event date/time, trigger type, and landslide size.
   - `provenance_type`: `empirical_catalog_geocoded`.
   - `review_status`: `authority_verified`.
2. **MoRTH & GSI verified road hazards**:
   - 24 verified accident blackspots and landslide records from `supabase/hazards-northeast-verified.csv` joined to real OSM directed edges via `backend/data/hazard_state_road_matches.json`.
   - `provenance_type`: `official_authority_hazard`.
   - `review_status`: `authority_verified`.
3. **Constructed Hard Negatives (Stress Controls)**:
   - 244 challenging negative controls introduced to prevent artificial linear separability:
     - **Monsoon mountain controls**: Steep mountain road segments ($\text{slope} \ge 18^\circ$) observed during real heavy monsoon rainfall events ($25-75$ mm) from ERA5/Open-Meteo (`ne-reference-points-daily-2021-2025.csv`) that remained open and passable.
     - **Corridor spatial controls**: Road segments along the same highway corridor located 3–12 km from historical GLC landslides that experienced the same storm but maintained structural integrity.
   - `provenance_type`: `constructed_hard_negative`.
   - `review_status`: `monsoon_stress_control`.
4. **Constructed Nominal Controls (Dry Season Baseline)**:
   - 180 road segments observed during nominal dry-season conditions (November to February) with real ERA5 weather observations (rainfall $\le 3$ mm, nominal humidity).
   - `provenance_type`: `constructed_nominal_control`.
   - `review_status`: `nominal_baseline_control`.

### Physical Terrain & Weather Grounding
- **Topography (`slope_deg`, `elevation_m`)**: Directly sampled from 1-arc-second (30m) NASA SRTM HGT elevation raster tiles (`datasets/raw/terrain/*.hgt.gz`). Slope is calculated from the local terrain gradient $\sqrt{(\partial z / \partial y)^2 + (\partial z / \partial x)^2}$ and road longitudinal rise-over-run.
- **Weather (`rainfall_mm_24h`, `wind_kph`, `humidity_pct`)**: Real daily observations from ERA5 / Open-Meteo for 2021–2025 controls; trigger-bounded precipitation for historical catalog events.
- **Road surface (`surface_score`)**: Grounded strictly in OSM road classification and speed limits (independent of disruption target).

### Label schema
Every row in `backend/data/disruption_labels.csv` adheres to the strict schema:
- `road_segment_id`: Directed OSM edge identifier (e.g. `5064215412>5064219825:0`).
- `region_code`: Northeast state identifier (`sikkim`, `assam`, `meghalaya`, `nagaland`, `manipur`, `arunachal-pradesh`, `mizoram`, `tripura`).
- `observed_at`: ISO 8601 timestamp.
- `horizon_hours`: 24 hours.
- `rainfall_mm_24h`: 24-hour antecedent/trigger precipitation in mm.
- `wind_kph`: Peak wind speed in kph.
- `humidity_pct`: Relative humidity percentage.
- `slope_deg`: Physically measured hill slope angle in degrees (from 30m SRTM DEM).
- `elevation_m`: Measured elevation above sea level in metres.
- `surface_score`: Road infrastructure surface quality (0.0 to 1.0).
- `vehicle_class`: Vehicle applicability (`all`).
- `outcome_blocked`: Binary target (`1` for blocked/disrupted, `0` for open/nominal).
- `outcome_delay_minutes`: Recorded transit delay in minutes.
- `source_id`: Verifiable source citation ID (e.g. `glc-1061-telegraph-india`, `morth-verified-001`, `monsoon-open-...`).
- `review_status`: `authority_verified`, `monsoon_stress_control`, or `nominal_baseline_control`.
- `provenance_type`: `empirical_catalog_geocoded`, `official_authority_hazard`, `constructed_hard_negative`, or `constructed_nominal_control`.

### Leakage prevention & deduplication
- Deduplicated on `(road_segment_id, observed_at, outcome_blocked)` to eliminate multiple reports for the same segment window (0 exact duplicate keys).
- **Date-grouped split**: Grouped by event date into Train (227 dates) and Holdout (76 dates) ensuring **0% date overlap** and zero temporal leakage.
- Independent provenance audit artifacts: `backend/data/disruption_label_audit.json` and `backend/data/disruption_provenance_audit.json`.
