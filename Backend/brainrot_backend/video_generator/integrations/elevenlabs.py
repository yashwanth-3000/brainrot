from __future__ import annotations

import asyncio
import base64
import hashlib
import io
import json
import logging
import os
import time
import wave
from dataclasses import dataclass
from typing import Any

import certifi
from elevenlabs.client import ElevenLabs
from elevenlabs.conversational_ai.conversation import AudioInterface, Conversation, ConversationInitiationData
from elevenlabs.types import (
    ArrayJsonSchemaPropertyInput,
    ConversationalConfig,
    LiteralJsonSchemaProperty,
    ObjectJsonSchemaPropertyInput,
    ToolRequestModel,
    ToolRequestModelToolConfig_Webhook,
    TtsConversationalConfigOutput,
    TurnConfig,
    VoiceSettings,
    WebhookToolApiSchemaConfigInput,
)

from brainrot_backend.config import Settings
from brainrot_backend.core.models.domain import (
    AgentConfigRecord,
    AgentConversationRecord,
    IngestedSource,
    NarrationArtifact,
    ScriptDraft,
    WordTiming,
)
from brainrot_backend.core.models.enums import AgentRole

logger = logging.getLogger(__name__)

VOICE_USE_CASE_PRIORITY = {
    "social_media": 0,
    "conversational": 1,
    "informative_educational": 2,
    "entertainment_tv": 3,
    "narrative_story": 4,
}


@dataclass(frozen=True)
class NarratorVoiceProfile:
    voice_id: str
    label: str
    source: str


class CollectingAudioInterface(AudioInterface):
    """Collects audio bytes from the conversation as a fallback source."""

    def __init__(self) -> None:
        self._chunks: list[bytes] = []
        self._input_callback = None

    def start(self, input_callback) -> None:  # noqa: ANN001
        self._input_callback = input_callback

    def stop(self) -> None:
        return None

    def output(self, audio: bytes) -> None:
        self._chunks.append(audio)

    def interrupt(self) -> None:
        return None

    def get_collected_audio(self) -> bytes:
        return b"".join(self._chunks)


class DiscardingAudioInterface(AudioInterface):
    def start(self, input_callback) -> None:  # noqa: ANN001
        self._input_callback = input_callback

    def stop(self) -> None:
        return None

    def output(self, audio: bytes) -> None:
        del audio

    def interrupt(self) -> None:
        return None

def build_producer_dynamic_variables(
    *,
    settings: Settings,
    batch_id: str,
    source: IngestedSource,
    requested_count: int,
) -> dict[str, str]:
    markdown = source.markdown
    if len(markdown) > settings.producer_source_char_limit:
        logger.warning(
            "Source markdown truncated from %d to %d chars for Producer dynamic variables",
            len(markdown), settings.producer_source_char_limit,
        )
        markdown = markdown[: settings.producer_source_char_limit] + "\n\n[... source truncated for brevity ...]"
    source_summary = str(
        source.metadata.get("source_summary")
        or source.metadata.get("summary")
        or source.metadata.get("description")
        or ""
    ).strip()
    return {
        "batch_id": batch_id,
        "source_title": source.title,
        "source_summary": source_summary,
        "source_markdown": markdown,
        "source_urls": json.dumps(source.normalized_urls or ([source.original_url] if source.original_url else [])),
        "requested_count": str(requested_count),
        "script_min_words": str(settings.script_min_words),
        "script_max_words": str(settings.script_max_words),
        "script_min_characters": str(settings.script_min_characters),
        "script_target_min_seconds": f"{settings.script_target_min_seconds:g}",
        "script_target_max_seconds": f"{settings.script_target_max_seconds:g}",
    }


def build_narrator_dynamic_variables(
    *,
    batch_id: str,
    batch_item_id: str,
    script: ScriptDraft,
) -> dict[str, str]:
    return {
        "batch_id": batch_id,
        "batch_item_id": batch_item_id,
        "title": script.title,
        "hook": script.hook,
        "script_text": script.narration_text,
        "pace": "high-energy",
        "pronunciation_terms": json.dumps(sorted(set(script.source_facts_used))),
    }


def build_narrator_override(
    *,
    premium_audio: bool,
    voice_id: str | None = None,
) -> dict[str, Any]:
    tts_override: dict[str, Any] = {}
    if premium_audio:
        tts_override["expressive_mode"] = True
    if voice_id:
        tts_override["voice_id"] = voice_id
    return {"tts": tts_override} if tts_override else {}


