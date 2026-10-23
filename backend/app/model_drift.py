"""Small, auditable feature-drift checks for advisory model monitoring."""
from __future__ import annotations

import math
from collections.abc import Iterable


def population_stability_index(reference: Iterable[float], current: Iterable[float], bins: int = 10) -> float:
    """Return PSI; callers should treat this as a monitoring signal, not a prediction."""
    ref = [float(x) for x in reference if math.isfinite(float(x))]
    cur = [float(x) for x in current if math.isfinite(float(x))]
    if not ref or not cur:
        return 0.0
    lo, hi = min(ref), max(ref)
    if hi <= lo:
        return 0.0
    width = (hi - lo) / bins
    def counts(values):
        out = [0] * bins
        for value in values:
            index = min(bins - 1, max(0, int((value - lo) / width)))
            out[index] += 1
        return out
    rc, cc = counts(ref), counts(cur)
    total_r, total_c = len(ref), len(cur)
    psi = 0.0
    for r, c in zip(rc, cc):
        rp = max(r / total_r, 1e-6)
        cp = max(c / total_c, 1e-6)
        psi += (cp - rp) * math.log(cp / rp)
    return round(psi, 6)


def monitor_features(reference: dict[str, list[float]], current: dict[str, list[float]]) -> dict:
    """Produce a JSON-safe drift report with transparent warning thresholds."""
    features = {}
    for name, values in reference.items():
        score = population_stability_index(values, current.get(name, []))
        features[name] = {"psi": score, "status": "alert" if score >= 0.25 else "watch" if score >= 0.1 else "stable"}
    return {"features": features, "thresholds": {"watch": 0.1, "alert": 0.25}, "advisory_only": True}
