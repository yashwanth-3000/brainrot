from brainrot_backend.config import Settings
from brainrot_backend.core.models.domain import AnglePlan, GeneratedBundle, ScriptDraft, SourceBrief
from brainrot_backend.video_generator.producer_crewai.flow import (
    CrewAIProducerFlow,
    TOKEN_RE,
    _trim_narration_to_max_words,
)
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

    # After the trim+stabilize fix, word count is measured with the same
    # tokenizer the validator uses (TOKEN_RE), not str.split(). The trim
    # guarantees the count is at most script_max_words.
    assert len(TOKEN_RE.findall(stabilized.narration_text)) <= settings.script_max_words
    # And we must be meaningfully close to the max (within 10 words) so we
    # are not silently under-trimming.
    assert (
        len(TOKEN_RE.findall(stabilized.narration_text))
        >= settings.script_max_words - 10
    )


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


DEVPOST_STYLE_COLLAPSED_MARKDOWN = """
Agentic AI Hackathon Powered by Microsoft is a global online hackathon for builders who want to ship agentic applications.

Participants will build, test, and publish multi-agent systems that can plan, use tools, and act on behalf of users.

The sponsor provides access to Azure OpenAI, Microsoft Copilot Studio, and a pool of compute credits reserved for finalists.

Eligible projects must integrate at least two agentic patterns: autonomous planning, tool use, retrieval grounding, or multi-agent coordination.

Judging rewards working prototypes, clean architecture diagrams, and demos that show the agent handling a realistic failure path.

Winners split a $150,000 prize pool and earn a mentoring session with the Azure AI Foundry team.

The schedule runs five weeks with weekly office hours, a midpoint demo milestone, and a final submission gate 48 hours before judging.

Submission rules require a short demo video, a public repo, a deployment link, and a one-page architecture writeup.
"""


def test_build_coverage_plan_assigns_unique_anchor_per_slot_for_collapsed_markdown():
    """Regression for the devpost-style source that collapsed everything under the article title.

    Previously the planner produced 5 clusters that all shared the same "first fact", which
    triggered an unwinnable 'primary fact cluster overlaps with another slot' repair loop.
    """
    plan = build_coverage_plan(
        title="Agentic AI Hackathon Powered by Microsoft",
        markdown=DEVPOST_STYLE_COLLAPSED_MARKDOWN,
        requested_count=5,
    )

    assert len(plan.slots) == 5

    anchor_keys = [" ".join(slot.anchor_fact.casefold().split()).rstrip(".") for slot in plan.slots]
    assert all(anchor_keys), "every slot must have an anchor fact"
    assert len(set(anchor_keys)) == len(anchor_keys), (
        f"slots must have globally unique anchor facts, got {anchor_keys}"
    )

    angle_families = [slot.angle_family for slot in plan.slots]
    assert len(set(angle_families)) == len(angle_families), (
        f"slots must have unique angle families, got {angle_families}"
    )

    headings = [slot.cluster.headings[0] for slot in plan.slots if slot.cluster.headings]
    assert len(set(headings)) == len(headings), (
        f"slots must have distinct primary headings even when source has no H1/H2, got {headings}"
    )


