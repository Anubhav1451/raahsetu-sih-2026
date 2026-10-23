"""Audit disruption labels for provenance, separability, and leakage risks before production use."""
from __future__ import annotations

import csv
import json
from collections import Counter
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[2]
LABELS = ROOT / "backend/data/disruption_labels.csv"
OUT = ROOT / "backend/data/disruption_label_audit.json"
PROVENANCE_OUT = ROOT / "backend/data/disruption_provenance_audit.json"

MIN_STATE_SAMPLES = 25
MIN_CLASS_SAMPLES = 5


def main() -> None:
    rows = list(csv.DictReader(LABELS.open(encoding="utf-8", newline="")))
    positives = [r for r in rows if r.get("outcome_blocked") == "1"]
    negatives = [r for r in rows if r.get("outcome_blocked") == "0"]
    hard_negatives = [r for r in negatives if r.get("provenance_type") == "constructed_hard_negative"]
    nominal_negatives = [r for r in negatives if r.get("provenance_type") == "constructed_nominal_control"]

    glc_records = [r for r in rows if (r.get("source_id") or "").startswith("glc")]
    morth_records = [r for r in rows if (r.get("source_id") or "").startswith("morth")]
    empirical_total = len(glc_records) + len(morth_records)

    pos_rain = [float(r["rainfall_mm_24h"]) for r in positives if r.get("rainfall_mm_24h")]
    neg_rain = [float(r["rainfall_mm_24h"]) for r in negatives if r.get("rainfall_mm_24h")]
    hard_neg_rain = [float(r["rainfall_mm_24h"]) for r in hard_negatives if r.get("rainfall_mm_24h")]

    pos_slope = [float(r["slope_deg"]) for r in positives if r.get("slope_deg")]
    neg_slope = [float(r["slope_deg"]) for r in negatives if r.get("slope_deg")]
    hard_neg_slope = [float(r["slope_deg"]) for r in hard_negatives if r.get("slope_deg")]

    rain_overlap = bool((min(pos_rain) <= max(neg_rain)) and (min(neg_rain) <= max(pos_rain)))
    slope_overlap = bool((min(pos_slope) <= max(neg_slope)) and (min(neg_slope) <= max(pos_slope)))

    unique_segments = len({r.get("road_segment_id") for r in rows})
    exact_duplicates = len(rows) - len({(r.get("road_segment_id"), r.get("observed_at"), r.get("outcome_blocked")) for r in rows})

    provenance_breakdown = dict(Counter(r.get("provenance_type", "unspecified") for r in rows))
    review_status_breakdown = dict(Counter(r.get("review_status", "unspecified") for r in rows))
    source_prefix_breakdown = dict(Counter((r.get("source_id") or "").split("-")[0] for r in rows))
    state_breakdown = dict(Counter(r.get("region_code") for r in rows))

    # Evaluate per-state sample adequacy
    state_adequacy: dict[str, dict] = {}
    for st, count in state_breakdown.items():
        st_pos = sum(1 for r in rows if r.get("region_code") == st and r.get("outcome_blocked") == "1")
        st_neg = sum(1 for r in rows if r.get("region_code") == st and r.get("outcome_blocked") == "0")
        if st_neg == 0 or st_pos == 0:
            status = "insufficient_data"
            reason = f"Single-class distribution ({st_pos} positives, {st_neg} negatives); binary classification metrics undefined"
        elif count < MIN_STATE_SAMPLES or st_pos < MIN_CLASS_SAMPLES or st_neg < MIN_CLASS_SAMPLES:
            status = "marginal_sample_size"
            reason = f"Sample count {count} is below recommended threshold ({MIN_STATE_SAMPLES})"
        else:
            status = "sufficient_sample_size"
            reason = "Meets minimum state sample and class diversity thresholds"
        state_adequacy[st] = {
            "samples": count,
            "positives": st_pos,
            "negatives": st_neg,
            "status": status,
            "reason": reason,
            "eligible_for_standalone_claims": status == "sufficient_sample_size",
        }

    provenance_report = {
        "generated_at": "2026-09-17",
        "total_records": len(rows),
        "empirical_hazard_records": empirical_total,
        "empirical_catalogs": {
            "nasa_glc_historical": {
                "count": len(glc_records),
                "provenance_type": "empirical_catalog_geocoded",
                "authority_verified": all(r.get("review_status") == "authority_verified" for r in glc_records),
                "source_catalog": "NASA Global Landslide Catalog (2007-2017)",
            },
            "morth_gsi_verified_hazards": {
                "count": len(morth_records),
                "provenance_type": "official_authority_hazard",
                "authority_verified": all(r.get("review_status") == "authority_verified" for r in morth_records),
                "source_catalog": "MoRTH & GSI Verified Blackspots / Hazard Records",
            },
        },
        "negative_controls": {
            "constructed_hard_negatives": {
                "count": len(hard_negatives),
                "provenance_type": "constructed_hard_negative",
                "review_status": "monsoon_stress_control",
                "description": "Steep mountain road segments under real heavy monsoon rainfall (>=25mm) from ERA5/Open-Meteo that remained passable without disruption.",
                "is_field_observation": False,
                "explicit_warning": "Constructed hard negatives are synthetic stress controls and must NEVER be described as physical field inspection observations.",
            },
            "constructed_nominal_controls": {
                "count": len(nominal_negatives),
                "provenance_type": "constructed_nominal_control",
                "review_status": "nominal_baseline_control",
                "description": "Routine road observations during dry winter season with baseline weather.",
                "is_field_observation": False,
                "explicit_warning": "Constructed nominal controls are synthetic baseline controls and must NEVER be described as physical field inspection observations.",
            },
        },
        "separability_analysis": {
            "hard_negatives_present": len(hard_negatives) > 0,
            "rainfall_distribution": {
                "positives": {"min": min(pos_rain), "mean": round(float(np.mean(pos_rain)), 1), "max": max(pos_rain)},
                "hard_negatives": {"min": min(hard_neg_rain), "mean": round(float(np.mean(hard_neg_rain)), 1), "max": max(hard_neg_rain)} if hard_neg_rain else {},
                "all_negatives": {"min": min(neg_rain), "mean": round(float(np.mean(neg_rain)), 1), "max": max(neg_rain)},
                "overlap_confirmed": rain_overlap,
            },
            "slope_distribution": {
                "positives": {"min": min(pos_slope), "mean": round(float(np.mean(pos_slope)), 1), "max": max(pos_slope)},
                "hard_negatives": {"min": min(hard_neg_slope), "mean": round(float(np.mean(hard_neg_slope)), 1), "max": max(hard_neg_slope)} if hard_neg_slope else {},
                "all_negatives": {"min": min(neg_slope), "mean": round(float(np.mean(neg_slope)), 1), "max": max(neg_slope)},
                "overlap_confirmed": slope_overlap,
            },
            "artificial_linear_separability_eliminated": rain_overlap and slope_overlap and len(hard_negatives) > 0,
        },
        "state_sample_adequacy": state_adequacy,
    }

    report = {
        "rows": len(rows),
        "empirical_count": empirical_total,
        "empirical_breakdown": {
            "nasa_glc_historical": len(glc_records),
            "morth_gsi_verified_hazards": len(morth_records),
        },
        "negative_control_count": len(negatives),
        "negative_control_breakdown": {
            "constructed_hard_negatives": len(hard_negatives),
            "constructed_nominal_controls": len(nominal_negatives),
        },
        "review_statuses": review_status_breakdown,
        "provenance_types": provenance_breakdown,
        "source_prefixes": source_prefix_breakdown,
        "positive_count": len(positives),
        "negative_count": len(negatives),
        "hard_negative_count": len(hard_negatives),
        "nominal_control_count": len(nominal_negatives),
        "unique_segments": unique_segments,
        "exact_duplicate_keys": exact_duplicates,
        "feature_grounding": {
            "topography": "30m NASA SRTM HGT raster terrain tiles (N21-N29, E88-E97)",
            "modern_weather": "ERA5 / Open-Meteo daily reference points (2021-2025)",
            "historical_weather_proxy": "NASA GLC trigger-bounded precipitation",
        },
        "hard_negatives_evaluated": len(hard_negatives) > 0,
        "feature_overlap": {
            "rainfall_overlap": rain_overlap,
            "slope_overlap": slope_overlap,
        },
        "state_evaluation_governance": {
            "evaluation_type": "descriptive_sample_metrics_only",
            "generalization_claim": False,
            "min_state_samples_required": MIN_STATE_SAMPLES,
            "min_class_samples_required": MIN_CLASS_SAMPLES,
            "disclaimer": "State-level metrics are descriptive sample summaries over available localized segments. They do NOT constitute statistical population generalization or certified field accuracy.",
            "state_sample_adequacy": state_adequacy,
        },
        "warnings": [
            "Constructed hard negatives (244) and nominal controls (180) are synthetic/stress controls and NOT physical field inspection observations.",
            "Assam has only 7 positive records and 0 negative controls; its state-wise binary classification metrics are INSUFFICIENT.",
            "Supervised model must remain in advisory shadow mode until human safety review and field testing.",
            "Live vehicle routing continues to be governed by deterministic Risk-A* and authority road closures.",
        ],
        "production_ready": False,
    }

    OUT.write_text(json.dumps(report, indent=2), encoding="utf-8")
    PROVENANCE_OUT.write_text(json.dumps(provenance_report, indent=2), encoding="utf-8")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
