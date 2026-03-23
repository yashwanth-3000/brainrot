from __future__ import annotations

import asyncio
from datetime import datetime, timezone
from pathlib import Path

from brainrot_backend.models.domain import (
    AgentConfigRecord,
    AgentConversationRecord,
    AgentRunRecord,
    AlignmentJobRecord,
    AssetRecord,
    BatchEventRecord,
    BatchItemRecord,
    BatchRecord,
    ChatRecord,
    GeneratedBundle,
    IngestedSource,
    ScriptDraft,
)
from brainrot_backend.models.enums import AgentRole, AssetKind, BatchEventType
from brainrot_backend.storage.base import BlobStore, Repository


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class InMemoryRepository(Repository):
    def __init__(self) -> None:
        self._chats: dict[str, ChatRecord] = {}
        self._batches: dict[str, BatchRecord] = {}
        self._items: dict[str, BatchItemRecord] = {}
        self._items_by_batch: dict[str, list[str]] = {}
        self._events: dict[str, list[BatchEventRecord]] = {}
        self._sources: dict[str, IngestedSource] = {}
        self._assets: dict[str, AssetRecord] = {}
        self._generated_bundles: dict[str, GeneratedBundle] = {}
        self._agent_configs: dict[str, AgentConfigRecord] = {}
        self._agent_runs: dict[str, AgentRunRecord] = {}
        self._agent_conversations: dict[str, AgentConversationRecord] = {}
        self._alignment_jobs: dict[str, AlignmentJobRecord] = {}
        self._event_sequences: dict[str, int] = {}
        self._lock = asyncio.Lock()

    async def create_chat(self, chat: ChatRecord) -> ChatRecord:
        async with self._lock:
            self._chats[chat.id] = chat
            return chat

    async def get_chat(self, chat_id: str) -> ChatRecord | None:
        return self._chats.get(chat_id)

    async def list_chats(self) -> list[ChatRecord]:
        chats = list(self._chats.values())
        return sorted(chats, key=lambda chat: chat.updated_at, reverse=True)

    async def update_chat(self, chat_id: str, **changes: object) -> ChatRecord:
        async with self._lock:
            changes.setdefault("updated_at", utc_now())
            chat = self._chats[chat_id].model_copy(update=changes)
            self._chats[chat_id] = chat
            return chat

    async def create_batch(self, batch: BatchRecord) -> BatchRecord:
        async with self._lock:
            self._batches[batch.id] = batch
            self._items_by_batch.setdefault(batch.id, [])
            return batch

    async def get_batch(self, batch_id: str) -> BatchRecord | None:
        return self._batches.get(batch_id)

    async def list_batches_for_chat(self, chat_id: str) -> list[BatchRecord]:
        batches = [
            batch
            for batch in self._batches.values()
            if (batch.chat_id or str(batch.metadata.get("chat_id") or "")) == chat_id
        ]
        return sorted(batches, key=lambda batch: batch.updated_at, reverse=True)

    async def update_batch(self, batch_id: str, **changes: object) -> BatchRecord:
        async with self._lock:
            changes.setdefault("updated_at", utc_now())
            batch = self._batches[batch_id].model_copy(update=changes)
            self._batches[batch_id] = batch
            return batch

    async def create_batch_items(self, items: list[BatchItemRecord]) -> list[BatchItemRecord]:
        async with self._lock:
            for item in items:
                self._items[item.id] = item
                self._items_by_batch.setdefault(item.batch_id, []).append(item.id)
            return items

    async def get_batch_items(self, batch_id: str) -> list[BatchItemRecord]:
        return [self._items[item_id] for item_id in self._items_by_batch.get(batch_id, [])]

    async def get_batch_item(self, item_id: str) -> BatchItemRecord | None:
        return self._items.get(item_id)

    async def update_batch_item(self, item_id: str, **changes: object) -> BatchItemRecord:
        async with self._lock:
            changes.setdefault("updated_at", utc_now())
            if isinstance(changes.get("script"), dict):
                changes["script"] = ScriptDraft.model_validate(changes["script"])
            item = self._items[item_id].model_copy(update=changes)
            self._items[item_id] = item
            return item

    async def append_event(
        self,
        batch_id: str,
        event_type: BatchEventType,
        payload: dict[str, object],
    ) -> BatchEventRecord:
        async with self._lock:
            sequence = self._event_sequences.get(batch_id, 0) + 1
            self._event_sequences[batch_id] = sequence
            event = BatchEventRecord(
                sequence=sequence,
                batch_id=batch_id,
                event_type=event_type,
                payload=payload,
            )
            self._events.setdefault(batch_id, []).append(event)
            return event

    async def list_batch_events(
        self,
        batch_id: str,
        *,
        after_sequence: int = 0,
    ) -> list[BatchEventRecord]:
        return [event for event in self._events.get(batch_id, []) if event.sequence > after_sequence]

    async def add_source_document(self, batch_id: str, source: IngestedSource) -> None:
        self._sources[batch_id] = source

    async def get_source_document(self, batch_id: str) -> IngestedSource | None:
        return self._sources.get(batch_id)

    async def create_asset(self, asset: AssetRecord) -> AssetRecord:
        self._assets[asset.id] = asset
        return asset

    async def list_assets(self, kind: AssetKind | None = None) -> list[AssetRecord]:
        assets = list(self._assets.values())
        if kind is None:
            return assets
        return [asset for asset in assets if asset.kind == kind]

    async def save_generated_bundle(self, batch_id: str, bundle: GeneratedBundle) -> None:
        self._generated_bundles[batch_id] = bundle

    async def get_generated_bundle(self, batch_id: str) -> GeneratedBundle | None:
        return self._generated_bundles.get(batch_id)

    async def upsert_agent_config(self, config: AgentConfigRecord) -> AgentConfigRecord:
        async with self._lock:
            if config.is_active:
                for existing_id, existing in list(self._agent_configs.items()):
                    if existing.role == config.role and existing.id != config.id and existing.is_active:
                        self._agent_configs[existing_id] = existing.model_copy(update={"is_active": False})
            self._agent_configs[config.id] = config
            return config

    async def get_agent_config(self, config_id: str) -> AgentConfigRecord | None:
        return self._agent_configs.get(config_id)

    async def get_agent_config_by_role(self, role: AgentRole) -> AgentConfigRecord | None:
        for config in self._agent_configs.values():
            if config.role == role and config.is_active:
                return config
        return None

    async def list_agent_configs(self, role: AgentRole | None = None) -> list[AgentConfigRecord]:
        configs = list(self._agent_configs.values())
        if role is None:
            return configs
        return [config for config in configs if config.role == role]

    async def create_agent_run(self, run: AgentRunRecord) -> AgentRunRecord:
        self._agent_runs[run.id] = run
        return run

    async def update_agent_run(self, run_id: str, **changes: object) -> AgentRunRecord:
        run = self._agent_runs[run_id].model_copy(update=changes)
        self._agent_runs[run_id] = run
        return run

    async def get_agent_run(self, run_id: str) -> AgentRunRecord | None:
        return self._agent_runs.get(run_id)

    async def upsert_agent_conversation(
        self,
        conversation: AgentConversationRecord,
    ) -> AgentConversationRecord:
        self._agent_conversations[conversation.conversation_id] = conversation
        return conversation

    async def get_agent_conversation(self, conversation_id: str) -> AgentConversationRecord | None:
        return self._agent_conversations.get(conversation_id)

    async def create_alignment_job(self, job: AlignmentJobRecord) -> AlignmentJobRecord:
        self._alignment_jobs[job.id] = job
        return job

    async def update_alignment_job(self, job_id: str, **changes: object) -> AlignmentJobRecord:
        job = self._alignment_jobs[job_id].model_copy(update=changes)
        self._alignment_jobs[job_id] = job
        return job

    async def get_alignment_job(self, batch_item_id: str) -> AlignmentJobRecord | None:
        for job in self._alignment_jobs.values():
            if job.batch_item_id == batch_item_id:
                return job
        return None


class LocalBlobStore(BlobStore):
    def __init__(self, root: Path) -> None:
        self.root = root
        self.root.mkdir(parents=True, exist_ok=True)

    async def upload_bytes(
        self,
        bucket: str,
        path: str,
        payload: bytes,
        *,
        content_type: str | None = None,
    ) -> str | None:
        del content_type
        file_path = self.root / bucket / path
        file_path.parent.mkdir(parents=True, exist_ok=True)
        await asyncio.to_thread(file_path.write_bytes, payload)
        return file_path.as_uri()

    async def materialize(self, bucket: str, path: str, destination: Path) -> Path:
        source = self.root / bucket / path
        destination.parent.mkdir(parents=True, exist_ok=True)
        await asyncio.to_thread(destination.write_bytes, source.read_bytes())
        return destination
