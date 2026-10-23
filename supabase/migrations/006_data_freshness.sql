-- Source freshness and immutable import audit metadata.
begin;
set local search_path = public, extensions;

create table if not exists public.data_source_registry (
    source_id text primary key,
    source_name text not null,
    agency text,
    source_url text,
    source_kind text not null,
    coverage text not null default '',
    status text not null check (status in ('fresh', 'stale', 'expired', 'fallback', 'standby', 'unknown')),
    last_observed_at timestamptz,
    last_imported_at timestamptz,
    valid_until timestamptz,
    dataset_version text,
    content_hash text,
    record_count integer not null default 0 check (record_count >= 0),
    review_status text not null default 'pending',
    metadata jsonb not null default '{}'::jsonb,
    updated_at timestamptz not null default now()
);
create index if not exists data_source_registry_status_idx
    on public.data_source_registry(status, updated_at desc);
create index if not exists data_source_registry_validity_idx
    on public.data_source_registry(valid_until);

create table if not exists public.data_import_runs (
    id bigint generated always as identity primary key,
    source_id text not null references public.data_source_registry(source_id),
    dataset_version text,
    content_hash text,
    started_at timestamptz not null default now(),
    completed_at timestamptz,
    status text not null check (status in ('started', 'succeeded', 'failed', 'rolled_back')),
    records_seen integer not null default 0 check (records_seen >= 0),
    error_message text,
    metadata jsonb not null default '{}'::jsonb
);
create index if not exists data_import_runs_source_idx
    on public.data_import_runs(source_id, started_at desc);

alter table public.data_source_registry enable row level security;
alter table public.data_import_runs enable row level security;
revoke all on public.data_source_registry, public.data_import_runs from anon, authenticated;
commit;
