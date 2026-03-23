from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field

from brainrot_backend.models.domain import AgentConfigRecord, AssetRecord, BatchItemRecord, BatchRecord, ChatRecord, ScriptDraft
from brainrot_backend.models.enums import BatchItemStatus, BatchStatus


class HealthResponse(BaseModel):
    status: str


class AssetUploadResponse(BaseModel):
    asset: AssetRecord


class AgentBootstrapResponse(BaseModel):
    agents: list[AgentConfigRecord]
    tool_ids: list[str]


class BatchEnvelope(BaseModel):
    batch: BatchRecord
    items: list[BatchItemRecord]


class BatchRetryResponse(BaseModel):
    batch: BatchRecord
    retried_item_ids: list[str]


class ChatCreateRequest(BaseModel):
    title: str | None = None
    source_label: str | None = None
    source_url: str | None = None


class ChatEnvelope(BaseModel):
    chat: ChatRecord


class ChatListResponse(BaseModel):
    items: list[ChatRecord]


class ChatGeneratedAsset(BaseModel):
    chat_id: str
    batch_id: str
    batch_status: BatchStatus
    batch_created_at: datetime
    batch_updated_at: datetime
    source_url: str | None = None
    title_hint: str | None = None
    item_id: str
    item_index: int
    item_status: BatchItemStatus
    output_url: str | None = None
    render_metadata: dict[str, Any] = Field(default_factory=dict)
    script: ScriptDraft | None = None
    created_at: datetime
    updated_at: datetime


class ChatGeneratedAssetsResponse(BaseModel):
    chat_id: str
    chat: ChatRecord | None = None
    items: list[ChatGeneratedAsset]


class WebhookAckResponse(BaseModel):
    status: str
    event_type: str


class SubtitlePresetOption(BaseModel):
    id: str
    label: str
    animation: str
    font_name: str
    preferred_tags: list[str]


class VideoEditOptionsResponse(BaseModel):
    gameplay_assets: list[AssetRecord]
    subtitle_presets: list[SubtitlePresetOption]


class VideoEditPreviewRequest(BaseModel):
    title: str
    narration_text: str
    gameplay_asset_id: str
    subtitle_preset_id: str
    premium_audio: bool = False
    music_asset_id: str | None = None


class VideoEditPreviewResponse(BaseModel):
    batch: BatchRecord
    item: BatchItemRecord