class ElevenLabsAgentsClient:
    def __init__(self, settings: Settings) -> None:
        os.environ.setdefault("SSL_CERT_FILE", certifi.where())
        os.environ.setdefault("REQUESTS_CA_BUNDLE", certifi.where())
        self.settings = settings
        self.client = ElevenLabs(api_key=settings.elevenlabs_api_key) if settings.elevenlabs_enabled else None
        self._narrator_voice_profiles: list[NarratorVoiceProfile] | None = None

    async def bootstrap_agents(
        self,
        public_base_url: str,
        *,
        include_producer: bool = True,
        include_narrator: bool = True,
    ) -> tuple[list[AgentConfigRecord], list[str]]:
        if not include_producer and not include_narrator:
            return [], []

        self._require_enabled()
        if include_producer and not public_base_url:
            raise RuntimeError("A public base URL is required to bootstrap ElevenLabs producer agents.")

        configs: list[AgentConfigRecord] = []
        tool_ids: list[str] = []

        if include_producer:
            self._require_agent_bootstrap_config()
            tool = await asyncio.to_thread(self._upsert_submit_script_tool, public_base_url.rstrip("/"))
            logger.info("Upserted submit_script_bundle tool: %s", tool.id)
            producer = await asyncio.to_thread(self._upsert_producer_agent, public_base_url.rstrip("/"), tool.id)
            logger.info("Upserted Producer agent: %s (branch=%s)", producer.agent_id, producer.branch_id)
            configs.append(
                AgentConfigRecord(
                    role=AgentRole.PRODUCER,
                    name=producer.name or self.settings.producer_agent_name,
                    agent_id=producer.agent_id,
                    branch_id=producer.branch_id,
                    version_id=producer.version_id,
                    tool_ids=[tool.id],
                    metadata={
                        "tags": list(producer.tags or []),
                        "conversation_config": dump_model(producer.conversation_config),
                    },
                )
            )
            tool_ids.append(tool.id)

        if include_narrator:
            narrator = await asyncio.to_thread(self._upsert_narrator_agent)
            logger.info("Upserted Narrator agent: %s (branch=%s)", narrator.agent_id, narrator.branch_id)
            configs.append(
                AgentConfigRecord(
                    role=AgentRole.NARRATOR,
                    name=narrator.name or self.settings.narrator_agent_name,
                    agent_id=narrator.agent_id,
                    branch_id=narrator.branch_id,
                    version_id=narrator.version_id,
                    tool_ids=[],
                    metadata={
                        "tags": list(narrator.tags or []),
                        "conversation_config": dump_model(narrator.conversation_config),
                    },
                )
            )

        return configs, tool_ids

    async def run_producer_conversation(
        self,
        *,
        agent_config: AgentConfigRecord,
        batch_id: str,
        source: IngestedSource,
        requested_count: int,
        timeout_seconds: int,
        bundle_ready: asyncio.Future[object],
    ) -> AgentConversationRecord | None:
        self._require_enabled()
        dynamic_variables = build_producer_dynamic_variables(
            settings=self.settings,
            batch_id=batch_id,
            source=source,
            requested_count=requested_count,
        )
        logger.info(
            "Starting Producer conversation for batch %s (agent=%s, timeout=%ds)",
            batch_id, agent_config.agent_id, timeout_seconds,
        )
        conversation = Conversation(
            client=self._client(),
            agent_id=agent_config.agent_id,
            requires_auth=True,
            audio_interface=DiscardingAudioInterface(),
            config=ConversationInitiationData(dynamic_variables=dynamic_variables),
        )
        await asyncio.to_thread(conversation.start_session)
        await self._wait_for_socket(conversation)
        logger.info("Producer WebSocket connected for batch %s", batch_id)

        await asyncio.to_thread(
            conversation.send_user_message,
            (
                "Analyze the injected source, generate the requested reel bundle, "
                "and call submit_script_bundle exactly once with the final structured payload."
            ),
        )
        logger.info("Sent trigger message to Producer for batch %s", batch_id)

        conversation_id: str | None = None
        try:
            await asyncio.wait_for(asyncio.shield(bundle_ready), timeout=timeout_seconds)
            logger.info("Producer bundle received for batch %s", batch_id)
        except asyncio.TimeoutError:
            logger.warning("Producer timed out after %ds for batch %s", timeout_seconds, batch_id)
            raise
        finally:
            await self._end_conversation(conversation)
            try:
                conversation_id = await asyncio.wait_for(
                    asyncio.to_thread(conversation.wait_for_session_end),
                    timeout=self.settings.session_end_timeout_seconds,
                )
            except (asyncio.TimeoutError, Exception) as exc:
                logger.warning("wait_for_session_end failed for batch %s: %s", batch_id, exc)
                conversation_id = _extract_conversation_id(conversation)

        if not conversation_id:
            logger.warning("No conversation_id obtained for Producer batch %s", batch_id)
            return None
        return await self.get_conversation_record(
            conversation_id=conversation_id,
            role=AgentRole.PRODUCER,
            agent_config_id=agent_config.id,
            batch_id=batch_id,
            batch_item_id=None,
        )

    async def narrate_script(
        self,
        *,
        agent_config: AgentConfigRecord,
        batch_id: str,
        batch_item_id: str,
        script: ScriptDraft,
        premium_audio: bool,
        timeout_seconds: int,
        idle_seconds: float,
        min_speech_seconds: float = 8.0,
        voice_id: str | None = None,
        voice_label: str | None = None,
    ) -> tuple[NarrationArtifact, AgentConversationRecord]:
        self._require_enabled()
        activity = {
            "last_audio": time.monotonic(),
            "last_any": time.monotonic(),
            "audio_chunks": 0,
            "text_seen": False,
        }
        audio_interface = CollectingAudioInterface()
        original_output = audio_interface.output

        def tracking_output(audio: bytes) -> None:
            original_output(audio)
            activity["audio_chunks"] += 1
            activity["last_audio"] = time.monotonic()
            activity["last_any"] = time.monotonic()

        def on_text(*_args) -> None:
            activity["text_seen"] = True
            activity["last_any"] = time.monotonic()

        audio_interface.output = tracking_output  # type: ignore[assignment]

        logger.info(
            "Starting Narrator conversation for item %s (agent=%s, timeout=%ds, idle=%.1fs, voice=%s)",
            batch_item_id,
            agent_config.agent_id,
            timeout_seconds,
            idle_seconds,
            voice_label or voice_id or "default",
        )
        conversation = Conversation(
            client=self._client(),
            agent_id=agent_config.agent_id,
            requires_auth=True,
            audio_interface=audio_interface,
            config=ConversationInitiationData(
                dynamic_variables=build_narrator_dynamic_variables(
                    batch_id=batch_id,
                    batch_item_id=batch_item_id,
                    script=script,
                ),
                conversation_config_override=build_narrator_override(
                    premium_audio=premium_audio,
                    voice_id=voice_id,
                ) or None,
            ),
            callback_agent_response=on_text,
            callback_audio_alignment=on_text,
        )
        await asyncio.to_thread(conversation.start_session)
        await self._wait_for_socket(conversation)
        logger.info("Narrator WebSocket connected for item %s (script ~%ds, %d words)",
                     batch_item_id, script.estimated_seconds, len(script.narration_text.split()))

        started_at = time.monotonic()
        while True:
            await asyncio.sleep(0.5)
            elapsed = time.monotonic() - started_at
            if elapsed >= timeout_seconds:
                logger.warning("Narrator timed out after %.1fs for item %s", elapsed, batch_item_id)
                break
            if elapsed < min_speech_seconds:
                continue
            has_audio = activity["audio_chunks"] > 0
            if not has_audio:
                continue
            since_last_audio = time.monotonic() - activity["last_audio"]
            if since_last_audio >= idle_seconds:
                logger.info(
                    "Narrator idle for %.1fs after %.1fs total (%d audio chunks), ending for item %s",
                    since_last_audio, elapsed, activity["audio_chunks"], batch_item_id,
                )
                break

        await self._end_conversation(conversation)
        conversation_id: str | None = None
        try:
            conversation_id = await asyncio.wait_for(
                asyncio.to_thread(conversation.wait_for_session_end),
                timeout=self.settings.session_end_timeout_seconds,
            )
        except (asyncio.TimeoutError, Exception) as exc:
            logger.warning("Narrator wait_for_session_end failed for item %s: %s", batch_item_id, exc)
            conversation_id = _extract_conversation_id(conversation)

        if not conversation_id:
            raise RuntimeError(f"Narrator conversation ended without a conversation ID for item {batch_item_id}.")

        collected_bytes = len(audio_interface.get_collected_audio())
        logger.info(
            "Narrator conversation %s ended for item %s (audio_chunks=%d, collected_bytes=%d, text_seen=%s)",
            conversation_id, batch_item_id, activity["audio_chunks"], collected_bytes, activity["text_seen"],
        )

        conversation_record = await self.wait_for_conversation_record(
            conversation_id=conversation_id,
            role=AgentRole.NARRATOR,
            agent_config_id=agent_config.id,
            batch_id=batch_id,
            batch_item_id=batch_item_id,
            timeout_seconds=timeout_seconds,
            require_audio=True,
        )

        collected_audio = audio_interface.get_collected_audio()
        if collected_audio and len(collected_audio) > 1000:
            logger.info(
                "Using collected audio (%d bytes, %d chunks) for conversation %s",
                len(collected_audio), activity["audio_chunks"], conversation_id,
            )
            wav_buffer = io.BytesIO()
            with wave.open(wav_buffer, "wb") as wav_file:
                wav_file.setnchannels(1)
                wav_file.setsampwidth(2)
                wav_file.setframerate(16000)
                wav_file.writeframes(collected_audio)
            audio_bytes = wav_buffer.getvalue()
            audio_format = "wav"
            audio_mime_type = "audio/wav"
        else:
            raw_audio_bytes = await self._fetch_conversation_audio(conversation_id)
            if not raw_audio_bytes:
                raise RuntimeError(
                    f"No audio produced for narrator conversation {conversation_id} (item {batch_item_id}). "
                    "The narrator agent may not have spoken."
                )
            audio_bytes, audio_format, audio_mime_type = normalize_conversation_audio(raw_audio_bytes)
        transcript = script.narration_text.strip()
        if conversation_record.transcript_text:
            observed_transcript = conversation_record.transcript_text.strip()
            if _normalize_alignment_text(observed_transcript) != _normalize_alignment_text(transcript):
                logger.warning(
                    "Narrator transcript diverged from script for item %s; using script_text for alignment",
                    batch_item_id,
                )
        logger.info("Running forced alignment for item %s (%d bytes audio)", batch_item_id, len(audio_bytes))
        alignment = await asyncio.to_thread(
            self._client().forced_alignment.create,
            file=(f"narration.{audio_format}", audio_bytes, audio_mime_type),
            text=transcript,
        )
        word_timings = word_timings_from_forced_alignment(alignment)
        trimmed_trailing_seconds = 0.0
        if word_timings and audio_format == "wav":
            audio_bytes, trimmed_trailing_seconds = trim_wav_trailing_padding(
                audio_bytes,
                target_duration_seconds=word_timings[-1].end + self.settings.narration_trim_padding_seconds,
                min_excess_seconds=self.settings.narration_trim_min_excess_seconds,
            )
            if trimmed_trailing_seconds > 0:
                logger.info(
                    "Trimmed %.2fs trailing narration padding for item %s",
                    trimmed_trailing_seconds,
                    batch_item_id,
                )
        artifact = NarrationArtifact(
            audio_bytes=audio_bytes,
            format=audio_format,
            transcript=transcript,
            word_timings=word_timings,
            conversation_id=conversation_id,
            metadata={
                "audio_mime_type": audio_mime_type,
                "forced_alignment": dump_model(alignment),
                "conversation": conversation_record.metadata,
                "trimmed_trailing_seconds": trimmed_trailing_seconds,
                "voice_id": voice_id,
                "voice_label": voice_label,
            },
        )
        logger.info(
            "Narration artifact ready for item %s: %d words, %.1fs audio",
            batch_item_id, len(artifact.word_timings),
            artifact.word_timings[-1].end if artifact.word_timings else 0,
        )
        return artifact, conversation_record

    async def narrate_script_tts(
        self,
        *,
        batch_id: str,
        batch_item_id: str,
        script: ScriptDraft,
        voice_id: str | None = None,
        voice_label: str | None = None,
    ) -> NarrationArtifact:
        self._require_enabled()
        selected_voice_id = voice_id or self.settings.default_elevenlabs_voice_id
        if not selected_voice_id:
            raise RuntimeError("BRAINROT_DEFAULT_ELEVENLABS_VOICE_ID must be configured for direct TTS narration.")

        logger.info(
            "Starting direct ElevenLabs TTS for item %s (voice=%s, model=%s)",
            batch_item_id,
            voice_label or selected_voice_id,
            self.settings.elevenlabs_model_id,
        )
        output_format = self.settings.elevenlabs_tts_output_format
        tts_response = await asyncio.to_thread(
            self._client().text_to_speech.convert_with_timestamps,
            selected_voice_id,
            text=script.narration_text,
            model_id=self.settings.elevenlabs_model_id,
            output_format=output_format,
            voice_settings=VoiceSettings(speed=self.settings.narrator_tts_speed),
        )
        response_payload = dump_model(tts_response)
        audio_base64 = str(
            response_payload.get("audio_base_64")
            or response_payload.get("audio_base64")
            or getattr(tts_response, "audio_base_64", "")
            or ""
        )
        audio_bytes = base64.b64decode(audio_base64) if audio_base64 else b""
        if not audio_bytes:
            raise RuntimeError(f"ElevenLabs TTS returned empty audio for item {batch_item_id}.")

        transcript = script.narration_text.strip()
        word_timings = word_timings_from_forced_alignment(tts_response)
        trimmed_trailing_seconds = 0.0
        audio_format = output_format.split("_", 1)[0]
        audio_mime_type = "audio/wav" if audio_format == "wav" else "audio/mpeg"
        if word_timings and audio_format == "wav":
            audio_bytes, trimmed_trailing_seconds = trim_wav_trailing_padding(
                audio_bytes,
                target_duration_seconds=word_timings[-1].end + self.settings.narration_trim_padding_seconds,
                min_excess_seconds=self.settings.narration_trim_min_excess_seconds,
            )

        return NarrationArtifact(
            audio_bytes=audio_bytes,
            format=audio_format,
            transcript=transcript,
            word_timings=word_timings,
            conversation_id=None,
            metadata={
                "audio_mime_type": audio_mime_type,
                "timing_response": response_payload,
                "trimmed_trailing_seconds": trimmed_trailing_seconds,
                "voice_id": selected_voice_id,
                "voice_label": voice_label or "Default narrator voice",
                "narration_mode": "elevenlabs_tts",
                "batch_id": batch_id,
                "batch_item_id": batch_item_id,
            },
        )

    async def select_narrator_voice(
        self,
        *,
        batch_id: str,
        item_index: int,
        requested_count: int,
    ) -> NarratorVoiceProfile | None:
        profiles = await self.list_narrator_voice_profiles()
        if not profiles:
            return None
        if len(profiles) == 1 or requested_count <= 1:
            return profiles[0]

        if requested_count >= 5:
            span = min(5, len(profiles))
        else:
            span = min(2, len(profiles))

        offset = int(hashlib.sha256(batch_id.encode("utf-8")).hexdigest()[:8], 16) % len(profiles)
        return profiles[(offset + item_index) % span]

    async def list_narrator_voice_profiles(self) -> list[NarratorVoiceProfile]:
        if self._narrator_voice_profiles is not None:
            return list(self._narrator_voice_profiles)

        configured = list(self._configured_narrator_voice_profiles())
        discovered: list[NarratorVoiceProfile] = []
        try:
            discovered = await asyncio.to_thread(self._discover_narrator_voice_profiles)
        except Exception as exc:  # pragma: no cover - network-backed fallback
            logger.warning("Failed to discover ElevenLabs narrator voices: %s", exc)

        merged: list[NarratorVoiceProfile] = []
        seen: set[str] = set()
        for profile in [*configured, *discovered]:
            if profile.voice_id in seen:
                continue
            seen.add(profile.voice_id)
            merged.append(profile)

        if not merged and self.settings.default_elevenlabs_voice_id:
            merged.append(
                NarratorVoiceProfile(
                    voice_id=self.settings.default_elevenlabs_voice_id,
                    label="Default narrator voice",
                    source="default",
                )
            )

        self._narrator_voice_profiles = merged[:5]
        return list(self._narrator_voice_profiles)

    async def _fetch_conversation_audio(self, conversation_id: str, retries: int = 3) -> bytes:
        for attempt in range(retries):
            try:
                raw = await asyncio.to_thread(
                    lambda: b"".join(self._client().conversational_ai.conversations.audio.get(conversation_id))
                )
                if raw:
                    logger.info("Fetched %d bytes audio from API for conversation %s", len(raw), conversation_id)
                    return raw
            except Exception as exc:
                logger.warning(
                    "Audio fetch attempt %d/%d failed for %s: %s",
                    attempt + 1, retries, conversation_id, exc,
                )
            if attempt < retries - 1:
                await asyncio.sleep(2.0 * (attempt + 1))
        return b""

    async def get_conversation_record(
        self,
        *,
        conversation_id: str,
        role: AgentRole,
        agent_config_id: str,
        batch_id: str,
        batch_item_id: str | None,
    ) -> AgentConversationRecord:
        self._require_enabled()
        response = await asyncio.to_thread(self._client().conversational_ai.conversations.get, conversation_id)
        transcript = [dump_model(item) for item in response.transcript]
        transcript_text = join_agent_messages(response.transcript)
        return AgentConversationRecord(
            conversation_id=response.conversation_id,
            batch_id=batch_id,
            batch_item_id=batch_item_id,
            role=role,
            agent_config_id=agent_config_id,
            status=str(response.status),
            transcript=transcript,
            transcript_text=transcript_text or None,
            has_audio=bool(response.has_audio),
            has_response_audio=bool(response.has_response_audio),
            metadata={
                "agent_id": response.agent_id,
                "agent_name": response.agent_name,
                "branch_id": response.branch_id,
                "version_id": response.version_id,
                "raw": dump_model(response),
            },
        )

    async def wait_for_conversation_record(
        self,
        *,
        conversation_id: str,
        role: AgentRole,
        agent_config_id: str,
        batch_id: str,
        batch_item_id: str | None,
        timeout_seconds: int,
        require_audio: bool,
    ) -> AgentConversationRecord:
        deadline = time.monotonic() + timeout_seconds
        last_record: AgentConversationRecord | None = None
        poll_interval = 1.0
        while time.monotonic() < deadline:
            try:
                record = await self.get_conversation_record(
                    conversation_id=conversation_id,
                    role=role,
                    agent_config_id=agent_config_id,
                    batch_id=batch_id,
                    batch_item_id=batch_item_id,
                )
                last_record = record
                if not require_audio or record.has_response_audio:
                    return record
            except Exception as exc:
                logger.warning("Polling conversation %s failed: %s", conversation_id, exc)
            await asyncio.sleep(poll_interval)
            poll_interval = min(poll_interval * 1.5, 5.0)
        if last_record is not None:
            logger.warning(
                "Returning conversation record without audio for %s (has_response_audio=%s)",
                conversation_id, last_record.has_response_audio,
            )
            return last_record
        raise TimeoutError(f"Timed out waiting for ElevenLabs conversation {conversation_id}.")

    async def verify_webhook(self, raw_body: bytes, signature: str) -> dict[str, Any]:
        self._require_enabled()
        if not self.settings.elevenlabs_webhook_secret:
            raise RuntimeError("BRAINROT_ELEVENLABS_WEBHOOK_SECRET is not configured.")
        event = await asyncio.to_thread(
            self._client().webhooks.construct_event,
            raw_body.decode("utf-8"),
            signature,
            self.settings.elevenlabs_webhook_secret,
        )
        return dump_model(event)

    async def _wait_for_socket(self, conversation: Conversation, timeout_seconds: float = 20.0) -> None:
        started_at = time.monotonic()
        while time.monotonic() - started_at < timeout_seconds:
            ws = getattr(conversation, "_ws", None) or getattr(conversation, "ws", None)
            if ws is not None:
                return
            if getattr(conversation, "_conversation_id", None) is not None:
                return
            await asyncio.sleep(0.15)
        raise TimeoutError("Timed out waiting for ElevenLabs conversation socket to connect.")

    async def _end_conversation(self, conversation: Conversation) -> None:
        try:
            await asyncio.to_thread(conversation.end_session)
        except Exception as exc:
            logger.warning("Failed to end ElevenLabs conversation cleanly: %s", exc)
            try:
                ws = getattr(conversation, "_ws", None) or getattr(conversation, "ws", None)
                if ws is not None:
                    await asyncio.to_thread(ws.close)
            except Exception:
                pass

    def _upsert_submit_script_tool(self, public_base_url: str):
        name = "submit_script_bundle"
        existing = self._find_tool_by_name(name)
        request = ToolRequestModel(
            tool_config=ToolRequestModelToolConfig_Webhook(
                name=name,
                description=(
                    "Submit the final source brief, angle plan, and reel scripts for a backend batch. "
                    "Call this exactly once when the full bundle is ready."
                ),
                execution_mode="immediate",
                disable_interruptions=True,
                tool_error_handling_mode="passthrough",
                response_timeout_secs=30,
                api_schema=WebhookToolApiSchemaConfigInput(
                    url=f"{public_base_url}{self.settings.api_prefix}/agents/tools/submit-script-bundle",
                    method="POST",
                    content_type="application/json",
                    request_headers={
                        "Authorization": f"Bearer {self.settings.elevenlabs_tool_token}",
                    },
                    request_body_schema=script_bundle_schema(),
                ),
            )
        )
        if existing is not None:
            return self._client().conversational_ai.tools.update(existing.id, request=request)
        return self._client().conversational_ai.tools.create(request=request)

    def _upsert_producer_agent(self, public_base_url: str, tool_id: str):
        name = self.settings.producer_agent_name
        existing = self._find_agent_by_name(name)
        prompt_config: dict[str, Any] = {
            "prompt": producer_prompt(),
            "llm": self.settings.producer_elevenlabs_model or self.settings.openai_model,
            "temperature": 0.2,
            "tool_ids": [tool_id],
            "backup_llm_config": {"preference": "disabled"},
        }
        if self.settings.producer_mode == "direct_openai":
            prompt_config.update(
                {
                    "llm": "custom-llm",
                    "reasoning_effort": self.settings.openai_reasoning_effort,
                    "custom_llm": {
                        "url": f"{public_base_url}{self.settings.api_prefix}/agents/custom-llm",
                        "model_id": self.settings.openai_model,
                        "api_type": "chat_completions",
                        "request_headers": {
                            "Authorization": f"Bearer {self.settings.elevenlabs_custom_llm_token}",
                        },
                    },
                }
            )
        conversation_config = ConversationalConfig.model_validate(
            {
                "conversation": {
                    "text_only": True,
                    "monitoring_enabled": False,
                    "max_duration_seconds": 900,
                },
                "turn": {
                    "turn_timeout": 120.0,
                    "silence_end_call_timeout": 120.0,
                    "turn_eagerness": "patient",
                },
                "agent": {
                    "language": "en",
                    "prompt": prompt_config,
                },
            }
        )
        if existing is None:
            created = self._client().conversational_ai.agents.create(
                name=name,
                tags=["brainrot", "producer"],
                conversation_config=conversation_config,
                enable_versioning=True,
            )
            return self._client().conversational_ai.agents.get(created.agent_id)
        return self._client().conversational_ai.agents.update(
            existing.agent_id,
            name=name,
            tags=["brainrot", "producer"],
            conversation_config=conversation_config,
            enable_versioning_if_not_enabled=True,
            branch_id=getattr(existing, "branch_id", None),
            version_description="Codex bootstrap sync",
        )

    def _upsert_narrator_agent(self):
        if not self.settings.default_elevenlabs_voice_id:
            raise RuntimeError("BRAINROT_DEFAULT_ELEVENLABS_VOICE_ID must be configured for narrator bootstrap.")
        name = self.settings.narrator_agent_name
        existing = self._find_agent_by_name(name)
        conversation_config = ConversationalConfig.model_validate(
            {
                "conversation": {
                    "text_only": False,
                    "monitoring_enabled": False,
                    "max_duration_seconds": 240,
                },
                "turn": {
                    "turn_timeout": 1.5,
                    "silence_end_call_timeout": 60.0,
                    "turn_eagerness": "patient",
                },
                "tts": {
                    "model_id": self.settings.elevenlabs_model_id,
                    "voice_id": self.settings.default_elevenlabs_voice_id,
                    "expressive_mode": False,
                    "stability": 0.45,
                    "similarity_boost": 0.8,
                    "speed": self.settings.narrator_tts_speed,
                },
                "agent": {
                    "language": "en",
                    "first_message": "{{script_text}}",
                    "disable_first_message_interruptions": True,
                    "prompt": {
                        "prompt": narrator_prompt(),
                        "llm": "gpt-4o-mini",
                        "backup_llm_config": {"preference": "disabled"},
                    },
                },
            }
        )
        if existing is None:
            created = self._client().conversational_ai.agents.create(
                name=name,
                tags=["brainrot", "narrator"],
                conversation_config=conversation_config,
                enable_versioning=True,
            )
            return self._client().conversational_ai.agents.get(created.agent_id)
        return self._client().conversational_ai.agents.update(
            existing.agent_id,
            name=name,
            tags=["brainrot", "narrator"],
            conversation_config=conversation_config,
            enable_versioning_if_not_enabled=True,
            branch_id=getattr(existing, "branch_id", None),
            version_description="Codex bootstrap sync",
        )

    def _configured_narrator_voice_profiles(self) -> list[NarratorVoiceProfile]:
        profiles: list[NarratorVoiceProfile] = []
        for index, voice_id in enumerate(self.settings.narrator_voice_ids):
            label = "Default narrator voice" if index == 0 else f"Configured narrator voice {index + 1}"
            profiles.append(
                NarratorVoiceProfile(
                    voice_id=voice_id,
                    label=label,
                    source="configured",
                )
            )
        return profiles

    def _discover_narrator_voice_profiles(self) -> list[NarratorVoiceProfile]:
        response = self._client().voices.get_all()
        voices = list(getattr(response, "voices", []) or [])
        ranked: list[tuple[int, str, NarratorVoiceProfile]] = []
        for voice in voices:
            labels = getattr(voice, "labels", {}) or {}
            language = str(labels.get("language") or "").strip().lower()
            if language and language != "en":
                continue
            use_case = str(labels.get("use_case") or "").strip().lower()
            category = str(getattr(voice, "category", "") or "").strip().lower()
            if category != "premade":
                continue
            voice_id = str(getattr(voice, "voice_id", "") or "").strip()
            if not voice_id:
                continue
            name = str(getattr(voice, "name", "") or "Narrator voice").strip()
            ranked.append(
                (
                    VOICE_USE_CASE_PRIORITY.get(use_case, 99),
                    name.casefold(),
                    NarratorVoiceProfile(
                        voice_id=voice_id,
                        label=name,
                        source="discovered",
                    ),
                )
            )

        ranked.sort(key=lambda item: (item[0], item[1]))
        discovered = [profile for _, _, profile in ranked]
        if self.settings.default_elevenlabs_voice_id:
            discovered.sort(
                key=lambda profile: 0 if profile.voice_id == self.settings.default_elevenlabs_voice_id else 1
            )
        return discovered

    def _find_tool_by_name(self, name: str):
        cursor: str | None = None
        while True:
            response = self._client().conversational_ai.tools.list(
                search=name,
                page_size=100,
                types="webhook",
                cursor=cursor,
            )
            for tool in response.tools:
                tool_name = getattr(getattr(tool, "tool_config", None), "name", None)
                if tool_name == name:
                    return tool
            if not response.has_more:
                return None
            cursor = response.next_cursor

    def _find_agent_by_name(self, name: str):
        cursor: str | None = None
        while True:
            response = self._client().conversational_ai.agents.list(
                search=name,
                page_size=100,
                show_only_owned_agents=True,
                cursor=cursor,
            )
            for agent in response.agents:
                if getattr(agent, "name", None) == name:
                    return agent
            if not response.has_more:
                return None
            cursor = response.next_cursor

    def _require_agent_bootstrap_config(self) -> None:
        required = {"BRAINROT_ELEVENLABS_TOOL_TOKEN": self.settings.elevenlabs_tool_token}
        if self.settings.producer_mode == "direct_openai":
            required["BRAINROT_ELEVENLABS_CUSTOM_LLM_TOKEN"] = self.settings.elevenlabs_custom_llm_token
        missing = [name for name, value in required.items() if not value]
        if missing:
            raise RuntimeError(f"Missing ElevenLabs bootstrap settings: {', '.join(missing)}")

    def _require_enabled(self) -> None:
        if self.client is None:
            raise RuntimeError("ElevenLabs API key is not configured.")

    def _client(self) -> ElevenLabs:
        self._require_enabled()
        assert self.client is not None
        return self.client


