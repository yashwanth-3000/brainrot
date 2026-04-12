from __future__ import annotations

from pathlib import Path
from typing import Literal

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


def _project_root() -> Path:
    return Path(__file__).resolve().parents[2]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=(".env", ".env.local"),
        env_prefix="BRAINROT_",
        extra="ignore",
        case_sensitive=False,
        env_ignore_empty=True,
    )

    app_name: str = "Brainrot Reel Backend"
    environment: str = "development"
    log_level: str = "INFO"
    api_prefix: str = "/v1"
    public_base_url: str | None = None

    project_root: Path = Field(default_factory=_project_root)
    data_dir: Path = Field(default_factory=lambda: _project_root() / "data")
    temp_dir: Path = Field(default_factory=lambda: _project_root() / "data" / "tmp")

    openai_api_key: str | None = None
    openai_model: str = "gpt-5.4-mini"
    openai_reasoning_effort: str = "low"
    openai_base_url: str = "https://api.openai.com/v1"

    firecrawl_api_key: str | None = None
    firecrawl_base_url: str = "https://api.firecrawl.dev"
    firecrawl_scrape_max_age_ms: int = 172_800_000
    firecrawl_site_url_limit: int = 8
    firecrawl_poll_attempts: int = 30
    firecrawl_poll_interval_seconds: float = 2.0
    firecrawl_request_timeout_seconds: float = 120.0
    firecrawl_connect_timeout_seconds: float = 10.0
    firecrawl_request_retries: int = 3
    firecrawl_retry_backoff_seconds: float = 2.0

    elevenlabs_api_key: str | None = None
    elevenlabs_base_url: str = "https://api.elevenlabs.io"
    default_elevenlabs_voice_id: str | None = None
    narrator_voice_ids_csv: str = ""
    elevenlabs_model_id: str = "eleven_flash_v2"
    elevenlabs_tts_output_format: str = "mp3_44100_128"
    elevenlabs_tool_token: str | None = None
    elevenlabs_custom_llm_token: str | None = None
    elevenlabs_webhook_secret: str | None = None
    producer_agent_name: str = "Brainrot Producer Agent"
    narrator_agent_name: str = "Brainrot Narrator Agent"
    producer_mode: Literal["direct_openai", "elevenlabs_native"] = "direct_openai"
    narration_mode: Literal["elevenlabs_tts", "elevenlabs_agent"] = "elevenlabs_tts"
    producer_elevenlabs_model: str | None = None
    producer_timeout_seconds: int = 180
    narrator_timeout_seconds: int = 120
    conversation_idle_seconds: float = 6.0
    narrator_min_speech_seconds: float = 20.0
    session_end_timeout_seconds: float = 15.0
    progress_heartbeat_seconds: float = 2.5
    narrator_tts_speed: float = 1.2
    narration_trim_padding_seconds: float = 0.35
    narration_trim_min_excess_seconds: float = 0.75
    producer_source_char_limit: int = 30_000
    script_min_words: int = 80
    script_max_words: int = 100
    script_min_characters: int = 500
    script_target_min_seconds: float = 25.0
    script_target_max_seconds: float = 30.0
    producer_chunk_size: int = 1
    producer_chunk_concurrency: int = 4

    storage_backend: Literal["auto", "supabase", "memory"] = "auto"
    supabase_url: str | None = None
    supabase_service_role_key: str | None = None
    supabase_public_url: str | None = None

    render_concurrency: int = 4
    ffmpeg_bin: str = "ffmpeg"
    ffprobe_bin: str = "ffprobe"

    auto_seed_assets: bool = True
    assets_dir: Path = Field(default_factory=lambda: _project_root() / "assets")
    allowed_gameplay_games_csv: str = "gta-5,minecraft,roblox,subway-surfers"

    source_bucket: str = "sources"
    gameplay_bucket: str = "gameplay"
    music_bucket: str = "music"
    font_bucket: str = "fonts"
    overlay_bucket: str = "overlays"
    temp_audio_bucket: str = "temp-audio"
    subtitle_bucket: str = "subtitles"
    final_render_bucket: str = "final-renders"

    @property
    def supabase_enabled(self) -> bool:
        return bool(self.supabase_url and self.supabase_service_role_key)

    @property
    def resolved_storage_backend(self) -> Literal["supabase", "memory"]:
        if self.storage_backend == "supabase":
            return "supabase"
        if self.storage_backend == "memory":
            return "memory"
        return "supabase" if self.supabase_enabled else "memory"

    @property
    def firecrawl_enabled(self) -> bool:
        return bool(self.firecrawl_api_key)

    @property
    def elevenlabs_enabled(self) -> bool:
        return bool(self.elevenlabs_api_key)

    @property
    def allowed_gameplay_games(self) -> tuple[str, ...]:
        return tuple(
            part.strip().casefold()
            for part in self.allowed_gameplay_games_csv.split(",")
            if part.strip()
        )

    @property
    def narrator_voice_ids(self) -> tuple[str, ...]:
        configured = [
            part.strip()
            for part in self.narrator_voice_ids_csv.split(",")
            if part.strip()
        ]
        ordered = [
            voice_id
            for voice_id in [self.default_elevenlabs_voice_id, *configured]
            if voice_id
        ]
        return tuple(dict.fromkeys(ordered))

    def ensure_directories(self) -> None:
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.temp_dir.mkdir(parents=True, exist_ok=True)
