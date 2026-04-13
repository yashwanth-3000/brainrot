from __future__ import annotations

import asyncio
import hashlib
import json
import logging
import re
import time
from contextlib import suppress
from datetime import datetime, timezone
from collections.abc import AsyncIterator
from typing import Any

import httpx

from brainrot_backend.config import Settings
from brainrot_backend.video_generator.integrations.elevenlabs import ElevenLabsAgentsClient
from brainrot_backend.video_generator.producer_crewai import CrewAIProducerFlow
from brainrot_backend.core.models.domain import (
    AgentConfigRecord,
    AgentConversationRecord,
    AgentRunRecord,
    AlignmentJobRecord,
    GeneratedBundle,
    IngestedSource,
    NarrationArtifact,
    ScriptDraft,
    ToolScriptBundlePayload,
)
from brainrot_backend.core.models.enums import AgentRole, BatchEventType
from brainrot_backend.video_generator.services.events import EventBroker
from brainrot_backend.core.storage.base import BlobStore, Repository

logger = logging.getLogger(__name__)
WORD_PATTERN = re.compile(r"[A-Za-z0-9]+(?:['-][A-Za-z0-9]+)*")
GENERIC_HOOK_STARTERS = (
    "meet ",
    "introducing ",
    "say hello to ",
    "what if ",
    "ready for ",
    "tired of ",
    "step into the future ",
)
SCRIPT_IDENTITY_PATTERNS = (
    {
        "id": "step-first",
        "hook": "{short_fact} is the step to watch first",
        "opening": "{fact} is the step to watch first.",
    },
    {
        "id": "constraint-angle",
        "hook": "{short_fact} is the constraint shaping the workflow",
        "opening": "{fact} is the constraint shaping the workflow.",
    },
    {
        "id": "workflow-edge",
        "hook": "{short_fact} is the handoff worth tracking",
        "opening": "{fact} is the handoff worth tracking.",
    },
    {
        "id": "proof-angle",
        "hook": "{short_fact} is the clearest proof point in the source",
        "opening": "{fact} is the clearest proof point in the source.",
    },
    {
        "id": "bottleneck-angle",
        "hook": "{short_fact} is the bottleneck to watch",
        "opening": "{fact} is the bottleneck to watch.",
    },
    {
        "id": "proof-to-practice",
        "hook": "{short_fact} is where the source gets specific",
        "opening": "{fact} is where the source gets specific.",
    },
    {
        "id": "creator-frame",
        "hook": "{short_fact} is the creator-facing change to notice",
        "opening": "{fact} is the creator-facing change to notice.",
    },
)
GENERIC_MARKETING_PHRASES = (
    "revolutionary",
    "ultimate solution",
    "powerful tool",
    "innovative add-on",
    "ai-powered sidekick",
    "step into the future",
    "future of content creation",
    "empowers your creativity",
    "forget generic outputs",
)
GENERIC_CANNED_HOOK_PHRASES = (
    "start with this detail",
    "watch this part first",
    "the strongest signal",
    "the fastest win here",
    "most people miss this part",
    "detail that changes the story",
    "part most people glide past",
    "move that saves the most time",
    "result falls apart",
    "flow gets weaker",
    "makes this feel ready for real use",
    "creators will care about",
)
SCHEMA_LEAK_TOKENS = {
    "qa_notes",
    "visual_beats",
    "gameplay_tags",
    "music_tags",
    "caption_text",
    "estimated_seconds",
    "narration_text",
    "source_facts_used",
    "title",
    "hook",
}
HOOK_STOPWORDS = {
    "a",
    "an",
    "and",
    "are",
    "for",
    "has",
    "have",
    "here",
    "into",
    "is",
    "it",
    "its",
    "just",
    "made",
    "make",
    "more",
    "never",
    "of",
    "on",
    "or",
    "our",
    "say",
    "simpler",
    "streamline",
    "than",
    "that",
    "the",
    "their",
    "this",
    "to",
    "tool",
    "tools",
    "transform",
    "your",
}


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class AgentService:
    def __init__(
        self,
        *,
        settings: Settings,
        repository: Repository,
        blob_store: BlobStore,
        events: EventBroker,
        elevenlabs: ElevenLabsAgentsClient,
    ) -> None:
        self.settings = settings
        self.repository = repository
        self.blob_store = blob_store
        self.events = events
        self.elevenlabs = elevenlabs
        self._producer_waiters: dict[str, asyncio.Future[GeneratedBundle]] = {}
        self.crewai_producer = CrewAIProducerFlow(settings=settings)

    async def bootstrap_agents(self, public_base_url: str) -> tuple[list[AgentConfigRecord], list[str]]:
        include_producer = self.settings.producer_mode == "elevenlabs_native"
        include_narrator = self.settings.narration_mode == "elevenlabs_agent"
        if not include_producer and not include_narrator:
            return [], []

        configs, tool_ids = await self.elevenlabs.bootstrap_agents(
            public_base_url,
            include_producer=include_producer,
            include_narrator=include_narrator,
        )
        saved = [await self.repository.upsert_agent_config(config) for config in configs]
        return saved, tool_ids

    async def get_agent_config(
        self,
        *,
        role: AgentRole,
        requested_config_id: str | None = None,
    ) -> AgentConfigRecord:
        if requested_config_id:
            config = await self.repository.get_agent_config(requested_config_id)
            if config is None:
                raise RuntimeError(f"Agent config {requested_config_id} was not found.")
            if config.role != role:
                raise RuntimeError(f"Agent config {requested_config_id} is not a {role.value} config.")
            return config

        config = await self.repository.get_agent_config_by_role(role)
        if config is None:
            raise RuntimeError(
                f"No active {role.value} agent config exists. Bootstrap the ElevenLabs agents first."
            )
        return config

    async def run_producer(
        self,
        *,
        batch_id: str,
        source: IngestedSource,
        requested_count: int,
        requested_config_id: str | None,
        use_cached_bundle: bool = True,
        persist_bundle: bool = True,
        emit_ready_events: bool = True,
        producer_label: str | None = None,
    ) -> GeneratedBundle:
        config = None
        if self.settings.producer_mode == "elevenlabs_native":
            config = await self.get_agent_config(role=AgentRole.PRODUCER, requested_config_id=requested_config_id)
        label_suffix = f" ({producer_label})" if producer_label else ""
        run = await self.repository.create_agent_run(
            AgentRunRecord(
                batch_id=batch_id,
                role=AgentRole.PRODUCER,
                agent_config_id=config.id if config is not None else None,
                status="running",
                payload={
                    "requested_count": requested_count,
                    "source_title": source.title,
                    **({"producer_label": producer_label} if producer_label else {}),
                },
            )
        )
        await self.events.publish(
            batch_id,
            BatchEventType.PRODUCER_CONVERSATION_STARTED,
            {
                "agent_config_id": config.id if config is not None else None,
                "agent_id": config.agent_id if config is not None else None,
                "run_id": run.id,
                "mode": self.settings.producer_mode,
                "model": (
                    self.settings.openai_model
                    if self.settings.producer_mode == "direct_openai"
                    else (self.settings.producer_elevenlabs_model or "elevenlabs-default")
                ),
                **({"producer_label": producer_label} if producer_label else {}),
            },
        )
        await self._publish_log(
            batch_id,
            stage="producer",
            message=f"Producer started{label_suffix}.",
            elapsed_seconds=0.0,
            mode=self.settings.producer_mode,
            model=(
                self.settings.openai_model
                if self.settings.producer_mode == "direct_openai"
                else (self.settings.producer_elevenlabs_model or "elevenlabs-default")
            ),
            requested_count=requested_count,
            **({"source": producer_label} if producer_label else {}),
        )

        logger.info(
            "Running Producer for batch %s (config=%s, count=%d, mode=%s)",
            batch_id,
            config.id if config is not None else "direct-openai",
            requested_count,
            self.settings.producer_mode,
        )
        try:
            existing_bundle = await self.repository.get_generated_bundle(batch_id) if use_cached_bundle else None
            if existing_bundle is not None:
                await self.repository.update_agent_run(run.id, status="completed", updated_at=utc_now())
                if emit_ready_events:
                    await self.events.publish(
                        batch_id,
                        BatchEventType.SCRIPTS_READY,
                        {
                            "run_id": run.id,
                            "script_count": len(existing_bundle.scripts),
                            "angle_count": len(existing_bundle.angles),
                            "planned_count": existing_bundle.metadata.get("planned_count"),
                            "section_count": existing_bundle.metadata.get("section_count"),
                            "covered_sections": existing_bundle.metadata.get("covered_sections"),
                            "unused_sections": existing_bundle.metadata.get("unused_sections"),
                        },
                    )
                await self._publish_log(
                    batch_id,
                    stage="producer",
                    message=f"Using previously generated script bundle{label_suffix}.",
                    elapsed_seconds=0.0,
                    script_count=len(existing_bundle.scripts),
                    **({"source": producer_label} if producer_label else {}),
                )
                return existing_bundle

            bundle: GeneratedBundle | None = None
            last_error: str | None = None
            repair_count = 0
            attempt_count = 0
            used_repair = False
            conversation_id: str | None = None
            started_at = time.perf_counter()
            for attempt in range(1, 4):
                attempt_count = attempt
                await self._publish_log(
                    batch_id,
                    stage="producer",
                    message=f"Producer attempt {attempt}/3 started{label_suffix}.",
                    attempt=attempt,
                    elapsed_seconds=round(time.perf_counter() - started_at, 1),
                    mode=self.settings.producer_mode,
                    **({"source": producer_label} if producer_label else {}),
                )
                try:
                    bundle, conversation_id = await self._generate_producer_bundle(
                        batch_id=batch_id,
                        config=config,
                        source=source,
                        requested_count=requested_count,
                        validation_feedback=last_error,
                        attempt_number=attempt,
                        producer_started_at=started_at,
                    )
                except Exception as generation_exc:
                    last_error = str(generation_exc)
                    logger.warning(
                        "Producer request failed for batch %s on attempt %d/3: %s",
                        batch_id, attempt, generation_exc,
                    )
                    await self._publish_log(
                        batch_id,
                        stage="producer",
                        message=f"Producer request failed on attempt {attempt}/3{label_suffix}. Retrying.",
                        attempt=attempt,
                        elapsed_seconds=round(time.perf_counter() - started_at, 1),
                        error=_truncate_log_text(last_error),
                        mode=self.settings.producer_mode,
                        **({"source": producer_label} if producer_label else {}),
                    )
                    if attempt == 3:
                        raise RuntimeError(last_error) from generation_exc
                    continue
                bundle, normalization = self._normalize_generated_bundle(bundle)
                if (
                    normalization["title_repairs"]
                    or normalization["hook_repairs"]
                    or normalization["fact_repairs"]
                    or normalization["narration_repairs"]
                ):
                    await self._publish_log(
                        batch_id,
                        stage="producer",
                        message=f"Applied local script fixes after attempt {attempt}/3{label_suffix}.",
                        attempt=attempt,
                        elapsed_seconds=round(time.perf_counter() - started_at, 1),
                        mode=self.settings.producer_mode,
                        title_repairs=normalization["title_repairs"],
                        hook_repairs=normalization["hook_repairs"],
                        fact_repairs=normalization["fact_repairs"],
                        narration_repairs=normalization["narration_repairs"],
                        **({"source": producer_label} if producer_label else {}),
                    )
                try:
                    self._validate_generated_bundle(bundle, requested_count=requested_count)
                    await self._publish_log(
                        batch_id,
                        stage="producer",
                        message=f"Producer validation passed on attempt {attempt}/3{label_suffix}.",
                        attempt=attempt,
                        elapsed_seconds=round(time.perf_counter() - started_at, 1),
                        mode=self.settings.producer_mode,
                        script_count=len(bundle.scripts),
                        **({"source": producer_label} if producer_label else {}),
                    )
                    break
                except RuntimeError as exc:
                    last_error = str(exc)
                    logger.warning(
                        "Producer validation failed for batch %s on attempt %d/3: %s",
                        batch_id, attempt, exc,
                    )
                    await self._publish_log(
                        batch_id,
                        stage="producer",
                        message=f"Validation failed on attempt {attempt}/3{label_suffix}. Starting repair.",
                        attempt=attempt,
                        elapsed_seconds=round(time.perf_counter() - started_at, 1),
                        mode=self.settings.producer_mode,
                        validation_summary=_truncate_log_text(last_error),
                        **({"source": producer_label} if producer_label else {}),
                    )
                    if self.settings.producer_mode != "elevenlabs_native":
                        if attempt == 3:
                            raise RuntimeError(last_error) from exc
                        await self._publish_log(
                            batch_id,
                            stage="producer",
                            message=f"CrewAI producer is restarting attempt {attempt + 1}/3 after QA rejection{label_suffix}.",
                            attempt=attempt + 1,
                            elapsed_seconds=round(time.perf_counter() - started_at, 1),
                            mode=self.settings.producer_mode,
                            validation_summary=_truncate_log_text(last_error),
                            **({"source": producer_label} if producer_label else {}),
                        )
                        continue
                    try:
                        repaired_bundle = await self._repair_generated_bundle(
                            batch_id=batch_id,
                            source=source,
                            bundle=bundle,
                            requested_count=requested_count,
                            validation_feedback=last_error,
                            attempt_number=attempt,
                            producer_started_at=started_at,
                        )
                        repaired_bundle, repair_normalization = self._normalize_generated_bundle(repaired_bundle)
                        if (
                            repair_normalization["title_repairs"]
                            or repair_normalization["hook_repairs"]
                            or repair_normalization["fact_repairs"]
                            or repair_normalization["narration_repairs"]
                        ):
                            await self._publish_log(
                                batch_id,
                                stage="producer",
                                message=f"Applied local script fixes after repair {attempt}/3{label_suffix}.",
                                attempt=attempt,
                                elapsed_seconds=round(time.perf_counter() - started_at, 1),
                                mode=self.settings.producer_mode,
                                title_repairs=repair_normalization["title_repairs"],
                                hook_repairs=repair_normalization["hook_repairs"],
                                fact_repairs=repair_normalization["fact_repairs"],
                                narration_repairs=repair_normalization["narration_repairs"],
                                **({"source": producer_label} if producer_label else {}),
                            )
                        self._validate_generated_bundle(repaired_bundle, requested_count=requested_count)
                        bundle = repaired_bundle
                        repair_count += 1
                        used_repair = True
                        logger.info("Producer repair succeeded for batch %s on attempt %d/3", batch_id, attempt)
                        await self._publish_log(
                            batch_id,
                            stage="producer",
                            message=f"Repair succeeded on attempt {attempt}/3{label_suffix}.",
                            attempt=attempt,
                            repair_count=repair_count,
                            elapsed_seconds=round(time.perf_counter() - started_at, 1),
                            mode=self.settings.producer_mode,
                            **({"source": producer_label} if producer_label else {}),
                        )
                        break
                    except Exception as repair_exc:
                        last_error = str(repair_exc)
                        repair_count += 1
                        logger.warning(
                            "Producer repair failed for batch %s on attempt %d/3: %s",
                            batch_id, attempt, repair_exc,
                        )
                        await self._publish_log(
                            batch_id,
                            stage="producer",
                            message=f"Repair failed on attempt {attempt}/3{label_suffix}.",
                            attempt=attempt,
                            repair_count=repair_count,
                            elapsed_seconds=round(time.perf_counter() - started_at, 1),
                            error=_truncate_log_text(last_error),
                            mode=self.settings.producer_mode,
                            **({"source": producer_label} if producer_label else {}),
                        )
                        if attempt == 3:
                            raise RuntimeError(last_error) from repair_exc
            assert bundle is not None
            elapsed_seconds = round(time.perf_counter() - started_at, 2)
            producer_metrics: dict[str, Any] = {
                "mode": self.settings.producer_mode,
                "final_bundle_source": "repair_openai" if used_repair else "crewai_openai",
                "attempt_count": attempt_count,
                "repair_count": repair_count,
                "elapsed_seconds": elapsed_seconds,
                "planned_count": bundle.metadata.get("planned_count"),
                "section_count": bundle.metadata.get("section_count"),
            }
            if conversation_id:
                producer_metrics["conversation_id"] = conversation_id
            if persist_bundle:
                await self.repository.save_generated_bundle(batch_id, bundle)
                batch = await self.repository.get_batch(batch_id)
                if batch is not None:
                    metadata = dict(batch.metadata)
                    metadata["producer_metrics"] = producer_metrics
                    await self.repository.update_batch(batch_id, metadata=metadata, updated_at=utc_now())
            if emit_ready_events:
                await self.events.publish(
                    batch_id,
                    BatchEventType.PRODUCER_TOOL_CALLED,
                    {
                        "batch_id": batch_id,
                        "script_count": len(bundle.scripts),
                        "angle_count": len(bundle.angles),
                        "mode": self.settings.producer_mode,
                        "planned_count": bundle.metadata.get("planned_count"),
                        "section_count": bundle.metadata.get("section_count"),
                        "covered_sections": bundle.metadata.get("covered_sections"),
                        "unused_sections": bundle.metadata.get("unused_sections"),
                        **({"producer_label": producer_label} if producer_label else {}),
                    },
                )
            await self.repository.update_agent_run(
                run.id, status="completed",
                conversation_id=conversation_id,
                metadata={
                        "method": self.settings.producer_mode,
                        "agent_config_id": config.id if config is not None else None,
                        "attempt_count": attempt_count,
                    "repair_count": repair_count,
                    "elapsed_seconds": elapsed_seconds,
                    "final_bundle_source": producer_metrics["final_bundle_source"],
                    **({"conversation_id": conversation_id} if conversation_id else {}),
                    **({"producer_label": producer_label} if producer_label else {}),
                },
                updated_at=utc_now(),
            )
            if emit_ready_events:
                await self.events.publish(
                    batch_id,
                    BatchEventType.SCRIPTS_READY,
                    {
                        "run_id": run.id,
                        "script_count": len(bundle.scripts),
                        "angle_count": len(bundle.angles),
                        **producer_metrics,
                        "covered_sections": bundle.metadata.get("covered_sections"),
                        "unused_sections": bundle.metadata.get("unused_sections"),
                        **({"producer_label": producer_label} if producer_label else {}),
                    },
                )
            await self._publish_log(
                batch_id,
                stage="producer",
                message=f"Producer finished and scripts are ready{label_suffix}.",
                elapsed_seconds=elapsed_seconds,
                attempt_count=attempt_count,
                repair_count=repair_count,
                script_count=len(bundle.scripts),
                mode=self.settings.producer_mode,
                planned_count=bundle.metadata.get("planned_count"),
                section_count=bundle.metadata.get("section_count"),
                **({"source": producer_label} if producer_label else {}),
            )
            return bundle
        except Exception as exc:
            logger.error("Producer failed for batch %s: %s", batch_id, exc, exc_info=True)
            await self.repository.update_agent_run(run.id, status="failed", error=str(exc), updated_at=utc_now())
            await self._publish_log(
                batch_id,
                stage="producer",
                message=f"Producer failed{label_suffix}.",
                error=_truncate_log_text(str(exc)),
                mode=self.settings.producer_mode,
                **({"source": producer_label} if producer_label else {}),
            )
            raise

    async def _generate_producer_bundle(
        self,
        *,
        batch_id: str,
        config: AgentConfigRecord | None,
        source: IngestedSource,
        requested_count: int,
        validation_feedback: str | None = None,
        attempt_number: int,
        producer_started_at: float,
    ) -> tuple[GeneratedBundle, str | None]:
        if self.settings.producer_mode == "elevenlabs_native":
            if config is None:
                raise RuntimeError("Producer agent config is required for elevenlabs_native producer mode.")
            return await self._run_producer_native(
                batch_id=batch_id,
                config=config,
                source=source,
                requested_count=requested_count,
            )
        async def publish_producer_event(event_type: BatchEventType, payload: dict[str, object]) -> None:
            await self.events.publish(
                batch_id,
                event_type,
                {
                    **payload,
                    "mode": self.settings.producer_mode,
                    "model": self.settings.openai_model,
                },
            )

        async def publish_producer_log(batch_id: str, *, stage: str, message: str, **payload: object) -> None:
            await self._publish_log(
                batch_id,
                stage=stage,
                message=message,
                mode=self.settings.producer_mode,
                model=self.settings.openai_model,
                **payload,
            )

        bundle = await self.crewai_producer.generate_bundle(
            batch_id=batch_id,
            source=source,
            requested_count=requested_count,
            publish_event=publish_producer_event,
            publish_log=publish_producer_log,
        )
        return bundle, None

    async def _run_producer_native(
        self,
        *,
        batch_id: str,
        config: AgentConfigRecord,
        source: IngestedSource,
        requested_count: int,
    ) -> tuple[GeneratedBundle, str | None]:
        loop = asyncio.get_running_loop()
        bundle_ready: asyncio.Future[GeneratedBundle] = loop.create_future()
        self._producer_waiters[batch_id] = bundle_ready
        conversation = None
        try:
            logger.info("Calling ElevenLabs native Producer for batch %s", batch_id)
            conversation = await self.elevenlabs.run_producer_conversation(
                agent_config=config,
                batch_id=batch_id,
                source=source,
                requested_count=requested_count,
                timeout_seconds=self.settings.producer_timeout_seconds,
                bundle_ready=bundle_ready,
            )
            if not bundle_ready.done():
                raise RuntimeError(f"Producer conversation completed without returning a bundle for batch {batch_id}.")
            return bundle_ready.result(), getattr(conversation, "conversation_id", None)
        finally:
            current = self._producer_waiters.get(batch_id)
            if current is bundle_ready:
                self._producer_waiters.pop(batch_id, None)

    async def _run_producer_direct(
        self,
        *,
        batch_id: str,
        source: IngestedSource,
        requested_count: int,
        validation_feedback: str | None = None,
        attempt_number: int,
        producer_started_at: float,
    ) -> GeneratedBundle:
        from brainrot_backend.video_generator.integrations.elevenlabs import (
            build_producer_dynamic_variables,
            producer_prompt,
        )

        if not self.settings.openai_api_key:
            raise RuntimeError("OpenAI API key is not configured.")

        dyn = build_producer_dynamic_variables(
            settings=self.settings,
            batch_id=batch_id,
            source=source,
            requested_count=requested_count,
        )
        system_prompt = producer_prompt()
        for key, value in dyn.items():
            system_prompt = system_prompt.replace(f"{{{{{key}}}}}", value)

        user_prompt_parts = [f"Source title: {source.title}"]
        if dyn["source_summary"]:
            user_prompt_parts.append(f"Source summary:\n{dyn['source_summary']}")
        user_prompt_parts.append(f"Source content:\n{dyn['source_markdown']}")
        user_prompt_parts.append(
            "Generate exactly "
            f"{requested_count} distinct reel scripts and call submit_script_bundle. "
            f"IMPORTANT: Each narration_text MUST be {self.settings.script_min_words}-"
            f"{self.settings.script_max_words} words long for "
            f"{self.settings.script_target_min_seconds:g}-{self.settings.script_target_max_seconds:g} second videos. "
            f"Each narration_text should also be at least {self.settings.script_min_characters} characters long so the read does not end too fast. "
            "Short or duplicate scripts will be rejected. "
            "Every script must include at least two concrete source details such as feature names, "
            "platform names, workflow steps, numeric constraints, or architecture specifics taken from the source. "
            "Every hook must mention a concrete detail that also appears in source_facts_used. "
            "Across one batch, do not reuse the same opening sentence frame. Make each first line distinct by anchoring it to a different concrete fact, step, limit, failure mode, or proof point from the source. "
            "Do not use reusable lead-ins like 'Start with this detail', 'The fastest win here', 'Most people miss this part', or 'If this gets skipped, the workflow falls apart'. "
            "Do not write generic ad copy, rhetorical-question hooks, or filler phrases like "
            "'revolutionary', 'ultimate solution', or 'step into the future'."
        )
        if validation_feedback:
            user_prompt_parts.append(
                "The previous attempt failed validation. Return a corrected full bundle only.\n"
                f"Validation errors:\n{validation_feedback}"
            )

        tool_schema = {
            "type": "function",
            "function": {
                "name": "submit_script_bundle",
                "description": "Submit the final source brief, angle plan, and reel scripts.",
                "parameters": {
                    "type": "object",
                    "required": ["batch_id", "source_brief", "angles", "scripts"],
                    "properties": {
                        "batch_id": {"type": "string"},
                        "source_brief": {
                            "type": "object",
                            "required": ["canonical_title", "summary", "facts", "entities", "tone", "do_not_drift", "source_urls"],
                            "properties": {
                                "canonical_title": {"type": "string"},
                                "summary": {"type": "string"},
                                "facts": {"type": "array", "items": {"type": "string"}},
                                "entities": {"type": "array", "items": {"type": "string"}},
                                "tone": {"type": "string"},
                                "do_not_drift": {"type": "array", "items": {"type": "string"}},
                                "source_urls": {"type": "array", "items": {"type": "string"}},
                            },
                        },
                        "angles": {
                            "type": "array",
                            "items": {
                                "type": "object",
                                "required": ["title", "hook_direction", "audience_frame", "energy_level", "visual_mood", "music_mood"],
                                "properties": {
                                    "title": {"type": "string"},
                                    "hook_direction": {"type": "string"},
                                    "audience_frame": {"type": "string"},
                                    "energy_level": {"type": "string"},
                                    "visual_mood": {"type": "string"},
                                    "music_mood": {"type": "string"},
                                },
                            },
                        },
                        "scripts": {
                            "type": "array",
                            "items": {
                                "type": "object",
                                "required": ["title", "hook", "narration_text", "caption_text", "estimated_seconds", "visual_beats", "music_tags", "gameplay_tags", "source_facts_used", "qa_notes"],
                                "properties": {
                                    "title": {"type": "string"},
                                    "hook": {"type": "string"},
                                    "narration_text": {"type": "string"},
                                    "caption_text": {"type": "string"},
                                    "estimated_seconds": {"type": "number"},
                                    "visual_beats": {"type": "array", "items": {"type": "string"}},
                                    "music_tags": {"type": "array", "items": {"type": "string"}},
                                    "gameplay_tags": {"type": "array", "items": {"type": "string"}},
                                    "source_facts_used": {"type": "array", "items": {"type": "string"}},
                                    "qa_notes": {"type": "array", "items": {"type": "string"}},
                                },
                            },
                        },
                    },
                },
            },
        }

        logger.info("Calling OpenAI directly for Producer (model=%s, batch=%s)", self.settings.openai_model, batch_id)
        direct_started_at = time.perf_counter()
        await self._publish_log(
            batch_id,
            stage="producer",
            message=f"OpenAI request started for producer attempt {attempt_number}/3.",
            elapsed_seconds=0.0,
            total_elapsed_seconds=round(time.perf_counter() - producer_started_at, 1),
            model=self.settings.openai_model,
            attempt=attempt_number,
            mode=self.settings.producer_mode,
        )
        async with httpx.AsyncClient(timeout=httpx.Timeout(180.0, connect=10.0)) as client:
            response = await self._await_with_heartbeat(
                client.post(
                    f"{self.settings.openai_base_url.rstrip('/')}/chat/completions",
                    headers={
                        "Authorization": f"Bearer {self.settings.openai_api_key}",
                        "Content-Type": "application/json",
                    },
                    json={
                        "model": self.settings.openai_model,
                        "temperature": 0.2,
                        "max_tokens": 16384,
                        "messages": [
                            {"role": "system", "content": system_prompt},
                            {
                                "role": "user",
                                "content": "\n\n".join(user_prompt_parts),
                            },
                        ],
                        "tools": [tool_schema],
                        "tool_choice": {"type": "function", "function": {"name": "submit_script_bundle"}},
                    },
                ),
                batch_id=batch_id,
                stage="producer",
                waiting_message=f"Waiting for OpenAI producer response on attempt {attempt_number}/3.",
                started_at=direct_started_at,
                total_started_at=producer_started_at,
                attempt=attempt_number,
                model=self.settings.openai_model,
            )
            response.raise_for_status()
            data = response.json()
        await self._publish_log(
            batch_id,
            stage="producer",
            message=f"OpenAI producer response received for attempt {attempt_number}/3.",
            elapsed_seconds=round(time.perf_counter() - direct_started_at, 1),
            total_elapsed_seconds=round(time.perf_counter() - producer_started_at, 1),
            attempt=attempt_number,
            mode=self.settings.producer_mode,
        )

        choices = data.get("choices", [])
        if not choices:
            raise RuntimeError("OpenAI returned no choices for Producer.")

        message = choices[0].get("message", {})
        tool_calls = message.get("tool_calls", [])
        if not tool_calls:
            raise RuntimeError(
                f"Producer LLM did not call submit_script_bundle. Response: {message.get('content', '')[:200]}"
            )

        arguments_str = tool_calls[0].get("function", {}).get("arguments", "{}")
        logger.info("Producer tool call received (%d chars)", len(arguments_str))
        await self._publish_log(
            batch_id,
            stage="producer",
            message="Producer submitted script bundle. Validating scripts now.",
            elapsed_seconds=round(time.perf_counter() - direct_started_at, 1),
            total_elapsed_seconds=round(time.perf_counter() - producer_started_at, 1),
            attempt=attempt_number,
            mode=self.settings.producer_mode,
        )
        raw_payload = json.loads(arguments_str)
        raw_payload["batch_id"] = batch_id

        payload = ToolScriptBundlePayload.model_validate(raw_payload)
        if not payload.source_brief.source_urls:
            payload.source_brief.source_urls = source.normalized_urls or ([source.original_url] if source.original_url else [])
        return GeneratedBundle(
            source_brief=payload.source_brief,
            angles=payload.angles,
            scripts=payload.scripts,
        )

    def _validate_generated_bundle(self, bundle: GeneratedBundle, *, requested_count: int) -> None:
        errors: list[str] = []
        if len(bundle.scripts) != requested_count:
            errors.append(f"expected exactly {requested_count} scripts but received {len(bundle.scripts)}")
        if len(bundle.angles) < requested_count:
            errors.append(f"expected at least {requested_count} angles but received {len(bundle.angles)}")

        seen_titles: set[str] = set()
        seen_hooks: set[str] = set()
        seen_opening_signatures: set[str] = set()
        seen_angle_families: set[str] = set()
        seen_section_ids: set[str] = set()
        seen_primary_fact_clusters: set[str] = set()
        product_name_first_openings = 0
        canonical_title_key = _normalize_script_text(bundle.source_brief.canonical_title)
        for index, script in enumerate(bundle.scripts, start=1):
            word_count = _count_words(script.narration_text)
            if not self.settings.script_min_words <= word_count <= self.settings.script_max_words:
                errors.append(
                    f"script {index} has {word_count} words; required range is "
                    f"{self.settings.script_min_words}-{self.settings.script_max_words}"
                )
            char_count = len(script.narration_text)
            if char_count < self.settings.script_min_characters:
                errors.append(
                    f"script {index} has {char_count} characters; required minimum is "
                    f"{self.settings.script_min_characters}"
                )

            script.estimated_seconds = _estimate_narration_seconds(
                word_count,
                min_seconds=self.settings.script_target_min_seconds,
                max_seconds=self.settings.script_target_max_seconds,
            )

            title_key = script.title.strip().casefold()
            hook_key = script.hook.strip().casefold()
            if title_key in seen_titles:
                errors.append(f"script {index} reuses a duplicate title")
            if hook_key in seen_hooks:
                errors.append(f"script {index} reuses a duplicate hook")
            seen_titles.add(title_key)
            seen_hooks.add(hook_key)

            opening_signature = _opening_signature(script.narration_text)
            if opening_signature in seen_opening_signatures:
                errors.append(f"script {index} reuses an opening sentence pattern")
            if opening_signature:
                seen_opening_signatures.add(opening_signature)
            if canonical_title_key and opening_signature == _opening_signature(bundle.source_brief.canonical_title):
                product_name_first_openings += 1

            if not script.caption_text.strip():
                errors.append(f"script {index} is missing caption_text")
            if not script.source_facts_used:
                errors.append(f"script {index} is missing source_facts_used")
            quality_issues = _script_quality_issues(script)
            errors.extend(f"script {index} {issue}" for issue in quality_issues)

            angle_family = script.metadata.get("angle_family") if isinstance(script.metadata, dict) else None
            if isinstance(angle_family, str) and angle_family:
                if angle_family in seen_angle_families:
                    errors.append(f"script {index} reuses an angle_family")
                seen_angle_families.add(angle_family)

            section_ids = script.metadata.get("section_ids") if isinstance(script.metadata, dict) else None
            if isinstance(section_ids, list) and section_ids:
                primary_section_id = str(section_ids[0])
                if primary_section_id in seen_section_ids:
                    errors.append(f"script {index} reuses a section cluster")
                seen_section_ids.add(primary_section_id)

            primary_fact = _normalize_script_text(script.source_facts_used[0]) if script.source_facts_used else ""
            if primary_fact:
                if primary_fact in seen_primary_fact_clusters:
                    errors.append(f"script {index} reuses a primary fact cluster")
                seen_primary_fact_clusters.add(primary_fact)

        if product_name_first_openings > 1:
            errors.append("more than one script starts with a product-name-first opening")

        if errors:
            raise RuntimeError("; ".join(errors))

    async def _repair_generated_bundle(
        self,
        *,
        batch_id: str,
        source: IngestedSource,
        bundle: GeneratedBundle,
        requested_count: int,
        validation_feedback: str,
        attempt_number: int,
        producer_started_at: float,
    ) -> GeneratedBundle:
        if not self.settings.openai_api_key:
            raise RuntimeError("OpenAI API key is not configured.")

        tool_schema = {
            "type": "function",
            "function": {
                "name": "submit_repaired_scripts",
                "description": "Return a corrected set of reel scripts that satisfy the validation rules.",
                "parameters": {
                    "type": "object",
                    "required": ["scripts"],
                    "properties": {
                        "scripts": {
                            "type": "array",
                            "items": {
                                "type": "object",
                                "required": [
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
                                "properties": {
                                    "title": {"type": "string"},
                                    "hook": {"type": "string"},
                                    "narration_text": {"type": "string"},
                                    "caption_text": {"type": "string"},
                                    "estimated_seconds": {"type": "number"},
                                    "visual_beats": {"type": "array", "items": {"type": "string"}},
                                    "music_tags": {"type": "array", "items": {"type": "string"}},
                                    "gameplay_tags": {"type": "array", "items": {"type": "string"}},
                                    "source_facts_used": {"type": "array", "items": {"type": "string"}},
                                    "qa_notes": {"type": "array", "items": {"type": "string"}},
                                },
                            },
                        }
                    },
                },
            },
        }
        target_min_words = min(self.settings.script_max_words, self.settings.script_min_words + 5)
        target_max_words = max(self.settings.script_min_words, self.settings.script_max_words - 5)
        existing_scripts_json = json.dumps(
            [script.model_dump(mode="json") for script in bundle.scripts],
            ensure_ascii=False,
            indent=2,
        )
        source_summary = str(
            source.metadata.get("source_summary")
            or source.metadata.get("summary")
            or source.metadata.get("description")
            or ""
        ).strip()

        repair_started_at = time.perf_counter()
        await self._publish_log(
            batch_id,
            stage="producer",
            message=f"Repair request started for attempt {attempt_number}/3.",
            elapsed_seconds=0.0,
            total_elapsed_seconds=round(time.perf_counter() - producer_started_at, 1),
            attempt=attempt_number,
            mode=self.settings.producer_mode,
            validation_summary=_truncate_log_text(validation_feedback),
        )

        async with httpx.AsyncClient(timeout=httpx.Timeout(180.0, connect=10.0)) as client:
            response = await self._await_with_heartbeat(
                client.post(
                    f"{self.settings.openai_base_url.rstrip('/')}/chat/completions",
                    headers={
                        "Authorization": f"Bearer {self.settings.openai_api_key}",
                        "Content-Type": "application/json",
                    },
                    json={
                        "model": self.settings.openai_model,
                        "temperature": 0.2,
                        "max_tokens": 16384,
                        "messages": [
                            {
                                "role": "system",
                                "content": (
                                    "You repair short-form narration scripts for a video backend. "
                                    "Keep them faithful to the source and return only corrected scripts via the tool call. "
                                    "Do not write generic startup ad copy, rhetorical-question hooks, or empty hype."
                                ),
                            },
                            {
                                "role": "user",
                                "content": (
                                    f"Source title: {source.title}\n\n"
                                    f"Source summary: {source_summary or 'N/A'}\n\n"
                                    f"Source content:\n{source.markdown[: self.settings.producer_source_char_limit]}\n\n"
                                    f"Validation errors:\n{validation_feedback}\n\n"
                                    f"Current scripts JSON:\n{existing_scripts_json}\n\n"
                                    f"Rewrite all {requested_count} scripts so every narration_text lands between "
                                    f"{target_min_words} and {target_max_words} words. "
                                    f"Each narration_text should also be at least {self.settings.script_min_characters} characters long. "
                                    "Preserve the core angle of each script, but add source-grounded detail so the pacing fits a 25-30 second video. "
                                    "Each repaired script must include at least two concrete details lifted from the source "
                                    "such as feature names, platform names, workflow steps, numeric constraints, or architecture notes. "
                                    "Every hook must mention a concrete source detail that also appears in source_facts_used. "
                                    "Do not let multiple scripts reuse the same opening sentence frame. Make the first line of each repaired script feel structurally distinct. "
                                    "Avoid generic hooks like 'Meet X', 'Introducing X', 'What if', 'Ready for', and hype words like "
                                    "'revolutionary', 'ultimate solution', or 'powerful tool'. "
                                    "Keep source_facts_used clean, human-readable, and limited to actual facts instead of leaking field names. "
                                    "Return all corrected scripts, not just the broken ones."
                                ),
                            },
                        ],
                        "tools": [tool_schema],
                        "tool_choice": {"type": "function", "function": {"name": "submit_repaired_scripts"}},
                    },
                ),
                batch_id=batch_id,
                stage="producer",
                waiting_message=f"Waiting for producer repair response on attempt {attempt_number}/3.",
                started_at=repair_started_at,
                total_started_at=producer_started_at,
                attempt=attempt_number,
                mode=self.settings.producer_mode,
            )
            response.raise_for_status()
            data = response.json()
        await self._publish_log(
            batch_id,
            stage="producer",
            message=f"Repair response received for attempt {attempt_number}/3.",
            elapsed_seconds=round(time.perf_counter() - repair_started_at, 1),
            total_elapsed_seconds=round(time.perf_counter() - producer_started_at, 1),
            attempt=attempt_number,
            mode=self.settings.producer_mode,
        )

        choices = data.get("choices", [])
        if not choices:
            raise RuntimeError("OpenAI returned no choices while repairing producer scripts.")

        message = choices[0].get("message", {})
        tool_calls = message.get("tool_calls", [])
        if not tool_calls:
            raise RuntimeError(
                f"Producer repair did not call submit_repaired_scripts. Response: {message.get('content', '')[:200]}"
            )

        arguments_str = tool_calls[0].get("function", {}).get("arguments", "{}")
        repaired_payload = json.loads(arguments_str)
        repaired_scripts = [ScriptDraft.model_validate(script) for script in repaired_payload.get("scripts", [])]
        return GeneratedBundle(
            source_brief=bundle.source_brief,
            angles=bundle.angles,
            scripts=repaired_scripts,
        )

    def _normalize_generated_bundle(
        self,
        bundle: GeneratedBundle,
    ) -> tuple[GeneratedBundle, dict[str, int]]:
        source_facts = _clean_fact_list(bundle.source_brief.facts)
        normalized_scripts: list[ScriptDraft] = []
        title_repairs = 0
        hook_repairs = 0
        fact_repairs = 0
        narration_repairs = 0

        for index, script in enumerate(bundle.scripts):
            cleaned_facts = _normalize_script_facts(script.source_facts_used, source_facts)
            if cleaned_facts != script.source_facts_used:
                fact_repairs += 1

            normalized_title = _sanitize_title(script.title, cleaned_facts or source_facts)
            if normalized_title != script.title.strip():
                title_repairs += 1

            normalized_hook = script.hook.strip()
            if cleaned_facts and not _hook_mentions_source_fact(normalized_hook, cleaned_facts):
                grounded_hook = _build_grounded_hook(script, cleaned_facts)
                if grounded_hook and grounded_hook != normalized_hook:
                    normalized_hook = grounded_hook
                    hook_repairs += 1

            normalized_narration = _expand_narration_text(
                script.narration_text,
                facts=cleaned_facts or source_facts,
                summary=bundle.source_brief.summary,
                min_words=self.settings.script_min_words,
                min_characters=self.settings.script_min_characters,
            )
            if normalized_narration != script.narration_text:
                narration_repairs += 1

            normalized_script = script.model_copy(
                update={
                    "title": normalized_title,
                    "hook": normalized_hook,
                    "narration_text": normalized_narration,
                    "source_facts_used": cleaned_facts,
                }
            )

            normalized_scripts.append(normalized_script)

        return (
            bundle.model_copy(update={"scripts": normalized_scripts}),
            {
                "title_repairs": title_repairs,
                "hook_repairs": hook_repairs,
                "fact_repairs": fact_repairs,
                "narration_repairs": narration_repairs,
            },
        )

    async def submit_script_bundle(self, payload: ToolScriptBundlePayload) -> GeneratedBundle:
        bundle = GeneratedBundle(
            source_brief=payload.source_brief,
            angles=payload.angles,
            scripts=payload.scripts,
        )
        await self.repository.save_generated_bundle(payload.batch_id, bundle)
        await self.events.publish(
            payload.batch_id,
            BatchEventType.PRODUCER_TOOL_CALLED,
            {
                "batch_id": payload.batch_id,
                "script_count": len(payload.scripts),
                "angle_count": len(payload.angles),
            },
        )
        waiter = self._producer_waiters.get(payload.batch_id)
        if waiter is not None and not waiter.done():
            waiter.set_result(bundle)
        return bundle

    async def narrate_item(
        self,
        *,
        batch_id: str,
        batch_item_id: str,
        item_index: int,
        requested_count: int,
        script: ScriptDraft,
        premium_audio: bool,
        requested_config_id: str | None,
    ) -> NarrationArtifact:
        config = None
        if self.settings.narration_mode == "elevenlabs_agent":
            config = await self.get_agent_config(role=AgentRole.NARRATOR, requested_config_id=requested_config_id)
        voice_profile = await self.elevenlabs.select_narrator_voice(
            batch_id=batch_id,
            item_index=item_index,
            requested_count=requested_count,
        )
        run = await self.repository.create_agent_run(
            AgentRunRecord(
                batch_id=batch_id,
                batch_item_id=batch_item_id,
                role=AgentRole.NARRATOR,
                agent_config_id=config.id if config is not None else None,
                status="running",
                payload={"title": script.title},
            )
        )
        await self.events.publish(
            batch_id,
            BatchEventType.NARRATOR_CONVERSATION_STARTED,
            {
                "item_id": batch_item_id,
                "run_id": run.id,
                "agent_config_id": config.id if config is not None else None,
                "agent_id": config.agent_id if config is not None else None,
                "mode": self.settings.narration_mode,
                "voice_id": voice_profile.voice_id if voice_profile else None,
                "voice_label": voice_profile.label if voice_profile else None,
            },
        )

        try:
            logger.info(
                "Narrating item %s for batch %s (mode=%s, config=%s)",
                batch_item_id,
                batch_id,
                self.settings.narration_mode,
                config.id if config is not None else "direct-tts",
            )
            narration_started_at = time.perf_counter()

            async def run_narration_with_voice(
                *,
                selected_voice_id: str | None,
                selected_voice_label: str | None,
            ) -> tuple[NarrationArtifact, AgentConversationRecord | None]:
                if self.settings.narration_mode == "elevenlabs_agent":
                    if config is None:
                        raise RuntimeError("Narrator agent config is required for elevenlabs_agent mode.")
                    return await self._await_with_heartbeat(
                        self.elevenlabs.narrate_script(
                            agent_config=config,
                            batch_id=batch_id,
                            batch_item_id=batch_item_id,
                            script=script,
                            premium_audio=premium_audio,
                            timeout_seconds=self.settings.narrator_timeout_seconds,
                            idle_seconds=self.settings.conversation_idle_seconds,
                            min_speech_seconds=self.settings.narrator_min_speech_seconds,
                            voice_id=selected_voice_id,
                            voice_label=selected_voice_label,
                        ),
                        batch_id=batch_id,
                        stage="narration",
                        waiting_message=f"Waiting for ElevenLabs narration audio for item {batch_item_id}.",
                        started_at=narration_started_at,
                        item_id=batch_item_id,
                        voice_label=selected_voice_label,
                    )

                artifact = await self._await_with_heartbeat(
                    self.elevenlabs.narrate_script_tts(
                        batch_id=batch_id,
                        batch_item_id=batch_item_id,
                        script=script,
                        voice_id=selected_voice_id,
                        voice_label=selected_voice_label,
                    ),
                    batch_id=batch_id,
                    stage="narration",
                    waiting_message=f"Waiting for ElevenLabs TTS audio for item {batch_item_id}.",
                    started_at=narration_started_at,
                    item_id=batch_item_id,
                    voice_label=selected_voice_label,
                )
                return artifact, None

            await self._publish_log(
                batch_id,
                stage="narration",
                message=f"Narration started for item {batch_item_id}.",
                item_id=batch_item_id,
                elapsed_seconds=0.0,
                premium_audio=premium_audio,
                voice_label=voice_profile.label if voice_profile else None,
            )
            try:
                artifact, conversation = await run_narration_with_voice(
                    selected_voice_id=voice_profile.voice_id if voice_profile else None,
                    selected_voice_label=voice_profile.label if voice_profile else None,
                )
            except Exception as exc:
                should_fallback = (
                    voice_profile is not None
                    and self.settings.default_elevenlabs_voice_id
                    and voice_profile.voice_id != self.settings.default_elevenlabs_voice_id
                    and any(marker in str(exc).lower() for marker in ("invalid_audio", "corrupted", "audio"))
                )
                if not should_fallback:
                    raise
                logger.warning(
                    "Narration failed for item %s with voice %s; retrying default voice: %s",
                    batch_item_id,
                    voice_profile.label,
                    exc,
                )
                await self._publish_log(
                    batch_id,
                    stage="narration",
                    message=f"Retrying narration for item {batch_item_id} with the default voice.",
                    item_id=batch_item_id,
                    elapsed_seconds=round(time.perf_counter() - narration_started_at, 1),
                    error=_truncate_log_text(str(exc)),
                    voice_label="Default narrator voice",
                )
                artifact, conversation = await run_narration_with_voice(
                    selected_voice_id=self.settings.default_elevenlabs_voice_id,
                    selected_voice_label="Default narrator voice",
                )
            await self._publish_log(
                batch_id,
                stage="narration",
                message=f"Narration audio received for item {batch_item_id}.",
                item_id=batch_item_id,
                elapsed_seconds=round(time.perf_counter() - narration_started_at, 1),
                word_count=len(artifact.word_timings),
                audio_format=artifact.format,
                voice_label=artifact.metadata.get("voice_label"),
            )
            audio_extension = artifact.format.lower()
            audio_content_type = str(artifact.metadata.get("audio_mime_type") or "audio/mpeg")
            audio_path = f"{batch_id}/{batch_item_id}/narration.{audio_extension}"
            await self.blob_store.upload_bytes(
                self.settings.temp_audio_bucket,
                audio_path,
                artifact.audio_bytes,
                content_type=audio_content_type,
            )
            stored_conversation = None
            if conversation is not None:
                stored_conversation = conversation.model_copy(
                    update={
                        "audio_bucket": self.settings.temp_audio_bucket,
                        "audio_path": audio_path,
                        "has_audio": True,
                        "has_response_audio": True,
                        "updated_at": utc_now(),
                    }
                )
                await self.repository.upsert_agent_conversation(stored_conversation)

            await self.events.publish(
                batch_id,
                BatchEventType.NARRATOR_AUDIO_READY,
                {
                    "item_id": batch_item_id,
                    "conversation_id": stored_conversation.conversation_id if stored_conversation else None,
                    "audio_path": audio_path,
                    "mode": self.settings.narration_mode,
                    "voice_id": artifact.metadata.get("voice_id"),
                    "voice_label": artifact.metadata.get("voice_label"),
                },
            )

            existing_job = await self.repository.get_alignment_job(batch_item_id)
            alignment_payload = {
                "status": "completed",
                "word_count": len(artifact.word_timings),
                "conversation_id": stored_conversation.conversation_id if stored_conversation else None,
                "metadata": {"transcript": artifact.transcript},
                "updated_at": utc_now(),
            }
            if existing_job is None:
                await self.repository.create_alignment_job(
                    AlignmentJobRecord(
                        batch_id=batch_id,
                        batch_item_id=batch_item_id,
                        conversation_id=stored_conversation.conversation_id if stored_conversation else None,
                        status="completed",
                        word_count=len(artifact.word_timings),
                        metadata={"transcript": artifact.transcript},
                    )
                )
            else:
                await self.repository.update_alignment_job(existing_job.id, **alignment_payload)

            await self.events.publish(
                batch_id,
                BatchEventType.ALIGNMENT_READY,
                {
                    "item_id": batch_item_id,
                    "conversation_id": stored_conversation.conversation_id if stored_conversation else None,
                    "word_count": len(artifact.word_timings),
                    "mode": self.settings.narration_mode,
                },
            )
            await self.repository.update_agent_run(
                run.id,
                status="completed",
                conversation_id=stored_conversation.conversation_id if stored_conversation else None,
                metadata={
                    "conversation_id": stored_conversation.conversation_id if stored_conversation else None,
                    "mode": self.settings.narration_mode,
                    "voice_id": artifact.metadata.get("voice_id"),
                    "voice_label": artifact.metadata.get("voice_label"),
                },
                updated_at=utc_now(),
            )
            return artifact
        except Exception as exc:
            logger.error("Narrator failed for item %s: %s", batch_item_id, exc, exc_info=True)
            await self.repository.update_agent_run(run.id, status="failed", error=str(exc), updated_at=utc_now())
            raise

    async def handle_elevenlabs_webhook(self, raw_body: bytes, signature: str) -> dict[str, Any]:
        event = await self.elevenlabs.verify_webhook(raw_body, signature)
        conversation_id = (
            event.get("conversation_id")
            or event.get("data", {}).get("conversation_id")
            or event.get("event", {}).get("conversation_id")
        )
        if conversation_id:
            existing = await self.repository.get_agent_conversation(conversation_id)
            if existing is not None:
                metadata = dict(existing.metadata)
                metadata.setdefault("webhooks", []).append(event)
                await self.repository.upsert_agent_conversation(
                    existing.model_copy(update={"metadata": metadata, "updated_at": utc_now()})
                )
        return event

    async def _publish_log(
        self,
        batch_id: str,
        *,
        stage: str,
        message: str,
        **payload: object,
    ) -> None:
        normalized_payload = {
            "stage": stage,
            "message": message,
            **payload,
        }
        elapsed = normalized_payload.get("elapsed_seconds")
        if isinstance(elapsed, float):
            normalized_payload["elapsed_seconds"] = round(elapsed, 1)
        await self.events.publish(batch_id, BatchEventType.LOG, normalized_payload)

    async def _await_with_heartbeat(
        self,
        awaitable,
        *,
        batch_id: str,
        stage: str,
        waiting_message: str,
        started_at: float,
        total_started_at: float | None = None,
        interval_seconds: float | None = None,
        **payload: object,
    ):
        heartbeat_interval = interval_seconds or self.settings.progress_heartbeat_seconds
        task = asyncio.create_task(awaitable)
        heartbeat_count = 0
        try:
            while True:
                try:
                    return await asyncio.wait_for(asyncio.shield(task), timeout=heartbeat_interval)
                except TimeoutError:
                    heartbeat_count += 1
                    await self._publish_log(
                        batch_id,
                        stage=stage,
                        message=waiting_message,
                        elapsed_seconds=round(time.perf_counter() - started_at, 1),
                        **(
                            {
                                "total_elapsed_seconds": round(time.perf_counter() - total_started_at, 1),
                            }
                            if total_started_at is not None
                            else {}
                        ),
                        heartbeat=heartbeat_count,
                        **payload,
                    )
        finally:
            if not task.done():
                task.cancel()
                with suppress(asyncio.CancelledError):
                    await task

    async def forward_custom_llm_request(
        self,
        *,
        body: bytes,
        content_type: str | None,
        endpoint_hint: str | None = None,
    ) -> tuple[int, str, AsyncIterator[bytes]]:
        if not self.settings.openai_api_key:
            raise RuntimeError("OpenAI API key is not configured.")
        payload = json.loads(body.decode("utf-8")) if body else {}
        if not isinstance(payload, dict):
            raise RuntimeError("Custom LLM payload must be a JSON object.")

        path, normalized_payload = self._normalize_custom_llm_payload(payload, endpoint_hint=endpoint_hint)
        url = f"{self.settings.openai_base_url.rstrip('/')}{path}"
        headers = {
            "Authorization": f"Bearer {self.settings.openai_api_key}",
            "Accept": "text/event-stream",
            "Content-Type": content_type or "application/json",
        }
        client = httpx.AsyncClient(timeout=httpx.Timeout(180.0, connect=10.0))
        request = client.build_request("POST", url, headers=headers, json=normalized_payload)
        response = await client.send(request, stream=True)

        async def iterator() -> AsyncIterator[bytes]:
            try:
                async for chunk in response.aiter_bytes():
                    yield chunk
            finally:
                await response.aclose()
                await client.aclose()

        return (
            response.status_code,
            response.headers.get("content-type", "text/event-stream"),
            iterator(),
        )

    def _normalize_custom_llm_payload(
        self,
        payload: dict[str, Any],
        *,
        endpoint_hint: str | None,
    ) -> tuple[str, dict[str, Any]]:
        if endpoint_hint == "chat_completions" or "messages" in payload:
            allowed_keys = {
                "messages",
                "model",
                "temperature",
                "max_tokens",
                "stream",
                "tools",
                "tool_choice",
                "parallel_tool_calls",
                "frequency_penalty",
                "presence_penalty",
                "top_p",
                "stop",
                "seed",
                "response_format",
                "stream_options",
                "logprobs",
                "top_logprobs",
                "n",
                "user",
            }
            normalized = {key: value for key, value in payload.items() if key in allowed_keys}
            user_id = normalized.pop("user_id", None)
            if user_id and "user" not in normalized:
                normalized["user"] = user_id
            original_user_id = payload.get("user_id")
            if original_user_id and "user" not in normalized:
                normalized["user"] = original_user_id
            max_tokens = normalized.get("max_tokens")
            if isinstance(max_tokens, (int, float)) and max_tokens < 1:
                normalized.pop("max_tokens", None)

            tool_names = {
                tool.get("function", {}).get("name")
                for tool in normalized.get("tools", [])
                if isinstance(tool, dict)
            }
            has_submit_tool = "submit_script_bundle" in tool_names

            msg_count = len(normalized.get("messages", []))
            has_tool_result = any(
                m.get("role") == "tool" for m in normalized.get("messages", [])
                if isinstance(m, dict)
            )
            if has_submit_tool and not normalized.get("tool_choice") and has_tool_result:
                normalized["tool_choice"] = "none"
            elif has_submit_tool and not normalized.get("tool_choice") and msg_count >= 4:
                normalized["tool_choice"] = {
                    "type": "function",
                    "function": {"name": "submit_script_bundle"},
                }

            if not normalized.get("max_tokens"):
                normalized["max_tokens"] = 16384

            logger.info(
                "Custom LLM proxy: messages=%d, tools=%d (has_submit=%s), tool_choice=%s, model=%s",
                msg_count, len(tool_names), has_submit_tool,
                normalized.get("tool_choice", "auto"),
                normalized.get("model", self.settings.openai_model),
            )

            normalized.setdefault("model", self.settings.openai_model)
            normalized["stream"] = True
            return "/chat/completions", normalized

        if endpoint_hint == "responses" or "input" in payload:
            normalized = dict(payload)
            max_output_tokens = normalized.get("max_output_tokens")
            if isinstance(max_output_tokens, (int, float)) and max_output_tokens < 1:
                normalized.pop("max_output_tokens", None)
            normalized.setdefault("model", self.settings.openai_model)
            normalized["stream"] = True
            return "/responses", normalized

        raise RuntimeError("Unsupported custom LLM payload. Expected chat.completions or responses format.")


def _count_words(text: str) -> int:
    return len(WORD_PATTERN.findall(text))


def _estimate_narration_seconds(
    word_count: int,
    *,
    min_seconds: float,
    max_seconds: float,
) -> float:
    estimated = round(word_count / 3.3, 1)
    return round(min(max(estimated, min_seconds), max_seconds), 1)


def _script_quality_issues(script: ScriptDraft) -> list[str]:
    issues: list[str] = []
    hook_text = _normalize_script_text(script.hook)
    title_text = _normalize_script_text(script.title)
    full_text = _normalize_script_text(" ".join([script.title, script.hook, script.narration_text]))
    matched_starter = next((starter for starter in GENERIC_HOOK_STARTERS if hook_text.startswith(starter)), None)
    if matched_starter is not None:
        issues.append(f"uses a generic hook starter ({matched_starter.strip()!r})")
    if hook_text and title_text and hook_text == title_text:
        issues.append("hook simply repeats the title")
    if _opening_signature(script.narration_text) and _opening_signature(script.narration_text) == _opening_signature(script.title):
        issues.append("opening sentence simply repeats the title")

    matched_phrases = [phrase for phrase in GENERIC_MARKETING_PHRASES if phrase in full_text]
    if matched_phrases:
        issues.append(
            "contains generic marketing phrasing "
            f"({', '.join(sorted(set(matched_phrases))[:3])})"
        )
    canned_phrases = [phrase for phrase in GENERIC_CANNED_HOOK_PHRASES if phrase in full_text]
    if canned_phrases:
        issues.append(
            "uses canned hook phrasing "
            f"({', '.join(sorted(set(canned_phrases))[:3])})"
        )

    facts = [fact.strip() for fact in script.source_facts_used if fact.strip()]
    if len(facts) < 2:
        issues.append("must include at least 2 source_facts_used entries")
    if any(_looks_like_schema_leak(fact) for fact in facts):
        issues.append("contains malformed source_facts_used entries")
    if facts and not _hook_mentions_source_fact(script.hook, facts):
        issues.append("hook is not grounded in source_facts_used")
    return issues


def _normalize_script_text(value: str) -> str:
    return " ".join(value.casefold().split())


def _opening_signature(value: str) -> str:
    normalized = " ".join(value.split()).strip().casefold()
    if not normalized:
        return ""
    sentence_breaks = [index for index in (normalized.find(". "), normalized.find("? "), normalized.find("! ")) if index != -1]
    opening = normalized[: min(sentence_breaks)] if sentence_breaks else normalized
    tokens = WORD_PATTERN.findall(opening)
    if not tokens:
        return ""
    return " ".join(tokens[:8])


def _looks_like_schema_leak(value: str) -> bool:
    normalized = _normalize_script_text(value)
    return any(token in normalized for token in SCHEMA_LEAK_TOKENS)


def _clean_fact_list(facts: list[str]) -> list[str]:
    cleaned: list[str] = []
    seen: set[str] = set()
    for fact in facts:
        candidate = " ".join(fact.split()).strip(" -:;,.")
        if not candidate or _looks_like_schema_leak(candidate):
            continue
        key = candidate.casefold()
        if key in seen:
            continue
        seen.add(key)
        cleaned.append(candidate)
    return cleaned


def _normalize_script_facts(script_facts: list[str], source_facts: list[str]) -> list[str]:
    cleaned = _clean_fact_list(script_facts)
    if len(cleaned) >= 2:
        return cleaned

    seen = {fact.casefold() for fact in cleaned}
    for fact in source_facts:
        key = fact.casefold()
        if key in seen:
            continue
        cleaned.append(fact)
        seen.add(key)
        if len(cleaned) >= 2:
            break
    return cleaned


def _sanitize_title(title: str, facts: list[str]) -> str:
    cleaned_title = " ".join(title.split()).strip()
    normalized_title = _normalize_script_text(cleaned_title)
    if not any(phrase in normalized_title for phrase in GENERIC_MARKETING_PHRASES):
        return cleaned_title
    if not facts:
        return cleaned_title
    fact_title = _shorten_hook_fact(facts[0])
    return fact_title.title() if fact_title.islower() else fact_title


def _expand_narration_text(
    narration_text: str,
    *,
    facts: list[str],
    summary: str,
    min_words: int,
    min_characters: int,
) -> str:
    expanded = " ".join(narration_text.split()).strip()
    if _count_words(expanded) >= min_words and len(expanded) >= min_characters:
        return expanded

    fact_sentences = []
    seen_sentences: set[str] = set()
    for fact in facts:
        for sentence in _fact_sentence_variants(fact):
            key = sentence.casefold()
            if key in seen_sentences or sentence.casefold() in expanded.casefold():
                continue
            seen_sentences.add(key)
            fact_sentences.append(sentence)

    if summary.strip():
        summary_sentence = _summary_to_sentence(summary)
        if summary_sentence.casefold() not in seen_sentences and summary_sentence.casefold() not in expanded.casefold():
            fact_sentences.append(summary_sentence)

    while fact_sentences and (_count_words(expanded) < min_words or len(expanded) < min_characters):
        expanded = f"{expanded} {fact_sentences.pop(0)}".strip()

    return expanded


def _hook_mentions_source_fact(hook: str, facts: list[str]) -> bool:
    hook_tokens = _content_tokens(hook)
    if not hook_tokens:
        return False
    return any(len(hook_tokens & _content_tokens(fact)) >= 2 for fact in facts)


def _build_grounded_hook(script: ScriptDraft, facts: list[str]) -> str:
    if not facts:
        return script.hook.strip()

    context_tokens = _content_tokens(" ".join([script.title, script.narration_text]))
    ranked_facts = sorted(
        facts,
        key=lambda fact: (
            -len(context_tokens & _content_tokens(fact)),
            len(fact),
        ),
    )
    best_fact = ranked_facts[0]
    shortened = _shorten_hook_fact(best_fact)
    grounded_fact = shortened or best_fact.strip().rstrip(".")
    if not grounded_fact:
        return script.hook.strip()
    templates = (
        "{fact} is the step to watch first",
        "{fact} is where the source gets specific",
        "{fact} is the clearest proof point in the source",
        "{fact} is the handoff worth tracking",
    )
    template_index = int(hashlib.sha256(grounded_fact.encode("utf-8")).hexdigest()[:8], 16) % len(templates)
    return templates[template_index].format(fact=grounded_fact).strip()


def _diversify_bundle_script_identity(
    script: ScriptDraft,
    *,
    facts: list[str],
    script_index: int,
    occupied_pattern_ids: set[str],
) -> tuple[ScriptDraft, str]:
    if not facts:
        return script, SCRIPT_IDENTITY_PATTERNS[0]["id"]

    fact = facts[script_index % len(facts)]
    shortened_fact = _shorten_hook_fact(fact)
    pattern = SCRIPT_IDENTITY_PATTERNS[script_index % len(SCRIPT_IDENTITY_PATTERNS)]
    if len(occupied_pattern_ids) < len(SCRIPT_IDENTITY_PATTERNS):
        for offset in range(len(SCRIPT_IDENTITY_PATTERNS)):
            candidate = SCRIPT_IDENTITY_PATTERNS[(script_index + offset) % len(SCRIPT_IDENTITY_PATTERNS)]
            if candidate["id"] not in occupied_pattern_ids:
                pattern = candidate
                break

    hook = pattern["hook"].format(fact=fact, short_fact=shortened_fact).strip()
    opening = pattern["opening"].format(fact=fact, short_fact=shortened_fact).strip()
    narration_text = _replace_narration_opening(script.narration_text, opening)
    source_facts_used = [entry for entry in script.source_facts_used if entry != fact]
    source_facts_used = [fact, *source_facts_used][: max(2, len(script.source_facts_used) + 1)]
    return (
        script.model_copy(
            update={
                "hook": hook or script.hook,
                "narration_text": narration_text,
                "source_facts_used": source_facts_used or script.source_facts_used,
            }
        ),
        pattern["id"],
    )


def _replace_narration_opening(narration_text: str, opening_sentence: str) -> str:
    normalized = " ".join(narration_text.split()).strip()
    if not normalized:
        return opening_sentence
    sentence_breaks = [index for index in (normalized.find(". "), normalized.find("? "), normalized.find("! ")) if index != -1]
    if sentence_breaks:
        first_break = min(sentence_breaks)
        remainder = normalized[first_break + 2 :].strip()
        return f"{opening_sentence} {remainder}".strip()
    return f"{opening_sentence} {normalized}".strip()


def _shorten_hook_fact(fact: str) -> str:
    candidate = fact.strip()
    for separator in (".", ";", " - ", " — ", ":"):
        if separator in candidate:
            candidate = candidate.split(separator, 1)[0].strip()
            break
    words = candidate.split()
    if len(words) > 12:
        candidate = " ".join(words[:12]).strip()
    return candidate.rstrip(" -:;,.")


def _fact_to_sentence(fact: str) -> str:
    cleaned = fact.strip().rstrip(".")
    return f"{cleaned}."


def _fact_sentence_variants(fact: str) -> list[str]:
    cleaned = fact.strip().rstrip(".")
    return [
        f"{cleaned}.",
        f"The source specifically calls out {cleaned}.",
        f"That detail matters because {cleaned}.",
    ]


def _summary_to_sentence(summary: str) -> str:
    cleaned = " ".join(summary.split()).strip().rstrip(".")
    return f"The source frames it as {cleaned}."


def _content_tokens(value: str) -> set[str]:
    return {
        token
        for token in WORD_PATTERN.findall(value.casefold())
        if len(token) >= 3 and token not in HOOK_STOPWORDS
    }


def _truncate_log_text(value: str, limit: int = 280) -> str:
    normalized = " ".join(value.split())
    if len(normalized) <= limit:
        return normalized
    return f"{normalized[: limit - 1]}…"