def _extract_conversation_id(conversation: Conversation) -> str | None:
    for attr in ("_conversation_id", "conversation_id", "_session_id"):
        value = getattr(conversation, attr, None)
        if value:
            return str(value)
    return None


def producer_prompt() -> str:
    return (
        "You are the Brainrot Producer Agent for a short-form reel backend. "
        "Use only the injected source_title, source_summary, source_markdown, and source_urls. "
        "Do not invent unsupported facts. Generate exactly {{requested_count}} distinct reel concepts. "
        "Internally execute these stages in order: brief_analysis, angle_planning, script_writing, qa_review. "
        "\n\nCRITICAL NARRATION LENGTH REQUIREMENTS:\n"
        "- Each narration_text MUST be {{script_min_words}} to {{script_max_words}} words long "
        "(this produces roughly {{script_target_min_seconds}}-{{script_target_max_seconds}} seconds of speech).\n"
        "- Each narration_text should also be at least {{script_min_characters}} characters so the pacing does not collapse into a too-short read.\n"
        "- Scripts outside that word-count range will be rejected.\n"
        "- Write in a punchy, fast-paced storytelling style with multiple sentences.\n"
        "- Each script should have a hook sentence, 3-4 body sentences with facts, and a closing punchline.\n"
        "- Every script must include at least two concrete source details such as feature names, platform names, "
        "workflow steps, numeric limits, or backend architecture specifics.\n"
        "- Avoid generic startup ad copy, rhetorical-question hooks, and filler phrases like 'Meet X', "
        "'Introducing X', 'revolutionary', 'ultimate solution', or 'step into the future'.\n"
        "- Do not use canned lead-ins like 'Start with this detail', 'The fastest win here', "
        "'Most people miss this part', 'If this gets skipped, the workflow falls apart', "
        "or 'Creators will care about this'.\n"
        "- Every hook must mention a concrete detail from the script's own source_facts_used list, not just a vague benefit promise.\n"
        "- Spread the scripts across different angles instead of repeating the same broad product pitch.\n"
        "\nEach script must stay faithful to the source, be unique, hyper-engaging, "
        "open with a strong first-3-second hook, and include concise visual, music, and gameplay hints. "
        "When the full bundle is complete, call submit_script_bundle exactly once. "
        "Do not answer in plain prose instead of calling the tool. "
        "The tool payload must include batch_id={{batch_id}}, a grounded source brief, distinct angles, "
        "and the final scripts."
    )


