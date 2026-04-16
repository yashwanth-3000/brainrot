from brainrot_backend.config import Settings
from brainrot_backend.core.models.domain import AnglePlan, GeneratedBundle, ScriptDraft, SourceBrief
from brainrot_backend.video_generator.producer_crewai.flow import CrewAIProducerFlow
from brainrot_backend.video_generator.producer_crewai.models import CoveragePlan, CoverageSlotPlan, CrewAIScriptPayload, SectionCluster
from brainrot_backend.video_generator.producer_crewai.tasks import build_crewai_llm
from brainrot_backend.video_generator.producer_crewai.sectioning import build_coverage_plan
from brainrot_backend.video_generator.services.agents import AgentService


HEADING_RICH_MARKDOWN = """
# Content Hub

## Overview

Content Hub turns long-form source material into social-ready assets.

## Thinking Mode

Thinking Mode pauses before writing and weighs multiple source-backed directions.
It is designed to keep the scripts grounded instead of jumping to generic copy.

## Use My Voice

Use My Voice studies previous posts so the generated output keeps the creator's phrasing style.
That matters when the account already has a recognizable tone.

## Platform Output

The product generates captions and posts for X, Instagram, and LinkedIn.
Each platform gets a different packaging layer for the same source material.

## Workflow

Teams can move from one article link to multiple ready-to-publish social assets.
The workflow is meant to reduce manual rewriting across channels.

## Validation

The system checks grounded facts, pacing, and duplicate ideas before anything ships.
"""


SPARSE_MARKDOWN = """
This tool captures source material and turns it into fast social output.

It uses one workflow for ingest, another for planning, and another for packaging.

Creators care about voice consistency, platform fit, and speed.

The main workflow still depends on source grounding and clean editing loops.

Teams also need a clear validation layer so the output does not drift.
"""


def test_build_coverage_plan_uses_distinct_sections_and_angles():
    plan = build_coverage_plan(
        title="Content Hub",
        markdown=HEADING_RICH_MARKDOWN,
        requested_count=5,
    )

    assert plan.actual_count == 5
    assert plan.planned_count >= 5
    assert plan.section_count >= 5
    assert len({slot.cluster.section_ids[0] for slot in plan.slots if slot.cluster.section_ids}) == 5
    assert len({slot.angle_family for slot in plan.slots}) == 5


def test_build_coverage_plan_deprioritizes_noisy_overview_sections():
    markdown = """
# Content Hub | Devpost

Content Hub Adobe Add On - YouTube
Tap to unmute
[Watch on](https://youtube.com/demo)

## Project Story

Content Hub turns long-form source material into social-ready captions.

## How Does Content Hub Work?

Users capture the design, choose a platform, then the backend applies platform constraints before generation starts.

## Thinking Mode

Thinking Mode pauses before writing and weighs multiple grounded directions.

## Edit Mode

Edit Mode treats changes as deltas instead of full rewrites.
"""
    plan = build_coverage_plan(
        title="Content Hub",
        markdown=markdown,
        requested_count=5,
    )

    first_heading = plan.slots[0].cluster.headings[0]
    assert first_heading != "Content Hub | Devpost"
    assert "How Does Content Hub Work?" in {slot.cluster.headings[0] for slot in plan.slots}


def test_build_coverage_plan_splits_sparse_markdown_into_minimum_slots():
    plan = build_coverage_plan(
        title="Sparse Article",
        markdown=SPARSE_MARKDOWN,
        requested_count=5,
    )

    assert plan.actual_count == 5
    assert plan.section_count >= 5
    assert len(plan.slots) == 5


def test_build_coverage_plan_prefers_semantic_angle_matches():
    markdown = """
## Thinking Mode

Thinking Mode pauses before writing and performs deeper reasoning before generation starts.

## Backend architecture

The backend orchestrates vision extraction, generation streaming, and reasoning summaries.

## Edit Mode

Edit Mode treats edits as deltas instead of full regenerations.

## X Tab

The X tab enforces a 280-character limit and shows a tweet-style preview.

## Use My Voice

Use My Voice adapts output to match the writer's tone and phrasing.
"""
    plan = build_coverage_plan(
        title="Content Hub",
        markdown=markdown,
        requested_count=5,
    )

    headings_to_angles = {
        slot.cluster.headings[0]: slot.angle_family
        for slot in plan.slots
    }
    assert headings_to_angles["Thinking Mode"] in {"differentiation", "proof", "output-quality"}
    assert headings_to_angles["Backend architecture"] in {"architecture", "implementation", "risk"}
    assert headings_to_angles["Edit Mode"] == "speed-win"


