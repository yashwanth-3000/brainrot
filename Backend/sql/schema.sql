create table if not exists chats (
  id text primary key,
  title text not null,
  library_scope text not null default 'general',
  owner_user_id uuid,
  created_at timestamptz not null,
  updated_at timestamptz not null,
  last_source_label text,
  last_source_url text,
  total_runs integer not null default 0,
  total_exported integer not null default 0,
  total_failed integer not null default 0,
  last_status text,
  cover_batch_id uuid,
  cover_item_id uuid,
  cover_output_url text,
  metadata jsonb not null default '{}'::jsonb
);

do $$
begin
  if not exists (
    select 1
    from pg_constraint
    where conname = 'chats_library_scope_check'
  ) then
    alter table chats
      add constraint chats_library_scope_check
      check (library_scope in ('general', 'user'));
  end if;
end $$;

do $$
begin
  if not exists (
    select 1
    from pg_constraint
    where conname = 'chats_owner_scope_consistency_check'
  ) then
    alter table chats
      add constraint chats_owner_scope_consistency_check
      check (
        (library_scope = 'general' and owner_user_id is null)
        or (library_scope = 'user' and owner_user_id is not null)
      );
  end if;
end $$;

create table if not exists batches (
  id uuid primary key,
  chat_id text references chats(id) on delete set null,
  source_kind text not null,
  source_url text,
  title_hint text,
  requested_count integer not null,
  status text not null,
  producer_agent_config_id uuid,
  narrator_agent_config_id uuid,
  premium_audio boolean not null default false,
  created_at timestamptz not null,
  updated_at timestamptz not null,
  error text,
  metadata jsonb not null default '{}'::jsonb
);

create index if not exists chats_updated_at_idx
  on chats (updated_at desc);

create index if not exists chats_library_scope_updated_at_idx
  on chats (library_scope, updated_at desc);

create index if not exists chats_owner_user_id_updated_at_idx
  on chats (owner_user_id, updated_at desc)
  where owner_user_id is not null;

create index if not exists batches_chat_id_idx
  on batches (chat_id);

create table if not exists batch_items (
  id uuid primary key,
  batch_id uuid not null references batches(id) on delete cascade,
  item_index integer not null,
  status text not null,
  script jsonb,
  narration_conversation_id text,
  output_url text,
  error text,
  render_metadata jsonb not null default '{}'::jsonb,
  created_at timestamptz not null,
  updated_at timestamptz not null
);

create table if not exists short_engagement_events (
  id uuid primary key,
  chat_id text not null references chats(id) on delete cascade,
  batch_id uuid references batches(id) on delete cascade,
  item_id uuid not null references batch_items(id) on delete cascade,
  viewer_id text not null,
  session_id text not null,
  watch_time_seconds double precision not null default 0,
  completion_ratio double precision not null default 0,
  max_progress_seconds double precision not null default 0,
  replay_count integer not null default 0,
  unmuted boolean not null default false,
  info_opened boolean not null default false,
  open_clicked boolean not null default false,
  liked boolean not null default false,
  skipped_early boolean not null default false,
  metadata jsonb not null default '{}'::jsonb,
  created_at timestamptz not null,
  updated_at timestamptz not null
);

create unique index if not exists short_engagement_events_session_id_idx
  on short_engagement_events (session_id);

create index if not exists short_engagement_events_chat_id_idx
  on short_engagement_events (chat_id, updated_at desc);

create table if not exists batch_events (
  sequence bigint generated always as identity primary key,
  batch_id uuid not null references batches(id) on delete cascade,
  event_type text not null,
  payload jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default timezone('utc', now())
);

create table if not exists source_documents (
  batch_id uuid primary key references batches(id) on delete cascade,
  source_kind text not null,
  original_url text,
  title text not null,
  content_markdown text not null,
  normalized_urls jsonb not null default '[]'::jsonb,
  metadata jsonb not null default '{}'::jsonb
);

create table if not exists assets (
  id uuid primary key,
  kind text not null,
  bucket text not null,
  path text not null,
  public_url text,
  tags jsonb not null default '[]'::jsonb,
  metadata jsonb not null default '{}'::jsonb,
  created_at timestamptz not null
);

create table if not exists agent_configs (
  id uuid primary key,
  role text not null,
  name text not null,
  agent_id text not null,
  branch_id text,
  version_id text,
  tool_ids jsonb not null default '[]'::jsonb,
  is_active boolean not null default true,
  metadata jsonb not null default '{}'::jsonb,
  created_at timestamptz not null,
  updated_at timestamptz not null
);

create table if not exists agent_runs (
  id uuid primary key,
  batch_id uuid not null references batches(id) on delete cascade,
  batch_item_id uuid references batch_items(id) on delete cascade,
  role text not null,
  agent_config_id uuid references agent_configs(id) on delete cascade,
  status text not null,
  conversation_id text,
  error text,
  payload jsonb not null default '{}'::jsonb,
  metadata jsonb not null default '{}'::jsonb,
  created_at timestamptz not null,
  updated_at timestamptz not null
);

create table if not exists agent_conversations (
  conversation_id text primary key,
  batch_id uuid references batches(id) on delete cascade,
  batch_item_id uuid references batch_items(id) on delete cascade,
  role text not null,
  agent_config_id uuid references agent_configs(id) on delete set null,
  status text not null,
  transcript jsonb not null default '[]'::jsonb,
  transcript_text text,
  has_audio boolean not null default false,
  has_response_audio boolean not null default false,
  audio_bucket text,
  audio_path text,
  metadata jsonb not null default '{}'::jsonb,
  created_at timestamptz not null,
  updated_at timestamptz not null
);

create table if not exists alignment_jobs (
  id uuid primary key,
  batch_id uuid not null references batches(id) on delete cascade,
  batch_item_id uuid not null references batch_items(id) on delete cascade,
  conversation_id text,
  status text not null,
  word_count integer not null default 0,
  metadata jsonb not null default '{}'::jsonb,
  created_at timestamptz not null,
  updated_at timestamptz not null
);
