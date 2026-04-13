alter table public.chats
  add column if not exists library_scope text;

alter table public.chats
  add column if not exists owner_user_id uuid;

update public.chats
set library_scope = 'general'
where library_scope is null
   or nullif(library_scope, '') is null;

alter table public.chats
  alter column library_scope set default 'general';

alter table public.chats
  alter column library_scope set not null;

do $$
begin
  if not exists (
    select 1
    from pg_constraint
    where conname = 'chats_library_scope_check'
  ) then
    alter table public.chats
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
    alter table public.chats
      add constraint chats_owner_scope_consistency_check
      check (
        (library_scope = 'general' and owner_user_id is null)
        or (library_scope = 'user' and owner_user_id is not null)
      );
  end if;
end $$;

create index if not exists chats_library_scope_updated_at_idx
  on public.chats (library_scope, updated_at desc);

create index if not exists chats_owner_user_id_updated_at_idx
  on public.chats (owner_user_id, updated_at desc)
  where owner_user_id is not null;
