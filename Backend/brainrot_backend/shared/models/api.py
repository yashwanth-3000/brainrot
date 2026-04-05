from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field

from brainrot_backend.shared.models.domain import (
    AgentConfigRecord,
    AssetRecord,
    BatchItemRecord,
    BatchRecord,
    ChatRecord,
    ScriptDraft,
    ShortEngagementRecord,
)
from brainrot_backend.shared.models.enums import BatchItemStatus, BatchStatus


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


class ShortEngagementRequest(BaseModel):
    batch_id: str | None = None
    item_id: str
    viewer_id: str
    session_id: str
    watch_time_seconds: float = 0.0
    completion_ratio: float = 0.0
    max_progress_seconds: float = 0.0
    replay_count: int = 0
    unmuted: bool = False
    info_opened: bool = False
    open_clicked: bool = False
    liked: bool = False
    skipped_early: bool = False
    metadata: dict[str, Any] = Field(default_factory=dict)


class ShortEngagementEnvelope(BaseModel):
    engagement: ShortEngagementRecord


class RecommendationInsight(BaseModel):
    key: str
    label: str
    score: float
    sample_size: int
    avg_completion_ratio: float
    avg_watch_time_seconds: float
    positive_action_rate: float


class ReelRetentionSummary(BaseModel):
    reel_number: int
    item_id: str
    title: str
    watch_time_seconds: float
    max_progress_seconds: float
    completion_ratio: float
    estimated_seconds: float | None = None
    replay_count: int = 0
    subtitle_style: str | None = None
    subtitle_font: str | None = None
    gameplay_label: str | None = None


class ChatRecommendationResponse(BaseModel):
    chat_id: str
    chat: ChatRecord | None = None
    session_id: str | None = None
    has_enough_data: bool
    min_reels_required: int = 3
    reels_tracked: int = 0
    total_sessions: int
    total_watch_time_seconds: float = 0.0
    unique_viewers: int
    high_retention_sessions: int
    recommendation_title: str | None = None
    recommendation_body: str | None = None
    generation_prompt: str | None = None
    top_gameplay: list[RecommendationInsight] = Field(default_factory=list)
    top_caption_styles: list[RecommendationInsight] = Field(default_factory=list)
    top_text_styles: list[RecommendationInsight] = Field(default_factory=list)
    retention_summary: list[ReelRetentionSummary] = Field(default_factory=list)
    winning_profile: dict[str, Any] = Field(default_factory=dict)


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
