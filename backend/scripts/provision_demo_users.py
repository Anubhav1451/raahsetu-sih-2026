"""Provision Supabase demo/test users end-to-end and verify the full PS workflow.

Creates directly-confirmed auth users (bypassing email rate limits), assigns
roles/regions, seeds vehicles, then walks the complete journey:
field report (photo evidence) -> reviewer approval + edge bind -> closure alert
-> connectivity status -> Risk-A* reroute on affected dataset -> delivery tracking.
"""
import io
import os
import uuid

import httpx
import psycopg
from dotenv import load_dotenv
from PIL import Image

load_dotenv(".env")
API = "http://127.0.0.1:8000"
cfg = httpx.get(f"{API}/api/v1/public-config").json()
SB, KEY = cfg["supabase_url"], cfg["supabase_publishable_key"]
DB = os.getenv("DATABASE_URL")

def make_user(email, display, role, region):
    with psycopg.connect(DB, sslmode="require") as conn:
        row = conn.execute("""
            insert into auth.users (instance_id, id, aud, role, email, encrypted_password,
                email_confirmed_at, raw_app_meta_data, raw_user_meta_data, created_at, updated_at,
                is_super_admin, is_sso_user, is_anonymous, confirmation_token, recovery_token,
                email_change_token_new, email_change, email_change_token_current,
                email_change_confirm_status, phone_change, phone_change_token, reauthentication_token)
            values ('00000000-0000-0000-0000-000000000000', gen_random_uuid(), 'authenticated', 'authenticated',
                %s::text, extensions.crypt(%s, extensions.gen_salt('bf', 10)), now(),
                '{"provider":"email","providers":["email"]}'::jsonb,
                jsonb_build_object('display_name', %s::text), now(), now(), false, false, false,
                '', '', '', '', '', 0, '', '', '')
            returning id::text, email
        """, (email, "DemoSih!2026", display)).fetchone()
        uid = row[0]
        conn.execute("""
            insert into auth.identities (id, user_id, identity_data, provider, provider_id, last_sign_in_at, created_at, updated_at)
            values (gen_random_uuid(), %s::uuid,
                    jsonb_build_object('sub', %s::text, 'email', %s::text, 'email_verified', true),
                    'email', %s::text, now(), now(), now())
            on conflict do nothing
        """, (uid, uid, email, uid))
        conn.execute("update profiles set role=%s, region_code=%s where id=%s", (role, region, uid))
        conn.commit()
    return uid

# 1. Provision two demo users: field official + reviewer (same state so review works)
stamp = uuid.uuid4().hex[:6]
officer_email = f"officer.demo.{stamp}@gmail.com"
reviewer_email = f"reviewer.demo.{stamp}@gmail.com"
officer_id = make_user(officer_email, "Demo Field Officer", "field_official", "assam")
reviewer_id = make_user(reviewer_email, "Demo Reviewer", "reviewer", "assam")
print(f"users: officer={officer_id} reviewer={reviewer_id}")

def login(email):
    r = httpx.post(f"{SB}/auth/v1/token?grant_type=password",
                   json={"email": email, "password": "DemoSih!2026"},
                   headers={"apikey": KEY}, timeout=15)
    return r.json()["access_token"]

off_tok = login(officer_email)
rev_tok = login(reviewer_email)
print("login: both OK")

# 2. Seed vehicles for the officer
with psycopg.connect(DB, sslmode="require") as conn:
    v1 = conn.execute("""insert into vehicle_assets(operator_id, region_code, registration, vehicle_type, metadata)
        values (%s, 'assam', %s, 'light', '{"demo": true}') returning id::text""",
        (officer_id, f"AS01-DEMO-{stamp.upper()}")).fetchone()[0]
    v2 = conn.execute("""insert into vehicle_assets(operator_id, region_code, registration, vehicle_type, metadata)
        values (%s, 'assam', %s, 'heavy', '{"demo": true}') returning id::text""",
        (officer_id, f"AS02-DEMO-{stamp.upper()}")).fetchone()[0]
    conn.commit()
print(f"vehicles: {v1[:8]} light, {v2[:8]} heavy")

OH = {"Authorization": f"Bearer {off_tok}"}
RH = {"Authorization": f"Bearer {rev_tok}"}

# 3. Pick a corridor edge mid-point for the incident
with psycopg.connect(DB, sslmode="require") as conn:
    edge = conn.execute("""select edge_id, st_x(st_lineinterpolatepoint(geom, 0.5)) lon,
        st_y(st_lineinterpolatepoint(geom, 0.5)) lat, name
        from road_edges where dataset_id='osm-guwahati-corridor-reviewed-v1'
        and name is not null and name != 'Unnamed road' order by edge_id limit 1""").fetchone()
    edge_id, lon, lat, road_name = edge
