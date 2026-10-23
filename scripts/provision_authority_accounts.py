"""Create the remaining Supabase Auth authority accounts and provision roles.

Accounts already provisioned earlier (sdrf.arunachal / pwd.assam reviewers) are
skipped automatically. Run this after the Supabase signup email rate limit resets
(typically one hour) or from a different network.

Usage (from repo root):
    python .venv/Scripts/python.exe scripts/provision_authority_accounts.py
"""

from __future__ import annotations

import os
import time
from pathlib import Path

import httpx
import psycopg
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[1]
load_dotenv(ROOT / ".env")

ACCOUNTS = [
    # (email, password environment variable, profile role, region, display name)
    ("sdrf.arunachal.raahsetu@gmail.com", "RAAHSETU_PASSWORD_SDRF_ARUNACHAL", "reviewer", "arunachal-pradesh", "Insp. Tenzing Norbu"),
    ("pwd.assam.raahsetu@gmail.com", "RAAHSETU_PASSWORD_PWD_ASSAM", "reviewer", "assam", "Er. Bhupen Barman"),
    ("dispatcher.ner.raahsetu@gmail.com", "RAAHSETU_PASSWORD_DISPATCHER", "field_official", "assam", "Rajesh Sharma"),
    ("driver.anup.raahsetu@gmail.com", "RAAHSETU_PASSWORD_DRIVER", "field_official", "assam", "Ranjit Gogoi"),
    ("admin.raahsetu.hq@gmail.com", "RAAHSETU_PASSWORD_ADMIN", "admin", None, "State Emergency Control Officer"),
]

# Frontend session role label used by the dashboard for profile-gated features.
SESSION_ROLE = {
    "reviewer": "reviewer",
    "field_official": "dispatcher",
    "admin": "admin",
}


def main() -> None:
    url = os.environ["SUPABASE_URL"]
    key = os.environ["SUPABASE_PUBLISHABLE_KEY"]
    db = os.environ["DATABASE_URL"]
    with psycopg.connect(db, connect_timeout=15) as conn:
        for email, password_var, role, region, name in ACCOUNTS:
            existing = conn.execute(
                "select id from auth.users where email=%s", (email,)
            ).fetchone()
            if existing:
                print(f"already exists: {email} (role set earlier or pending)")
                continue
            pwd = os.getenv(password_var)
            if not pwd:
                print(f"SKIPPED {email}: set {password_var} in the local environment first")
                continue
            resp = httpx.post(
                f"{url}/auth/v1/signup",
                headers={"apikey": key, "Content-Type": "application/json"},
                json={"email": email, "password": pwd, "data": {"display_name": name}},
                timeout=30,
            )
            if resp.status_code in (200, 201):
                uid = resp.json().get("user", {}).get("id") or resp.json().get("id")
                with conn.cursor() as cur:
                    cur.execute(
                        "update profiles set role=%s, region_code=%s, display_name=%s where id=%s",
                        (role, region, name, uid),
                    )
                conn.commit()
                print(f"created {email} -> {role}")
            else:
                print(f"FAILED {email}: {resp.status_code} {resp.text[:120]}")
                print("Email rate limit active; retry in ~1 hour.")
                return
            time.sleep(5)
    print("Authority account provisioning complete.")


if __name__ == "__main__":
    main()
