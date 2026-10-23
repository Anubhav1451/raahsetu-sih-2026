# Disruption model readiness & strict audit status

## Current state

- **Weather anomaly model**: Locked and available.
- **Disruption model gate**: Passed at `794/200` audited outcomes across all 8 Northeast states. The file contains 370 empirical/authority-positive records and 424 constructed controls; provenance is never hidden.
- **Model version**: `v1.1-audited-grounded` (retrained following independent provenance audit and hard-negative grounding).
- **Deployment mode**: Strictly active in advisory `shadow_mode`.
- **Production routing**: Governed by deterministic Risk-A* and official government road closure decrees. Supervised model does NOT alter routing weights.
- **Production ready**: `false` (pending real-world field trials and formal human safety signoff).

## Strict audit findings & remediation

An independent audit of the previous `v1.0` benchmark revealed:
1. **Separability defect**: Previous holdout metrics were artificially perfect (F1 = 1.0) because negative controls were low-rainfall dry winter observations with no hard negatives.
2. **Derived features**: Topography and rainfall had been derived from catalog-trigger formulas rather than physical raster or gauge data.
3. **Observation clustering**: Multiple events were clustered on duplicate observation dates.

### Remediation implemented in `v1.1`
- **Raw terrain grounding**: All segment slopes and elevations are now physically sampled from 1-arc-second (30m) NASA SRTM HGT raster tiles (`datasets/raw/terrain/*.hgt.gz`).
- **Real weather grounding**: Modern negative controls ingest actual daily observations from ERA5 / Open-Meteo (`ne-reference-points-daily-2021-2025.csv`).
- **Authentic hard negatives added**: 244 hard negative controls (steep mountain road segments with slope $\ge 18^\circ$ under real heavy monsoon rain $\ge 25$ mm, plus spatial corridor controls 3–12 km from historical landslides) were incorporated.
- **Date-grouped holdout split**: Event dates were partitioned into Train (594 samples, 227 dates) and Holdout (200 samples, 76 dates) with verified zero date overlap (0% temporal/event leakage).
- **Uncoupled surface scoring**: Road surface attributes are derived strictly from road infrastructure hierarchy (NH vs SH vs local), eliminating target-variable leakage.

## Dataset provenance breakdown (`backend/data/disruption_labels.csv`)

Total rows: **794**
- **Empirical NASA GLC historical events**: 346 (`provenance_type: "empirical_catalog_geocoded"`, `review_status: "authority_verified"`)
- **MoRTH / GSI verified hazards**: 24 (`provenance_type: "official_authority_hazard"`, `review_status: "authority_verified"`)
- **Constructed hard negatives**: 244 (`provenance_type: "constructed_hard_negative"`, `review_status: "monsoon_stress_control"`)
- **Constructed nominal baseline controls**: 180 (`provenance_type: "constructed_nominal_control"`, `review_status: "nominal_baseline_control"`)
- **Exact duplicate keys**: 0
- **Unique road segments**: 715

## Holdout metrics comparison

| Metric | Previous Synthetic Baseline (`v1.0`) | Audited Grounded Model (`v1.1`) | Interpretation |
| :--- | :--- | :--- | :--- |
| **Accuracy** | 1.000 | **0.6950** (69.5%) | Grounded realistic discrimination |
| **Precision** | 1.000 | **0.6993** (69.9%) | Robust precision under hard negatives |
| **Recall** | 1.000 | **0.8475** (84.8%) | High safety recall (minimizes missed disruptions) |
| **F1-Score** | 1.000 | **0.7663** (76.6%) | Balanced harmonic performance |
| **Brier Score** | 0.0009 | **0.2161** | Non-trivial, calibrated probabilistic loss |
| **Expected Calibration Error** | 0.0208 | **0.0868** (8.7%) | Well-calibrated probabilities across risk bins |
| **Temporal Leakage** | Present (clustering) | **0.0%** (date-grouped disjoint split) | Zero event-date contamination |

## State-wise confusion matrices (`backend/data/disruption_state_metrics.json`)

| State | Samples | Pos / Neg | Hard Neg | TP | FP | TN | FN | Accuracy | F1-Score | ROC-AUC |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| **Arunachal Pradesh** | 133 | 62 / 71 | 42 | 55 | 26 | 45 | 7 | 75.2% | 0.769 | 0.814 |
| **Assam** | 7 | 7 / 0 | 0 | 7 | 0 | 0 | 0 | 100.0% | 1.000 | — |
| **Manipur** | 183 | 89 / 94 | 51 | 74 | 36 | 58 | 15 | 72.1% | 0.744 | 0.783 |
| **Meghalaya** | 85 | 40 / 45 | 26 | 27 | 15 | 30 | 13 | 67.1% | 0.659 | 0.775 |
| **Mizoram** | 86 | 37 / 49 | 32 | 32 | 17 | 32 | 5 | 74.4% | 0.744 | 0.815 |
| **Nagaland** | 171 | 81 / 90 | 51 | 68 | 30 | 60 | 13 | 74.9% | 0.760 | 0.806 |
| **Sikkim** | 110 | 49 / 61 | 38 | 37 | 23 | 38 | 12 | 68.2% | 0.679 | 0.790 |
| **Tripura** | 19 | 5 / 14 | 4 | 3 | 2 | 12 | 2 | 78.9% | 0.600 | 0.900 |

*Geographic holdout generalization (Sikkim evaluated out-of-state)*: Accuracy 71.8%, F1 0.726, ROC-AUC 0.788.

## Safety and governance guarantees

1. **Advisory only**: The supervised disruption model runs strictly in shadow mode; it does NOT alter production edge traversability weights or trigger automated road closures.
2. **Deterministic safety fallback**: Deterministic Risk-A* routing and official government road closure decrees remain the authoritative ground truth for all navigation decisions.
3. **Truth in advertising**: Artifact SHA-256 (`backend/data/disruption_model.json`), provenance disclosures, and explicit disclaimer (`production_ready: false`) are published via `/api/v1/admin/registry`.
4. **Prerequisites for production activation**: Real-world field trials, continuous telematics ground truth collection, and formal safety committee signoff.