def narrator_prompt() -> str:
    return (
        "You are the Brainrot Narrator Agent. Speak only the exact script_text variable. "
        "Do not add greetings, commentary, or explanations. "
        "Keep the delivery clean, energetic, and easy to caption. "
        "Honor the title and pace variables for tone, but never change the wording of {{script_text}}."
    )


def ideal_narration_speed(estimated_seconds: float) -> float:
    if estimated_seconds <= 25:
        return 0.96
    if estimated_seconds >= 30:
        return 1.08
    return 1.0


def normalize_conversation_audio(
    audio_bytes: bytes,
    *,
    sample_rate: int | None = None,
) -> tuple[bytes, str, str]:
    if not audio_bytes:
        raise RuntimeError("Empty audio bytes received.")

    if audio_bytes[:4] == b"RIFF":
        return audio_bytes, "wav", "audio/wav"

    if audio_bytes[:3] == b"ID3" or audio_bytes[:2] == b"\xff\xfb":
        return audio_bytes, "mp3", "audio/mpeg"

    if audio_bytes[:4] == b"fLaC":
        return audio_bytes, "flac", "audio/flac"

    if audio_bytes[:4] == b"OggS":
        return audio_bytes, "ogg", "audio/ogg"

    rate = sample_rate or 16000
    wav_buffer = io.BytesIO()
    with wave.open(wav_buffer, "wb") as wav_file:
        wav_file.setnchannels(1)
        wav_file.setsampwidth(2)
        wav_file.setframerate(rate)
        wav_file.writeframes(audio_bytes)
    logger.info("Wrapped %d bytes raw PCM as WAV (rate=%d)", len(audio_bytes), rate)
    return wav_buffer.getvalue(), "wav", "audio/wav"