def test_enforce_cross_slot_uniqueness_rescues_colliding_payloads():
    settings = Settings()
    flow = CrewAIProducerFlow(settings=settings)
    plan = build_coverage_plan(
        title="Agentic AI Hackathon Powered by Microsoft",
        markdown=DEVPOST_STYLE_COLLAPSED_MARKDOWN,
        requested_count=5,
    )
    source_brief = SourceBrief(
        canonical_title="Agentic AI Hackathon Powered by Microsoft",
        summary="A hackathon for agentic apps sponsored by Microsoft.",
        facts=[fact for slot in plan.slots for fact in slot.cluster.facts][:10],
        entities=["Microsoft", "Azure"],
        tone="specific, fast, grounded",
        do_not_drift=["Keep each script tied to its assigned article section."],
        source_urls=["https://ai-agentic-hackathon.devpost.com"],
    )

    duplicate_fact = plan.slots[0].cluster.facts[0] if plan.slots[0].cluster.facts else plan.slots[0].anchor_fact
    payloads: dict[str, CrewAIScriptPayload] = {}
    for slot in plan.slots:
        payloads[slot.slot_id] = CrewAIScriptPayload(
            title="Agentic hackathon overview",
            hook="Build agentic apps with Microsoft",
            narration_text="Agentic apps need planning, tool use, and grounded retrieval. " + ("word " * 85),
            caption_text="agentic hackathon",
            visual_beats=["beat 1"],
            music_tags=["driving"],
            gameplay_tags=["systematic"],
            source_facts_used=[duplicate_fact, "Winners split a $150,000 prize pool"],
            qa_notes=[],
        )

    flow._enforce_cross_slot_uniqueness(
        payloads=payloads,
        coverage_plan=plan,
        source_brief=source_brief,
    )

    primary_keys = [
        " ".join(payloads[slot.slot_id].source_facts_used[0].casefold().split()).rstrip(".")
        for slot in plan.slots
    ]
    assert len(set(primary_keys)) == len(primary_keys), (
        f"cross-slot coordinator must guarantee unique primary facts, got {primary_keys}"
    )

    titles = [payloads[slot.slot_id].title for slot in plan.slots]
    hooks = [payloads[slot.slot_id].hook for slot in plan.slots]
    assert len({title.casefold() for title in titles}) == len(titles)
    assert len({hook.casefold() for hook in hooks}) == len(hooks)

    issues = flow._validate_slot_payloads(
        payloads=payloads,
        coverage_plan=plan,
        source_brief=source_brief,
    )
    overlap_problems = [
        problem
        for issue in issues
        for problem in issue.problems
        if "overlaps with another slot" in problem
    ]
    assert overlap_problems == [], f"no overlap problems expected, got {overlap_problems}"


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


def test_trim_narration_uses_validator_tokenizer_for_numeric_text():
    """Regression: numeric tokens like '3.1' tokenize to TWO words for the
    validator (TOKEN_RE) but ONE word for str.split(). Trimming with
    str.split() left scripts at 101-105 validator words and trapped the
    repair loop. The trimmer must use the same tokenization as the
    validator so post-trim count is always <= max_words."""

    settings = Settings()
    text = "The release covers 3.1, 3.2, 3.3 and Days 1-4 of the rollout. " * 30
    trimmed = _trim_narration_to_max_words(text, max_words=settings.script_max_words)
    assert len(TOKEN_RE.findall(trimmed)) <= settings.script_max_words, (
        f"expected <= {settings.script_max_words} validator tokens after trim, "
        f"got {len(TOKEN_RE.findall(trimmed))}"
    )


def test_trim_narration_prefers_sentence_boundary():
    """The trimmer should round down to a sentence boundary when one fits, so
    the narration never ends mid-thought."""

    text = (
        "Hour one cleans the source. "
        "Hour two writes the script. "
        "Hour three records narration. "
        "Hour four renders the video."
    )
    trimmed = _trim_narration_to_max_words(text, max_words=10)
    assert trimmed.endswith(".")
    assert "mid" not in trimmed


def test_stabilize_payload_rewrites_opening_when_it_repeats_the_hook():
    """Regression for the 'opening repeats the hook' validator failure that
    kept slot 3/4 in a repair loop. The stabilizer must rewrite the opening
    deterministically from the slot's anchor fact instead of waiting on the
    LLM to fix it."""

    settings = Settings()
    flow = CrewAIProducerFlow(settings=settings)
    hook = "The Generate tab orchestrates ingest planning and packaging"
    slot = CoverageSlotPlan(
        slot_index=0,
        slot_id="slot-1",
        angle_family="workflow",
        semantic_objective="generate",
        hook_direction="process-first",
        audience_frame="builders",
        visual_mood="systematic",
        music_mood="driving",
        anchor_fact="The Generate tab orchestrates ingest planning and packaging",
        cluster=SectionCluster(
            cluster_id="cluster-1",
            position=1,
            section_ids=["section-1"],
            headings=["1. Generate Tab"],
            section_summary="The Generate tab routes the source through ingest, planning and packaging.",
            facts=[
                "The Generate tab orchestrates ingest planning and packaging",
                "Each step writes status updates back to the operator console",
            ],
            entities=["Generate Tab"],
            source_span={"start_line": 1, "end_line": 4},
            priority_score=2.0,
            raw_markdown="## 1. Generate Tab",
        ),
    )
    narration = (
        f"{hook}. "
        "Each step writes status updates back to the operator console. "
        "Hour one cleans the source. "
        "Hour two writes the script. "
        "Hour three records narration. "
        "Hour four renders the video. "
        "The team can review the output before publishing."
    )
    # Pad so we are above min_words / min_characters before stabilization.
    narration = narration + " " + " ".join(["operators iterate."] * 30)
    payload = CrewAIScriptPayload(
        title="Generate tab routes",
        hook=hook,
        narration_text=narration,
        caption_text="generate tab routes",
        visual_beats=["beat 1"],
        music_tags=["driving"],
        gameplay_tags=["systematic"],
        source_facts_used=[
            "The Generate tab orchestrates ingest planning and packaging",
            "Each step writes status updates back to the operator console",
        ],
        qa_notes=[],
    )
    brief = SourceBrief(
        canonical_title="img-crafter",
        summary="img-crafter routes source content through ingest, planning and packaging stages.",
        facts=slot.cluster.facts,
        entities=["Generate Tab"],
        tone="specific, fast, grounded",
        do_not_drift=["Keep each script tied to its assigned article section."],
        source_urls=["https://example.com/img-crafter"],
    )

    stabilized = flow._stabilize_payload(payload=payload, slot=slot, source_brief=brief)
    plan = CoveragePlan(
        requested_count=1, planned_count=1, actual_count=1, section_count=1, slots=[slot],
    )
    issues = flow._validate_slot_payloads(
        payloads={slot.slot_id: stabilized},
        coverage_plan=plan,
        source_brief=brief,
    )

    problem_strings = [problem for issue in issues for problem in issue.problems]
    assert "opening repeats the hook" not in problem_strings, (
        f"stabilizer must auto-fix opening==hook, but validator still saw: {problem_strings}"
    )