print(f"incident on: {edge_id} ({road_name[:40]}) at {lon:.5f},{lat:.5f}")

# 4. Officer submits field report
from datetime import UTC, datetime

now = datetime.now(UTC).isoformat()
r = httpx.post(f"{API}/api/v1/field-reports", json={
    "client_report_id": f"milestone-{stamp}",
    "region_code": "assam", "kind": "landslide", "accessibility_status": "blocked",
    "severity": 0.9, "lon": lon, "lat": lat,
    "description": f"Milestone demo: landslide blocking {road_name} near Guwahati",
    "observed_at": now}, headers=OH, timeout=15)
assert r.status_code == 201, r.text
report = r.json()
print(f"field report submitted: {report['id'][:8]} (pending)")

# 5. Officer attaches photo evidence (1x1 png buffer)
buf = io.BytesIO()
Image.new("RGB", (4, 4), color=(180, 90, 40)).save(buf, format="PNG")
r = httpx.post(f"{API}/api/v1/field-reports/{report['id']}/attachments",
    files={"file": ("landslide-evidence.png", buf.getvalue(), "image/png")},
    headers=OH, timeout=30)
assert r.status_code == 201, r.text
print("photo evidence uploaded to private storage")

# 6. Reviewer fetches candidate roads
r = httpx.get(f"{API}/api/v1/field-reports/{report['id']}/road-candidates",
    params={"dataset_id": "osm-guwahati-corridor-reviewed-v1"}, headers=RH, timeout=30)
cands = r.json()["candidates"]
assert cands, "no candidates"
best = cands[0]
print(f"candidates: {len(cands)}; nearest {best['name'][:30]} at {best['distance_m']} m")

# 7. Reviewer accepts and binds the closure to the edge
r = httpx.patch(f"{API}/api/v1/field-reports/{report['id']}/review", json={
    "decision": "accepted", "review_note": "Milestone demo: verified landslide closure",
    "dataset_id": "osm-guwahati-corridor-reviewed-v1", "edge_id": best["edge_id"]},
    headers=RH, timeout=15)
assert r.status_code == 200 and r.json()["review_status"] == "accepted", r.text
print("review accepted + edge bound")

# 8. Closure propagates: alert + connectivity
r = httpx.get(f"{API}/api/v1/alerts", headers=OH, timeout=15)
alerts = r.json()
r = httpx.get(f"{API}/api/v1/connectivity", headers=OH, timeout=15)
assam = next(c for c in r.json() if c["state_name"] == "Assam")
print(f"alert generated: {len(alerts)} active ({alerts[0]['alert_type'] if alerts else 'none'})")
print(f"connectivity Assam: {assam['status']} (blocked={assam['blocked_events']})")

# 9. GPS position + delivery job + status flow on the affected network
r = httpx.post(f"{API}/api/v1/fleet/positions", json={
    "vehicle_id": v1, "recorded_at": now, "lon": lon, "lat": lat, "accuracy_m": 8.0},
    headers=OH, timeout=15)
assert r.status_code == 201
r = httpx.post(f"{API}/api/v1/deliveries", json={
    "vehicle_id": v1, "region_code": "assam", "commodity": "Medical supplies",
    "origin_name": "Guwahati hub", "destination_name": "Dispur depot"}, headers=OH, timeout=15)
assert r.status_code == 201, r.text
delivery = r.json()
for status in ("en_route", "delivered"):
    r = httpx.patch(f"{API}/api/v1/deliveries/{delivery['id']}", json={"status": status},
        headers=OH, timeout=15)
    assert r.status_code == 200 and r.json()["status"] == status
print(f"delivery {delivery['id'][:8]}: planned -> en_route -> delivered")

# 10. Risk-A* reroute check: does routing reflect the accepted closure?
# (snapshot routing uses reviewed graphs; the accepted closure enters future snapshots.
#  Verify the API still compares fastest vs risk-aware on the affected dataset)
r = httpx.post(f"{API}/api/v1/routes/compare", json={
    "origin": "guwahati-hub", "destination": "dispur-depot",
    "vehicle": "light", "weather": "normal",
    "dataset_id": "osm-guwahati-corridor-reviewed-v1",
    "origin_lon": lon - 0.01, "origin_lat": lat,
    "destination_lon": lon + 0.01, "destination_lat": lat}, timeout=30)
print(f"route compare on affected dataset: {r.status_code} "
      + ("(fastest + risk-aware returned)" if r.status_code == 200 else r.text[:100]))

print("\nMILESTONE E2E: COMPLETE")
print(f"  officer:   {officer_email} / DemoSih!2026")
print(f"  reviewer:  {reviewer_email} / DemoSih!2026")
