begin;
set local search_path = public, extensions;
create table if not exists public.disruption_candidates (
    id uuid primary key default gen_random_uuid(),
    candidate_id text not null unique,
    region_code text not null references public.region_catalog(code),
    road_text text not null,
    source_url text not null,
    source_type text not null,
    published_at timestamptz,
    reported_status text not null,
    review_status text not null default 'pending' check (review_status in ('pending','needs_location','needs_time','needs_second_review','approved','rejected','duplicate','non_operational')),
    road_segment_id text,
    incident_started_at timestamptz,
    incident_ended_at timestamptz,
    reviewer_id uuid references auth.users(id),
    reviewed_at timestamptz,
    review_note text not null default '',
    evidence_hash text,
    metadata jsonb not null default '{}'::jsonb,
    created_at timestamptz not null default now(),
    check (review_status <> 'approved' or (road_segment_id is not null and incident_started_at is not null))
);
create index if not exists disruption_candidates_review_idx on public.disruption_candidates(review_status, region_code, published_at desc);
alter table public.disruption_candidates enable row level security;
revoke all on public.disruption_candidates from anon, authenticated;
commit;
