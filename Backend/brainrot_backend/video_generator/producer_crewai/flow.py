from __future__ import annotations

import asyncio
import json
import re
from collections import Counter
from collections.abc import Awaitable, Callable
from typing import Any

from crewai import Crew, Process

from brainrot_backend.config import Settings
from brainrot_backend.core.models.domain import AnglePlan, GeneratedBundle, IngestedSource, ScriptDraft, SourceBrief
from brainrot_backend.core.models.enums import BatchEventType
from brainrot_backend.video_generator.producer_crewai.models import (
    CoveragePlan,
    CoverageSlotPlan,
    CoverageValidationIssue,
    CrewAIScriptPayload,
)
from brainrot_backend.video_generator.producer_crewai.sectioning import build_coverage_plan, build_source_brief_metadata
from brainrot_backend.video_generator.producer_crewai.tasks import (
    build_crewai_llm,
    build_repair_agent,
    build_repair_task,
    build_writer_agent,
    build_writer_task,
)

PublishEvent = Callable[[BatchEventType, dict[str, object]], Awaitable[None]]
PublishLog = Callable[..., Awaitable[None]]

TOKEN_RE = re.compile(r"[A-Za-z0-9]+(?:['-][A-Za-z0-9]+)*")
MARKETING_REPLACEMENTS = {
    "innovative add-on": "focused workflow tool",
    "powerful tool": "workflow tool",
    "revolutionary": "practical",
    "ultimate solution": "clear workflow",
    "future of content creation": "content workflow",
    "ai-powered sidekick": "assistant",
}
GENERIC_MARKETING_LEADS = (
    "transform your",
    "maximize your",
    "elevate your",
    "unlock ",
    "streamline your",
    "content hub is",
    "with content hub",
    "in the content hub",
    "this tool",
    "this platform",
    "this product",
)
HOOK_STOPWORDS = {
    "a",
    "an",
    "and",
    "are",
    "for",
    "from",
    "has",
    "have",
    "how",
    "in",
    "into",
    "is",
    "it",
    "its",
    "of",
    "on",
    "or",
    "the",
    "their",
    "this",
    "to",
    "with",
    "your",
}