def trim_wav_trailing_padding(
    audio_bytes: bytes,
    *,
    target_duration_seconds: float,
    min_excess_seconds: float,
) -> tuple[bytes, float]:
    with wave.open(io.BytesIO(audio_bytes), "rb") as wav_file:
        frame_rate = wav_file.getframerate()
        frame_count = wav_file.getnframes()
        channels = wav_file.getnchannels()
        sample_width = wav_file.getsampwidth()
        current_duration_seconds = frame_count / frame_rate if frame_rate else 0.0
        excess_seconds = current_duration_seconds - target_duration_seconds
        if excess_seconds < min_excess_seconds:
            return audio_bytes, 0.0
        max_frame_count = max(1, int(target_duration_seconds * frame_rate))
        frames = wav_file.readframes(max_frame_count)

    trimmed_buffer = io.BytesIO()
    with wave.open(trimmed_buffer, "wb") as wav_file:
        wav_file.setnchannels(channels)
        wav_file.setsampwidth(sample_width)
        wav_file.setframerate(frame_rate)
        wav_file.writeframes(frames)
    return trimmed_buffer.getvalue(), round(excess_seconds, 2)


def _normalize_alignment_text(value: str) -> str:
    return " ".join(value.lower().split())


def join_agent_messages(transcript: list[Any]) -> str:
    parts: list[str] = []
    for item in transcript:
        role = getattr(item, "role", None)
        message = getattr(item, "message", None)
        if role == "agent" and message:
            parts.append(str(message).strip())
    return " ".join(part for part in parts if part).strip()


