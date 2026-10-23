"""Explainable seasonal weather anomaly inference (advisory only)."""
from __future__ import annotations

import json
import math
from datetime import UTC, datetime
from functools import lru_cache
from pathlib import Path

def _find_weather_model() -> Path:
    direct = Path(__file__).resolve().parents[1] / "data/weather_anomaly_model.json"
    if direct.exists():
        return direct
    for fallback in [
        Path("/app/backend/data/weather_anomaly_model.json"),
        Path.cwd() / "data/weather_anomaly_model.json",
        Path.cwd() / "backend/data/weather_anomaly_model.json",
    ]:
        if fallback.exists():
            return fallback
    return direct


MODEL_PATH = _find_weather_model()
FEATURES = ("precipitation_mm_24h", "wind_kph", "temperature_range_c", "humidity_pct")
@lru_cache(maxsize=1)
def load_weather_anomaly_model():
    return json.loads(MODEL_PATH.read_text(encoding="utf-8")) if MODEL_PATH.exists() else None
def score_weather_anomaly(region_code, precipitation_mm_24h, wind_kph, temperature_max_c=None, temperature_min_c=None, humidity_pct=None, observed_at=None):
    model=load_weather_anomaly_model(); base={"available":False,"model_version":None,"anomaly_score":None,"level":"unknown","factors":[]}
    if not model or region_code not in model.get("states",{}): return {**base,"meaning":"Historical weather anomaly model is unavailable for this state."}
    stats=model["states"][region_code]; when=observed_at or datetime.now(UTC).isoformat(); month=int(str(when)[5:7]) if len(str(when))>=7 else datetime.now(UTC).month
    values={"precipitation_mm_24h":max(0,float(precipitation_mm_24h)),"wind_kph":max(0,float(wind_kph)),"temperature_range_c":max(0,float(temperature_max_c or 0)-float(temperature_min_c or 0)),"humidity_pct":humidity_pct}
    factors=[]; squared=0.0
    for feature in FEATURES:
        if values[feature] is None: continue
        s=stats.get("seasonal_baseline",{}).get(str(month),{}).get(feature) or stats["global"][feature]; z=(values[feature]-s["mean"])/max(s["std"],1e-6); squared+=max(0,z)**2
        factors.append({"feature":feature,"value":round(values[feature],2),"z_score":round(z,2),"p95":s["p95"],"contribution_pct":None})
    distance=math.sqrt(squared); score=round(1-math.exp(-distance/3),4); factors.sort(key=lambda x:x["z_score"],reverse=True)
    for f in factors: f["contribution_pct"]=round(100*max(0,f["z_score"])**2/max(1e-9,squared),1)
    return {"available":True,"model_version":model["model_version"],"trained_through":model["training_window"]["end"],"source":model["source"],"source_sha256":model["source_sha256"],"source_date":model.get("source_date"),"observation_date":str(when)[:10],"season_month":month,"training_samples":stats["sample_count"],"anomaly_score":score,"level":"extreme" if score>=.8 else "elevated" if score>=.55 else "normal","thresholds":stats["thresholds"],"factors":factors,"meaning":"Seasonal deviation from the state's historical reference-point weather; not a landslide or road-closure probability."}