class CrewAIProducerFlow:
    def __init__(self, *, settings: Settings) -> None:
        self.settings = settings

    async def generate_bundle(
        self,
        *,
        batch_id: str,
        source: IngestedSource,
        requested_count: int,
        publish_event: PublishEvent,
        publish_log: PublishLog,
    ) -> GeneratedBundle:
        if not self.settings.openai_api_key:
            raise RuntimeError("OpenAI API key is not configured.")

        await publish_event(
            BatchEventType.SECTION_PLANNING_STARTED,
            {
                "requested_count": requested_count,
                "source_title": source.title,
            },
        )
        await publish_log(
            batch_id,
            stage="producer",
            message="CrewAI section planning started.",
            requested_count=requested_count,
            source_title=source.title,
        )

        coverage_plan = build_coverage_plan(
            title=source.title,
            markdown=source.markdown[: self.settings.producer_source_char_limit],
            requested_count=requested_count,
        )
        source_brief = self._build_source_brief(source=source, coverage_plan=coverage_plan)

        await publish_event(
            BatchEventType.SECTION_PLANNING_COMPLETED,
            {
                "requested_count": requested_count,
                "planned_count": coverage_plan.planned_count,
                "section_count": coverage_plan.section_count,
            },
        )
        await publish_log(
            batch_id,
            stage="producer",
            message="CrewAI section planning completed.",
            requested_count=requested_count,
            planned_count=coverage_plan.planned_count,
            section_count=coverage_plan.section_count,
        )
        await publish_event(
            BatchEventType.COVERAGE_PLAN_READY,
            {
                "requested_count": requested_count,
                "planned_count": coverage_plan.planned_count,
                "section_count": coverage_plan.section_count,
                "slot_count": len(coverage_plan.slots),
                "angle_families": [slot.angle_family for slot in coverage_plan.slots],
                "slot_section_map": [
                    {
                        "slot_index": slot.slot_index,
                        "slot_id": slot.slot_id,
                        "section_id": slot.cluster.section_ids[0] if slot.cluster.section_ids else None,
                        "section_heading": slot.cluster.headings[0] if slot.cluster.headings else None,
                        "angle_family": slot.angle_family,
                    }
                    for slot in coverage_plan.slots
                ],
            },
        )
        await publish_log(
            batch_id,
            stage="producer",
            message="CrewAI coverage plan is ready.",
            requested_count=requested_count,
            planned_count=coverage_plan.planned_count,
            slot_count=len(coverage_plan.slots),
            section_count=coverage_plan.section_count,
        )

        initial_payloads = await self._run_writer_stage(
            batch_id=batch_id,
            source_brief=source_brief,
            coverage_plan=coverage_plan,
            publish_event=publish_event,
            publish_log=publish_log,
        )
        issues = self._validate_slot_payloads(
            payloads=initial_payloads,
            coverage_plan=coverage_plan,
            source_brief=source_brief,
        )
        if issues:
            repaired_payloads = await self._run_repair_stage(
                batch_id=batch_id,
                source_brief=source_brief,
                coverage_plan=coverage_plan,
                payloads=initial_payloads,
                issues=issues,
                publish_event=publish_event,
                publish_log=publish_log,
            )
            initial_payloads.update(repaired_payloads)
            issues = self._validate_slot_payloads(
                payloads=initial_payloads,
                coverage_plan=coverage_plan,
                source_brief=source_brief,
            )
            if issues:
                issue_summary = "; ".join(
                    f"slot {issue.slot_index + 1}: {', '.join(issue.problems)}"
                    for issue in issues
                )
                raise RuntimeError(f"CrewAI producer could not repair all slots: {issue_summary}")

        bundle = self._build_bundle(
            source_brief=source_brief,
            coverage_plan=coverage_plan,
            payloads=initial_payloads,
        )
        await publish_event(
            BatchEventType.PRODUCER_BUNDLE_COMPLETED,
            {
                "requested_count": requested_count,
                "planned_count": coverage_plan.planned_count,
                "section_count": coverage_plan.section_count,
                "slot_count": len(bundle.scripts),
                "covered_sections": [slot.cluster.section_ids[0] for slot in coverage_plan.slots if slot.cluster.section_ids],
                "unused_sections": build_source_brief_metadata(coverage_plan)["unused_sections"],
            },
        )
        await publish_log(
            batch_id,
            stage="producer",
            message="CrewAI bundle completed.",
            requested_count=requested_count,
            planned_count=coverage_plan.planned_count,
            section_count=coverage_plan.section_count,
            script_count=len(bundle.scripts),
        )
        return bundle

    async def _run_writer_stage(
        self,
        *,
        batch_id: str,
        source_brief: SourceBrief,
        coverage_plan: CoveragePlan,
        publish_event: PublishEvent,
        publish_log: PublishLog,
    ) -> dict[str, CrewAIScriptPayload]:
        for slot in coverage_plan.slots:
            await publish_event(
                BatchEventType.SLOT_GENERATION_STARTED,
                {
                    "slot_index": slot.slot_index,
                    "slot_id": slot.slot_id,
                    "section_id": slot.cluster.section_ids[0] if slot.cluster.section_ids else None,
                    "section_heading": slot.cluster.headings[0] if slot.cluster.headings else None,
                    "angle_family": slot.angle_family,
                    "writer_attempt": 1,
                },
            )
            await publish_log(
                batch_id,
                stage="producer",
                message=f"CrewAI slot generation started for slot {slot.slot_index + 1}.",
                slot_index=slot.slot_index,
                slot_id=slot.slot_id,
                section_id=slot.cluster.section_ids[0] if slot.cluster.section_ids else None,
                section_heading=slot.cluster.headings[0] if slot.cluster.headings else None,
                angle_family=slot.angle_family,
                writer_attempt=1,
            )

        task_by_slot_id = {
            slot.slot_id: asyncio.create_task(
                self._generate_slot_payload(
                    slot=slot,
                    source_brief=source_brief,
                )
            )
            for slot in coverage_plan.slots
        }
        results = await self._collect_slot_results_with_heartbeat(
            tasks_by_slot_id=task_by_slot_id,
            slots=coverage_plan.slots,
            publish_log=publish_log,
            batch_id=batch_id,
            stage="writer",
            message="CrewAI slot generation is still running.",
        )

        payloads: dict[str, CrewAIScriptPayload] = {}
        failures: list[str] = []
        for slot, result in zip(coverage_plan.slots, results, strict=True):
            if isinstance(result, Exception):
                failures.append(f"slot {slot.slot_index + 1}: {result}")
                await publish_event(
                    BatchEventType.SLOT_GENERATION_FAILED,
                    {
                        "slot_index": slot.slot_index,
                        "slot_id": slot.slot_id,
                        "section_id": slot.cluster.section_ids[0] if slot.cluster.section_ids else None,
                        "section_heading": slot.cluster.headings[0] if slot.cluster.headings else None,
                        "angle_family": slot.angle_family,
                        "writer_attempt": 1,
                        "error": str(result),
                    },
                )
                await publish_log(
                    batch_id,
                    stage="producer",
                    message=f"CrewAI slot generation failed for slot {slot.slot_index + 1}.",
                    slot_index=slot.slot_index,
                    slot_id=slot.slot_id,
                    section_id=slot.cluster.section_ids[0] if slot.cluster.section_ids else None,
                    section_heading=slot.cluster.headings[0] if slot.cluster.headings else None,
                    angle_family=slot.angle_family,
                    writer_attempt=1,
                    error=str(result),
                )
                continue

            payloads[slot.slot_id] = result
            await publish_event(
                BatchEventType.SLOT_GENERATION_COMPLETED,
                {
                    "slot_index": slot.slot_index,
                    "slot_id": slot.slot_id,
                    "section_id": slot.cluster.section_ids[0] if slot.cluster.section_ids else None,
                    "section_heading": slot.cluster.headings[0] if slot.cluster.headings else None,
                    "angle_family": slot.angle_family,
                    "writer_attempt": 1,
                },
            )
            await publish_log(
                batch_id,
                stage="producer",
                message=f"CrewAI slot generation completed for slot {slot.slot_index + 1}.",
                slot_index=slot.slot_index,
                slot_id=slot.slot_id,
                section_id=slot.cluster.section_ids[0] if slot.cluster.section_ids else None,
                section_heading=slot.cluster.headings[0] if slot.cluster.headings else None,
                angle_family=slot.angle_family,
                writer_attempt=1,
            )

        if failures:
            raise RuntimeError("; ".join(failures))
        return payloads

    async def _run_repair_stage(
        self,
        *,
        batch_id: str,
        source_brief: SourceBrief,
        coverage_plan: CoveragePlan,
        payloads: dict[str, CrewAIScriptPayload],
        issues: list[CoverageValidationIssue],
        publish_event: PublishEvent,
        publish_log: PublishLog,
    ) -> dict[str, CrewAIScriptPayload]:
        slots_by_id = {slot.slot_id: slot for slot in coverage_plan.slots}
        issue_map = {issue.slot_id: issue for issue in issues}
        target_slots = [slots_by_id[slot_id] for slot_id in issue_map]
        for slot in target_slots:
            issue = issue_map[slot.slot_id]
            validation_feedback = "; ".join(issue.problems)
            await publish_event(
                BatchEventType.SLOT_REPAIR_STARTED,
                {
                    "slot_index": slot.slot_index,
                    "slot_id": slot.slot_id,
                    "section_id": slot.cluster.section_ids[0] if slot.cluster.section_ids else None,
                    "section_heading": slot.cluster.headings[0] if slot.cluster.headings else None,
                    "angle_family": slot.angle_family,
                    "repair_attempt": 1,
                    "validation_feedback": validation_feedback,
                },
            )
            await publish_log(
                batch_id,
                stage="producer",
                message=f"CrewAI repair started for slot {slot.slot_index + 1}.",
                slot_index=slot.slot_index,
                slot_id=slot.slot_id,
                section_id=slot.cluster.section_ids[0] if slot.cluster.section_ids else None,
                section_heading=slot.cluster.headings[0] if slot.cluster.headings else None,
                angle_family=slot.angle_family,
                repair_attempt=1,
                validation_summary=validation_feedback,
            )

        task_by_slot_id = {
            slot.slot_id: asyncio.create_task(
                self._repair_slot_payload(
                    slot=slot,
                    source_brief=source_brief,
                    current_payload=payloads[slot.slot_id],
                    validation_feedback="; ".join(issue_map[slot.slot_id].problems),
                )
            )
            for slot in target_slots
        }
        results = await self._collect_slot_results_with_heartbeat(
            tasks_by_slot_id=task_by_slot_id,
            slots=target_slots,
            publish_log=publish_log,
            batch_id=batch_id,
            stage="repair",
            message="CrewAI slot repair is still running.",
        )

        repaired: dict[str, CrewAIScriptPayload] = {}
        failures: list[str] = []
        for slot, result in zip(target_slots, results, strict=True):
            if isinstance(result, Exception):
                failures.append(f"slot {slot.slot_index + 1}: {result}")
                await publish_event(
                    BatchEventType.SLOT_GENERATION_FAILED,
                    {
                        "slot_index": slot.slot_index,
                        "slot_id": slot.slot_id,
                        "section_id": slot.cluster.section_ids[0] if slot.cluster.section_ids else None,
                        "section_heading": slot.cluster.headings[0] if slot.cluster.headings else None,
                        "angle_family": slot.angle_family,
                        "repair_attempt": 1,
                        "error": str(result),
                    },
                )
                continue
            repaired[slot.slot_id] = result
            await publish_event(
                BatchEventType.SLOT_REPAIR_COMPLETED,
                {
                    "slot_index": slot.slot_index,
                    "slot_id": slot.slot_id,
                    "section_id": slot.cluster.section_ids[0] if slot.cluster.section_ids else None,
                    "section_heading": slot.cluster.headings[0] if slot.cluster.headings else None,
                    "angle_family": slot.angle_family,
                    "repair_attempt": 1,
                },
            )
            await publish_log(
                batch_id,
                stage="producer",
                message=f"CrewAI repair completed for slot {slot.slot_index + 1}.",
                slot_index=slot.slot_index,
                slot_id=slot.slot_id,
                section_id=slot.cluster.section_ids[0] if slot.cluster.section_ids else None,
                section_heading=slot.cluster.headings[0] if slot.cluster.headings else None,
                angle_family=slot.angle_family,
                repair_attempt=1,
            )
        if failures:
            raise RuntimeError("; ".join(failures))
        return repaired

    async def _generate_slot_payload(
        self,
        *,
        slot: CoverageSlotPlan,
        source_brief: SourceBrief,
    ) -> CrewAIScriptPayload:
        llm = build_crewai_llm(
            model=self.settings.openai_model,
            api_key=self.settings.openai_api_key or "",
            base_url=self.settings.openai_base_url,
            temperature=0.25,
            max_tokens=2500,
            reasoning_effort=self.settings.openai_reasoning_effort,
        )
        agent = build_writer_agent(llm=llm)
        task = build_writer_task(
            agent=agent,
            slot=slot,
            source_title=source_brief.canonical_title,
            canonical_summary=source_brief.summary,
            section_count=source_brief.metadata.get("section_count", 0) if isinstance(source_brief.metadata, dict) else 0,
        )
        crew = Crew(
            name=f"writer-{slot.slot_id}",
            agents=[agent],
            tasks=[task],
            process=Process.sequential,
            verbose=False,
            tracing=False,
        )
        result = await crew.kickoff_async()
        payload = self._extract_payload(result)
        stabilized = self._stabilize_payload(payload=payload, slot=slot, source_brief=source_brief)
        return stabilized.model_copy(
            update={
                "metadata": {
                    **stabilized.metadata,
                    "section_id": slot.cluster.section_ids[0] if slot.cluster.section_ids else None,
                    "section_heading": slot.cluster.headings[0] if slot.cluster.headings else None,
                    "angle_family": slot.angle_family,
                    "semantic_objective": slot.semantic_objective,
                }
            }
        )

    async def _repair_slot_payload(
        self,
        *,
        slot: CoverageSlotPlan,
        source_brief: SourceBrief,
        current_payload: CrewAIScriptPayload,
        validation_feedback: str,
    ) -> CrewAIScriptPayload:
        llm = build_crewai_llm(
            model=self.settings.openai_model,
            api_key=self.settings.openai_api_key or "",
            base_url=self.settings.openai_base_url,
            temperature=0.15,
            max_tokens=2500,
            reasoning_effort=self.settings.openai_reasoning_effort,
        )
        agent = build_repair_agent(llm=llm)
        task = build_repair_task(
            agent=agent,
            slot=slot,
            source_title=source_brief.canonical_title,
            canonical_summary=source_brief.summary,
            current_script_json=json.dumps(current_payload.model_dump(mode="json"), ensure_ascii=False, indent=2),
            validation_feedback=validation_feedback,
        )
        crew = Crew(
            name=f"repair-{slot.slot_id}",
            agents=[agent],
            tasks=[task],
            process=Process.sequential,
            verbose=False,
            tracing=False,
        )
        result = await crew.kickoff_async()
        payload = self._extract_payload(result)
        stabilized = self._stabilize_payload(payload=payload, slot=slot, source_brief=source_brief)
        return stabilized.model_copy(
            update={
                "metadata": {
                    **stabilized.metadata,
                    "section_id": slot.cluster.section_ids[0] if slot.cluster.section_ids else None,
                    "section_heading": slot.cluster.headings[0] if slot.cluster.headings else None,
                    "angle_family": slot.angle_family,
                    "semantic_objective": slot.semantic_objective,
                }
            }
        )

    def _extract_payload(self, crew_output) -> CrewAIScriptPayload:
        if getattr(crew_output, "tasks_output", None):
            task_output = crew_output.tasks_output[0]
            if task_output.pydantic is not None:
                return CrewAIScriptPayload.model_validate(task_output.pydantic.model_dump())
            if task_output.json_dict is not None:
                return CrewAIScriptPayload.model_validate(task_output.json_dict)
            if task_output.raw:
                return CrewAIScriptPayload.model_validate_json(task_output.raw)
        if getattr(crew_output, "pydantic", None) is not None:
            return CrewAIScriptPayload.model_validate(crew_output.pydantic.model_dump())
        if getattr(crew_output, "json_dict", None) is not None:
            return CrewAIScriptPayload.model_validate(crew_output.json_dict)
        if getattr(crew_output, "raw", None):
            return CrewAIScriptPayload.model_validate_json(crew_output.raw)
        raise RuntimeError("CrewAI returned no structured output for a slot.")

    async def _collect_slot_results_with_heartbeat(
        self,
        *,
        tasks_by_slot_id: dict[str, asyncio.Task[CrewAIScriptPayload]],
        slots: list[CoverageSlotPlan],
        publish_log: PublishLog,
        batch_id: str,
        stage: str,
        message: str,
    ) -> list[CrewAIScriptPayload | Exception]:
        slot_order = [slot.slot_id for slot in slots]
        heartbeat = 0
        pending = set(tasks_by_slot_id.values())
        while pending:
            done, pending = await asyncio.wait(
                pending,
                timeout=self.settings.progress_heartbeat_seconds,
                return_when=asyncio.FIRST_COMPLETED,
            )
            if done:
                continue
            heartbeat += 1
            active_slots = [
                slot.slot_index + 1
                for slot in slots
                if not tasks_by_slot_id[slot.slot_id].done()
            ]
            await publish_log(
                batch_id,
                stage="producer",
                message=message,
                substage=stage,
                heartbeat=heartbeat,
                active_slot_count=len(active_slots),
                active_slots=active_slots,
            )

        results: list[CrewAIScriptPayload | Exception] = []
        for slot_id in slot_order:
            task = tasks_by_slot_id[slot_id]
            try:
                results.append(task.result())
            except Exception as exc:  # pragma: no cover - exercised via caller handling
                results.append(exc)
        return results

    def _build_source_brief(self, *, source: IngestedSource, coverage_plan: CoveragePlan) -> SourceBrief:
        all_facts: list[str] = []
        all_entities: list[str] = []
        for section in coverage_plan.sections:
            all_facts.extend(section.facts)
            all_entities.extend(section.entities)
        summary = " ".join(
            cluster.section_summary
            for cluster in [slot.cluster for slot in coverage_plan.slots[:2]]
            if cluster.section_summary
        ) or source.title
        metadata = build_source_brief_metadata(coverage_plan)
        return SourceBrief(
            canonical_title=source.title,
            summary=summary.strip(),
            facts=_unique_text(all_facts)[:12],
            entities=_unique_text(all_entities)[:12],
            tone="specific, fast, grounded",
            do_not_drift=[
                "Do not invent product claims.",
                "Keep each script tied to its assigned article section.",
                "Do not collapse the batch into one repeated feature pitch.",
            ],
            source_urls=source.normalized_urls or ([source.original_url] if source.original_url else []),
            metadata=metadata,
        )

    def _build_bundle(
        self,
        *,
        source_brief: SourceBrief,
        coverage_plan: CoveragePlan,
        payloads: dict[str, CrewAIScriptPayload],
    ) -> GeneratedBundle:
        scripts: list[ScriptDraft] = []
        angles: list[AnglePlan] = []
        slot_section_map: list[dict[str, object]] = []
        angle_families: list[str] = []
        for slot in coverage_plan.slots:
            payload = payloads[slot.slot_id]
            scripts.append(
                ScriptDraft(
                    title=payload.title,
                    hook=payload.hook,
                    narration_text=payload.narration_text,
                    caption_text=payload.caption_text,
                    estimated_seconds=26.0,
                    visual_beats=payload.visual_beats[:4],
                    music_tags=payload.music_tags[:4] or [slot.music_mood],
                    gameplay_tags=payload.gameplay_tags[:4] or [slot.visual_mood, slot.angle_family],
                    source_facts_used=payload.source_facts_used[:6],
                    qa_notes=payload.qa_notes,
                    metadata={
                        **payload.metadata,
                        "section_ids": slot.cluster.section_ids,
                        "section_heading": slot.cluster.headings[0] if slot.cluster.headings else None,
                        "angle_family": slot.angle_family,
                    },
                )
            )
            angles.append(
                AnglePlan(
                    title=payload.title,
                    hook_direction=slot.hook_direction,
                    audience_frame=slot.audience_frame,
                    energy_level="high",
                    visual_mood=slot.visual_mood,
                    music_mood=slot.music_mood,
                    angle_family=slot.angle_family,
                    section_id=slot.cluster.section_ids[0] if slot.cluster.section_ids else None,
                    section_heading=slot.cluster.headings[0] if slot.cluster.headings else None,
                    metadata={
                        "semantic_objective": slot.semantic_objective,
                        "section_ids": slot.cluster.section_ids,
                    },
                )
            )
            slot_section_map.append(
                {
                    "slot_index": slot.slot_index,
                    "slot_id": slot.slot_id,
                    "section_id": slot.cluster.section_ids[0] if slot.cluster.section_ids else None,
                    "section_heading": slot.cluster.headings[0] if slot.cluster.headings else None,
                    "angle_family": slot.angle_family,
                }
            )
            angle_families.append(slot.angle_family)

        unused_sections = build_source_brief_metadata(coverage_plan)["unused_sections"]
        return GeneratedBundle(
            source_brief=source_brief,
            angles=angles,
            scripts=scripts,
            metadata={
                "requested_count": coverage_plan.requested_count,
                "planned_count": coverage_plan.planned_count,
                "section_count": coverage_plan.section_count,
                "coverage_plan": source_brief.metadata.get("coverage_plan", []),
                "slot_section_map": slot_section_map,
                "angle_families": angle_families,
                "covered_sections": [entry["section_id"] for entry in slot_section_map],
                "unused_sections": unused_sections,
                "fallback_flags": coverage_plan.fallback_flags,
            },
        )

    def _validate_slot_payloads(
        self,
        *,
        payloads: dict[str, CrewAIScriptPayload],
        coverage_plan: CoveragePlan,
        source_brief: SourceBrief,
    ) -> list[CoverageValidationIssue]:
        issues: list[CoverageValidationIssue] = []
        title_keys: Counter[str] = Counter()
        hook_keys: Counter[str] = Counter()
        primary_fact_keys: Counter[str] = Counter()
        product_name_first_slots = 0

        for slot in coverage_plan.slots:
            payload = payloads.get(slot.slot_id)
            if payload is None:
                issues.append(
                    CoverageValidationIssue(
                        slot_index=slot.slot_index,
                        slot_id=slot.slot_id,
                        section_id=slot.cluster.section_ids[0] if slot.cluster.section_ids else None,
                        angle_family=slot.angle_family,
                        problems=["missing payload"],
                    )
                )
                continue

            problems: list[str] = []
            narration = " ".join(payload.narration_text.split()).strip()
            word_count = len(TOKEN_RE.findall(narration))
            if not self.settings.script_min_words <= word_count <= self.settings.script_max_words:
                problems.append(
                    f"narration word count is {word_count}, required {self.settings.script_min_words}-{self.settings.script_max_words}"
                )
            if len(narration) < self.settings.script_min_characters:
                problems.append(f"narration characters are below {self.settings.script_min_characters}")
            if len(payload.source_facts_used) < 2:
                problems.append("requires at least two source facts")

            title_key = _normalize_text(payload.title)
            hook_key = _normalize_text(payload.hook)
            title_keys[title_key] += 1
            hook_keys[hook_key] += 1

            if _starts_with_product_name(payload.narration_text, source_brief.canonical_title):
                product_name_first_slots += 1

            assigned_fact_tokens = [_content_tokens(fact) for fact in slot.cluster.facts[:8]]
            fact_overlap_hits = 0
            for fact in payload.source_facts_used:
                fact_tokens = _content_tokens(fact)
                if any(len(fact_tokens & assigned_tokens) >= 2 for assigned_tokens in assigned_fact_tokens):
                    fact_overlap_hits += 1
            if fact_overlap_hits < 2:
                problems.append("source_facts_used drift away from the assigned section cluster")

            hook_tokens = _content_tokens(payload.hook)
            if hook_tokens and hook_tokens == _content_tokens(payload.title):
                problems.append("hook repeats the title")
            opening = _opening_sentence(payload.narration_text)
            if _normalize_text(opening) == _normalize_text(payload.title):
                problems.append("opening repeats the title")
            if _normalize_text(opening) == _normalize_text(payload.hook):
                problems.append("opening repeats the hook")
            if not any(len(hook_tokens & assigned_tokens) >= 2 for assigned_tokens in assigned_fact_tokens):
                problems.append("hook is not grounded in the assigned section facts")
            if _looks_like_templated_lead(payload.hook):
                problems.append("hook uses a templated lead instead of a concrete article fact")
            if _looks_like_templated_lead(opening):
                problems.append("opening uses a templated lead instead of a concrete article fact")
            if _looks_truncated(payload.hook):
                problems.append("hook looks truncated or clipped mid-thought")

            primary_fact = _normalize_text(payload.source_facts_used[0]) if payload.source_facts_used else ""
            if primary_fact:
                primary_fact_keys[primary_fact] += 1

            if problems:
                issues.append(
                    CoverageValidationIssue(
                        slot_index=slot.slot_index,
                        slot_id=slot.slot_id,
                        section_id=slot.cluster.section_ids[0] if slot.cluster.section_ids else None,
                        angle_family=slot.angle_family,
                        problems=problems,
                    )
                )

        for slot in coverage_plan.slots:
            slot_issues = next((issue for issue in issues if issue.slot_id == slot.slot_id), None)
            payload = payloads.get(slot.slot_id)
            if payload is None:
                continue
            extra: list[str] = []
            if title_keys[_normalize_text(payload.title)] > 1:
                extra.append("title overlaps with another slot")
            if hook_keys[_normalize_text(payload.hook)] > 1:
                extra.append("hook overlaps with another slot")
            primary_fact = _normalize_text(payload.source_facts_used[0]) if payload.source_facts_used else ""
            if primary_fact and primary_fact_keys[primary_fact] > 1:
                extra.append("primary fact cluster overlaps with another slot")
            if extra:
                if slot_issues is None:
                    issues.append(
                        CoverageValidationIssue(
                            slot_index=slot.slot_index,
                            slot_id=slot.slot_id,
                            section_id=slot.cluster.section_ids[0] if slot.cluster.section_ids else None,
                            angle_family=slot.angle_family,
                            problems=extra,
                        )
                    )
                else:
                    slot_issues.problems.extend(extra)

        if product_name_first_slots > 1:
            for slot in coverage_plan.slots:
                payload = payloads.get(slot.slot_id)
                if payload is None or not _starts_with_product_name(payload.narration_text, source_brief.canonical_title):
                    continue
                slot_issue = next((issue for issue in issues if issue.slot_id == slot.slot_id), None)
                if slot_issue is None:
                    issues.append(
                        CoverageValidationIssue(
                            slot_index=slot.slot_index,
                            slot_id=slot.slot_id,
                            section_id=slot.cluster.section_ids[0] if slot.cluster.section_ids else None,
                            angle_family=slot.angle_family,
                            problems=["too many product-name-first openings across the batch"],
                        )
                    )
                else:
                    slot_issue.problems.append("too many product-name-first openings across the batch")

        return issues

    def _stabilize_payload(
        self,
        *,
        payload: CrewAIScriptPayload,
        slot: CoverageSlotPlan,
        source_brief: SourceBrief,
    ) -> CrewAIScriptPayload:
        assigned_facts = _unique_text(slot.cluster.facts)[:6]
        normalized_facts = _unique_text([*assigned_facts, *payload.source_facts_used])[:6]
        if len(normalized_facts) < 2 and source_brief.facts:
            normalized_facts = _unique_text([*normalized_facts, *source_brief.facts])[:6]
        grounding_facts = assigned_facts or normalized_facts or source_brief.facts
        selected_fact = _select_best_fact_for_slot(
            slot=slot,
            facts=grounding_facts,
            product_name=source_brief.canonical_title,
        )

        hook = " ".join(payload.hook.split()).strip()
        if (
            not hook
            or not _hook_is_grounded(hook, grounding_facts)
            or len(hook) > 96
            or _starts_with_product_name(hook, source_brief.canonical_title)
            or _sounds_like_generic_marketing(hook)
        ):
            hook = _grounded_hook_for_slot(slot=slot, fact=selected_fact)
        hook = _scrub_marketing_phrases(hook)

        title = _scrub_marketing_phrases(" ".join(payload.title.split()).strip() or slot.cluster.headings[0])
        caption_text = _scrub_marketing_phrases(" ".join(payload.caption_text.split()).strip() or title)
        narration_text = _expand_narration_to_target(
            text=_scrub_marketing_phrases(payload.narration_text),
            facts=normalized_facts or grounding_facts,
            section_summary=slot.cluster.section_summary,
            min_words=self.settings.script_min_words,
            min_characters=self.settings.script_min_characters,
        )
        if (
            _starts_with_product_name(narration_text, source_brief.canonical_title)
            or _opening_sentence(narration_text).casefold().startswith("in the realm of")
            or _sounds_like_generic_marketing(_opening_sentence(narration_text))
        ):
            narration_text = _replace_opening_sentence(
                narration_text,
                _opening_for_slot(slot=slot, fact=selected_fact),
            )
            narration_text = _expand_narration_to_target(
                text=narration_text,
                facts=normalized_facts or grounding_facts,
                section_summary=slot.cluster.section_summary,
                min_words=self.settings.script_min_words,
                min_characters=self.settings.script_min_characters,
            )
        narration_text = _trim_narration_to_max_words(
            narration_text,
            max_words=self.settings.script_max_words,
        )

        return payload.model_copy(
            update={
                "title": title,
                "hook": hook,
                "caption_text": caption_text,
                "narration_text": narration_text,
                "source_facts_used": normalized_facts[:6],
            }
        )


