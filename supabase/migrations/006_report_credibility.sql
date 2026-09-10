-- Evidence corroboration is informational: only a reviewer or admin can promote a report.
begin;
set local search_path = public, extensions;

create or replace view public.field_report_credibility as
select
    report.id as report_id,
    count(distinct corroborator.reporter_id) filter (
        where corroborator.reporter_id is not null
          and corroborator.reporter_id <> report.reporter_id
    )::int as corroborating_reporters,
    count(corroborator.id)::int as corroborating_reports,
    case
        when report.review_status = 'accepted' then 'verified'
        when report.review_status = 'rejected' then 'rejected'
        when count(distinct corroborator.reporter_id) filter (
            where corroborator.reporter_id is not null
              and corroborator.reporter_id <> report.reporter_id
        ) >= 2 then 'corroborated'
        else 'pending_evidence'
    end as credibility_status
from public.field_reports report
left join public.field_reports corroborator
    on corroborator.id <> report.id
   and corroborator.region_code = report.region_code
   and corroborator.kind = report.kind
   and corroborator.accessibility_status = report.accessibility_status
   and corroborator.review_status in ('pending', 'accepted')
   and corroborator.observed_at between report.observed_at - interval '6 hours'
                                and report.observed_at + interval '6 hours'
   and st_dwithin(corroborator.geom::geography, report.geom::geography, 1000)
group by report.id, report.review_status;

comment on view public.field_report_credibility is
    'Nearby, time-bounded independent-report corroboration. It never auto-accepts or auto-closes a road.';

revoke all on public.field_report_credibility from anon, authenticated;
grant select on public.field_report_credibility to service_role;

commit;
