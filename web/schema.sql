-- Drive Radio for Friends — initial schema
-- Run this once in the Supabase SQL Editor (Dashboard -> SQL Editor -> New query).

-- ============================================================
-- allowlist: gates account creation. No RLS policies are defined
-- for it below, which means anon/authenticated get zero access by
-- default (RLS on with no policy = deny-all for those roles) — the
-- only way in is the SECURITY DEFINER trigger function below, or
-- the service_role key (which bypasses RLS entirely), or you
-- editing it directly in the SQL Editor.
-- ============================================================
create table public.allowlist (
  email text primary key,
  created_at timestamptz not null default now()
);

alter table public.allowlist enable row level security;

-- Seed with your own email (and each friend's, before inviting them) via
-- the SQL Editor or the Supabase table view — not committed here, since
-- this repo is public.
-- insert into public.allowlist (email) values ('you@example.com');

-- Enforce the allowlist at the database level, so it can't be
-- bypassed by client-side logic — reject signup for any email not
-- already present in the table.
create or replace function public.check_allowlist()
returns trigger
language plpgsql
security definer
set search_path = public
as $$
begin
  if not exists (select 1 from public.allowlist where email = new.email) then
    raise exception 'Email % is not on the allowlist', new.email;
  end if;
  return new;
end;
$$;

create trigger enforce_allowlist
before insert on auth.users
for each row execute function public.check_allowlist();

-- Supabase Auth wraps the trigger's exception into a generic "Database
-- error saving new user" rather than passing the message through, so the
-- client can't distinguish "not invited" from any other failure. This RPC
-- lets the login page check *before* attempting sign-in and show an
-- accurate message. SECURITY DEFINER + explicit grant is required since
-- allowlist itself has no policies (anon/authenticated get zero direct
-- access to the table).
create or replace function public.is_allowlisted(check_email text)
returns boolean
language sql
security definer
set search_path = public
as $$
  select exists (select 1 from public.allowlist where email = check_email);
$$;

grant execute on function public.is_allowlisted(text) to anon, authenticated;

-- ============================================================
-- user_preferences: one row per user, editable by that user only.
-- ============================================================
create table public.user_preferences (
  user_id uuid primary key references auth.users(id) on delete cascade,
  rss_feeds text[] not null default '{}',
  hn_story_count int not null default 15,
  target_word_count_min int not null default 2200,
  target_word_count_max int not null default 2700,
  host_a_voice text not null default 'am_onyx',
  host_b_voice text not null default 'af_heart',
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

alter table public.user_preferences enable row level security;

create policy "select own preferences"
  on public.user_preferences for select
  using (auth.uid() = user_id);

create policy "insert own preferences"
  on public.user_preferences for insert
  with check (auth.uid() = user_id);

create policy "update own preferences"
  on public.user_preferences for update
  using (auth.uid() = user_id)
  with check (auth.uid() = user_id);

-- Keep updated_at current on every edit.
create or replace function public.set_updated_at()
returns trigger
language plpgsql
as $$
begin
  new.updated_at = now();
  return new;
end;
$$;

create trigger user_preferences_set_updated_at
before update on public.user_preferences
for each row execute function public.set_updated_at();

-- ============================================================
-- episodes: written by the generation script (service_role, which
-- bypasses RLS) — no insert/update/delete policy is defined for
-- anon/authenticated, so users can only ever read their own rows,
-- never write to this table directly.
-- ============================================================
create table public.episodes (
  id uuid primary key default gen_random_uuid(),
  user_id uuid not null references auth.users(id) on delete cascade,
  mp3_filename text not null,
  title text not null,
  description text not null,
  url text not null,
  pub_date timestamptz not null,
  duration_seconds int not null,
  file_size_bytes bigint not null,
  created_at timestamptz not null default now()
);

alter table public.episodes enable row level security;

create policy "select own episodes"
  on public.episodes for select
  using (auth.uid() = user_id);

create index episodes_user_id_pub_date_idx
  on public.episodes (user_id, pub_date desc);

-- Lets multi_tenant.py upsert on (user_id, mp3_filename) instead of blindly
-- inserting, so a same-day re-run (manual workflow_dispatch landing on top
-- of the scheduled cron, an Actions retry) replaces that day's row instead
-- of duplicating it.
create unique index episodes_user_id_mp3_filename_idx
  on public.episodes (user_id, mp3_filename);
