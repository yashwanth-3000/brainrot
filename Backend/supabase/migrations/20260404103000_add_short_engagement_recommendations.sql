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
