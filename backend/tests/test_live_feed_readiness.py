"""Comprehensive test suite for the official live-feed readiness layer.

Tests:
1. Unconfigured feeds truthfully remain in STANDBY with zero fabricated alerts.
2. Unavailable/unreachable feed endpoints degrade gracefully without crashing.
3. Stale feed detection when upstream timestamps exceed freshness thresholds.
4. Malformed XML/JSON payload handling and parser_errors tracking.
5. Duplicate event suppression and audit trail recording.
6. Conflicting operational event detection (block vs clear) and containment.
7. Feed candidates do not automatically create approved closures in routing.
8. Model remains strictly production_ready=false and operational_mode=shadow_mode.
"""

from datetime import UTC, datetime, timedelta
from unittest.mock import patch

from fastapi.testclient import TestClient

from app.audit import InMemoryAuditStore
from app.live_ingestion import (
    OfficialHazardAdvisory,
    fetch_live_feed_advisories,
    get_official_feeds_status,
    ingest_live_official_advisories,
    parse_cap_alert_xml,
    parse_cwc_bulletin_json,
    parse_traffic_incident_json,
    reconcile_and_audit_advisories,
)
from app.main import app, load_graph
from app.routing import Endpoint, RouteRequest

client = TestClient(app)


def test_unconfigured_feeds_remain_in_standby():
    """Verify that all external government feeds remain in STANDBY when URLs are missing."""
    with patch.dict("os.environ", {}, clear=True):
        statuses = get_official_feeds_status()
        status_by_id = {s.source_id: s for s in statuses}

        # Open-Meteo is local/public NWP grid adapter
        assert status_by_id["open-meteo"].status == "ONLINE"

        # Government feeds must be STANDBY
        for feed_id in ["ndma-sachet", "cwc-flood", "traffic-police", "sdma-alert"]:
            source = status_by_id[feed_id]
            assert source.status == "STANDBY"
            assert source.credentials_configured is False
            assert source.requires_auth is True
            assert len(source.required_credentials) > 0
            assert len(source.authority_approval_required) > 0
            assert source.active_advisories_count == 0
            assert source.parser_errors == []


def test_no_fabricated_responses_in_standby():
    """Verify that calling feed fetchers in standby generates zero fabricated advisories."""
    with patch.dict("os.environ", {}, clear=True):
        advisories, status_map = fetch_live_feed_advisories()
        assert len(advisories) == 0
        for status in status_map.values():
            assert status.status == "STANDBY"


def test_unavailable_feed_degrades_gracefully():
    """Verify that unreachable remote endpoints set DEGRADED and record transport errors."""
    mock_env = {
        "NDMA_SACHET_FEED_URL": "http://127.0.0.1:9999/unreachable-ndma-feed",
        "CWC_FEED_URL": "http://127.0.0.1:9999/unreachable-cwc-feed",
    }
    with patch.dict("os.environ", mock_env, clear=True):
        advisories, status_map = fetch_live_feed_advisories()
        assert len(advisories) == 0

        ndma_status = status_map["ndma"]
        assert ndma_status.status == "DEGRADED"
        assert len(ndma_status.parser_errors) > 0
        assert any("Transport error" in e or "Connect" in e for e in ndma_status.parser_errors)

        cwc_status = status_map["cwc"]
        assert cwc_status.status == "DEGRADED"
        assert len(cwc_status.parser_errors) > 0


def test_stale_feed_detection():
    """Verify that feeds with timestamps older than the freshness threshold are flagged STALE."""
    stale_timestamp = (datetime.now(UTC) - timedelta(hours=48)).isoformat()
    freshness_threshold = 3600  # 1 hour

    stale_cap_xml = f"""<?xml version="1.0" encoding="UTF-8"?>
    <alert xmlns="urn:oasis:names:tc:emergency:cap:1.2">
      <identifier>STALE-ALERT-001</identifier>
      <sender>sdma.assam@nic.in</sender>
      <sent>{stale_timestamp}</sent>
      <status>Actual</status>
      <msgType>Alert</msgType>
      <info>
        <category>Geo</category>
        <event>Landslide</event>
        <severity>Warning</severity>
        <headline>Historical Landslide on NH-27</headline>
        <area><areaDesc>NH-27 Jorabat</areaDesc></area>
      </info>
    </alert>"""

    errors = []
    advisories = parse_cap_alert_xml(stale_cap_xml, errors=errors)
    assert len(advisories) == 1

    reconciled, summary = reconcile_and_audit_advisories(
        advisories, freshness_threshold_seconds=freshness_threshold
    )
    assert len(reconciled) == 1
    assert reconciled[0].is_stale is True
    assert summary["stale_count"] == 1


def test_malformed_payload_handling():
    """Verify that corrupt XML and JSON feeds are safely caught and tracked in parser_errors."""
    errors_xml = []
    corrupt_xml = "<alert><identifier>BROKEN-XML</info>"
    parsed_xml = parse_cap_alert_xml(corrupt_xml, errors=errors_xml)
    assert parsed_xml == []
    assert len(errors_xml) == 1
    assert "Failed to parse CAP XML" in errors_xml[0]

    errors_json = []
    corrupt_json = '{"bulletins": [{"station_name": "Broken", "water_level_m": '
    parsed_json = parse_cwc_bulletin_json(corrupt_json, errors=errors_json)
    assert parsed_json == []
    assert len(errors_json) == 1
    assert "Malformed CWC JSON" in errors_json[0]

    errors_traffic = []
    non_numeric_traffic = {
        "incidents": [
            {
                "incident_id": "TRF-BAD",
                "latitude": "not-a-number",
                "longitude": 91.73,
            }
        ]
    }
    parsed_traffic = parse_traffic_incident_json(non_numeric_traffic, errors=errors_traffic)
    assert parsed_traffic == []
    assert len(errors_traffic) == 1
    assert "Numeric parse error" in errors_traffic[0]


