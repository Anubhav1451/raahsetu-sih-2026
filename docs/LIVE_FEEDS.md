# Live Feed Readiness, Governance & Operational Procedures

This document defines the live feed ingestion architecture, external source readiness, statutory clearances, operational safety guarantees, and operator procedures for the RaahSetu Northeast logistics platform.

---

## 1. Safety Guarantees & Presentation Integrity

### What judges and evaluators MUST be told (Safe Claims)
1. **Truthful Standby Status**: External government feeds (NDMA SACHET, Central Water Commission, State Highway Traffic Police, and State Disaster Management Authorities) are currently held in **STANDBY** status awaiting official ministerial credentials and subscriber endpoint configurations.
2. **Zero Synthetic Ingestion**: No synthetic, mocked, or fabricated incident alerts are passed off as live government warnings. Feeds in `STANDBY` return zero alerts to the operational queue.
3. **Quarantine by Default**: Early-warning advisories parsed from configured feeds or test suites are registered as `candidate_advisory` items. They are strictly quarantined from the routing engine and **CANNOT inflate edge weights or block highways** in deterministic Risk-A* routing.
4. **Mandatory Human-in-the-Loop Review**: An advisory can only be promoted to an active highway closure when an authorized operations reviewer validates the source evidence, corridor, and road segment ID.
5. **Deterministic Production Controls**: Route pathing relies exclusively on deterministic Risk-A* with authority-confirmed highway closures (`accessibility_events`).
6. **Disruption ML Shadow Mode**: The disruption model v1.1 operates in strict advisory shadow mode (`operational_mode: "shadow_mode"`, `production_ready: false`, cost weight `0.0`). It has zero influence on vehicle routing recommendations.

### Forbidden Claims (Never Claim in Demos or Slides)
- ❌ **DO NOT claim** that NDMA SACHET or CWC live production feeds are streaming live real-time government disaster data into the production routing graph without credentials.
- ❌ **DO NOT claim** that AI / ML is autonomously closing roads, predicting landslides with production certainty, or making autonomous traffic routing decisions.
- ❌ **DO NOT claim** that `STANDBY` means "all highways are safe and clear of hazards". STANDBY explicitly denotes "NOT CONNECTED / AWAITING AUTHORIZED CREDENTIALS".
- ❌ **DO NOT claim** that citizen or candidate reports immediately reroute freight trucks.

---

## 2. Monitored Feed Sources & Required Statutory Clearances

| Source ID | Agency / Platform | Data Format | Freshness Limit | Security Env Variables | Statutory Clearance Required | Default Operational Status |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| `open-meteo` | Open-Meteo NWP Grid | JSON Grid API | 3,600s (1 hr) | *(None required)* | Open-Meteo Non-Commercial / Research License | **ONLINE** |
| `ndma-sachet` | National Disaster Management Authority (NDMA) | CAP XML (v1.2) | 7,200s (2 hrs) | `NDMA_SACHET_FEED_URL`, `NDMA_SACHET_API_KEY` | NDMA SACHET authorized CAP subscriber agreement & IP whitelist | **STANDBY** |
| `cwc-flood` | Central Water Commission (CWC) | REST JSON | 7,200s (2 hrs) | `CWC_FEED_URL`, `CWC_API_KEY` | CWC Hydrological Data Directorate API access MoU | **STANDBY** |
| `traffic-police` | Northeast State Highway Traffic Police / PWD | JSON Feed | 3,600s (1 hr) | `TRAFFIC_INCIDENT_FEED_URL`, `TRAFFIC_FEED_API_KEY` | State Police Traffic Control Room API access clearance | **STANDBY** |
| `sdma-alert` | State Disaster Management Authorities (ASDMA, SDMA) | CAP XML / JSON | 7,200s (2 hrs) | `SDMA_ALERT_FEED_URL`, `SDMA_API_TOKEN` | State Disaster Management Authority nodal officer authorization | **STANDBY** |

---

## 3. Feed Parsing, Reconciliation & Safety Filters

All incoming feeds pass through the automated reconciliation pipeline in `backend/app/live_ingestion.py`:

