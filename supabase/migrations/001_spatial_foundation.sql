-- Run in a Supabase project's SQL editor. Application access is through FastAPI.
begin;
create schema if not exists extensions;
create extension if not exists postgis with schema extensions;
set local search_path = public, extensions;

create table if not exists public.dataset_versions (
    id text primary key,
    content_hash text not null,
    metadata jsonb not null,
    imported_at timestamptz not null default now()
);
create table if not exists public.road_nodes (
    dataset_id text not null references public.dataset_versions(id),
    node_id text not null,
    label text,
    geom geometry(Point, 4326) not null,
    primary key (dataset_id, node_id)
);
create table if not exists public.road_edges (
    dataset_id text not null references public.dataset_versions(id),
    edge_id text not null,
    u text not null,
    v text not null,
    name text not null,
    geom geometry(LineString, 4326) not null,
    attributes jsonb not null,
    primary key (dataset_id, edge_id),
    foreign key (dataset_id, u) references public.road_nodes(dataset_id, node_id),
    foreign key (dataset_id, v) references public.road_nodes(dataset_id, node_id)
);
create index if not exists road_edges_geom_gist on public.road_edges using gist(geom);
create index if not exists road_edges_geography_gist on public.road_edges using gist((geom::geography));
create index if not exists road_nodes_geom_gist on public.road_nodes using gist(geom);

create table if not exists public.hazard_observations (
    id uuid primary key default gen_random_uuid(),
    source text not null,
    source_record_id text not null,
    kind text not null check (kind in ('accident', 'blackspot', 'landslide', 'flood', 'road_damage')),
    severity double precision not null check (severity >= 0 and severity <= 1),
    -- Severity is a documented index; not an accident probability.
    geom geometry(Point, 4326) not null,
    observed_at timestamptz not null,
    valid_until timestamptz,
    positional_accuracy_m double precision check (positional_accuracy_m >= 0),
    is_synthetic boolean not null default false,
    details jsonb not null default '{}'::jsonb,
    unique(source, source_record_id),
    check (valid_until is null or valid_until >= observed_at)
);
create index if not exists hazard_geom_gist on public.hazard_observations using gist(geom);
create index if not exists hazard_geography_gist on public.hazard_observations using gist((geom::geography));
create index if not exists hazard_time_idx on public.hazard_observations(observed_at);

create table if not exists public.edge_hazard_reviews (
    dataset_id text not null,
    edge_id text not null,
    hazard_id uuid not null references public.hazard_observations(id),
    decision text not null check (decision in ('candidate', 'accepted', 'rejected')),
    review_note text not null default '',
    reviewed_at timestamptz,
    primary key(dataset_id, edge_id, hazard_id),
    foreign key(dataset_id, edge_id) references public.road_edges(dataset_id, edge_id)
);

-- Proximity produces CANDIDATES, never silently verified matches. Check parallel
-- carriageways, bridges, coordinate accuracy, observation age and road identity.
create or replace function public.hazard_edge_candidates(
    p_dataset text, p_hazard uuid, p_radius_m double precision default 150
) returns table(edge_id text, name text, distance_m double precision)
language sql stable security invoker set search_path = public, extensions as $$
    select e.edge_id, e.name, st_distance(e.geom::geography, h.geom::geography)
    from public.road_edges e cross join public.hazard_observations h
    where e.dataset_id = p_dataset and h.id = p_hazard
      and p_radius_m between 1 and 2000
      and st_dwithin(e.geom::geography, h.geom::geography, p_radius_m)
    order by st_distance(e.geom::geography, h.geom::geography)
    limit 10
$$;

alter table public.dataset_versions enable row level security;
alter table public.road_nodes enable row level security;
alter table public.road_edges enable row level security;
alter table public.hazard_observations enable row level security;
alter table public.edge_hazard_reviews enable row level security;
-- No browser access policies. Keep privileged credentials in backend/server tooling.
revoke all on public.dataset_versions, public.road_nodes, public.road_edges,
    public.hazard_observations, public.edge_hazard_reviews from anon, authenticated;
revoke all on function public.hazard_edge_candidates(text, uuid, double precision) from public;
grant execute on function public.hazard_edge_candidates(text, uuid, double precision) to service_role;
commit;
