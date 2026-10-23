"""Train a transparent seasonal weather anomaly model from Open-Meteo history."""
from __future__ import annotations

import csv
import hashlib
import json
import math
import statistics
from datetime import UTC, datetime
from pathlib import Path

ROOT=Path(__file__).resolve().parents[2]
SOURCE=ROOT/"datasets/processed/weather/ne-reference-points-daily-2021-2025.csv"
OUTPUT=ROOT/"backend/data/weather_anomaly_model.json"
HOLDOUT=ROOT/"backend/data/weather_anomaly_holdout_2025.json"
FEATURES=("precipitation_mm_24h","wind_kph","temperature_range_c","humidity_pct")
def pct(v,f):
    a=sorted(v); return a[min(len(a)-1,max(0,round((len(a)-1)*f)))]
def describe(v):
    return {"mean":round(statistics.fmean(v),4),"std":round(max(statistics.pstdev(v),1e-6),4),"p95":round(pct(v,.95),2),"p99":round(pct(v,.99),2)}
def train():
    grouped={}
    with SOURCE.open(encoding="utf-8-sig",newline="") as f:
        for r in csv.DictReader(f):
            if not r.get("relative_humidity_2m_mean"): raise RuntimeError("incomplete humidity coverage")
            grouped.setdefault(r["state"],[]).append({"date":r["date"],"month":int(r["date"][5:7]),"precipitation_mm_24h":float(r.get("precipitation_sum") or 0),"wind_kph":float(r.get("wind_speed_10m_max") or 0),"temperature_range_c":max(0,float(r.get("temperature_2m_max") or 0)-float(r.get("temperature_2m_min") or 0)),"humidity_pct":float(r["relative_humidity_2m_mean"])})
    states={}; holdout={}
    for state,rows in sorted(grouped.items()):
        tr=[r for r in rows if r["date"]<"2025-01-01"]; te=[r for r in rows if r["date"]>="2025-01-01"]
        seasonal={}
        for m in range(1,13):
            sub=[r for r in tr if r["month"]==m]; seasonal[str(m)]={f:describe([r[f] for r in sub]) for f in FEATURES}
        global_stats={f:describe([r[f] for r in tr]) for f in FEATURES}
        def score(r, seasonal_baseline=seasonal):
            z=[max(0,(r[f]-seasonal_baseline[str(r["month"])][f]["mean"])/seasonal_baseline[str(r["month"])][f]["std"]) for f in FEATURES]
            return 1-math.exp(-math.sqrt(sum(x*x for x in z))/3)
        train_scores=[score(r) for r in tr]; test_scores=[score(r) for r in te]
        thresholds={"feature_p95":{f:global_stats[f]["p95"] for f in FEATURES},"feature_p99":{f:global_stats[f]["p99"] for f in FEATURES},"score_p95":round(pct(train_scores,.95),4),"score_p99":round(pct(train_scores,.99),4),"level_cutoffs":{"elevated":.55,"extreme":.8}}
        states[state]={"sample_count":len(tr),"features":FEATURES,"global":global_stats,"seasonal_baseline":seasonal,"thresholds":thresholds}
        holdout[state]={"days":len(te),"mean_score":round(statistics.fmean(test_scores),4),"max_score":round(max(test_scores,default=0),4),"flagged_score_days":sum(x>=thresholds["score_p95"] for x in test_scores),"flag_rate_pct":round(100*sum(x>=thresholds["score_p95"] for x in test_scores)/max(1,len(te)),2),"evaluation_type":"2025 temporal holdout; anomaly stability only, no disruption labels"}
    h=hashlib.sha256(SOURCE.read_bytes()).hexdigest(); version=f"weather-anomaly-v2-{h[:10]}"
    artifact={"model_version":version,"model_type":"state-wise seasonal standardized-distance anomaly detector","trained_at":datetime.now(UTC).isoformat(),"training_window":{"start":"2021-01-01","end":"2024-12-31"},"holdout_window":{"start":"2025-01-01","end":"2025-12-31"},"source":str(SOURCE.relative_to(ROOT)).replace("\\","/"),"source_sha256":h,"source_date":"2026-09-17","coverage":"one Open-Meteo reanalysis reference point per Northeast state; not statewide station coverage","features":FEATURES,"humidity_definition":"daily mean relative humidity at 2 m (%)","seasonal_baseline":"calendar-month baseline estimated from 2021-2024 training data","target":"weather anomaly, not road disruption or landslide occurrence","states":states,"holdout_evaluation":holdout,"limitations":["No road-disruption labels are available for supervised calibration.","Anomaly is advisory and cannot close a road.","Reference-point reanalysis is not a replacement for field gauges."]}
    OUTPUT.write_text(json.dumps(artifact,indent=2),encoding="utf-8"); HOLDOUT.write_text(json.dumps({"model_version":version,"holdout_window":artifact["holdout_window"],"states":holdout},indent=2),encoding="utf-8"); return artifact
if __name__=="__main__": print(json.dumps(train(),indent=2)[:1000])
