create table if not exists public.chats (
  id text primary key,
  title text not null,
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

alter table public.batches
  add column if not exists chat_id text;

update public.batches
set chat_id = metadata ->> 'chat_id'
where chat_id is null
  and metadata ? 'chat_id'
  and nullif(metadata ->> 'chat_id', '') is not null;

do $$
begin
  if not exists (
    select 1
    from pg_constraint
    where conname = 'batches_chat_id_fkey'
  ) then
    alter table public.batches
      add constraint batches_chat_id_fkey
      foreign key (chat_id) references public.chats(id) on delete set null;
  end if;
end $$;

create index if not exists chats_updated_at_idx
  on public.chats (updated_at desc);

create index if not exists batches_chat_id_idx
  on public.batches (chat_id);

with batch_stats as (
  select
    b.chat_id,
    min(b.created_at) as created_at,
    max(b.updated_at) as updated_at,
    (array_agg(coalesce(sd.title, b.title_hint, b.source_url, 'Untitled chat') order by b.updated_at desc))[1] as last_source_label,
    (array_agg(b.source_url order by b.updated_at desc))[1] as last_source_url,
    count(*)::integer as total_runs,
    coalesce(sum(item_stats.uploaded_count), 0)::integer as total_exported,
    coalesce(sum(item_stats.failed_count), 0)::integer as total_failed,
    (array_agg(b.status order by b.updated_at desc))[1] as last_status
  from public.batches b
  left join public.source_documents sd
    on sd.batch_id = b.id
  left join lateral (
    select
      count(*) filter (where bi.status = 'uploaded') as uploaded_count,
      count(*) filter (where bi.status = 'failed') as failed_count
    from public.batch_items bi
    where bi.batch_id = b.id
  ) item_stats on true
  where b.chat_id is not null
    and b.chat_id <> ''
  group by b.chat_id
),
chat_covers as (
  select distinct on (b.chat_id)
    b.chat_id,
    b.id as cover_batch_id,
    bi.id as cover_item_id,
    bi.output_url as cover_output_url
  from public.batches b
  join public.batch_items bi
    on bi.batch_id = b.id
  where b.chat_id is not null
    and b.chat_id <> ''
    and bi.status = 'uploaded'
    and bi.output_url is not null
  order by b.chat_id, b.updated_at desc, bi.updated_at desc, bi.item_index asc
)
insert into public.chats (
  id,
  title,
  created_at,
  updated_at,
  last_source_label,
  last_source_url,
  total_runs,
  total_exported,
  total_failed,
  last_status,
  cover_batch_id,
  cover_item_id,
  cover_output_url,
  metadata
)
select
  batch_stats.chat_id,
  coalesce(batch_stats.last_source_label, 'Untitled chat'),
  batch_stats.created_at,
  batch_stats.updated_at,
  batch_stats.last_source_label,
  batch_stats.last_source_url,
  batch_stats.total_runs,
  batch_stats.total_exported,
  batch_stats.total_failed,
  batch_stats.last_status,
  chat_covers.cover_batch_id,
  chat_covers.cover_item_id,
  chat_covers.cover_output_url,
  '{}'::jsonb
from batch_stats
left join chat_covers
  on chat_covers.chat_id = batch_stats.chat_id
on conflict (id) do update
set
  title = excluded.title,
  updated_at = excluded.updated_at,
  last_source_label = excluded.last_source_label,
  last_source_url = excluded.last_source_url,
  total_runs = excluded.total_runs,
  total_exported = excluded.total_exported,
  total_failed = excluded.total_failed,
  last_status = excluded.last_status,
  cover_batch_id = excluded.cover_batch_id,
  cover_item_id = excluded.cover_item_id,
  cover_output_url = excluded.cover_output_url;
