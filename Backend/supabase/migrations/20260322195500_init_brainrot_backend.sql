create table if not exists public.batches (
  id uuid primary key,
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

create index if not exists batches_metadata_chat_id_idx
  on public.batches ((metadata ->> 'chat_id'));

create table if not exists public.batch_items (
  id uuid primary key,
  batch_id uuid not null references public.batches(id) on delete cascade,
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

create table if not exists public.batch_events (
  sequence bigint generated always as identity primary key,
  batch_id uuid not null references public.batches(id) on delete cascade,
  event_type text not null,
  payload jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default timezone('utc', now())
);

create table if not exists public.source_documents (
  batch_id uuid primary key references public.batches(id) on delete cascade,
  source_kind text not null,
  original_url text,
  title text not null,
  content_markdown text not null,
  normalized_urls jsonb not null default '[]'::jsonb,
  metadata jsonb not null default '{}'::jsonb
);

create table if not exists public.assets (
  id uuid primary key,
  kind text not null,
  bucket text not null,
  path text not null,
  public_url text,
  tags jsonb not null default '[]'::jsonb,
  metadata jsonb not null default '{}'::jsonb,
  created_at timestamptz not null
);

create table if not exists public.agent_configs (
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

create table if not exists public.agent_runs (
  id uuid primary key,
  batch_id uuid not null references public.batches(id) on delete cascade,
  batch_item_id uuid references public.batch_items(id) on delete cascade,
  role text not null,
  agent_config_id uuid not null references public.agent_configs(id) on delete cascade,
  status text not null,
  conversation_id text,
  error text,
  payload jsonb not null default '{}'::jsonb,
  metadata jsonb not null default '{}'::jsonb,
  created_at timestamptz not null,
  updated_at timestamptz not null
);

create table if not exists public.agent_conversations (
  conversation_id text primary key,
  batch_id uuid references public.batches(id) on delete cascade,
  batch_item_id uuid references public.batch_items(id) on delete cascade,
  role text not null,
  agent_config_id uuid references public.agent_configs(id) on delete set null,
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

create table if not exists public.alignment_jobs (
  id uuid primary key,
  batch_id uuid not null references public.batches(id) on delete cascade,
  batch_item_id uuid not null references public.batch_items(id) on delete cascade,
  conversation_id text,
  status text not null,
  word_count integer not null default 0,
  metadata jsonb not null default '{}'::jsonb,
  created_at timestamptz not null,
  updated_at timestamptz not null
);

insert into storage.buckets (id, name, public)
values
  ('sources', 'sources', true),
  ('gameplay', 'gameplay', true),
  ('music', 'music', true),
  ('fonts', 'fonts', true),
  ('overlays', 'overlays', true),
  ('temp-audio', 'temp-audio', true),
  ('subtitles', 'subtitles', true),
  ('final-renders', 'final-renders', true)
on conflict (id) do nothing;
