import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient

from app.auth import AuthUser, require_reviewer, require_user
from app.main import app, get_field_report_store


def test_missing_and_invalid_bearer_rejected():
    for header in (None, "", "Basic credentials"):
        with pytest.raises(HTTPException) as error:
            require_user(header)
        assert error.value.status_code == 401


def test_field_official_cannot_review():
    with pytest.raises(HTTPException) as error:
        require_reviewer(AuthUser(id="test", role="field_official"))
    assert error.value.status_code == 403


def test_local_demo_auth_is_explicit_and_non_production(monkeypatch):
    monkeypatch.setenv("ALLOW_DEMO_AUTH", "true")
    monkeypatch.setenv("APP_ENV", "development")
    assert require_user("Bearer demo:reviewer").role == "reviewer"
    assert require_user("Bearer demo:admin").role == "admin"

    monkeypatch.setenv("APP_ENV", "production")
    monkeypatch.setenv("SUPABASE_URL", "")
    monkeypatch.setenv("SUPABASE_PUBLISHABLE_KEY", "")
    with pytest.raises(HTTPException) as error:
        require_user("Bearer demo:reviewer")
    assert error.value.status_code == 503


def test_region_restriction_and_cors():
    class Store:
        def list(self, region_code, limit, *args, **kwargs):
            assert region_code == "sikkim"
            return []

    app.dependency_overrides[require_user] = lambda: AuthUser(
        id="test", region_code="sikkim"
    )
    app.dependency_overrides[get_field_report_store] = Store
    try:
        with TestClient(app) as client:
            assert client.get("/api/v1/field-reports").status_code == 200
            assert client.get("/api/v1/field-reports?region_code=assam").status_code == 403
            cors = client.options(
                "/api/v1/field-reports/example/review",
                headers={
                    "Origin": "http://127.0.0.1:5173",
                    "Access-Control-Request-Method": "PATCH",
                    "Access-Control-Request-Headers": "authorization,content-type",
                },
            )
            assert cors.status_code == 200
    finally:
        app.dependency_overrides.clear()
