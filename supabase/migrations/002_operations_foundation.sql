-- NER catalog and field-accessibility operations. Application writes go through FastAPI.
begin;
set local search_path = public, extensions;

create table if not exists public.region_catalog (
    code text primary key,
    state_name text not null unique,
    capital_name text not null,
    capital_geom geometry(Point, 4326) not null,
    boundary geometry(MultiPolygon, 4326),
    road_ways integer not null check (road_ways >= 0),
    place_features integer not null check (place_features >= 0),
    facility_features integer not null check (facility_features >= 0),
    runtime_graph jsonb,
    source_metadata jsonb not null default '{}'::jsonb,
    updated_at timestamptz not null default now()
);
create index if not exists region_catalog_capital_gist on public.region_catalog using gist(capital_geom);
create index if not exists region_catalog_boundary_gist on public.region_catalog using gist(boundary);

create table if not exists public.field_reports (
    id uuid primary key default gen_random_uuid(),
    client_report_id text not null unique,
    reporter_id uuid references auth.users(id) on delete set null,
    region_code text not null references public.region_catalog(code),
    district text,
    place_name text,
    kind text not null check (kind in (
        'road_blocked', 'road_damage', 'bridge_damage', 'landslide', 'flood',
        'heavy_rain', 'traffic_congestion', 'other'
    )),
    accessibility_status text not null check (
        accessibility_status in ('open', 'restricted', 'blocked', 'unknown')
    ),
    severity double precision not null check (severity between 0 and 1),
    geom geometry(Point, 4326) not null,
    description text not null check (char_length(description) between 5 and 2000),
    observed_at timestamptz not null,
    submitted_at timestamptz not null default now(),
    review_status text not null default 'pending' check (
        review_status in ('pending', 'accepted', 'rejected', 'expired')
    ),
    reviewed_by uuid references auth.users(id) on delete set null,
    reviewed_at timestamptz,
    review_note text not null default '',
    valid_until timestamptz,
    offline_created_at timestamptz,
    details jsonb not null default '{}'::jsonb,
    check (valid_until is null or valid_until >= observed_at),
    check ((review_status = 'pending' and reviewed_at is null) or review_status <> 'pending')
);
create index if not exists field_reports_geom_gist on public.field_reports using gist(geom);
create index if not exists field_reports_region_status_idx
    on public.field_reports(region_code, review_status, observed_at desc);

create table if not exists public.field_report_attachments (
    id uuid primary key default gen_random_uuid(),
    report_id uuid not null references public.field_reports(id) on delete cascade,
    storage_bucket text not null default 'field-report-evidence',
    storage_path text not null unique,
    mime_type text not null check (mime_type in ('image/jpeg', 'image/png', 'image/webp')),
    byte_size integer not null check (byte_size between 1 and 10485760),
    sha256 text not null check (sha256 ~ '^[0-9a-f]{64}$'),
    captured_at timestamptz,
    uploaded_at timestamptz not null default now(),
    metadata jsonb not null default '{}'::jsonb
);
create index if not exists field_report_attachments_report_idx
    on public.field_report_attachments(report_id);

create table if not exists public.accessibility_events (
    id uuid primary key default gen_random_uuid(),
    source_report_id uuid unique references public.field_reports(id) on delete set null,
    region_code text not null references public.region_catalog(code),
    dataset_id text,
    edge_id text,
    kind text not null,
    accessibility_status text not null check (
        accessibility_status in ('open', 'restricted', 'blocked')
    ),
    severity double precision not null check (severity between 0 and 1),
    geom geometry(Point, 4326) not null,
    starts_at timestamptz not null,
    ends_at timestamptz,
    source text not null,
    details jsonb not null default '{}'::jsonb,
    created_at timestamptz not null default now(),
    check (ends_at is null or ends_at >= starts_at)
);
create index if not exists accessibility_events_geom_gist
    on public.accessibility_events using gist(geom);
create index if not exists accessibility_events_active_idx
    on public.accessibility_events(region_code, starts_at desc, ends_at);

create table if not exists public.alerts (
    id uuid primary key default gen_random_uuid(),
    event_id uuid not null references public.accessibility_events(id) on delete cascade,
    alert_type text not null check (alert_type in ('blocked_route', 'high_risk', 'delay', 'reopened')),
    severity double precision not null check (severity between 0 and 1),
    title text not null,
    message_key text not null,
    message_params jsonb not null default '{}'::jsonb,
    created_at timestamptz not null default now(),
    expires_at timestamptz,
    check (expires_at is null or expires_at >= created_at)
);
create index if not exists alerts_created_idx on public.alerts(created_at desc);

create table if not exists public.operation_audit_log (
    id bigint generated always as identity primary key,
    actor_id uuid references auth.users(id) on delete set null,
    action text not null,
    entity_type text not null,
    entity_id text not null,
    before_state jsonb,
    after_state jsonb,
    created_at timestamptz not null default now()
);
create index if not exists operation_audit_entity_idx
    on public.operation_audit_log(entity_type, entity_id, created_at desc);

alter table public.region_catalog enable row level security;
alter table public.field_reports enable row level security;
alter table public.field_report_attachments enable row level security;
alter table public.accessibility_events enable row level security;
alter table public.alerts enable row level security;
alter table public.operation_audit_log enable row level security;

revoke all on public.region_catalog, public.field_reports, public.field_report_attachments,
    public.accessibility_events, public.alerts, public.operation_audit_log from anon, authenticated;

commit;
