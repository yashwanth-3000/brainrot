from __future__ import annotations

from pathlib import Path
from typing import Protocol

from brainrot_backend.core.models.domain import (
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
from brainrot_backend.core.models.enums import AgentRole, AssetKind, BatchEventType, ChatLibraryScope


class Repository(Protocol):
    async def create_chat(self, chat: ChatRecord) -> ChatRecord: ...

    async def get_chat(self, chat_id: str) -> ChatRecord | None: ...

    async def list_chats(
        self,
        *,
        library_scope: ChatLibraryScope | None = None,
        owner_user_id: str | None = None,
    ) -> list[ChatRecord]: ...

    async def update_chat(self, chat_id: str, **changes: object) -> ChatRecord: ...

    async def upsert_short_engagement(
        self,
        engagement: ShortEngagementRecord,
    ) -> ShortEngagementRecord: ...

    async def list_short_engagements(self, chat_id: str) -> list[ShortEngagementRecord]: ...

    async def create_batch(self, batch: BatchRecord) -> BatchRecord: ...

    async def get_batch(self, batch_id: str) -> BatchRecord | None: ...

    async def list_batches_for_chat(self, chat_id: str) -> list[BatchRecord]: ...

    async def update_batch(self, batch_id: str, **changes: object) -> BatchRecord: ...

    async def create_batch_items(self, items: list[BatchItemRecord]) -> list[BatchItemRecord]: ...

    async def get_batch_items(self, batch_id: str) -> list[BatchItemRecord]: ...

    async def get_batch_item(self, item_id: str) -> BatchItemRecord | None: ...

    async def update_batch_item(self, item_id: str, **changes: object) -> BatchItemRecord: ...

    async def append_event(
        self,
        batch_id: str,
        event_type: BatchEventType,
        payload: dict[str, object],
    ) -> BatchEventRecord: ...

    async def list_batch_events(
        self,
        batch_id: str,
        *,
        after_sequence: int = 0,
    ) -> list[BatchEventRecord]: ...

    async def add_source_document(self, batch_id: str, source: IngestedSource) -> None: ...

    async def get_source_document(self, batch_id: str) -> IngestedSource | None: ...

    async def create_asset(self, asset: AssetRecord) -> AssetRecord: ...

    async def list_assets(self, kind: AssetKind | None = None) -> list[AssetRecord]: ...

    async def save_generated_bundle(self, batch_id: str, bundle: GeneratedBundle) -> None: ...

    async def get_generated_bundle(self, batch_id: str) -> GeneratedBundle | None: ...

    async def upsert_agent_config(self, config: AgentConfigRecord) -> AgentConfigRecord: ...

    async def get_agent_config(self, config_id: str) -> AgentConfigRecord | None: ...

    async def get_agent_config_by_role(self, role: AgentRole) -> AgentConfigRecord | None: ...

    async def list_agent_configs(self, role: AgentRole | None = None) -> list[AgentConfigRecord]: ...

    async def create_agent_run(self, run: AgentRunRecord) -> AgentRunRecord: ...

    async def update_agent_run(self, run_id: str, **changes: object) -> AgentRunRecord: ...

    async def get_agent_run(self, run_id: str) -> AgentRunRecord | None: ...

    async def upsert_agent_conversation(
        self,
        conversation: AgentConversationRecord,
    ) -> AgentConversationRecord: ...

    async def get_agent_conversation(
        self,
        conversation_id: str,
    ) -> AgentConversationRecord | None: ...

    async def create_alignment_job(self, job: AlignmentJobRecord) -> AlignmentJobRecord: ...

    async def update_alignment_job(self, job_id: str, **changes: object) -> AlignmentJobRecord: ...

    async def get_alignment_job(self, batch_item_id: str) -> AlignmentJobRecord | None: ...


class BlobStore(Protocol):
    async def upload_bytes(
        self,
        bucket: str,
        path: str,
        payload: bytes,
        *,
        content_type: str | None = None,
    ) -> str | None: ...

    async def materialize(self, bucket: str, path: str, destination: Path) -> Path: ...
