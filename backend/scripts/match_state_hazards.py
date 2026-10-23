"""State-wide verified hazard coordinate road matching against real OSM networks.

Matches MoRTH accident blackspots, GSI landslide records, CWC flood points,
and PWD bridge constraints against real OSM road graphs for all 8 Northeast states.
Computes exact perpendicular geodesic distance to road polylines with spatial indexing.
"""

from __future__ import annotations

import csv
import itertools
import json
import logging
import math
from datetime import UTC, datetime
from pathlib import Path

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("raahsetu.match_state_hazards")

ROOT = Path(__file__).resolve().parents[2]
CSV_PATH = ROOT / "supabase" / "hazards-northeast-verified.csv"
DATA_DIR = ROOT / "backend" / "data"
OUTPUT_PATH = DATA_DIR / "hazard_state_road_matches.json"

STATE_FILE_MAP = {
    "assam": "osm-assam-real.json",
    "arunachal pradesh": "osm-arunachal-pradesh-real.json",
    "manipur": "osm-manipur-real.json",
    "meghalaya": "osm-meghalaya-real.json",
    "mizoram": "osm-mizoram-real.json",
    "nagaland": "osm-nagaland-real.json",
    "sikkim": "osm-sikkim-real.json",
    "tripura": "osm-tripura-real.json",
}


def distance_m(lon1: float, lat1: float, lon2: float, lat2: float) -> float:
    """Haversine distance in meters between two lon/lat coordinates."""
    lat1, lat2 = math.radians(lat1), math.radians(lat2)
    dlat, dlon = lat2 - lat1, math.radians(lon2 - lon1)
    a = math.sin(dlat / 2) ** 2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon / 2) ** 2
    return 6371009 * 2 * math.asin(math.sqrt(min(1.0, max(0.0, a))))


def point_to_polyline_m(lon: float, lat: float, geometry: list[list[float]]) -> float:
    """Compute minimum geodesic distance from point to polyline segments in meters."""
    cos_lat = math.cos(math.radians(lat))
    best_dist = float("inf")
    for p1, p2 in itertools.pairwise(geometry):
        ax, ay = p1[0] * cos_lat, p1[1]
        bx, by = p2[0] * cos_lat, p2[1]
        px, py = lon * cos_lat, lat
        dx, dy = bx - ax, by - ay
        denom = dx * dx + dy * dy or 1.0
        t = max(0.0, min(1.0, ((px - ax) * dx + (py - ay) * dy) / denom))
        proj_lon = (ax + t * dx) / (cos_lat or 1.0)
        proj_lat = ay + t * dy
        dist = distance_m(lon, lat, proj_lon, proj_lat)
        best_dist = min(best_dist, dist)
    return best_dist


