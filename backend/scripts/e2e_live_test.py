"""Live E2E: Supabase password login -> role lookup -> fleet -> delivery -> field report -> alerts."""
import os
import uuid

import httpx
import psycopg
from dotenv import load_dotenv

load_dotenv("D:/FORSIH/.env")
API = "http://127.0.0.1:8000"
cfg = httpx.get(f"{API}/api/v1/public-config").json()
SB, KEY = cfg["supabase_url"], cfg["supabase_publishable_key"]
EMAIL, PASSWORD = "e2e.direct2.b2fe692f@gmail.com", "TestE2E!Secure42"

def sb(path, method="GET", payload=None, token=None):
    headers = {"apikey": KEY, "Content-Type": "application/json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    return httpx.request(method, f"{SB}{path}", json=payload, headers=headers, timeout=15)

def api(path, method="GET", payload=None, token=None):
    headers = {}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    return httpx.request(method, f"{API}{path}", json=payload, headers=headers, timeout=15)

results = []
def step(name, ok, detail=""):
    results.append((name, ok, detail))
    print(f"{'PASS' if ok else 'FAIL'}: {name}" + (f" — {detail}" if detail else ""))

# 1. Password login (live GoTrue)
r = sb("/auth/v1/token?grant_type=password", "POST", {"email": EMAIL, "password": PASSWORD})
token = r.json().get("access_token") if r.status_code == 200 else None
step("Supabase password login (live)", token is not None, f"status {r.status_code}")

# 2. Profile trigger + role lookup via /me
me = api("/api/v1/me", token=token)
step("Profile trigger + role lookup via /me", me.status_code == 200 and me.json()["role"] == "field_official",
     f"{me.status_code}: {me.text[:120] if me.status_code != 200 else me.json()['role']}")
user_id = me.json()["id"] if me.status_code == 200 else None

# 3. Seed vehicle asset (DB-side, as designed)
vehicle_id = None
if user_id:
    with psycopg.connect(os.getenv("DATABASE_URL"), sslmode="require") as conn:
        row = conn.execute(
            """insert into vehicle_assets(operator_id, region_code, registration, vehicle_type)
               values (%s, 'assam', %s, 'light') returning id::text""",
            (user_id, f"AS01-E2E-{uuid.uuid4().hex[:6].upper()}")).fetchone()
        vehicle_id = row[0]
step("Seed vehicle asset (DB-side)", vehicle_id is not None, vehicle_id[:8] if vehicle_id else "")

# 4. List own vehicles via API
r = api("/api/v1/fleet/vehicles", token=token)
step("List assigned vehicles", r.status_code == 200 and any(v["id"] == vehicle_id for v in r.json()),
     f"status {r.status_code}, {len(r.json())} vehicles")

# 5. Record GPS position
r = api("/api/v1/fleet/positions", "POST", {"vehicle_id": vehicle_id, "recorded_at": "2026-09-08T12:00:00Z", "lon": 91.7462, "lat": 26.1455, "accuracy_m": 12.5}, token=token)
step("Record GPS position", r.status_code == 201, f"status {r.status_code}")

# 6. Fleet positions listing (region-scoped)
r = api("/api/v1/fleet/positions", token=token)
step("List fleet positions (region-scoped)", r.status_code == 200 and len(r.json()) >= 1, f"{len(r.json())} positions")

# 7. Create delivery job
r = api("/api/v1/deliveries", "POST", {"vehicle_id": vehicle_id, "region_code": "assam", "commodity": "Medical supplies", "origin_name": "West distribution hub", "destination_name": "East medical depot"}, token=token)
delivery_id = r.json().get("id") if r.status_code == 201 else None
step("Create delivery job", delivery_id is not None, f"status {r.status_code}: {r.text[:120] if delivery_id is None else ''}")

# 8. Update delivery status
r = api(f"/api/v1/deliveries/{delivery_id}", "PATCH", {"status": "delivered"}, token=token)
step("Update delivery to delivered", r.status_code == 200 and r.json()["status"] == "delivered", f"status {r.status_code}")

# 9. Submit field report
r = api("/api/v1/field-reports", "POST", {"client_report_id": f"e2e-{uuid.uuid4().hex[:8]}", "region_code": "assam", "kind": "road_damage", "accessibility_status": "restricted", "severity": 0.6, "lon": 91.7462, "lat": 26.1455, "description": "E2E test report of road damage near Dispur", "observed_at": "2026-09-08T12:00:00Z"}, token=token)
report_id = r.json().get("id") if r.status_code == 201 else None
step("Submit field report", report_id is not None, f"status {r.status_code}: {r.text[:150] if report_id is None else ''}")

# 10. List field reports
r = api("/api/v1/field-reports", token=token)
step("List field reports", r.status_code == 200, f"{len(r.json())} reports")

# 11. Alerts + connectivity
r = api("/api/v1/alerts", token=token)
step("List alerts", r.status_code == 200, f"{len(r.json())} alerts")
r = api("/api/v1/connectivity", token=token)
statuses = {c["state_name"]: c["status"] for c in r.json()} if r.status_code == 200 else {}
step("Connectivity summary (8 states)", r.status_code == 200 and len(statuses) == 8, f"Assam: {statuses.get('Assam')}")

# 12. Unauthorized request rejected
r = api("/api/v1/fleet/positions")
step("Unauthenticated request rejected", r.status_code == 401, f"status {r.status_code}")

# 13. Invalid token rejected
r = api("/api/v1/me", token="invalid-token-xyz")
step("Invalid token rejected", r.status_code == 401, f"status {r.status_code}")

print(f"\n{'='*50}\n{sum(1 for _, ok, _ in results if ok)}/{len(results)} steps passed")
if all(ok for _, ok, _ in results):
    print("E2E RESULT: ALL PASS")
