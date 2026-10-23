"""Create a local PostGIS-compatible database and apply RaahSetu migrations."""

from __future__ import annotations

import os
from pathlib import Path

import psycopg
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[2]
load_dotenv(ROOT / ".env")

COMPATIBILITY_SQL = """
create extension if not exists postgis;
create extension if not exists pgcrypto;
create schema if not exists auth;
create schema if not exists storage;
do $$ begin
  if not exists (select 1 from pg_roles where rolname = 'anon') then create role anon nologin; end if;
  if not exists (select 1 from pg_roles where rolname = 'authenticated') then create role authenticated nologin; end if;
  if not exists (select 1 from pg_roles where rolname = 'service_role') then create role service_role nologin; end if;
end $$;
create table if not exists auth.users (
  id uuid primary key,
  email text unique,
  raw_user_meta_data jsonb default '{}'::jsonb
);
create table if not exists storage.buckets (
  id text primary key,
  name text not null,
  public boolean not null default false,
  created_at timestamptz default now(),
  updated_at timestamptz default now()
);
create table if not exists storage.objects (
  id uuid primary key default gen_random_uuid(),
  bucket_id text not null references storage.buckets(id),
  name text not null,
  owner uuid,
  created_at timestamptz default now(),
  updated_at timestamptz default now(),
  metadata jsonb default '{}'::jsonb
);
create or replace function storage.foldername(name text)
returns text[] language sql immutable as $$ select string_to_array(name, '/') $$;
create or replace function auth.uid()
returns uuid language sql stable as $$ select null::uuid $$;
"""


def main() -> None:
    url = os.getenv("LOCAL_DATABASE_URL")
    if not url:
        raise SystemExit("LOCAL_DATABASE_URL is required in .env")
    sslmode = os.getenv("LOCAL_DATABASE_SSLMODE", "disable")
    migrations = sorted((ROOT / "supabase" / "migrations").glob("*.sql"))
    with psycopg.connect(url, sslmode=sslmode) as conn:
        conn.execute(COMPATIBILITY_SQL)
        for migration in migrations:
            conn.execute(migration.read_text(encoding="utf-8"))
            print(f"Applied {migration.name}")
    print("Local PostGIS database is ready.")


if __name__ == "__main__":
    main()