def _unique_text(values: list[str]) -> list[str]:
    seen: set[str] = set()
    ordered: list[str] = []
    for value in values:
        normalized = " ".join(value.split()).strip()
        if not normalized:
            continue
        key = normalized.casefold()
        if key in seen:
            continue
        seen.add(key)
        ordered.append(normalized)
    return ordered


def _normalize_text(value: str) -> str:
    return " ".join(value.casefold().split())


def _content_tokens(value: str) -> set[str]:
    return {
        token.casefold()
        for token in TOKEN_RE.findall(value)
        if len(token) >= 3 and token.casefold() not in HOOK_STOPWORDS
    }


def _opening_sentence(text: str) -> str:
    normalized = " ".join(text.split()).strip()
    if not normalized:
        return ""
    for delimiter in (". ", "! ", "? "):
        if delimiter in normalized:
            return normalized.split(delimiter, 1)[0].strip()
    return normalized


def _starts_with_product_name(text: str, product_name: str) -> bool:
    opening = _normalize_text(_opening_sentence(text))
    title_tokens = [
        token
        for token in TOKEN_RE.findall(product_name.casefold())
        if len(token) >= 3 and token not in {"devpost", "medium", "youtube"}
    ]
    if not opening or not title_tokens:
        return False
    product_prefix = " ".join(title_tokens[: min(2, len(title_tokens))])
    return bool(product_prefix) and opening.startswith(product_prefix)


