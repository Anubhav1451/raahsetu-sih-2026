from datetime import UTC, datetime, timedelta

import pytest
from fastapi.testclient import TestClient

import app.main as app_main
from app.field_reports import InMemoryFieldReportStore
from app.main import app


@pytest.fixture
def admin_client(monkeypatch):
    monkeypatch.setenv("ALLOW_DEMO_AUTH", "true")
    monkeypatch.setenv("APP_ENV", "development")
    monkeypatch.delenv("DATABASE_URL", raising=False)
    app_main._field_report_store = InMemoryFieldReportStore()
    with TestClient(app) as client:
        yield client


def test_admin_endpoints_unauthenticated(admin_client):
    endpoints = [
        ("GET", "/api/v1/admin/sources-status"),
        ("POST", "/api/v1/admin/sources/osm-sikkim/refresh"),
        ("GET", "/api/v1/admin/telemetry/health"),
        ("GET", "/api/v1/admin/cache/health"),
        ("GET", "/api/v1/admin/audit-log"),
        ("GET", "/api/v1/admin/registry"),
        ("GET", "/api/v1/admin/alerts/broadcasts"),
    ]
    for method, path in endpoints:
        resp = admin_client.request(method, path)
        assert resp.status_code == 401, f"{method} {path} should require auth, got {resp.status_code}"


def test_field_official_forbidden_on_reviewer_and_admin_endpoints(admin_client):
    headers = {"Authorization": "Bearer demo:field_official"}
    
    # Audit log requires admin -> 403
    resp = admin_client.get("/api/v1/admin/audit-log", headers=headers)
    assert resp.status_code == 403

    # Source refresh requires admin -> 403
    resp = admin_client.post("/api/v1/admin/sources/osm-sikkim/refresh", headers=headers)
    assert resp.status_code == 403

    # Resolving accessibility event requires reviewer or admin -> 403
    fake_id = "11111111-1111-1111-1111-111111111111"
    resp = admin_client.patch(
        f"/api/v1/accessibility-events/{fake_id}",
        json={"status": "resolved", "note": "Unauthorized attempt"},
        headers=headers,
    )
    assert resp.status_code == 403


def test_reviewer_permissions_and_event_resolution(admin_client):
    headers = {"Authorization": "Bearer demo:reviewer"}

    cache_resp = admin_client.get("/api/v1/admin/cache/health", headers=headers)
    assert cache_resp.status_code == 200
    assert cache_resp.json()["authoritative_store"] == "PostgreSQL/PostGIS"

    # Reviewer can view sources status
    resp = admin_client.get("/api/v1/admin/sources-status", headers=headers)
    assert resp.status_code == 200
    data = resp.json()
    assert "sources" in data
    assert len(data["sources"]) == 11
    # Check that each source has required fields
    for source in data["sources"]:
        assert "id" in source
        assert "name" in source
        assert "status" in source
        assert "coverage_scope" in source
        assert "disclaimer" in source

    # List active events
    events_resp = admin_client.get("/api/v1/accessibility-events?include_inactive=true")
    assert events_resp.status_code == 200
    events_data = events_resp.json()
    assert "events" in events_data
    events = events_data["events"]
    assert len(events) >= 1
    event = events[0]
    event_id = event["id"]

    # Reviewer can resolve an event
    resolve_resp = admin_client.patch(
        f"/api/v1/accessibility-events/{event_id}",
        json={"status": "resolved", "note": "Resolved by inspector post-clearance"},
        headers=headers,
    )
    assert resolve_resp.status_code == 200
    updated = resolve_resp.json()
    assert updated["status"] == "resolved"
    assert updated["ends_at"] is not None

    # Reviewer can extend expiry
    new_expiry = (datetime.now(UTC) + timedelta(hours=48)).isoformat()
    extend_resp = admin_client.patch(
        f"/api/v1/accessibility-events/{event_id}",
        json={"ends_at": new_expiry, "note": "Extending closure due to continued rockfall"},
        headers=headers,
    )
    assert extend_resp.status_code == 200
    assert extend_resp.json()["ends_at"] is not None


