"""Validate public disruption candidates without promoting them to labels."""
from __future__ import annotations

import json
from pathlib import Path

ROOT=Path(__file__).resolve().parents[2]
SOURCE=ROOT/"backend/data/public_disruption_candidates.json"
def main():
    data=json.loads(SOURCE.read_text(encoding="utf-8")); candidates=data.get("candidates",[])
    queue=[]
    for candidate in candidates:
        missing=[]
        if not candidate.get("road_segment_id") or not candidate.get("coordinates_verified"):
            missing.append("exact road segment/coordinates")
        if not candidate.get("incident_started_at"):
            missing.append("incident start time")
        if not candidate.get("reported_status"):
            missing.append("confirmed disruption status")
        if not candidate.get("reviewer_id"):
            missing.append("reviewer approval")
        queue.append({"candidate_id":candidate.get("candidate_id"),"region_code":candidate.get("region_code"),"missing":missing,"graph_available":(ROOT/"backend/data"/f"osm-{candidate.get('region_code')}-real.json").exists()})
    report={"candidates":len(candidates),"pending":sum(c.get("review_status")!="approved" for c in candidates),"promotable":sum(c.get("review_status")=="approved" and c.get("coordinates_verified") and c.get("road_segment_id") for c in candidates),"verification_queue":queue,"policy":data["policy"]}
    print(json.dumps(report,indent=2))
if __name__=="__main__": main()