def _hook_is_grounded(hook: str, facts: list[str]) -> bool:
    hook_tokens = _content_tokens(hook)
    if not hook_tokens:
        return False
    return any(len(hook_tokens & _content_tokens(fact)) >= 2 for fact in facts)


def _grounded_hook_for_slot(*, slot: CoverageSlotPlan, fact: str) -> str:
    return _compress_fact_for_hook(fact)


def _opening_for_slot(*, slot: CoverageSlotPlan, fact: str) -> str:
    opening = _sentence_case(_inline_clause_fact(fact)).rstrip(".")
    return f"{opening}."


def _select_best_fact_for_slot(*, slot: CoverageSlotPlan, facts: list[str], product_name: str) -> str:
    if not facts:
        return _clean_fact_candidate(slot.cluster.section_summary or slot.cluster.headings[0])
    return max(
        (_clean_fact_candidate(fact) for fact in facts if fact.strip()),
        key=lambda fact: _fact_score_for_slot(slot=slot, fact=fact, product_name=product_name),
    )


def _fact_reads_like_clause(value: str) -> bool:
    lowered = " ".join(value.casefold().split())
    return lowered.startswith(
        (
            "when ",
            "if ",
            "because ",
            "since ",
            "while ",
            "for ",
            "users ",
            "teams ",
            "creators ",
            "the backend ",
            "content hub ",
        )
    )


