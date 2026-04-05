from __future__ import annotations

from enum import Enum


class StrEnum(str, Enum):
    def __str__(self) -> str:
        return self.value


class SourceKind(StrEnum):
    ARTICLE = "article"
    WEBSITE = "website"
    PDF_URL = "pdf_url"
    PDF_UPLOAD = "pdf_upload"


class BatchStatus(StrEnum):
    QUEUED = "queued"
    INGESTING = "ingesting"
    SCRIPTING = "scripting"
    RENDERING = "rendering"
    COMPLETED = "completed"
    PARTIAL_FAILED = "partial_failed"
    FAILED = "failed"


class BatchItemStatus(StrEnum):
    QUEUED = "queued"
    NARRATING = "narrating"
    SELECTING_ASSETS = "selecting_assets"
    RENDERING = "rendering"
    UPLOADED = "uploaded"
    FAILED = "failed"


class AssetKind(StrEnum):
    GAMEPLAY = "gameplay"
    MUSIC = "music"
    FONT = "font"
    OVERLAY = "overlay"


class BatchEventType(StrEnum):
    STATUS = "status"
    LOG = "log"
    SOURCE_INGESTED = "source_ingested"
    PRODUCER_CONVERSATION_STARTED = "producer_conversation_started"
    PRODUCER_TOOL_CALLED = "producer_tool_called"
    SCRIPTS_READY = "scripts_ready"
    NARRATOR_CONVERSATION_STARTED = "narrator_conversation_started"
    NARRATOR_AUDIO_READY = "narrator_audio_ready"
    ALIGNMENT_READY = "alignment_ready"
    RENDER_STARTED = "render_started"
    ITEM_COMPLETED = "item_completed"
    BATCH_COMPLETED = "batch_completed"
    ERROR = "error"
    DONE = "done"


class AgentRole(StrEnum):
    PRODUCER = "producer"
    NARRATOR = "narrator"
