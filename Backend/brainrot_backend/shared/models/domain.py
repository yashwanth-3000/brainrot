from __future__ import annotations

from datetime import datetime, timezone
from typing import Any
from uuid import uuid4

from pydantic import BaseModel, Field

from brainrot_backend.shared.models.enums import (
    AgentRole,
    AssetKind,
    BatchEventType,
    BatchItemStatus,
    BatchStatus,
    SourceKind,
)


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class WordTiming(BaseModel):
    text: str
    start: float
    end: float


class SourceBrief(BaseModel):
    canonical_title: str
    summary: str
    facts: list[str]
    entities: list[str]
    tone: str
    do_not_drift: list[str]
    source_urls: list[str] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)


class AnglePlan(BaseModel):
    title: str
    hook_direction: str
    audience_frame: str
    energy_level: str
    visual_mood: str
    music_mood: str
    angle_family: str | None = None
    section_id: str | None = None
    section_heading: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class ScriptDraft(BaseModel):
    title: str
    hook: str
    narration_text: str
    caption_text: str
    estimated_seconds: float
    visual_beats: list[str]
    music_tags: list[str]
    gameplay_tags: list[str]
    source_facts_used: list[str]
    qa_notes: list[str] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)


class IngestedSource(BaseModel):
    source_kind: SourceKind
    original_url: str | None = None
    title: str
    markdown: str
    normalized_urls: list[str] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)


class GeneratedBundle(BaseModel):
    source_brief: SourceBrief
    angles: list[AnglePlan]
    scripts: list[ScriptDraft]
    metadata: dict[str, Any] = Field(default_factory=dict)


class NarrationArtifact(BaseModel):
    audio_bytes: bytes
    format: str = "mp3"
    transcript: str
    word_timings: list[WordTiming]
    conversation_id: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class AgentConfigRecord(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid4()))
    role: AgentRole
    name: str
    agent_id: str
    branch_id: str | None = None
    version_id: str | None = None
    tool_ids: list[str] = Field(default_factory=list)
    is_active: bool = True
    metadata: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=utc_now)
    updated_at: datetime = Field(default_factory=utc_now)


class AgentRunRecord(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid4()))
    batch_id: str
    batch_item_id: str | None = None
    role: AgentRole
    agent_config_id: str | None = None
    status: str = "queued"
    conversation_id: str | None = None
    error: str | None = None
    payload: dict[str, Any] = Field(default_factory=dict)
    metadata: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=utc_now)
    updated_at: datetime = Field(default_factory=utc_now)


class AgentConversationRecord(BaseModel):
    conversation_id: str
    batch_id: str | None = None
    batch_item_id: str | None = None
    role: AgentRole
    agent_config_id: str | None = None
    status: str = "initiated"
    transcript: list[dict[str, Any]] = Field(default_factory=list)
    transcript_text: str | None = None
    has_audio: bool = False
    has_response_audio: bool = False
    audio_bucket: str | None = None
    audio_path: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=utc_now)
    updated_at: datetime = Field(default_factory=utc_now)


class AlignmentJobRecord(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid4()))
    batch_id: str
    batch_item_id: str
    conversation_id: str | None = None
    status: str = "queued"
    word_count: int = 0
    metadata: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=utc_now)
    updated_at: datetime = Field(default_factory=utc_now)


class AssetRecord(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid4()))
    kind: AssetKind
    bucket: str
    path: str
    public_url: str | None = None
    tags: list[str] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=utc_now)


class ChatRecord(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid4()))
    title: str = "Untitled chat"
    created_at: datetime = Field(default_factory=utc_now)
    updated_at: datetime = Field(default_factory=utc_now)
    last_source_label: str | None = None
    last_source_url: str | None = None
    total_runs: int = 0
    total_exported: int = 0
    total_failed: int = 0
    last_status: str | None = None
    cover_batch_id: str | None = None
    cover_item_id: str | None = None
    cover_output_url: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class ShortEngagementRecord(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid4()))
    chat_id: str
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
    created_at: datetime = Field(default_factory=utc_now)
    updated_at: datetime = Field(default_factory=utc_now)


class BatchRecord(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid4()))
    chat_id: str | None = None
    source_kind: SourceKind
    source_url: str | None = None
    title_hint: str | None = None
    requested_count: int
    status: BatchStatus = BatchStatus.QUEUED
    producer_agent_config_id: str | None = None
    narrator_agent_config_id: str | None = None
    premium_audio: bool = False
    created_at: datetime = Field(default_factory=utc_now)
    updated_at: datetime = Field(default_factory=utc_now)
    error: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class BatchItemRecord(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid4()))
    batch_id: str
    item_index: int
    status: BatchItemStatus = BatchItemStatus.QUEUED
    script: ScriptDraft | None = None
    narration_conversation_id: str | None = None
    output_url: str | None = None
    error: str | None = None
    render_metadata: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=utc_now)
    updated_at: datetime = Field(default_factory=utc_now)


class BatchEventRecord(BaseModel):
    sequence: int
    batch_id: str
    event_type: BatchEventType
    payload: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=utc_now)


class ToolScriptBundlePayload(BaseModel):
    batch_id: str
    source_brief: SourceBrief
    angles: list[AnglePlan]
    scripts: list[ScriptDraft]