def _inline_clause_fact(value: str) -> str:
    normalized = " ".join(value.split()).strip()
    lowered = normalized.casefold()
    if lowered.startswith("content hub "):
        return normalized
    if lowered.startswith(
        (
            "when ",
            "if ",
            "because ",
            "since ",
            "while ",
            "for ",
            "users ",
            "teams ",
            "creators ",
            "the backend ",
            "the ui runtime ",
            "the document sandbox runtime ",
            "edit mode ",
        )
    ) and normalized[:1].isupper():
        return normalized[:1].lower() + normalized[1:]
    return normalized


def _compress_fact_for_hook(value: str) -> str:
    normalized = _inline_clause_fact(value).rstrip(".")
    if ", " in normalized:
        lead, remainder = normalized.split(", ", 1)
        lower_lead = lead.casefold()
        if lower_lead.startswith(("when ", "if ", "since ", "while ", "for ", "once ")):
            candidate = _sentence_case(remainder.rstrip("."))
            if candidate:
                normalized = candidate
    words = normalized.split()
    if len(words) > 18:
        normalized = " ".join(words[:18]).strip().rstrip(",;:")
        while normalized.casefold().endswith(("the", "a", "an", "to", "for", "with", "of", "and", "or", "because", "when", "is")):
            pieces = normalized.split()
            if len(pieces) <= 6:
                break
            normalized = " ".join(pieces[:-1]).strip()
    return _sentence_case(normalized)


