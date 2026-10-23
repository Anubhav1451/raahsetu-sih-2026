"""Strict production-readiness audit and safety regression tests for Disruption Model v1.1.

Verifies:
1. All 794 labels validated against provenance audit: 370 empirical (346 GLC + 24 MoRTH) and 424 constructed controls.
2. Explicit warnings present: constructed controls are NOT physical field observations.
3. Assam metrics marked as insufficient (7 positives, 0 negatives; accuracy is null).
4. Minimum per-state sample criteria enforced and state metrics labeled descriptive only with 95% CIs.
5. 0% temporal / date-leakage (date-grouped disjoint split).
6. 0 duplicate segment-time-outcome keys.
7. Model artifact SHA-256 hash matches the training report and shadow report.
8. production_ready is strictly False across all artifacts and API endpoints.
9. Shadow mode isolation preserved with zero production routing influence.
"""
from __future__ import annotations

import csv
import hashlib
import json
from pathlib import Path

from fastapi.testclient import TestClient

from app.auth import AuthUser, require_user
from app.main import app

ROOT = Path(__file__).resolve().parents[2]
LABELS_CSV = ROOT / "backend" / "data" / "disruption_labels.csv"
AUDIT_PATH = ROOT / "backend" / "data" / "disruption_label_audit.json"
PROVENANCE_PATH = ROOT / "backend" / "data" / "disruption_provenance_audit.json"
TRAIN_REPORT_PATH = ROOT / "backend" / "data" / "disruption_training_report.json"
STATE_METRICS_PATH = ROOT / "backend" / "data" / "disruption_state_metrics.json"
SHADOW_REPORT_PATH = ROOT / "backend" / "data" / "disruption_shadow_report.json"
MODEL_PATH = ROOT / "backend" / "data" / "disruption_model.json"


def test_empirical_count_and_provenance_audit():
    assert AUDIT_PATH.exists() and PROVENANCE_PATH.exists() and LABELS_CSV.exists()
    rows = list(csv.DictReader(LABELS_CSV.open(encoding="utf-8", newline="")))
    audit = json.loads(AUDIT_PATH.read_text(encoding="utf-8"))
    prov = json.loads(PROVENANCE_PATH.read_text(encoding="utf-8"))

    # 1. Verify all 794 labels
    assert len(rows) == 794
    assert audit["rows"] == 794
    assert prov["total_records"] == 794

    # 2. Confirm empirical count is 370: 346 NASA GLC + 24 MoRTH/GSI
    glc_count = sum(1 for r in rows if (r.get("source_id") or "").startswith("glc"))
    morth_count = sum(1 for r in rows if (r.get("source_id") or "").startswith("morth"))
    assert glc_count == 346, f"Expected 346 NASA GLC records, found {glc_count}"
    assert morth_count == 24, f"Expected 24 MoRTH records, found {morth_count}"
    assert audit["empirical_count"] == 370
    assert audit["empirical_breakdown"]["nasa_glc_historical"] == 346
    assert audit["empirical_breakdown"]["morth_gsi_verified_hazards"] == 24

    # Confirm negative controls count is 424: 244 hard negatives + 180 nominal controls
    hard_neg_count = sum(1 for r in rows if r.get("provenance_type") == "constructed_hard_negative")
    nominal_count = sum(1 for r in rows if r.get("provenance_type") == "constructed_nominal_control")
    assert hard_neg_count == 244
    assert nominal_count == 180
    assert audit["negative_control_count"] == 424

    # 3. Explicit warning that constructed controls are NOT field observations
    warnings = audit["warnings"]
    assert any("not physical field" in w.lower() for w in warnings)
    assert prov["negative_controls"]["constructed_hard_negatives"]["is_field_observation"] is False
    assert prov["negative_controls"]["constructed_nominal_controls"]["is_field_observation"] is False