def dump_model(value: Any) -> Any:
    if hasattr(value, "model_dump"):
        return value.model_dump(mode="json")
    if isinstance(value, list):
        return [dump_model(item) for item in value]
    if isinstance(value, dict):
        return {key: dump_model(item) for key, item in value.items()}
    return value


def script_bundle_schema() -> ObjectJsonSchemaPropertyInput:
    return object_schema(
        "Structured payload containing the final source brief, angles, and scripts for a batch.",
        properties={
            "batch_id": string_schema("Batch identifier from the injected dynamic variables."),
            "source_brief": object_schema(
                "Grounded summary of the source content.",
                properties={
                    "canonical_title": string_schema("Canonical title for the source."),
                    "summary": string_schema("Concise summary of the source."),
                    "facts": array_of_strings("Key facts that the scripts can rely on."),
                    "entities": array_of_strings("Important people, companies, products, or concepts."),
                    "tone": string_schema("Tone of the original source."),
                    "do_not_drift": array_of_strings("Constraints the scripts must not violate."),
                    "source_urls": array_of_strings("Normalized URLs used for grounding."),
                },
                required=[
                    "canonical_title",
                    "summary",
                    "facts",
                    "entities",
                    "tone",
                    "do_not_drift",
                    "source_urls",
                ],
            ),
            "angles": ArrayJsonSchemaPropertyInput(
                type="array",
                description="Distinct hook and framing angles for the batch.",
                items=object_schema(
                    "A single angle plan.",
                    properties={
                        "title": string_schema("Internal angle title."),
                        "hook_direction": string_schema("What the opening hook should emphasize."),
                        "audience_frame": string_schema("Who the framing is speaking to."),
                        "energy_level": string_schema("Expected delivery energy."),
                        "visual_mood": string_schema("Visual mood for gameplay/background."),
                        "music_mood": string_schema("Music mood for backing track."),
                    },
                    required=[
                        "title",
                        "hook_direction",
                        "audience_frame",
                        "energy_level",
                        "visual_mood",
                        "music_mood",
                    ],
                ),
            ),
            "scripts": ArrayJsonSchemaPropertyInput(
                type="array",
                description="Final short-form reel scripts.",
                items=object_schema(
                    "A single script draft.",
                    properties={
                        "title": string_schema("Script title."),
                        "hook": string_schema("First three second hook."),
                        "narration_text": string_schema("Narration text for the reel."),
                        "caption_text": string_schema("Caption-safe condensed text."),
                        "estimated_seconds": number_schema("Estimated runtime in seconds."),
                        "visual_beats": array_of_strings("Visual beat instructions."),
                        "music_tags": array_of_strings("Desired music tags."),
                        "gameplay_tags": array_of_strings("Desired gameplay tags."),
                        "source_facts_used": array_of_strings("Facts used in the script."),
                        "qa_notes": array_of_strings("Optional QA notes."),
                    },
                    required=[
                        "title",
                        "hook",
                        "narration_text",
                        "caption_text",
                        "estimated_seconds",
                        "visual_beats",
                        "music_tags",
                        "gameplay_tags",
                        "source_facts_used",
                        "qa_notes",
                    ],
                ),
            ),
        },
        required=["batch_id", "source_brief", "angles", "scripts"],
    )