def _sentence_case(value: str) -> str:
    normalized = " ".join(value.split()).strip()
    if not normalized:
        return ""
    return normalized[:1].upper() + normalized[1:]


def _looks_like_templated_lead(value: str) -> bool:
    normalized = _normalize_text(value)
    return normalized.startswith(
        (
            "start with this detail",
            "watch this part first",
            "watch this first",
            "the strongest signal",
            "the fastest win here",
            "the workflow stays smooth because",
            "what separates this from generic tools is",
            "the clearest use case shows up when",
            "creators should steal this first",
        )
    )


def _looks_truncated(value: str) -> bool:
    normalized = " ".join(value.split()).strip().casefold().rstrip(".!?")
    if not normalized:
        return False
    trailing_tokens = ("the", "a", "an", "to", "for", "with", "of", "and", "or", "because", "when", "is")
    return normalized.endswith(trailing_tokens)


def _fact_score_for_slot(*, slot: CoverageSlotPlan, fact: str, product_name: str) -> float:
    lowered = fact.casefold()
    score = len(_content_tokens(fact)) * 0.25
    if _starts_with_product_name(fact, product_name):
        score -= 3.0
    if " is a " in lowered or " is an " in lowered:
        score -= 1.5
    if any(hint in lowered for hint in ("youtube", "subscribers", "watch on", "try it here", "working prototype")):
        score -= 4.0
    if slot.angle_family in {"workflow", "speed-win"} and any(
        hint in lowered for hint in ("start", "select", "generate", "stream", "edit", "delta", "preview", "route")
    ):
        score += 2.0
    if slot.angle_family in {"architecture", "implementation", "risk"} and any(
        hint in lowered for hint in ("backend", "sandbox", "runtime", "orchestrates", "proxy", "models", "fastapi")
    ):
        score += 2.4
    if slot.angle_family in {"proof", "differentiation", "output-quality"} and any(
        hint in lowered for hint in ("thinking mode", "use my voice", "higher-quality", "personal writing style")
    ):
        score += 2.4
    if slot.angle_family in {"use-case", "comparison", "hidden-detail"} and any(
        hint in lowered for hint in ("x tab", "instagram", "linkedin", "280-character", "preview")
    ):
        score += 2.0
    return score


