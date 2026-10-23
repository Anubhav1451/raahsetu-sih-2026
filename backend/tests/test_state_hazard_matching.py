"""Automated tests for state-wide verified hazard coordinate road matching."""

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
MATCHES_FILE = ROOT / "backend" / "data" / "hazard_state_road_matches.json"


def test_hazard_state_road_matches_structure():
    assert MATCHES_FILE.exists(), f"Matches file missing: {MATCHES_FILE}"
    data = json.loads(MATCHES_FILE.read_text(encoding="utf-8"))

    assert data["total_hazards_evaluated"] == 24
    assert data["total_matches_generated"] == 24
    assert "state_breakdown" in data
    assert len(data["state_breakdown"]) == 8

    # All 8 Northeast states must be accounted for
    expected_states = {
        "Assam",
        "Arunachal Pradesh",
        "Manipur",
        "Meghalaya",
        "Mizoram",
        "Nagaland",
        "Sikkim",
        "Tripura",
    }
    assert set(data["state_breakdown"].keys()) == expected_states

    # Verify individual matches
    matches = data["matches"]
    assert len(matches) == 24

    for m in matches:
        assert m["source_record_id"]
        assert m["state"] in expected_states
        assert m["kind"] in {"blackspot", "landslide", "flood", "road_damage"}
        assert m["matched_edge_id"] is not None
        assert m["distance_m"] is not None
        assert m["distance_m"] >= 0.0
        assert len(m["top_candidates"]) >= 1

        # Check candidate structure
        for cand in m["top_candidates"]:
            assert "edge_id" in cand
            assert "distance_m" in cand
            assert cand["distance_m"] >= 0.0


def test_morth_blackspot_direct_road_proximity():
    """Verify that MoRTH highway blackspots snap with high fidelity (<= 25m) to road polylines."""
    data = json.loads(MATCHES_FILE.read_text(encoding="utf-8"))
    blackspots = [m for m in data["matches"] if m["kind"] == "blackspot"]
    assert len(blackspots) >= 8

    # Check key state blackspots snap tightly to roads
    tight_matches = [b for b in blackspots if b["distance_m"] <= 25.0]
    # At least 6 out of 8 state capital/corridor blackspots snap directly to the road surface (<25m)
    assert len(tight_matches) >= 6
