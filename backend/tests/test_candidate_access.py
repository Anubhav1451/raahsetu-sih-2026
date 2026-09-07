from unittest.mock import MagicMock

import pytest
from fastapi.testclient import TestClient

from app.auth import AuthUser, require_reviewer
from app.field_reports import PostgresFieldReportStore
from app.main import app, get_field_report_store


@pytest.mark.parametrize(
    "role,assigned,report_region,expected",
    [
        ("reviewer", "sikkim", "assam", 403),
        ("reviewer", "sikkim", "sikkim", 200),
        ("admin", "sikkim", "assam", 200),
        ("reviewer", None, "assam", 200),
        ("reviewer", "sikkim", None, 404),
    ],
)
def test_candidate_access_checks_report_before_reading_roads(
    monkeypatch, role, assigned, report_region, expected,
):
    store = PostgresFieldReportStore("unused")
    conn = MagicMock()
    conn.execute.return_value.fetchone.return_value = (
        {"region_code": report_region} if report_region else None
    )
    conn.execute.return_value.fetchall.return_value = [
        {"edge_id": "road-1", "name": "Test road", "distance_m": 12},
    ]
    context = MagicMock()
    context.__enter__.return_value = conn
    monkeypatch.setattr(store, "_connect", lambda: context)
    app.dependency_overrides[require_reviewer] = lambda: AuthUser(
        id="reviewer-test", role=role, region_code=assigned,
    )
    app.dependency_overrides[get_field_report_store] = lambda: store
    try:
        with TestClient(app) as client:
            response = client.get(
                "/api/v1/field-reports/11111111-1111-1111-1111-111111111111"
                "/road-candidates?dataset_id=osm-assam",
            )
        assert response.status_code == expected
        if expected == 200:
            assert response.json()["candidates"][0]["edge_id"] == "road-1"
            assert conn.execute.call_count == 2
        else:
            # A rejected request must never execute the spatial candidate query.
            assert conn.execute.call_count == 1
            assert "road-1" not in response.text
    finally:
        app.dependency_overrides.clear()
