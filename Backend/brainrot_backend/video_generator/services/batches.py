from __future__ import annotations

import asyncio
from datetime import datetime, timezone
from uuid import uuid4

from brainrot_backend.config import Settings
from brainrot_backend.shared.models.api import BatchEnvelope
from brainrot_backend.shared.models.domain import BatchItemRecord, BatchRecord, ScriptDraft
from brainrot_backend.shared.models.enums import AgentRole, BatchEventType, BatchItemStatus, BatchStatus, SourceKind
from brainrot_backend.video_generator.services.assets import sanitize_filename
from brainrot_backend.recommendation_system.service import ChatService
from brainrot_backend.video_generator.services.events import EventBroker
from brainrot_backend.shared.storage.base import BlobStore, Repository
from brainrot_backend.video_generator.workers.orchestrator import BatchOrchestrator


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class BatchService:
    def __init__(
        self,
        *,
        settings: Settings,
        repository: Repository,
        blob_store: BlobStore,
        events: EventBroker,
        orchestrator: BatchOrchestrator,
        chat_service: ChatService,
    ) -> None:
        self.settings = settings
        self.repository = repository
        self.blob_store = blob_store
        self.events = events
        self.orchestrator = orchestrator
        self.chat_service = chat_service
        self._tasks: dict[str, asyncio.Task[None]] = {}

    async def create_batch(
        self,
        *,
        source_kind: SourceKind,
        source_url: str | None,
        count: int,
        chat_id: str | None,
        title_hint: str | None,
        producer_agent_config_id: str | None,
        narrator_agent_config_id: str | None,
        premium_audio: bool,
        uploaded_filename: str | None = None,
        uploaded_bytes: bytes | None = None,
        uploaded_content_type: str | None = None,
    ) -> BatchEnvelope:
        producer_config = await self._resolve_producer_config_id(producer_agent_config_id)
        narrator_config = await self._resolve_narrator_config_id(narrator_agent_config_id)

        metadata: dict[str, object] = {}
        if uploaded_bytes is not None and uploaded_filename is not None:
            safe_name = sanitize_filename(uploaded_filename)
            unique_name = f"{uuid4()}-{safe_name}"
            upload_path = f"uploads/{unique_name}"
            local_upload_path = self.settings.temp_dir / "uploads" / unique_name
            local_upload_path.parent.mkdir(parents=True, exist_ok=True)
            local_upload_path.write_bytes(uploaded_bytes)
            await self.blob_store.upload_bytes(
                self.settings.source_bucket,
                upload_path,
                uploaded_bytes,
                content_type=uploaded_content_type or "application/pdf",
            )
            metadata["uploaded_file_path"] = str(local_upload_path.relative_to(self.settings.project_root))
            metadata["uploaded_bucket"] = self.settings.source_bucket
            metadata["uploaded_blob_path"] = upload_path

        if chat_id:
            await self.chat_service.ensure_chat(
                chat_id,
                title=title_hint,
                source_label=title_hint,
                source_url=source_url,
                last_status=BatchStatus.QUEUED.value,
            )

        batch = BatchRecord(
            chat_id=chat_id,
            source_kind=source_kind,
            source_url=source_url,
            title_hint=title_hint,
            requested_count=count,
            producer_agent_config_id=producer_config,
            narrator_agent_config_id=narrator_config,
            premium_audio=premium_audio,
            metadata=metadata,
        )
        batch = await self.repository.create_batch(batch)
        items = [
            BatchItemRecord(
                batch_id=batch.id,
                item_index=index,
                status=BatchItemStatus.QUEUED,
            )
            for index in range(count)
        ]
        items = await self.repository.create_batch_items(items)
        if chat_id:
            await self.chat_service.refresh_chat_summary(chat_id)
        await self.events.publish(
            batch.id,
            BatchEventType.STATUS,
            {
                "status": batch.status.value,
                "count": count,
                "producer_agent_config_id": producer_config,
                "narrator_agent_config_id": narrator_config,
            },
        )
        self._schedule(batch.id, retry_failed_only=False)
        return BatchEnvelope(batch=batch, items=items)

    async def get_batch(self, batch_id: str) -> BatchEnvelope:
        batch = await self.repository.get_batch(batch_id)
        if batch is None:
            raise KeyError(batch_id)
        items = await self.repository.get_batch_items(batch_id)
        return BatchEnvelope(batch=batch, items=items)

    async def retry_failed_items(self, batch_id: str) -> list[str]:
        items = await self.repository.get_batch_items(batch_id)
        failed = [item.id for item in items if item.status == BatchItemStatus.FAILED]
        if failed:
            self._schedule(batch_id, retry_failed_only=True)
        return failed

    async def create_video_edit_preview(
        self,
        *,
        title: str,
        narration_text: str,
        gameplay_asset_id: str,
        subtitle_preset_id: str,
        premium_audio: bool,
        music_asset_id: str | None = None,
        narrator_agent_config_id: str | None = None,
    ) -> BatchEnvelope:
        narrator_config = await self._resolve_narrator_config_id(narrator_agent_config_id)

        batch = BatchRecord(
            source_kind=SourceKind.ARTICLE,
            source_url="preview://video-edit",
            title_hint=title,
            requested_count=1,
            narrator_agent_config_id=narrator_config,
            status=BatchStatus.QUEUED,
            premium_audio=premium_audio,
            metadata={
                "preview_mode": True,
                "gameplay_asset_id": gameplay_asset_id,
                "music_asset_id": music_asset_id,
                "subtitle_preset_id": subtitle_preset_id,
            },
        )
        batch = await self.repository.create_batch(batch)

        word_count = len([word for word in narration_text.split() if word.strip()])
        estimated_seconds = max(8.0, min(30.0, round(word_count / 3.3, 1)))
        source_facts = [
            title.strip(),
            " ".join(narration_text.split())[:160].strip(),
        ]
        item = BatchItemRecord(
            batch_id=batch.id,
            item_index=0,
            status=BatchItemStatus.QUEUED,
            script=ScriptDraft(
                title=title.strip(),
                hook=title.strip(),
                narration_text=" ".join(narration_text.split()).strip(),
                caption_text=title.strip(),
                estimated_seconds=estimated_seconds,
                visual_beats=["Preview subtitle timing and placement."],
                music_tags=[],
                gameplay_tags=[],
                source_facts_used=[fact for fact in source_facts if fact],
                qa_notes=["Preview render"],
            ),
        )
        [item] = await self.repository.create_batch_items([item])
        await self.events.publish(
            batch.id,
            BatchEventType.STATUS,
            {
                "status": batch.status.value,
                "count": 1,
                "narrator_agent_config_id": narrator_config,
                "preview_mode": True,
            },
        )
        self._schedule_preview(
            batch.id,
            item.id,
            gameplay_asset_id=gameplay_asset_id,
            subtitle_preset_id=subtitle_preset_id,
            music_asset_id=music_asset_id,
        )
        return BatchEnvelope(batch=batch, items=[item])

    async def _resolve_agent_config_id(self, role: AgentRole, requested_id: str | None) -> str:
        if requested_id:
            config = await self.repository.get_agent_config(requested_id)
            if config is None:
                raise RuntimeError(f"Agent config {requested_id} was not found.")
            if config.role != role:
                raise RuntimeError(f"Agent config {requested_id} is not a {role.value} config.")
            return config.id

        config = await self.repository.get_agent_config_by_role(role)
        if config is None:
            raise RuntimeError(f"No active {role.value} agent config exists. Bootstrap ElevenLabs agents first.")
        return config.id

    async def _resolve_producer_config_id(self, requested_id: str | None) -> str | None:
        if self.settings.producer_mode == "direct_openai":
            return None
        return await self._resolve_agent_config_id(AgentRole.PRODUCER, requested_id)

    async def _resolve_narrator_config_id(self, requested_id: str | None) -> str | None:
        if self.settings.narration_mode == "elevenlabs_tts":
            return None
        return await self._resolve_agent_config_id(AgentRole.NARRATOR, requested_id)

    def _schedule(self, batch_id: str, *, retry_failed_only: bool) -> None:
        if batch_id in self._tasks and not self._tasks[batch_id].done():
            return
        task = asyncio.create_task(self.orchestrator.run_batch(batch_id, retry_failed_only=retry_failed_only))
        self._tasks[batch_id] = task

        def _cleanup(done_task: asyncio.Task[None]) -> None:
            self._tasks.pop(batch_id, None)
            try:
                done_task.result()
            except Exception:
                pass

        task.add_done_callback(_cleanup)

    def _schedule_preview(
        self,
        batch_id: str,
        item_id: str,
        *,
        gameplay_asset_id: str,
        subtitle_preset_id: str,
        music_asset_id: str | None,
    ) -> None:
        if batch_id in self._tasks and not self._tasks[batch_id].done():
            return
        task = asyncio.create_task(
            self.orchestrator.run_preview(
                batch_id,
                item_id=item_id,
                gameplay_asset_id=gameplay_asset_id,
                subtitle_preset_id=subtitle_preset_id,
                music_asset_id=music_asset_id,
            )
        )
        self._tasks[batch_id] = task

        def _cleanup(done_task: asyncio.Task[None]) -> None:
            self._tasks.pop(batch_id, None)
            try:
                done_task.result()
            except Exception:
                pass

        task.add_done_callback(_cleanup)