def test_build_coverage_plan_deprioritizes_openai_style_boilerplate_sections():
    markdown = """
## Introducing GPT-5.3-Codex-Spark

GPT-5.3-Codex-Spark is the fastest coding model in the release and it is tuned for low-latency agent loops.

## Coding

The model targets code editing, tool use, and fast iterative workflows across repositories.

## Powered by Cerebras

Inference runs on Cerebras so token delivery is optimized for quick turn-around in coding sessions.

## Availability & details

The release is available in the API and includes rollout details for teams adopting it today.

## Latency improvements for all models

The release reduces response latency across the broader model family so interactive coding loops feel faster.

## What's next

Future rollout notes and follow-up work will be shared later.

## Keep reading

Read the related launch posts and product updates.

## Author

OpenAI team
"""
    plan = build_coverage_plan(
        title="Introducing GPT-5.3-Codex-Spark | OpenAI",
        markdown=markdown,
        requested_count=5,
    )

    headings = {slot.cluster.headings[0] for slot in plan.slots}
    assert "What's next" not in headings
    assert "Keep reading" not in headings
    assert "Author" not in headings


def test_stabilize_payload_reanchors_hook_and_facts_to_assigned_section():
    settings = Settings()
    flow = CrewAIProducerFlow(settings=settings)
    assigned_facts = [
        "Codex-Spark is rolling out today as a research preview for ChatGPT Pro users in the latest versions of the Codex app, CLI, and VS Code extension",
        "Because it runs on specialized low-latency hardware, usage is governed by a separate rate limit that may adjust based on demand during the research preview",
    ]
    slot = CoverageSlotPlan(
        slot_index=4,
        slot_id="slot-5",
        angle_family="workflow",
        semantic_objective="workflow",
        hook_direction="process-first",
        audience_frame="builders",
        visual_mood="systematic",
        music_mood="driving",
        cluster=SectionCluster(
            cluster_id="cluster-5",
            position=5,
            section_ids=["section-7"],
            headings=["Availability & details"],
            section_summary="Availability details cover the rollout target, surfaces, and rate limit constraints.",
            facts=assigned_facts,
            entities=["Codex-Spark", "ChatGPT Pro", "Codex app", "CLI", "VS Code extension"],
            source_span={"start_line": 1, "end_line": 8},
            priority_score=2.0,
            raw_markdown="## Availability & details",
        ),
    )
    payload = CrewAIScriptPayload(
        title="Codex-Spark rollout details",
        hook="Cerebras capacity is ramping up for early experiments",
        narration_text=(
            "The rollout is happening in the latest Codex surfaces today and the separate rate limit matters because the model is running on specialized hardware. "
            "That changes how teams should plan usage during the research preview while still keeping the workflow fast for real coding sessions."
        ),
        caption_text="rollout details",
        visual_beats=["beat 1"],
        music_tags=["driving"],
        gameplay_tags=["systematic"],
        source_facts_used=[
            "We’re working with Cerebras to ramp up datacenter capacity while the preview expands",
            "The model is designed for real-time coding",
        ],
        qa_notes=[],
    )
    brief = SourceBrief(
        canonical_title="Introducing GPT-5.3-Codex-Spark | OpenAI",
        summary="Codex-Spark rollout details.",
        facts=assigned_facts,
        entities=["Codex-Spark"],
        tone="specific, fast, grounded",
        do_not_drift=["Keep each script tied to its assigned article section."],
        source_urls=["https://openai.com/index/introducing-gpt-5-3-codex-spark/"],
    )

    stabilized = flow._stabilize_payload(payload=payload, slot=slot, source_brief=brief)
    issues = flow._validate_slot_payloads(
        payloads={slot.slot_id: stabilized},
        coverage_plan=CoveragePlan(
            requested_count=5,
            planned_count=5,
            actual_count=1,
            section_count=1,
            sections=[],
            slots=[slot],
            fallback_flags=[],
        ),
        source_brief=brief,
    )

    assert stabilized.source_facts_used[:2] == assigned_facts
    assert "ChatGPT Pro users" in stabilized.hook or "separate rate limit" in stabilized.hook
    assert not any("hook is not grounded" in problem for issue in issues for problem in issue.problems)
    assert not any("source_facts_used drift away" in problem for issue in issues for problem in issue.problems)