```
External Alert Feed
        │
        ▼
  Parser Engine (CAP XML / CWC JSON / Traffic JSON)
        │
        ├── Malformed XML / JSON? ──> Log error, mark feed DEGRADED, do not crash
        │
        ▼
  Reconciliation & Deduplication
        │
        ├── Exact Hash / ID duplicate? ──> Suppress redundant ingest, log to audit
        ├── Age > Freshness Threshold? ──> Flag advisory as is_stale=True
        ├── Contradictory claims?     ──> Flag conflict_detected=True, review_status='conflicting'
        │
        ▼
  Quarantine Candidate Store
        │
        └── Stored as 'candidate_advisory' / 'pending_review'
            (Zero routing weight; does NOT block road graph)
```

---

## 4. Controlled Dry-Run Procedure

To test feed parsing logic safely without altering production road graphs or generating live closures:

### Via Admin Operations Panel
1. Open the Admin Operations Panel at `http://127.0.0.1:5173/` (or navigate via the **Operations Console** button in the header).
2. Click the **Live Feed Readiness** tab (indicated by 🛰️).
3. Click the **Parser Diagnostics & Health** button in the top action bar.
4. Click **Execute Controlled Dry-Run Diagnostics**.
5. The panel executes all parsers in isolated memory, verifies XML entity handling, checks coordinate bounds, evaluates deduplication, and displays the diagnostic report and cryptographic audit hash.

### Via REST API
```bash
curl -X POST "http://127.0.0.1:8000/api/v1/admin/feeds/diagnostics/run" \
  -H "Authorization: Bearer <ADMIN_OR_REVIEWER_TOKEN>" \
  -H "Content-Type: application/json" \
  -d '{"dry_run_source": "all"}'
```

Response includes:
- `diagnostic_disclosure`: Explicit statement confirming test isolation.
- `feeds_tested`: List of evaluated feeds.
- `overall_status`: `ALL_PARSERS_OPERATIONAL`.
- `diagnostics`: Per-feed parsed count, error count, and payload validation hash.
- `audit_entry`: Cryptographic audit log ID and action record.

---

## 5. Candidate Advisory Triage & Promotion Procedure

When an early-warning advisory is received in the quarantine queue:

1. **Inspect Advisory**: Open **Live Feed Readiness** -> **Operator Review Queue**.
2. **Review Corroboration**: Click **Triage & Review** on the target advisory card.
3. **Inspect Ground Evidence**: Verify physical evidence (e.g. DC office wireless broadcast, SDRF spot patrol, CWC river gauging station data).
4. **Choose Decision**:
   - **Accept & Promote**: Promotes advisory to an active highway closure. Requires:
     - `source_evidence` ($\ge 5$ characters)
     - `affected_corridor` ($\ge 3$ characters)
     - `road_segment_id` (OSM edge ID in the target network snapshot)
     - `review_note` ($\ge 5$ characters)
   - **Reject**: Marks advisory as rejected; records operational rationale.
   - **Mark Duplicate**: Suppresses advisory as duplicate of an existing verified incident.
   - **Flag Conflicting**: Quarantines advisory when contradictory agency reports exist.
5. **Commit Decision**: Submitting writes an immutable entry into the RaahSetu Audit Store with the reviewer's identity and timestamp.

---

## 6. Rollback & Incident Reopening Procedure

If an advisory was promoted erroneously or conditions on the ground have cleared:

1. **Reopen Corridor**: Navigate to the **Active Closures** tab in the Operations Panel.
2. **Locate Closure**: Find the event corresponding to the road segment.
3. **Resolve Closure**: Click **Resolve Closure**, enter clearance notes (e.g. "PWD earthmovers cleared rockfall at km 42; verified 40T freight passable"), and confirm road reopening.
4. **Immediate Graph Release**: The event's `ends_at` is set to `now()`, immediately releasing the edge in Risk-A* routing.
5. **Re-evaluate Advisory**: Return to the **Live Feed Readiness** tab and change the advisory's status to `rejected` with an explanation note.
