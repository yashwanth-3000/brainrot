from __future__ import annotations

from crewai import Agent, LLM, Task

from brainrot_backend.video_generator.producer_crewai.models import CoverageSlotPlan, CrewAIScriptPayload
from brainrot_backend.video_generator.producer_crewai.prompts import (
    build_repair_task_prompt,
    build_writer_task_prompt,
    repair_system_prompt,
    writer_system_prompt,
)


def _uses_max_completion_tokens(model: str) -> bool:
    normalized = model.rsplit("/", 1)[-1].casefold()
    return normalized.startswith("gpt-5")


class OpenAICompatibleCrewAILLM(LLM):
    def _prepare_completion_params(self, messages, tools=None):
        params = super()._prepare_completion_params(messages, tools)
        if _uses_max_completion_tokens(self.model):
            if "max_tokens" in params:
                params["max_completion_tokens"] = params.pop("max_tokens")
            params.pop("stop", None)
        return params


def build_crewai_llm(
    *,
    model: str,
    api_key: str,
    base_url: str,
    temperature: float = 0.2,
    max_tokens: int = 2200,
    reasoning_effort: str | None = None,
) -> LLM:
    return OpenAICompatibleCrewAILLM(
        model=model,
        api_key=api_key,
        base_url=base_url,
        temperature=temperature,
        max_tokens=max_tokens,
        reasoning_effort=reasoning_effort,
    )


def build_writer_agent(*, llm: LLM) -> Agent:
    return Agent(
        role="Section Coverage Script Writer",
        goal="Write one source-grounded short-form script for a specific article section cluster.",
        backstory=writer_system_prompt(),
        llm=llm,
        verbose=False,
        allow_delegation=False,
        max_iter=6,
    )


def build_repair_agent(*, llm: LLM) -> Agent:
    return Agent(
        role="Section Coverage Script Repairer",
        goal="Repair one rejected script without breaking section coverage or semantic diversity.",
        backstory=repair_system_prompt(),
        llm=llm,
        verbose=False,
        allow_delegation=False,
        max_iter=6,
    )


def build_writer_task(
    *,
    agent: Agent,
    slot: CoverageSlotPlan,
    source_title: str,
    canonical_summary: str,
    section_count: int,
) -> Task:
    return Task(
        name=f"write-{slot.slot_id}",
        description=build_writer_task_prompt(
            slot=slot,
            source_title=source_title,
            canonical_summary=canonical_summary,
            section_count=section_count,
        ),
        expected_output="A single structured short-form script payload.",
        agent=agent,
        async_execution=True,
        output_pydantic=CrewAIScriptPayload,
    )


def build_repair_task(
    *,
    agent: Agent,
    slot: CoverageSlotPlan,
    source_title: str,
    canonical_summary: str,
    current_script_json: str,
    validation_feedback: str,
) -> Task:
    return Task(
        name=f"repair-{slot.slot_id}",
        description=build_repair_task_prompt(
            slot=slot,
            source_title=source_title,
            canonical_summary=canonical_summary,
            current_script_json=current_script_json,
            validation_feedback=validation_feedback,
        ),
        expected_output="A repaired structured short-form script payload.",
        agent=agent,
        async_execution=True,
        output_pydantic=CrewAIScriptPayload,
    )
