from __future__ import annotations

import asyncio
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any

from supabase import Client, create_client

from brainrot_backend.shared.models.domain import (
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
    ShortEngagementRecord,
)
from brainrot_backend.shared.models.enums import AgentRole, AssetKind, BatchEventType
from brainrot_backend.shared.storage.base import BlobStore, Repository


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _dump(model: Any) -> dict[str, Any]:
    return model.model_dump(mode="json")


def _dump_value(value: Any) -> Any:
    if isinstance(value, (datetime, date)):
        return value.isoformat()
    if hasattr(value, "model_dump"):
        return value.model_dump(mode="json")
    if isinstance(value, list):
        return [_dump_value(item) for item in value]
    if isinstance(value, dict):
        return {key: _dump_value(item) for key, item in value.items()}
    return value


def _dump_changes(changes: dict[str, object]) -> dict[str, object]:
    return {key: _dump_value(value) for key, value in changes.items()}


class SupabaseRepository(Repository):
    def __init__(self, url: str, service_role_key: str) -> None:
        self.client: Client = create_client(url, service_role_key)
        self._lock = asyncio.Lock()

    async def _call(self, fn, *args, **kwargs):
        async with self._lock:
            return await asyncio.to_thread(fn, *args, **kwargs)

    async def create_batch(self, batch: BatchRecord) -> BatchRecord:
        response = await self._call(lambda: self.client.table("batches").insert(_dump(batch)).execute())
        return BatchRecord.model_validate(response.data[0])

    async def create_chat(self, chat: ChatRecord) -> ChatRecord:
        response = await self._call(lambda: self.client.table("chats").insert(_dump(chat)).execute())
        return ChatRecord.model_validate(response.data[0])

    async def get_chat(self, chat_id: str) -> ChatRecord | None:
        response = await self._call(
            lambda: self.client.table("chats").select("*").eq("id", chat_id).limit(1).execute()
        )
        if not response.data:
            return None
        return ChatRecord.model_validate(response.data[0])

    async def list_chats(self) -> list[ChatRecord]:
        response = await self._call(
            lambda: self.client.table("chats").select("*").order("updated_at", desc=True).execute()
        )
        return [ChatRecord.model_validate(row) for row in response.data]

    async def update_chat(self, chat_id: str, **changes: object) -> ChatRecord:
        changes.setdefault("updated_at", utc_now())
        response = await self._call(
            lambda: self.client.table("chats").update(_dump_changes(changes)).eq("id", chat_id).execute()
        )
        return ChatRecord.model_validate(response.data[0])

    async def upsert_short_engagement(
        self,
        engagement: ShortEngagementRecord,
    ) -> ShortEngagementRecord:
        response = await self._call(
            lambda: self.client.table("short_engagement_events")
            .upsert(_dump(engagement), on_conflict="session_id")
            .execute()
        )
        return ShortEngagementRecord.model_validate(response.data[0])

    async def list_short_engagements(self, chat_id: str) -> list[ShortEngagementRecord]:
        response = await self._call(
            lambda: self.client.table("short_engagement_events")
            .select("*")
            .eq("chat_id", chat_id)
            .order("updated_at", desc=True)
            .execute()
        )
        return [ShortEngagementRecord.model_validate(row) for row in response.data]

    async def get_batch(self, batch_id: str) -> BatchRecord | None:
        response = await self._call(
            lambda: self.client.table("batches").select("*").eq("id", batch_id).limit(1).execute()
        )
        if not response.data:
            return None
        return BatchRecord.model_validate(response.data[0])

    async def list_batches_for_chat(self, chat_id: str) -> list[BatchRecord]:
        response = await self._call(
            lambda: self.client.table("batches")
            .select("*")
            .eq("chat_id", chat_id)
            .order("updated_at", desc=True)
            .execute()
        )
        return [BatchRecord.model_validate(row) for row in response.data]

    async def update_batch(self, batch_id: str, **changes: object) -> BatchRecord:
        changes.setdefault("updated_at", utc_now())
        response = await self._call(
            lambda: self.client.table("batches").update(_dump_changes(changes)).eq("id", batch_id).execute()
        )
        return BatchRecord.model_validate(response.data[0])

    async def create_batch_items(self, items: list[BatchItemRecord]) -> list[BatchItemRecord]:
        response = await self._call(
            lambda: self.client.table("batch_items").insert([_dump(item) for item in items]).execute()
        )
        return [BatchItemRecord.model_validate(row) for row in response.data]

    async def get_batch_items(self, batch_id: str) -> list[BatchItemRecord]:
        response = await self._call(
            lambda: self.client.table("batch_items")
            .select("*")
            .eq("batch_id", batch_id)
            .order("item_index")
            .execute()
        )
        return [BatchItemRecord.model_validate(row) for row in response.data]

    async def get_batch_item(self, item_id: str) -> BatchItemRecord | None:
        response = await self._call(
            lambda: self.client.table("batch_items").select("*").eq("id", item_id).limit(1).execute()
        )
        if not response.data:
            return None
        return BatchItemRecord.model_validate(response.data[0])

    async def update_batch_item(self, item_id: str, **changes: object) -> BatchItemRecord:
        changes.setdefault("updated_at", utc_now())
        response = await self._call(
            lambda: self.client.table("batch_items").update(_dump_changes(changes)).eq("id", item_id).execute()
        )
        return BatchItemRecord.model_validate(response.data[0])

    async def append_event(
        self,
        batch_id: str,
        event_type: BatchEventType,
        payload: dict[str, object],
    ) -> BatchEventRecord:
        response = await self._call(
            lambda: self.client.table("batch_events")
            .insert({"batch_id": batch_id, "event_type": event_type.value, "payload": payload})
            .execute()
        )
        return BatchEventRecord.model_validate(response.data[0])

    async def list_batch_events(
        self,
        batch_id: str,
        *,
        after_sequence: int = 0,
    ) -> list[BatchEventRecord]:
        response = await self._call(
            lambda: self.client.table("batch_events")
            .select("*")
            .eq("batch_id", batch_id)
            .gt("sequence", after_sequence)
            .order("sequence")
            .execute()
        )
        return [BatchEventRecord.model_validate(row) for row in response.data]

    async def add_source_document(self, batch_id: str, source: IngestedSource) -> None:
        payload = source.model_dump(mode="json")
        payload["batch_id"] = batch_id
        payload["content_markdown"] = payload.pop("markdown")
        await self._call(lambda: self.client.table("source_documents").upsert(payload).execute())

    async def get_source_document(self, batch_id: str) -> IngestedSource | None:
        response = await self._call(
            lambda: self.client.table("source_documents").select("*").eq("batch_id", batch_id).limit(1).execute()
        )
        if not response.data:
            return None
        row = dict(response.data[0])
        row["markdown"] = row.pop("content_markdown", "")
        return IngestedSource.model_validate(row)

    async def create_asset(self, asset: AssetRecord) -> AssetRecord:
        response = await self._call(lambda: self.client.table("assets").insert(_dump(asset)).execute())
        return AssetRecord.model_validate(response.data[0])

    async def list_assets(self, kind: AssetKind | None = None) -> list[AssetRecord]:
        query = self.client.table("assets").select("*")
        if kind is not None:
            query = query.eq("kind", kind.value)
        response = await self._call(query.execute)
        return [AssetRecord.model_validate(row) for row in response.data]

    async def save_generated_bundle(self, batch_id: str, bundle: GeneratedBundle) -> None:
        batch = await self.get_batch(batch_id)
        if batch is None:
            raise KeyError(batch_id)
        metadata = dict(batch.metadata)
        metadata["generated_bundle"] = bundle.model_dump(mode="json")
        await self.update_batch(batch_id, metadata=metadata)

    async def get_generated_bundle(self, batch_id: str) -> GeneratedBundle | None:
        batch = await self.get_batch(batch_id)
        if batch is None:
            return None
        payload = batch.metadata.get("generated_bundle")
        if not payload:
            return None
        return GeneratedBundle.model_validate(payload)

    async def upsert_agent_config(self, config: AgentConfigRecord) -> AgentConfigRecord:
        if config.is_active:
            await self._call(
                lambda: self.client.table("agent_configs")
                .update({"is_active": False})
                .eq("role", config.role.value)
                .neq("id", config.id)
                .execute()
            )
        response = await self._call(
            lambda: self.client.table("agent_configs").upsert(_dump(config), on_conflict="id").execute()
        )
        return AgentConfigRecord.model_validate(response.data[0])

    async def get_agent_config(self, config_id: str) -> AgentConfigRecord | None:
        response = await self._call(
            lambda: self.client.table("agent_configs").select("*").eq("id", config_id).limit(1).execute()
        )
        if not response.data:
            return None
        return AgentConfigRecord.model_validate(response.data[0])

    async def get_agent_config_by_role(self, role: AgentRole) -> AgentConfigRecord | None:
        response = await self._call(
            lambda: self.client.table("agent_configs")
            .select("*")
            .eq("role", role.value)
            .eq("is_active", True)
            .limit(1)
            .execute()
        )
        if not response.data:
            return None
        return AgentConfigRecord.model_validate(response.data[0])

    async def list_agent_configs(self, role: AgentRole | None = None) -> list[AgentConfigRecord]:
        query = self.client.table("agent_configs").select("*")
        if role is not None:
            query = query.eq("role", role.value)
        response = await self._call(query.execute)
        return [AgentConfigRecord.model_validate(row) for row in response.data]

    async def create_agent_run(self, run: AgentRunRecord) -> AgentRunRecord:
        response = await self._call(lambda: self.client.table("agent_runs").insert(_dump(run)).execute())
        return AgentRunRecord.model_validate(response.data[0])

    async def update_agent_run(self, run_id: str, **changes: object) -> AgentRunRecord:
        response = await self._call(
            lambda: self.client.table("agent_runs").update(_dump_changes(changes)).eq("id", run_id).execute()
        )
        return AgentRunRecord.model_validate(response.data[0])

    async def get_agent_run(self, run_id: str) -> AgentRunRecord | None:
        response = await self._call(
            lambda: self.client.table("agent_runs").select("*").eq("id", run_id).limit(1).execute()
        )
        if not response.data:
            return None
        return AgentRunRecord.model_validate(response.data[0])

    async def upsert_agent_conversation(
        self,
        conversation: AgentConversationRecord,
    ) -> AgentConversationRecord:
        response = await self._call(
            lambda: self.client.table("agent_conversations")
            .upsert(_dump(conversation), on_conflict="conversation_id")
            .execute()
        )
        return AgentConversationRecord.model_validate(response.data[0])

    async def get_agent_conversation(self, conversation_id: str) -> AgentConversationRecord | None:
        response = await self._call(
            lambda: self.client.table("agent_conversations")
            .select("*")
            .eq("conversation_id", conversation_id)
            .limit(1)
            .execute()
        )
        if not response.data:
            return None
        return AgentConversationRecord.model_validate(response.data[0])

    async def create_alignment_job(self, job: AlignmentJobRecord) -> AlignmentJobRecord:
        response = await self._call(lambda: self.client.table("alignment_jobs").insert(_dump(job)).execute())
        return AlignmentJobRecord.model_validate(response.data[0])

    async def update_alignment_job(self, job_id: str, **changes: object) -> AlignmentJobRecord:
        response = await self._call(
            lambda: self.client.table("alignment_jobs").update(_dump_changes(changes)).eq("id", job_id).execute()
        )
        return AlignmentJobRecord.model_validate(response.data[0])

    async def get_alignment_job(self, batch_item_id: str) -> AlignmentJobRecord | None:
        response = await self._call(
            lambda: self.client.table("alignment_jobs")
            .select("*")
            .eq("batch_item_id", batch_item_id)
            .limit(1)
            .execute()
        )
        if not response.data:
            return None
        return AlignmentJobRecord.model_validate(response.data[0])


class SupabaseBlobStore(BlobStore):
    def __init__(self, url: str, service_role_key: str, public_url: str | None = None) -> None:
        self.client: Client = create_client(url, service_role_key)
        self.public_url = public_url
        self._lock = asyncio.Lock()

    async def _call(self, fn, *args, **kwargs):
        async with self._lock:
            return await asyncio.to_thread(fn, *args, **kwargs)

    async def upload_bytes(
        self,
        bucket: str,
        path: str,
        payload: bytes,
        *,
        content_type: str | None = None,
    ) -> str | None:
        await self._call(
            lambda: self.client.storage.from_(bucket).upload(
                path,
                payload,
                file_options={
                    "content-type": content_type or "application/octet-stream",
                    "cache-control": "31536000",
                    "upsert": "true",
                },
            )
        )
        return self.client.storage.from_(bucket).get_public_url(path)

    async def materialize(self, bucket: str, path: str, destination: Path) -> Path:
        data = await self._call(lambda: self.client.storage.from_(bucket).download(path))
        destination.parent.mkdir(parents=True, exist_ok=True)
        await asyncio.to_thread(destination.write_bytes, data)
        return destination
