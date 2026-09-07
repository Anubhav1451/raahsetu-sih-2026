"""Generate a deterministic, fictional road network. No government data is implied."""

import json
import math
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def main():
    nodes = []
    labels = {
        "n2_0": "West distribution hub",
        "n2_6": "East medical depot",
        "n0_3": "Hill relief centre",
        "n4_3": "River supply point",
        "n1_1": "North dispatch station",
        "n3_5": "Community hospital",
        "n4_0": "South warehouse",
        "n0_6": "Remote service centre",
    }
    for row in range(5):
        for col in range(7):
            node_id = f"n{row}_{col}"
            nodes.append(
                {
                    "id": node_id,
                    "lon": round(91.66 + col * 0.02, 6),
                    "lat": round(26.22 - row * 0.018, 6),
                    "label": labels.get(node_id),
                }
            )
    by_id = {n["id"]: n for n in nodes}
    edges = []

    def connect(u, v, name, risk=0.06, speed=38, limits=None):
        a, b = by_id[u], by_id[v]
        dx = (b["lon"] - a["lon"]) * 111320 * math.cos(math.radians(a["lat"]))
        dy = (b["lat"] - a["lat"]) * 111320
        mid = [(a["lon"] + b["lon"]) / 2 + 0.0007, (a["lat"] + b["lat"]) / 2 + 0.0006]
        geometry = [[a["lon"], a["lat"]], mid, [b["lon"], b["lat"]]]
        for start, end, points in ((u, v, geometry), (v, u, geometry[::-1])):
            edge = {
                "id": f"{start}>{end}",
                "u": start,
                "v": end,
                "name": name,
                "length_m": round(math.hypot(dx, dy) * 1.05, 2),
                "speed_kph": speed,
                "geometry": points,
                "accident_score": risk,
                "surface_score": min(1, risk * 0.85),
                "weather_score": risk * 0.5,
                "flood_susceptibility": 0.8 if "River" in name else 0.2,
                "max_height_m": 4.8,
                "max_weight_t": 30,
                "max_width_m": 3.2,
                "hgv_allowed": True,
                "evidence": "Synthetic demo scenario",
            }
            if limits:
                edge.update(limits)
            edges.append(edge)

    for row in range(5):
        for col in range(6):
            names = [
                "Hill connector",
                "Northern bypass",
                "Central freight corridor",
                "River approach",
                "Southern service road",
            ]
            risk = 0.92 if row == 2 and col in (2, 3) else (0.38 if row == 3 else 0.06)
            limits = {"max_weight_t": 8} if row == 0 and col == 3 else None
            connect(
                f"n{row}_{col}",
                f"n{row}_{col + 1}",
                names[row],
                risk,
                55 if row == 2 else 48,
                limits,
            )
    for row in range(4):
        for col in (0, 1, 3, 5, 6):
            connect(f"n{row}_{col}", f"n{row + 1}_{col}", f"Link road {col + 1}", 0.08, 40)
    # A parallel edge exercises true multigraph routing; restricted to light vehicles.
    connect("n2_2", "n2_3", "Old narrow bridge", 0.02, 65, {"max_width_m": 2.0})
    for edge in edges[-2:]:
        edge["id"] += ":bridge"
    closures = [e["id"] for e in edges if {e["u"], e["v"]} == {"n1_3", "n1_4"}]
    isolated = [e["id"] for e in edges if e["u"] == "n2_6" or e["v"] == "n2_6"]
    dataset = {
        "id": "ner-synthetic-v1",
        "title": "North-East logistics sandbox",
        "region": "Guwahati-inspired demonstration area",
        "source": "Fictional road network",
        "generated_at": "2026-09-06T00:00:00Z",
        "is_synthetic": True,
        "hazard_source": "Synthetic scenarios; no eDAR or MoRTH records loaded",
        "limitations": [
            "Roads, facilities and hazards are fictional demonstration data.",
            "Terrain is illustrative, not measured elevation.",
            "Travel times are model estimates; no live traffic or weather feed.",
            "Vehicle limits are synthetic. This is not operational navigation.",
        ],
        "nodes": nodes,
        "edges": edges,
        "scenarios": [
            {
                "id": "bypass_closed",
                "label": "Bypass closure",
                "description": "A simulated landslide closes the northern bypass in both directions.",
                "closed_edge_ids": closures,
            },
            {
                "id": "depot_isolated",
                "label": "Depot isolated",
                "description": "Flooding disconnects the east medical depot from every approach.",
                "closed_edge_ids": isolated,
            },
        ],
        "default_origin": "n2_0",
        "default_destination": "n2_6",
    }
    path = ROOT / "data" / "demo-network.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(dataset, indent=2), encoding="utf-8")
    print(f"Generated {len(nodes)} nodes and {len(edges)} directed edges: {path}")


if __name__ == "__main__":
    main()