def test_validate_slot_payloads_accepts_within_word_tolerance():
    """The validator must accept narrations that drift by up to
    settings.script_word_tolerance words past the target window. This is
    the safety net for the 101-105-word writer drift the user kept hitting
    on Devpost-style sources with numeric section IDs."""

    settings = Settings()
    assert settings.script_word_tolerance >= 5, (
        "script_word_tolerance should default to a small positive value so "
        "we never enter the validator loop the user reported"
    )

    flow = CrewAIProducerFlow(settings=settings)
    slot = CoverageSlotPlan(
        slot_index=0,
        slot_id="slot-1",
        angle_family="workflow",
        semantic_objective="generate",
        hook_direction="process-first",
        audience_frame="builders",
        visual_mood="systematic",
        music_mood="driving",
        anchor_fact="The Generate tab orchestrates ingest planning and packaging",
        cluster=SectionCluster(
            cluster_id="cluster-1",
            position=1,
            section_ids=["section-1"],
            headings=["1. Generate Tab"],
            section_summary="The Generate tab routes the source through ingest, planning and packaging.",
            facts=[
                "The Generate tab orchestrates ingest planning and packaging",
                "Each step writes status updates back to the operator console",
            ],
            entities=["Generate Tab"],
            source_span={"start_line": 1, "end_line": 4},
            priority_score=2.0,
            raw_markdown="## 1. Generate Tab",
        ),
    )

    # Build a narration whose validator-visible TOKEN_RE count is exactly
    # settings.script_max_words + 4, i.e. inside the tolerance band.
    target_total = settings.script_max_words + 4
    filler = ["operators"] * target_total
    narration = " ".join(filler) + "."

    payload = CrewAIScriptPayload(
        title="Generate tab routes",
        hook="The Generate tab orchestrates ingest planning and packaging end to end",
        narration_text=narration,
        caption_text="generate tab routes",
        visual_beats=["beat 1"],
        music_tags=["driving"],
        gameplay_tags=["systematic"],
        source_facts_used=[
            "The Generate tab orchestrates ingest planning and packaging",
            "Each step writes status updates back to the operator console",
        ],
        qa_notes=[],
    )

    brief = SourceBrief(
        canonical_title="img-crafter",
        summary="img-crafter routes source content through ingest, planning and packaging stages.",
        facts=slot.cluster.facts,
        entities=["Generate Tab"],
        tone="specific, fast, grounded",
        do_not_drift=["Keep each script tied to its assigned article section."],
        source_urls=["https://example.com/img-crafter"],
    )

    plan = CoveragePlan(
        requested_count=1, planned_count=1, actual_count=1, section_count=1, slots=[slot],
    )
    issues = flow._validate_slot_payloads(
        payloads={slot.slot_id: payload},
        coverage_plan=plan,
        source_brief=brief,
    )
    problem_strings = [problem for issue in issues for problem in issue.problems]
    assert not any("narration word count" in problem for problem in problem_strings), (
        f"validator should accept word counts within tolerance, but got: {problem_strings}"
    )
