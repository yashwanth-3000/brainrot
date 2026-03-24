from __future__ import annotations

from datetime import datetime, timezone
from urllib.parse import urlparse

from brainrot_backend.models.api import ChatEnvelope, ChatGeneratedAsset, ChatGeneratedAssetsResponse, ChatListResponse
from brainrot_backend.models.domain import BatchRecord, ChatRecord, ScriptDraft
from brainrot_backend.models.enums import BatchItemStatus
from brainrot_backend.storage.base import Repository


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class ChatService:
    def __init__(self, *, repository: Repository) -> None:
        self.repository = repository

    async def create_chat(
        self,
        *,
        title: str | None = None,
        source_label: str | None = None,
        source_url: str | None = None,
    ) -> ChatEnvelope:
        resolved_title = self._resolve_chat_title(
            title=title,
            source_label=source_label,
            source_url=source_url,
            fallback="Untitled chat",
        )
        chat = ChatRecord(
            title=resolved_title,
            last_source_label=source_label,
            last_source_url=source_url,
        )
        chat = await self.repository.create_chat(chat)
        return ChatEnvelope(chat=chat)

    async def ensure_chat(
        self,
        chat_id: str,
        *,
        title: str | None = None,
        source_label: str | None = None,
        source_url: str | None = None,
        last_status: str | None = None,
    ) -> ChatRecord:
        existing = await self.repository.get_chat(chat_id)
        resolved_title = self._resolve_chat_title(
            title=title,
            source_label=source_label,
            source_url=source_url,
            fallback=existing.title if existing else "Untitled chat",
        )
        now = utc_now()
        if existing is None:
            return await self.repository.create_chat(
                ChatRecord(
                    id=chat_id,
                    title=resolved_title,
                    updated_at=now,
                    last_source_label=source_label,
                    last_source_url=source_url,
                    last_status=last_status,
                )
            )

        changes: dict[str, object] = {"updated_at": now}
        if resolved_title and resolved_title != existing.title:
            changes["title"] = resolved_title
        if source_label is not None:
            changes["last_source_label"] = source_label
        if source_url is not None:
            changes["last_source_url"] = source_url
        if last_status is not None:
            changes["last_status"] = last_status
        return await self.repository.update_chat(chat_id, **changes)

    async def list_chats(self) -> ChatListResponse:
        chats = await self.repository.list_chats()
        public_chats = [chat for chat in chats if chat.total_exported > 0]
        return ChatListResponse(items=public_chats)

    async def get_chat(self, chat_id: str) -> ChatEnvelope:
        chat = await self.repository.get_chat(chat_id)
        if chat is None:
            raise KeyError(chat_id)
        return ChatEnvelope(chat=chat)

    async def list_chat_generated_assets(self, chat_id: str) -> ChatGeneratedAssetsResponse:
        chat = await self.repository.get_chat(chat_id)
        batches = await self.repository.list_batches_for_chat(chat_id)
        assets: list[ChatGeneratedAsset] = []

        for batch in batches:
            items = await self.repository.get_batch_items(batch.id)
            for item in items:
                if item.status != BatchItemStatus.UPLOADED or not item.output_url:
                    continue
                assets.append(
                    ChatGeneratedAsset(
                        chat_id=chat_id,
                        batch_id=batch.id,
                        batch_status=batch.status,
                        batch_created_at=batch.created_at,
                        batch_updated_at=batch.updated_at,
                        source_url=batch.source_url,
                        title_hint=batch.title_hint,
                        item_id=item.id,
                        item_index=item.item_index,
                        item_status=item.status,
                        output_url=item.output_url,
                        render_metadata=item.render_metadata,
                        script=(
                            item.script
                            if isinstance(item.script, ScriptDraft)
                            else ScriptDraft.model_validate(item.script)
                            if item.script is not None
                            else None
                        ),
                        created_at=item.created_at,
                        updated_at=item.updated_at,
                    )
                )

        assets.sort(key=lambda asset: (asset.batch_updated_at, asset.updated_at, -asset.item_index), reverse=True)
        return ChatGeneratedAssetsResponse(chat_id=chat_id, chat=chat, items=assets)

    async def refresh_chat_summary(self, chat_id: str) -> ChatRecord:
        chat = await self.repository.get_chat(chat_id)
        batches = await self.repository.list_batches_for_chat(chat_id)
        if not batches:
            if chat is None:
                chat = await self.repository.create_chat(ChatRecord(id=chat_id))
            return chat

        latest_batch = batches[0]
        latest_source = await self.repository.get_source_document(latest_batch.id)
        fallback_source_label = chat.last_source_label if chat is not None else None
        last_source_label = (
            latest_source.title
            if latest_source is not None and latest_source.title
            else latest_batch.title_hint or fallback_source_label or self._source_label_from_batch(latest_batch)
        )
        last_source_url = latest_batch.source_url or (chat.last_source_url if chat else None)
        title = self._resolve_chat_title(
            title=latest_batch.title_hint,
            source_label=last_source_label,
            source_url=last_source_url,
            fallback=chat.title if chat else "Untitled chat",
        )

        total_exported = 0
        total_failed = 0
        cover_batch_id: str | None = None
        cover_item_id: str | None = None
        cover_output_url: str | None = None
        cover_thumbnail_url: str | None = None

        for batch in batches:
            items = await self.repository.get_batch_items(batch.id)
            uploaded = [item for item in items if item.status == BatchItemStatus.UPLOADED and item.output_url]
            failed = [item for item in items if item.status == BatchItemStatus.FAILED]
            total_exported += len(uploaded)
            total_failed += len(failed)
            if cover_item_id is None and uploaded:
                cover_item = sorted(
                    uploaded,
                    key=lambda item: (item.updated_at, -item.item_index),
                    reverse=True,
                )[0]
                cover_batch_id = batch.id
                cover_item_id = cover_item.id
                cover_output_url = cover_item.output_url
                cover_thumbnail_url = str(cover_item.render_metadata.get("thumbnail_url") or "") or None

        metadata = dict(chat.metadata) if chat is not None else {}
        if cover_thumbnail_url:
            metadata["cover_thumbnail_url"] = cover_thumbnail_url
        else:
            metadata.pop("cover_thumbnail_url", None)

        changes = {
            "title": title,
            "updated_at": latest_batch.updated_at,
            "last_source_label": last_source_label,
            "last_source_url": last_source_url,
            "total_runs": len(batches),
            "total_exported": total_exported,
            "total_failed": total_failed,
            "last_status": latest_batch.status.value if hasattr(latest_batch.status, "value") else str(latest_batch.status),
            "cover_batch_id": cover_batch_id,
            "cover_item_id": cover_item_id,
            "cover_output_url": cover_output_url,
            "metadata": metadata,
        }

        if chat is None:
            created_at = min(batch.created_at for batch in batches)
            chat = await self.repository.create_chat(
                ChatRecord(
                    id=chat_id,
                    created_at=created_at,
                    **changes,
                )
            )
            return chat

        return await self.repository.update_chat(chat_id, **changes)

    async def sync_existing_chats(self) -> None:
        chats = await self.repository.list_chats()
        for chat in chats:
            await self.refresh_chat_summary(chat.id)

    def _source_label_from_batch(self, batch: BatchRecord) -> str | None:
        if batch.source_url:
            parsed = urlparse(batch.source_url)
            if parsed.netloc:
                return parsed.netloc
            return batch.source_url
        return batch.title_hint

    def _resolve_chat_title(
        self,
        *,
        title: str | None,
        source_label: str | None,
        source_url: str | None,
        fallback: str,
    ) -> str:
        for candidate in (title, source_label):
            if candidate and candidate.strip():
                return candidate.strip()
        if source_url:
            parsed = urlparse(source_url)
            if parsed.netloc:
                return parsed.netloc
            if source_url.strip():
                return source_url.strip()
        return fallback