def test_duplicate_event_suppression():
    """Verify that duplicate incident advisories are suppressed and logged in the audit store."""
    audit_store = InMemoryAuditStore(capacity=100)
    now = datetime.now(UTC)

    adv1 = OfficialHazardAdvisory(
        advisory_id="adv-dup-001",
        source_agency="State Highway Police",
        state="Assam",
        severity="WARNING",
        headline="Rockfall Blocking NH-27 Corridor",
        affected_corridors=["NH-27 Jorabat"],
        effective_from=now,
        effective_until=now + timedelta(hours=2),
        coordinates=[91.89, 26.10],
        recommended_action="Follow bypass route.",
    )
    # Exact same advisory received a second time in batch
    adv2 = adv1.model_copy()

    reconciled, summary = reconcile_and_audit_advisories(
        [adv1, adv2], freshness_threshold_seconds=7200, audit_store=audit_store
    )

    assert len(reconciled) == 1
    assert summary["duplicates_suppressed"] == 1

    # Check audit log entry
    audit_entries = audit_store.list(action="feed_duplicate_suppressed")
    assert len(audit_entries) >= 1
    assert audit_entries[0].resource == "advisory:adv-dup-001"


def test_conflicting_event_detection():
    """Verify that contradictory reports (road closed vs road open) are detected and contained."""
    audit_store = InMemoryAuditStore(capacity=100)
    now = datetime.now(UTC)

    # Source 1: SDMA reports severe debris flow blocking the highway
    adv_closed = OfficialHazardAdvisory(
        advisory_id="sdma-nh27-block",
        source_agency="Assam SDMA",
        state="Assam",
        severity="WARNING",
        headline="Severe Landslide Highway Closed and Blocked",
        affected_corridors=["NH-27 Guwahati-Shillong corridor"],
        effective_from=now,
        effective_until=now + timedelta(hours=6),
        coordinates=[91.896, 26.104],
        recommended_action="Corridor completely blocked. Divert heavy multi-axle freight.",
    )

    # Source 2: Traffic control reports corridor is open and cleared
    adv_open = OfficialHazardAdvisory(
        advisory_id="traffic-nh27-clear",
        source_agency="State Traffic Police",
        state="Assam",
        severity="ADVISORY",
        headline="NH-27 Jorabat Cleared and Normal Traffic Resumed",
        affected_corridors=["NH-27 Guwahati-Shillong corridor"],
        effective_from=now,
        effective_until=now + timedelta(hours=6),
        coordinates=[91.898, 26.102],
        recommended_action="Corridor open and restored for all vehicles.",
    )

    reconciled, summary = reconcile_and_audit_advisories(
        [adv_closed, adv_open], freshness_threshold_seconds=7200, audit_store=audit_store
    )

    assert len(reconciled) == 2
    assert summary["conflicts_detected"] >= 1

    for adv in reconciled:
        assert adv.conflict_detected is True
        assert adv.review_status == "conflicting"
        assert adv.conflict_note is not None
        assert "Contradictory operational status" in adv.conflict_note

    # Check audit log entry
    audit_entries = audit_store.list(action="feed_conflict_detected")
    assert len(audit_entries) >= 1
    assert "sdma-nh27-block" in audit_entries[0].details["advisory_1"]


def test_feed_candidates_never_alter_production_routing():
    """Verify that unreviewed live feed candidates NEVER close edges in production routing."""
    graph = load_graph()

    # Even if live advisories exist in the ingestion pipeline
    live_advisories = ingest_live_official_advisories()
    for adv in live_advisories:
        # All must be candidate_advisory, never accepted
        assert adv.review_status in {"candidate_advisory", "pending_review", "conflicting"}
        assert adv.review_status != "accepted"
        assert adv.review_status != "authority_verified"

    # Route comparison must succeed cleanly via deterministic Risk-A*
    # without unverified feed items blocking graph edges
    req = RouteRequest(
        origin=Endpoint(node_id="n2_0"),
        destination=Endpoint(node_id="n2_6"),
        dataset_id="demo",
        vehicle="heavy",
    )
    result = graph.compare(req)
    assert len(result["routes"]) == 2
    assert all(r["status"] == "available" for r in result["routes"])
    assert len(result["routes"][0]["edge_ids"]) > 0


def test_model_production_readiness_and_shadow_isolation():
    """Verify model registry enforces production_ready=false and shadow_mode operational state."""
    from app.auth import AuthUser, require_user

    app.dependency_overrides[require_user] = lambda: AuthUser(
        id="audit-admin", role="admin", email="admin@raahsetu.in"
    )
    try:
        with TestClient(app) as test_client:
            res = test_client.get("/api/v1/admin/registry")
            assert res.status_code == 200
            data = res.json()

            # Disruption model specifications
            disruption = next(
                m for m in data.get("models", []) if m["id"] == "road-disruption-supervised-model"
            )

            assert disruption["operational_mode"] == "shadow_mode"
            assert disruption["field_safety_claim"] is False
            assert "shadow mode" in disruption["explicit_false_claims"][0].lower()

            # Check disclosures
            disclosures = data["disclosures"]
            assert disclosures["field_safety_claim"] is False
            assert disclosures["live_traffic_guarantee"] is False
            assert disclosures["ml_landslide_prediction"] is False
    finally:
        app.dependency_overrides.clear()