def _clean_fact_candidate(value: str) -> str:
    cleaned = re.sub(r"[*_`]+", "", " ".join(value.split()).strip()).rstrip(".")
    cleaned = re.sub(r"(?i)^one of the key features that sets [^ ]+(?: [^ ]+)? apart is ", "", cleaned).strip()
    separators = (".", ";", " - ")
    for separator in separators:
        if separator in cleaned:
            cleaned = cleaned.split(separator, 1)[0].strip()
            break
    return cleaned.rstrip(",;:")


def _expand_narration_to_target(
    *,
    text: str,
    facts: list[str],
    section_summary: str,
    min_words: int,
    min_characters: int,
) -> str:
    expanded = " ".join(text.split()).strip()
    additions = [f"{fact.rstrip('.')}." for fact in facts]
    if section_summary:
        additions.append(f"The section frames it as {section_summary.rstrip('.')}.")
    while (len(TOKEN_RE.findall(expanded)) < min_words or len(expanded) < min_characters) and additions:
        next_sentence = additions.pop(0)
        if next_sentence.casefold() in expanded.casefold():
            continue
        expanded = f"{expanded} {next_sentence}".strip()
    return expanded


def _trim_narration_to_max_words(text: str, *, max_words: int) -> str:
    normalized = " ".join(text.split()).strip()
    words = normalized.split()
    if len(words) <= max_words:
        return normalized
    trimmed = " ".join(words[:max_words]).rstrip(",;:")
    if trimmed and trimmed[-1] not in ".!?":
        trimmed = f"{trimmed}."
    return trimmed


def _replace_opening_sentence(text: str, new_opening: str) -> str:
    normalized = " ".join(text.split()).strip()
    if not normalized:
        return new_opening
    for delimiter in (". ", "! ", "? "):
        if delimiter in normalized:
            remainder = normalized.split(delimiter, 1)[1].strip()
            return f"{new_opening} {remainder}".strip()
    return f"{new_opening} {normalized}".strip()


def _scrub_marketing_phrases(text: str) -> str:
    cleaned = " ".join(text.split()).strip()
    for source, replacement in MARKETING_REPLACEMENTS.items():
        cleaned = re.sub(re.escape(source), replacement, cleaned, flags=re.IGNORECASE)
    return cleaned


def _sounds_like_generic_marketing(text: str) -> bool:
    lowered = " ".join(text.split()).strip().casefold()
    if not lowered:
        return False
    return any(lowered.startswith(prefix) for prefix in GENERIC_MARKETING_LEADS)
