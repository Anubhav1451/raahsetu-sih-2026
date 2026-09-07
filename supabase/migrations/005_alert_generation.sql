begin;
set local search_path = public, extensions;

create unique index if not exists alerts_event_type_unique
    on public.alerts(event_id, alert_type);

comment on column public.alerts.message_key is
    'Stable translation key; clients render localized text from this key and message_params.';

commit;
