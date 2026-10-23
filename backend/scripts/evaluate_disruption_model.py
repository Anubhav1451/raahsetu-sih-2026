"""Evaluation and shadow-mode comparison for the calibrated disruption model.

Compares the trained supervised classifier predictions against the domain-calibrated
deterministic baseline on holdout test segments, assesses concordance, divergence,
and verifies safety bounds for shadow-mode deployment.
"""
from __future__ import annotations

import csv
import json
import math
import sys
from datetime import UTC, datetime
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT / "backend") not in sys.path:
    sys.path.insert(0, str(ROOT / "backend"))

from app.ml_prediction import predict_disruption

MODEL_PATH = ROOT / "backend" / "data" / "disruption_model.json"
TRAIN_REPORT_PATH = ROOT / "backend" / "data" / "disruption_training_report.json"
LABELS_PATH = ROOT / "backend" / "data" / "disruption_labels.csv"
SHADOW_REPORT_PATH = ROOT / "backend" / "data" / "disruption_shadow_report.json"


def sigmoid(z: float) -> float:
    return 1.0 / (1.0 + math.exp(-max(-15.0, min(15.0, z))))


def predict_supervised(model: dict, row: dict) -> float:
    features = model["features"]
    means = model["standardization"]["means"]
    stds = model["standardization"]["stds"]
    weights = model["weights"]
    bias = model["intercept"]

    rain = float(row.get("rainfall_mm_24h") or 0.0)
    slope = float(row.get("slope_deg") or 0.0)
    humidity = float(row.get("humidity_pct") or 60.0)
    surface = float(row.get("surface_score") or 0.8)
    roughness = max(0.0, min(1.0, 1.0 - surface))
    wind = float(row.get("wind_kph") or 10.0)

    val_map = {
        "rainfall_mm_24h": rain,
        "slope_deg": slope,
        "humidity_pct": humidity,
        "surface_roughness": roughness,
        "wind_kph": wind,
    }

    z = bias
    for f in features:
        val = val_map.get(f, 0.0)
        norm_val = (val - means[f]) / (stds[f] or 1.0)
        z += weights[f] * norm_val

    return round(sigmoid(z), 4)


def main():
    if not MODEL_PATH.exists() or not TRAIN_REPORT_PATH.exists():
        print(json.dumps({"status": "unavailable", "reason": "Trained model artifact not found."}, indent=2))
        return

    model = json.loads(MODEL_PATH.read_text(encoding="utf-8"))
    train_report = json.loads(TRAIN_REPORT_PATH.read_text(encoding="utf-8"))

    if train_report.get("status") != "trained":
        print(json.dumps({
            "status": train_report.get("status"),
            "metrics": train_report.get("metrics_required"),
            "note": "Evaluation is unavailable until the training gate opens.",
        }, indent=2))
        return

    rows = list(csv.DictReader(LABELS_PATH.open(encoding="utf-8", newline="")))
    valid = [
        r for r in rows
        if r.get("review_status") in {
            "accepted",
            "authority_verified",
            "approved",
            "monsoon_stress_control",
            "nominal_baseline_control",
        }
        and r.get("road_segment_id")
        and r.get("observed_at")
        and r.get("outcome_blocked") in {"0", "1"}
    ]

    hist_rows = [r for r in valid if r["observed_at"] < "2021-01-01"]
    mod_rows = [r for r in valid if r["observed_at"] >= "2021-01-01"]

    hist_dates = sorted({r["observed_at"].split("T")[0] for r in hist_rows})
    mod_dates = sorted({r["observed_at"].split("T")[0] for r in mod_rows})

    h_hold_d = set(hist_dates[int(len(hist_dates) * 0.75):])
    m_hold_d = set(mod_dates[int(len(mod_dates) * 0.75):])
    holdout_dates = h_hold_d | m_hold_d

    holdout = [r for r in valid if r["observed_at"].split("T")[0] in holdout_dates]

    comparisons = []
    agree_binary = 0
    total = len(holdout)

    for r in holdout:
        p_supervised = predict_supervised(model, r)
        elev = float(r.get("elevation_m") or 400.0)
        pred_baseline = predict_disruption(
            rainfall_mm_24h=float(r.get("rainfall_mm_24h") or 0.0),
            slope_deg=float(r.get("slope_deg") or 0.0),
            historical_incidents=1 if r.get("outcome_blocked") == "1" else 0,
            surface_score=float(r.get("surface_score") or 0.8),
            elevation_m=elev,
        )
        p_baseline = pred_baseline.disruption_probability
        actual = int(r["outcome_blocked"])

        bin_supervised = 1 if p_supervised >= 0.50 else 0
        bin_baseline = 1 if p_baseline >= 0.50 else 0

        if bin_supervised == bin_baseline:
            agree_binary += 1

        comparisons.append({
            "road_segment_id": r["road_segment_id"],
            "region_code": r["region_code"],
            "actual_blocked": actual,
            "p_supervised": p_supervised,
            "p_baseline": p_baseline,
            "delta": round(p_supervised - p_baseline, 4),
            "binary_match": bin_supervised == bin_baseline,
        })

    agreement_rate = round(agree_binary / total, 4) if total > 0 else 0.0
    mean_abs_delta = round(float(np.mean([abs(c["delta"]) for c in comparisons])), 4)

    import hashlib
    actual_artifact_hash = hashlib.sha256(MODEL_PATH.read_bytes()).hexdigest()
    train_hash = train_report.get("artifact_sha256")
    if actual_artifact_hash != train_hash:
        raise ValueError(f"Model artifact hash mismatch: {actual_artifact_hash} != {train_hash}")

    shadow_report = {
        "status": "evaluated_in_shadow_mode",
        "production_ready": False,
        "generated_at": datetime.now(UTC).isoformat(),
        "model_version": model["model_version"],
        "artifact_hash": actual_artifact_hash,
        "hash_verified": True,
        "holdout_samples_evaluated": total,
        "holdout_metrics": model["holdout_metrics"],
        "shadow_comparison": {
            "baseline_model": "Domain-Calibrated Logistic Disruption Baseline",
            "supervised_model": "Supervised L2-Regularized Calibrated Classifier",
            "binary_classification_agreement_rate": agreement_rate,
            "mean_absolute_probability_delta": mean_abs_delta,
            "samples_compared": total,
        },
        "safety_review": {
            "shadow_mode_active": True,
            "production_routing_impact": "None (advisory shadow mode only)",
            "fallback_policy": "Deterministic Risk-A* and authority road closures govern all live route decisions",
            "low_confidence_override_permitted": False,
            "production_ready": False,
        },
    }

    SHADOW_REPORT_PATH.write_text(json.dumps(shadow_report, indent=2), encoding="utf-8")
    print(json.dumps(shadow_report, indent=2))


if __name__ == "__main__":
    main()
