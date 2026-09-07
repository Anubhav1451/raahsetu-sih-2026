begin;
set local search_path = public, extensions;

create table if not exists public.vehicle_assets (
    id uuid primary key default gen_random_uuid(),
    operator_id uuid not null references auth.users(id) on delete cascade,
    region_code text not null references public.region_catalog(code),
    registration text not null,
    vehicle_type text not null check (vehicle_type in ('heavy', 'emergency', 'light')),
    active boolean not null default true,
    metadata jsonb not null default '{}'::jsonb,
    created_at timestamptz not null default now(),
    unique (operator_id, registration)
);
create index if not exists vehicle_assets_region_idx on public.vehicle_assets(region_code, active);

create table if not exists public.vehicle_positions (
    id bigint generated always as identity primary key,
    vehicle_id uuid not null references public.vehicle_assets(id) on delete cascade,
    recorded_at timestamptz not null,
    geom geometry(Point, 4326) not null,
    speed_kph double precision check (speed_kph is null or speed_kph between 0 and 200),
    heading double precision check (heading is null or heading between 0 and 360),
    status text not null default 'en_route' check (status in ('en_route', 'delayed', 'stopped', 'delivered')),
    accuracy_m double precision check (accuracy_m is null or accuracy_m between 0 and 10000),
    metadata jsonb not null default '{}'::jsonb,
    unique (vehicle_id, recorded_at)
);
create index if not exists vehicle_positions_latest_idx on public.vehicle_positions(vehicle_id, recorded_at desc);
create index if not exists vehicle_positions_geom_gist on public.vehicle_positions using gist(geom);

create table if not exists public.delivery_jobs (
    id uuid primary key default gen_random_uuid(),
    vehicle_id uuid not null references public.vehicle_assets(id) on delete restrict,
    region_code text not null references public.region_catalog(code),
    commodity text not null,
    origin_name text not null,
    destination_name text not null,
    status text not null default 'planned' check (status in ('planned', 'en_route', 'delayed', 'delivered', 'cancelled')),
    eta_at timestamptz,
    delivered_at timestamptz,
    created_at timestamptz not null default now(),
    metadata jsonb not null default '{}'::jsonb
);
create index if not exists delivery_jobs_region_status_idx on public.delivery_jobs(region_code, status, created_at desc);

alter table public.vehicle_assets enable row level security;
alter table public.vehicle_positions enable row level security;
alter table public.delivery_jobs enable row level security;
revoke all on public.vehicle_assets, public.vehicle_positions, public.delivery_jobs from anon, authenticated;
commit;