def test_admin_capabilities_and_audit_log(admin_client):
    headers = {"Authorization": "Bearer demo:admin"}

    # Admin can refresh a source
    refresh_resp = admin_client.post("/api/v1/admin/sources/weather-data/refresh", headers=headers)
    assert refresh_resp.status_code == 200
    unsupported_refresh = admin_client.post("/api/v1/admin/sources/osm-sikkim/refresh", headers=headers)
    assert unsupported_refresh.status_code == 409
    res = refresh_resp.json()
    assert res["status"] == "success"
    assert res["source_id"] == "weather-data"

    # Admin can view telemetry health
    telemetry_resp = admin_client.get("/api/v1/admin/telemetry/health", headers=headers)
    assert telemetry_resp.status_code == 200
    t_data = telemetry_resp.json()
    assert "rejection_summary" in t_data
    assert "simulated_disclosure" in t_data
    assert "recent_rejections" in t_data
    assert len(t_data["recent_rejections"]) > 0
    # Check rejection structure
    rejection = t_data["recent_rejections"][0]
    assert "vehicle_id" in rejection
    assert "reason" in rejection

    # Admin can view model registry
    registry_resp = admin_client.get("/api/v1/admin/registry", headers=headers)
    assert registry_resp.status_code == 200
    reg_data = registry_resp.json()
    assert "models" in reg_data
    assert len(reg_data["models"]) == 4
    for model in reg_data["models"]:
        assert "explicit_false_claims" in model
        assert "name" in model

    # Admin can view broadcast history
    broadcast_resp = admin_client.get("/api/v1/admin/alerts/broadcasts", headers=headers)
    assert broadcast_resp.status_code == 200
    b_data = broadcast_resp.json()
    assert "broadcasts" in b_data
    assert len(b_data["broadcasts"]) >= 2
    # Validate delivery statuses
    assert all("deliveries" in b for b in b_data["broadcasts"])

    # Admin can query audit log
    audit_resp = admin_client.get("/api/v1/admin/audit-log", headers=headers)
    assert audit_resp.status_code == 200
    data = audit_resp.json()
    assert "entries" in data
    entries = data["entries"]
    assert len(entries) >= 1
    # Check audit fields
    for entry in entries:
        assert "actor_id" in entry
        assert "action" in entry
        assert "resource" in entry
        assert "timestamp" in entry


def test_field_reports_filtering(admin_client):
    headers = {"Authorization": "Bearer demo:admin"}

    # List all field reports
    resp = admin_client.get("/api/v1/field-reports", headers=headers)
    assert resp.status_code == 200
    all_reports = resp.json()
    assert len(all_reports) >= 3

    # Filter by pending
    pending_resp = admin_client.get("/api/v1/field-reports?status=pending", headers=headers)
    assert pending_resp.status_code == 200
    pending_reports = pending_resp.json()
    assert all(r["review_status"] == "pending" for r in pending_reports)


def test_public_candidate_timestamp_semantics_remain_distinct(admin_client):
    headers = {"Authorization": "Bearer demo:reviewer"}
    response = admin_client.get("/api/v1/admin/public-candidates", headers=headers)
    assert response.status_code == 200
    first = next(item for item in response.json() if item["candidate_id"] == "meghalaya-nh206-2026-08-09")
    assert first["review_status"] == "pending"
    assert first["incident_started_at"] is None
    assert first["restriction_effective_at"] == "2026-08-10T22:00:00+05:30"
    assert first["reopening_effective_at"] == "2026-08-10T00:00:00+05:30"
    assert "does not establish the original incident/closure start" in first["evidence_note"]

    # Approval still cannot bypass the original incident timestamp requirement.
    review = admin_client.patch(
        "/api/v1/admin/public-candidates/meghalaya-nh206-2026-08-09/review",
        json={"decision": "approved", "road_segment_id": "candidate-segment", "review_note": "Source reviewed"},
        headers=headers,
    )
    assert review.status_code == 422


def test_all_seeded_public_candidates_remain_pending_until_verified(admin_client):
    headers = {"Authorization": "Bearer demo:admin"}
    response = admin_client.get("/api/v1/admin/public-candidates", headers=headers)
    assert response.status_code == 200
    candidates = {item["candidate_id"]: item for item in response.json()}
    expected = {
        "meghalaya-nh206-2026-08-09",
        "meghalaya-nh6-2024-06",
        "manipur-news-on-air-nh37-2026-06-24",
        "manipur-news-on-air-nh37-2023-08-16",
        "tripura-info-nh8-flood-disruption-2026-07-14",
    }
    assert expected <= candidates.keys()
    for candidate_id in expected:
        candidate = candidates[candidate_id]
        assert candidate["review_status"] == "pending"
        assert candidate["coordinates_verified"] is False
    assert all(item.get("incident_started_at") is None for item in candidates.values())


def test_admin_model_drift(admin_client):
    headers = {"Authorization": "Bearer demo:reviewer"}
    resp = admin_client.get("/api/v1/admin/model-drift", headers=headers)
    assert resp.status_code == 200
    data = resp.json()
    assert "overall_psi" in data
    assert "overall_status" in data
    assert "features" in data
    assert "rainfall_mm_24h" in data["features"]
    assert "slope_deg" in data["features"]
    assert data["advisory_only"] is True
    assert data["overall_status"] in ("stable", "watch", "alert")