def test_validate_slot_payloads_allows_single_fact_clusters_to_pass_grounding():
    settings = Settings()
    flow = CrewAIProducerFlow(settings=settings)
    assigned_fact = "Anthropic expanded its partnership with Google and Broadcom for multiple gigawatts of next-generation compute."
    slot = CoverageSlotPlan(
        slot_index=4,
        slot_id="slot-5",
        angle_family="risk",
        semantic_objective="risk",
        hook_direction="constraint-first",
        audience_frame="builders",
        visual_mood="serious",
        music_mood="driving",
        cluster=SectionCluster(
            cluster_id="cluster-5",
            position=5,
            section_ids=["section-9"],
            headings=["Compute partnership"],
            section_summary="The section focuses on Anthropic expanding infrastructure partnerships for future compute capacity.",
            facts=[assigned_fact],
            entities=["Anthropic", "Google", "Broadcom"],
            source_span={"start_line": 1, "end_line": 4},
            priority_score=2.0,
            raw_markdown="## Compute partnership",
        ),
    )
    payload = CrewAIScriptPayload(
        title="Anthropic expands compute capacity",
        hook="Anthropic expands compute capacity with Google and Broadcom.",
        narration_text=(
            "Anthropic says it is expanding its partnership with Google and Broadcom for multiple gigawatts of next-generation compute. "
            "That matters because model progress is no longer just about better training ideas. "
            "It also depends on whether the company can lock in enough infrastructure to ship the next jump in capability without bottlenecks."
        ),
        caption_text="compute capacity",
        visual_beats=["beat 1"],
        music_tags=["driving"],
        gameplay_tags=["serious"],
        source_facts_used=[
            assigned_fact,
            "The company frames compute access as a real constraint on future model rollout and scaling.",
        ],
        qa_notes=[],
    )
    brief = SourceBrief(
        canonical_title="Introducing Claude Opus 4.7",
        summary="Anthropic expands its compute partnerships.",
        facts=[assigned_fact],
        entities=["Anthropic", "Google", "Broadcom"],
        tone="specific, fast, grounded",
        do_not_drift=["Keep each script tied to its assigned article section."],
        source_urls=["https://www.anthropic.com/news/claude-opus-4-7"],
    )

    stabilized = flow._stabilize_payload(payload=payload, slot=slot, source_brief=brief)
    issues = flow._validate_slot_payloads(
        payloads={slot.slot_id: stabilized},
        coverage_plan=CoveragePlan(
            requested_count=5,
            planned_count=5,
            actual_count=1,
            section_count=1,
            sections=[],
            slots=[slot],
            fallback_flags=[],
        ),
        source_brief=brief,
    )

    assert not any("source_facts_used drift away" in problem for issue in issues for problem in issue.problems)


def test_stabilize_payload_trims_narration_to_max_words():
    settings = Settings()
    flow = CrewAIProducerFlow(settings=settings)
    slot = CoverageSlotPlan(
        slot_index=0,
        slot_id="slot-1",
        angle_family="workflow",
        semantic_objective="workflow",
        hook_direction="process-first",
        audience_frame="builders",
        visual_mood="systematic",
        music_mood="driving",
        cluster=SectionCluster(
            cluster_id="cluster-1",
            position=1,
            section_ids=["section-1"],
            headings=["Workflow"],
            section_summary="The workflow moves from ingest to generation and then validation.",
            facts=[
                "The workflow moves from ingest to generation and then validation",
                "Teams review the output before publishing",
            ],
            entities=["Workflow"],
            source_span={"start_line": 1, "end_line": 4},
            priority_score=2.0,
            raw_markdown="## Workflow",
        ),
    )
    payload = CrewAIScriptPayload(
        title="Workflow rollout",
        hook="The workflow moves from ingest to generation and then validation",
        narration_text=" ".join(["workflow"] * 110),
        caption_text="workflow rollout",
        visual_beats=["beat 1"],
        music_tags=["driving"],
        gameplay_tags=["systematic"],
        source_facts_used=["The workflow moves from ingest to generation and then validation"],
        qa_notes=[],
    )
    brief = SourceBrief(
        canonical_title="Workflow",
        summary="The workflow moves from ingest to generation and then validation.",
        facts=slot.cluster.facts,
        entities=["Workflow"],
        tone="specific, fast, grounded",
        do_not_drift=["Keep each script tied to its assigned article section."],
        source_urls=["https://example.com/workflow"],
    )

    stabilized = flow._stabilize_payload(payload=payload, slot=slot, source_brief=brief)

    assert len(stabilized.narration_text.split()) == settings.script_max_words