def match_hazards_for_state(
    state_name: str, hazards: list[dict], graph_path: Path
) -> list[dict]:
    """Match a list of hazard records to the nearest edges in a state's OSM graph."""
    if not graph_path.exists():
        logger.warning("Graph file missing for %s: %s", state_name, graph_path.name)
        return []

    logger.info("Loading %s for state %s (%d hazards)...", graph_path.name, state_name, len(hazards))
    graph_data = json.loads(graph_path.read_text(encoding="utf-8"))
    edges = graph_data.get("edges", [])
    logger.info("Loaded %d edges from %s. Matching...", len(edges), graph_path.name)

    # Pre-extract edge spatial bounds to accelerate candidate filtering
    indexed_edges = []
    for e in edges:
        geom = e.get("geometry", [])
        if not geom or len(geom) < 2:
            continue
        lons = [g[0] for g in geom]
        lats = [g[1] for g in geom]
        indexed_edges.append({
            "edge": e,
            "min_lon": min(lons),
            "max_lon": max(lons),
            "min_lat": min(lats),
            "max_lat": max(lats),
        })

    matches = []
    for h in hazards:
        hlon = float(h["longitude"])
        hlat = float(h["latitude"])
        rec_id = h["source_record_id"]
        kind = h["kind"]
        desc = h["description"]
        corridor = h.get("corridor", "")

        # Multi-tiered spatial filter: start tight (0.05 deg ~ 5.5 km), expand if needed
        candidates = []
        for search_deg in [0.05, 0.15, 0.35]:
            min_lo, max_lo = hlon - search_deg, hlon + search_deg
            min_la, max_la = hlat - search_deg, hlat + search_deg

            for ie in indexed_edges:
                if ie["max_lon"] < min_lo or ie["min_lon"] > max_lo:
                    continue
                if ie["max_lat"] < min_la or ie["min_lat"] > max_la:
                    continue
                d = point_to_polyline_m(hlon, hlat, ie["edge"]["geometry"])
                candidates.append((d, ie["edge"]))

            if candidates:
                break

        if not candidates:
            # Fallback scan all if extreme point
            for ie in indexed_edges:
                d = point_to_polyline_m(hlon, hlat, ie["edge"]["geometry"])
                candidates.append((d, ie["edge"]))

        candidates.sort(key=lambda x: x[0])
        top_candidates = candidates[:5]

        best_dist, best_edge = top_candidates[0] if top_candidates else (float("inf"), None)

        match_record = {
            "source_record_id": rec_id,
            "state": state_name,
            "district": h.get("district", ""),
            "kind": kind,
            "severity": float(h.get("severity", 0.8)),
            "coordinates": [hlon, hlat],
            "corridor": corridor,
            "description": desc,
            "source": h.get("source", ""),
            "evidence_url": h.get("evidence_url", ""),
            "matched_edge_id": best_edge["id"] if best_edge else None,
            "matched_road_name": best_edge.get("name", "Unnamed Road") if best_edge else None,
            "distance_m": round(best_dist, 1) if best_edge else None,
            "review_status": "matched_candidate",
            "proximity_classification": (
                "direct_on_road" if best_dist <= 25.0
                else ("corridor_proximity" if best_dist <= 500.0
                else ("catchment_area" if best_dist <= 2000.0 else "regional_context"))
            ),
            "top_candidates": [
                {
                    "edge_id": c[1]["id"],
                    "road_name": c[1].get("name", "Unnamed Road"),
                    "distance_m": round(c[0], 1),
                    "speed_kph": c[1].get("speed_kph"),
                    "length_m": round(c[1].get("length_m", 0), 1),
                }
                for c in top_candidates[:3]
            ],
        }
        matches.append(match_record)
        logger.info(
            "  [%s] %s -> Edge %s (%s) at %.1f m (%s)",
            state_name,
            rec_id,
            match_record["matched_edge_id"],
            match_record["matched_road_name"],
            match_record["distance_m"] or 0.0,
            match_record["proximity_classification"],
        )

    return matches


def run_state_hazard_matching() -> dict:
    """Match all 24 verified Northeast hazards against state-specific real OSM graphs."""
    if not CSV_PATH.exists():
        raise FileNotFoundError(f"Verified hazards CSV not found: {CSV_PATH}")

    with CSV_PATH.open(encoding="utf-8-sig", newline="") as f:
        all_hazards = list(csv.DictReader(f))

    logger.info("Found %d verified Northeast hazard records across 8 states.", len(all_hazards))

    # Group hazards by state
    by_state: dict[str, list[dict]] = {}
    for h in all_hazards:
        st = h.get("state", "").strip()
        by_state.setdefault(st, []).append(h)

    all_matches = []
    state_summaries = {}

    for state, state_hazards in sorted(by_state.items()):
        slug = state.lower()
        file_name = STATE_FILE_MAP.get(slug)
        if not file_name:
            logger.warning("No state graph mapping for state: %s", state)
            continue

        graph_path = DATA_DIR / file_name
        matches = match_hazards_for_state(state, state_hazards, graph_path)
        all_matches.extend(matches)

        state_summaries[state] = {
            "hazards_count": len(state_hazards),
            "matched_count": len(matches),
            "nearest_distance_m": min((m["distance_m"] for m in matches if m["distance_m"] is not None), default=None),
            "median_distance_m": sorted(m["distance_m"] for m in matches if m["distance_m"] is not None)[len(matches) // 2] if matches else None,
        }

    report = {
        "matched_at": datetime.now(UTC).isoformat(),
        "total_hazards_evaluated": len(all_hazards),
        "total_matches_generated": len(all_matches),
        "methodology": "Geodesic perpendicular point-to-polyline snapping against real OSM highway networks",
        "boundary_rule": "Candidate review edges are spatial candidates; unverified road closures are not asserted as facts.",
        "state_breakdown": state_summaries,
        "matches": all_matches,
    }

    OUTPUT_PATH.write_text(json.dumps(report, indent=2), encoding="utf-8")
    logger.info("Saved state-wide road matches audit report to %s", OUTPUT_PATH)
    return report


if __name__ == "__main__":
    run_state_hazard_matching()
