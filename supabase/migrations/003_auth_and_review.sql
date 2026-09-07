-- Authenticated field operations and reviewer-controlled incident promotion.
begin;
set local search_path = public, extensions;

create table if not exists public.profiles (
    id uuid primary key references auth.users(id) on delete cascade,
    display_name text,
    role text not null default 'field_official'
        check (role in ('field_official', 'reviewer', 'admin')),
    region_code text references public.region_catalog(code),
    created_at timestamptz not null default now(),
    updated_at timestamptz not null default now()
);

create or replace function public.handle_new_user()
returns trigger language plpgsql security definer set search_path = public as $$
begin
    insert into public.profiles(id, display_name)
    values(new.id, coalesce(new.raw_user_meta_data ->> 'display_name', split_part(new.email, '@', 1)))
    on conflict(id) do nothing;
    return new;
end;
$$;

drop trigger if exists on_auth_user_created on auth.users;
create trigger on_auth_user_created
after insert on auth.users for each row execute procedure public.handle_new_user();

insert into public.profiles(id, display_name)
select id, coalesce(raw_user_meta_data ->> 'display_name', split_part(email, '@', 1))
from auth.users on conflict(id) do nothing;

insert into storage.buckets(id, name, public, file_size_limit, allowed_mime_types)
values(
    'field-report-evidence', 'field-report-evidence', false, 10485760,
    array['image/jpeg', 'image/png', 'image/webp']
)
on conflict(id) do update set
    public=false, file_size_limit=excluded.file_size_limit,
    allowed_mime_types=excluded.allowed_mime_types;

drop policy if exists "field officials upload own evidence" on storage.objects;
create policy "field officials upload own evidence" on storage.objects
for insert to authenticated
with check (
    bucket_id = 'field-report-evidence'
    and (storage.foldername(name))[1] = (select auth.uid()::text)
);
drop policy if exists "field officials read own evidence" on storage.objects;
create policy "field officials read own evidence" on storage.objects
for select to authenticated
using (
    bucket_id = 'field-report-evidence'
    and (storage.foldername(name))[1] = (select auth.uid()::text)
);

alter table public.profiles enable row level security;
revoke all on public.profiles from anon, authenticated;

commit;