def test_validate_generated_bundle_rejects_semantic_overlap_metadata():
    service = AgentService.__new__(AgentService)
    service.settings = Settings()
    bundle = GeneratedBundle(
        source_brief=SourceBrief(
            canonical_title="Content Hub",
            summary="A workflow tool",
            facts=["Thinking Mode pauses before writing", "Use My Voice studies previous posts"],
            entities=["Content Hub"],
            tone="specific",
            do_not_drift=["Do not invent product features"],
            source_urls=["https://example.com/post"],
        ),
        angles=[
            AnglePlan(
                title="Angle 1",
                hook_direction="detail-first",
                audience_frame="builders",
                energy_level="high",
                visual_mood="focused",
                music_mood="driving",
                angle_family="workflow",
                section_id="section-1",
            ),
            AnglePlan(
                title="Angle 2",
                hook_direction="detail-first",
                audience_frame="builders",
                energy_level="high",
                visual_mood="focused",
                music_mood="driving",
                angle_family="workflow",
                section_id="section-1",
            ),
        ],
        scripts=[
            ScriptDraft(
                title="Angle 1",
                hook="Thinking Mode pauses before writing",
                narration_text="Thinking Mode pauses before writing. " + ("word " * 90),
                caption_text="caption",
                estimated_seconds=26,
                visual_beats=["beat"],
                music_tags=["music"],
                gameplay_tags=["gameplay"],
                source_facts_used=["Thinking Mode pauses before writing", "Use My Voice studies previous posts"],
                qa_notes=[],
                metadata={"section_ids": ["section-1"], "angle_family": "workflow"},
            ),
            ScriptDraft(
                title="Angle 2",
                hook="Use My Voice studies previous posts",
                narration_text="Use My Voice studies previous posts. " + ("word " * 90),
                caption_text="caption",
                estimated_seconds=26,
                visual_beats=["beat"],
                music_tags=["music"],
                gameplay_tags=["gameplay"],
                source_facts_used=["Thinking Mode pauses before writing", "Use My Voice studies previous posts"],
                qa_notes=[],
                metadata={"section_ids": ["section-1"], "angle_family": "workflow"},
            ),
        ],
    )

    try:
        service._validate_generated_bundle(bundle, requested_count=2)  # type: ignore[attr-defined]
    except RuntimeError as exc:
        message = str(exc)
        assert "reuses an angle_family" in message
        assert "reuses a section cluster" in message
        assert "reuses a primary fact cluster" in message
    else:
        raise AssertionError("Expected semantic-overlap validation to fail.")


def test_build_crewai_llm_uses_max_completion_tokens_for_gpt5_models():
    llm = build_crewai_llm(
        model="gpt-5.4-mini",
        api_key="test-key",
        base_url="https://api.openai.com/v1",
        max_tokens=2500,
        reasoning_effort="low",
    )

    params = llm._prepare_completion_params("hello")

    assert params["model"] == "gpt-5.4-mini"
    assert params["max_completion_tokens"] == 2500
    assert "max_tokens" not in params
    assert "stop" not in params
    assert params["reasoning_effort"] == "low"


def test_build_crewai_llm_keeps_max_tokens_for_non_gpt5_models():
    llm = build_crewai_llm(
        model="gpt-4o-mini",
        api_key="test-key",
        base_url="https://api.openai.com/v1",
        max_tokens=1800,
    )

    params = llm._prepare_completion_params("hello")

    assert params["model"] == "gpt-4o-mini"
    assert params["max_tokens"] == 1800
    assert "max_completion_tokens" not in params