def object_schema(
    description: str,
    *,
    properties: dict[str, Any],
    required: list[str],
) -> ObjectJsonSchemaPropertyInput:
    return ObjectJsonSchemaPropertyInput(
        type="object",
        description=description,
        properties=properties,
        required=required,
    )


def string_schema(description: str) -> LiteralJsonSchemaProperty:
    return LiteralJsonSchemaProperty(type="string", description=description)


def number_schema(description: str) -> LiteralJsonSchemaProperty:
    return LiteralJsonSchemaProperty(type="number", description=description)


def array_of_strings(description: str) -> ArrayJsonSchemaPropertyInput:
    return ArrayJsonSchemaPropertyInput(
        type="array",
        description=description,
        items=LiteralJsonSchemaProperty(type="string", description="String item."),
    )


def word_timings_from_alignment(alignment: dict[str, Any]) -> list[WordTiming]:
    characters = alignment.get("characters") or alignment.get("chars") or []
    starts = alignment.get("character_start_times_seconds") or alignment.get("character_start_times") or []
    ends = alignment.get("character_end_times_seconds") or alignment.get("character_end_times") or []
    if not characters or not starts or not ends:
        return []

    timings: list[WordTiming] = []
    current_chars: list[str] = []
    current_start: float | None = None
    current_end: float | None = None

    for char, start, end in zip(characters, starts, ends, strict=False):
        if char.isspace():
            if current_chars and current_start is not None and current_end is not None:
                timings.append(WordTiming(text="".join(current_chars), start=float(current_start), end=float(current_end)))
            current_chars = []
            current_start = None
            current_end = None
            continue
        current_chars.append(char)
        current_start = float(start) if current_start is None else current_start
        current_end = float(end)

    if current_chars and current_start is not None and current_end is not None:
        timings.append(WordTiming(text="".join(current_chars), start=current_start, end=current_end))
    return timings


def word_timings_from_forced_alignment(response: Any) -> list[WordTiming]:
    words = getattr(response, "words", None) or []
    timings: list[WordTiming] = []
    for word in words:
        text = getattr(word, "text", None)
        start = getattr(word, "start", None)
        end = getattr(word, "end", None)
        if text is None or start is None or end is None:
            continue
        timings.append(WordTiming(text=str(text), start=float(start), end=float(end)))
    if timings:
        return timings
    payload = dump_model(response)
    if isinstance(payload, dict):
        alignment = payload.get("normalized_alignment") or payload.get("alignment") or {}
        if isinstance(alignment, dict):
            return word_timings_from_alignment(alignment)
    return []
