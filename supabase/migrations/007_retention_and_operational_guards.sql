begin;
set local search_path = public, extensions;

-- Operational queries read the newest positions and active jobs. These indexes
-- keep those bounded as history grows.
create index if not exists vehicle_positions_recorded_brin
    on public.vehicle_positions using brin(recorded_at);
create index if not exists delivery_jobs_vehicle_status_idx
    on public.delivery_jobs(vehicle_id, status, created_at desc);

-- Retention is deliberately explicit: an administrator schedules this function
-- only after the deployment's consent and records-retention policy is approved.
create or replace function public.purge_expired_operational_data(
    position_retention_days integer default 90,
    completed_job_retention_days integer default 365
)
returns table(deleted_positions bigint, deleted_jobs bigint)
language plpgsql
security definer
set search_path = public, pg_temp
as $$
declare
    position_count bigint;
    job_count bigint;
begin
    if position_retention_days < 1 or completed_job_retention_days < 1 then
        raise exception 'Retention windows must be at least one day';
    end if;

    delete from public.vehicle_positions
    where recorded_at < now() - make_interval(days => position_retention_days);
    get diagnostics position_count = row_count;

    delete from public.delivery_jobs
    where status in ('delivered', 'cancelled')
      and created_at < now() - make_interval(days => completed_job_retention_days);
    get diagnostics job_count = row_count;

    return query select position_count, job_count;
end;
$$;

revoke all on function public.purge_expired_operational_data(integer, integer)
    from public, anon, authenticated;

commit;