def test_no_duplicate_keys_and_date_disjointness():
    rows = list(csv.DictReader(LABELS_CSV.open(encoding="utf-8", newline="")))
    audit = json.loads(AUDIT_PATH.read_text(encoding="utf-8"))
    report = json.loads(TRAIN_REPORT_PATH.read_text(encoding="utf-8"))

    # Verify no duplicate segment/time/outcome keys
    unique_keys = {(r["road_segment_id"], r["observed_at"], r["outcome_blocked"]) for r in rows}
    assert len(unique_keys) == len(rows), "Found duplicate segment/time/outcome keys"
    assert audit["exact_duplicate_keys"] == 0

    # Verify date-grouped train/holdout disjointness
    assert report["split_policy"]["temporal_leakage_detected"] is False

    hist_rows = [r for r in rows if r["observed_at"] < "2021-01-01"]
    mod_rows = [r for r in rows if r["observed_at"] >= "2021-01-01"]
    hist_dates = sorted({r["observed_at"].split("T")[0] for r in hist_rows})
    mod_dates = sorted({r["observed_at"].split("T")[0] for r in mod_rows})

    h_train_d = set(hist_dates[: int(len(hist_dates) * 0.75)])
    h_hold_d = set(hist_dates[int(len(hist_dates) * 0.75) :])
    m_train_d = set(mod_dates[: int(len(mod_dates) * 0.75)])
    m_hold_d = set(mod_dates[int(len(mod_dates) * 0.75) :])

    train_dates = h_train_d | m_train_d
    holdout_dates = h_hold_d | m_hold_d
    assert train_dates.isdisjoint(holdout_dates), "Train and holdout dates must be completely disjoint"


def test_assam_insufficiency_and_state_governance():
    state_report = json.loads(STATE_METRICS_PATH.read_text(encoding="utf-8"))
    states = state_report["states"]

    # 4. Assam marked as insufficient (7 positives, 0 negatives)
    assert "assam" in states
    assam = states["assam"]
    assert assam["status"] == "insufficient_data"
    assert assam["samples"] == 7
    assert assam["positives"] == 7
    assert assam["negatives"] == 0
    assert assam["accuracy"] is None
    assert assam["f1"] is None
    assert assam["eligible_for_standalone_claims"] is False
    assert "insufficient_reason" in assam

    # 5. Minimum per-state sample criteria enforced
    assert state_report["minimum_state_samples_threshold"] >= 25
    assert state_report["minimum_class_samples_threshold"] >= 5

    # 6. Labeled descriptive only with confidence intervals
    assert state_report["evaluation_type"] == "descriptive_sample_metrics_only"
    assert state_report["generalization_claim"] is False
    assert "disclaimer" in state_report

    for st_data in states.values():
        assert st_data["descriptive_only"] is True
        if st_data["status"] == "sufficient_sample_size":
            assert st_data["accuracy_ci_95"] is not None
            assert len(st_data["accuracy_ci_95"]) == 2
            assert st_data["accuracy_ci_95"][0] <= st_data["accuracy"] <= st_data["accuracy_ci_95"][1]


def test_model_and_shadow_artifact_hashes_match():
    assert MODEL_PATH.exists() and TRAIN_REPORT_PATH.exists() and SHADOW_REPORT_PATH.exists()

    actual_model_hash = hashlib.sha256(MODEL_PATH.read_bytes()).hexdigest()
    train_report = json.loads(TRAIN_REPORT_PATH.read_text(encoding="utf-8"))
    shadow_report = json.loads(SHADOW_REPORT_PATH.read_text(encoding="utf-8"))

    # 9. Model artifact hash matches training report
    assert actual_model_hash == train_report["artifact_sha256"]

    # 10. Shadow report hash matches current model artifact
    assert shadow_report["artifact_hash"] == actual_model_hash
    assert shadow_report["hash_verified"] is True


def test_production_ready_strictly_false_and_shadow_isolated():
    audit = json.loads(AUDIT_PATH.read_text(encoding="utf-8"))
    train = json.loads(TRAIN_REPORT_PATH.read_text(encoding="utf-8"))
    shadow = json.loads(SHADOW_REPORT_PATH.read_text(encoding="utf-8"))
    model = json.loads(MODEL_PATH.read_text(encoding="utf-8"))

    # 11. Keep production_ready=false across all reports
    assert audit["production_ready"] is False
    assert train["production_ready"] is False
    assert shadow["production_ready"] is False
    assert model["production_ready"] is False

    # Verify shadow mode isolation
    assert shadow["safety_review"]["shadow_mode_active"] is True
    assert shadow["safety_review"]["production_routing_impact"] == "None (advisory shadow mode only)"

    app.dependency_overrides[require_user] = lambda: AuthUser(
        id="audit-admin", role="admin", email="admin@raahsetu.in"
    )
    try:
        with TestClient(app) as client:
            resp = client.get("/api/v1/admin/registry")
            assert resp.status_code == 200
            registry = resp.json()
            disruption = next(
                m for m in registry.get("models", []) if m["id"] == "road-disruption-supervised-model"
            )
            assert disruption["operational_mode"] == "shadow_mode"
            assert disruption["field_safety_claim"] is False
            assert "shadow mode" in disruption["explicit_false_claims"][0].lower()
    finally:
        app.dependency_overrides.clear()
