import json
import asyncio

from brainrot_backend.config import Settings
from brainrot_backend.video_generator.integrations.elevenlabs import (
    NarratorVoiceProfile,
    build_narrator_override,
    build_producer_dynamic_variables,
)
from brainrot_backend.core.models.domain import GeneratedBundle, IngestedSource, ScriptDraft, SourceBrief
from brainrot_backend.core.models.domain import AnglePlan
from brainrot_backend.core.models.enums import SourceKind
from brainrot_backend.video_generator.integrations.elevenlabs import ElevenLabsAgentsClient
from brainrot_backend.video_generator.services.agents import AgentService
from brainrot_backend.video_generator.workers.orchestrator import BatchOrchestrator


def test_build_producer_dynamic_variables_serializes_context():
    source = IngestedSource(
        source_kind=SourceKind.ARTICLE,
        original_url="https://example.com/post",
        title="Example Post",
        markdown="# Title\n\nBody",
        normalized_urls=["https://example.com/post"],
    )
    payload = build_producer_dynamic_variables(
        settings=Settings(),
        batch_id="batch-123",
        source=source,
        requested_count=7,
    )
    assert payload["batch_id"] == "batch-123"
    assert payload["requested_count"] == "7"
    assert json.loads(payload["source_urls"]) == ["https://example.com/post"]
    assert payload["script_min_words"] == "80"


def test_build_narrator_override_only_sets_supported_flags():
    override = build_narrator_override(premium_audio=True)
    assert override == {"tts": {"expressive_mode": True}}


def test_build_narrator_override_can_switch_voice():
    override = build_narrator_override(premium_audio=False, voice_id="voice-123")
    assert override == {"tts": {"voice_id": "voice-123"}}


def test_diversify_script_identity_rotates_intro_styles():
    script = ScriptDraft(
        title="Angle One",
        hook="Original hook",
        narration_text=(
            "Original first sentence. Then it explains the workflow in more detail so the rest of the script "
            "still has enough room to land naturally and stay inside the target timing."
        ),
        caption_text="caption",
        estimated_seconds=26,
        visual_beats=["beat"],
        music_tags=["music"],
        gameplay_tags=["gameplay"],
        source_facts_used=["Thinking Mode inside Adobe Express", "Editable captions for every platform"],
        qa_notes=[],
    )

    first, first_style = BatchOrchestrator._diversify_script_identity(
        script,
        source_facts=["Thinking Mode inside Adobe Express", "Editable captions for every platform"],
        item_index=0,
        occupied_intro_style_ids=set(),
    )
    second, second_style = BatchOrchestrator._diversify_script_identity(
        script,
        source_facts=["Thinking Mode inside Adobe Express", "Editable captions for every platform"],
        item_index=1,
        occupied_intro_style_ids={first_style},
    )

    assert first_style != second_style
    assert first.hook != second.hook
    assert first.narration_text != second.narration_text
    assert first.source_facts_used[0] != second.source_facts_used[0]
    assert "detail that changes the story" not in first.hook.casefold()
    assert "part most people glide past" not in second.hook.casefold()


def test_prepare_script_for_acceptance_preserves_grounded_direct_openai_script():
    script = ScriptDraft(
        title="Architecture angle",
        hook="The backend routes generation work through a section coverage plan.",
        narration_text=(
            "The backend routes generation work through a section coverage plan. "
            "That keeps one short focused on architecture instead of flattening the whole article into one repeated pitch."
        ),
        caption_text="caption",
        estimated_seconds=26,
        visual_beats=["beat"],
        music_tags=["music"],
        gameplay_tags=["gameplay"],
        source_facts_used=[
            "The backend routes generation work through a section coverage plan",
            "Each slot maps to a distinct section cluster",
        ],
        qa_notes=[],
    )

    prepared, style_id = BatchOrchestrator._prepare_script_for_acceptance(
        script,
        source_facts=script.source_facts_used,
        item_index=0,
        occupied_intro_style_ids=set(),
    )

    assert prepared == script
    assert style_id == "grounded"


def test_prepare_script_for_acceptance_preserves_structured_script_identity():
    script = ScriptDraft(
        title="Architecture angle",
        hook="The backend routes generation work through a section coverage plan.",
        narration_text=(
            "The backend routes generation work through a section coverage plan. "
            "That keeps one short focused on architecture instead of flattening the whole article into one repeated pitch."
        ),
        caption_text="caption",
        estimated_seconds=26,
        visual_beats=["beat"],
        music_tags=["music"],
        gameplay_tags=["gameplay"],
        source_facts_used=["The backend routes generation work through a section coverage plan", "Each slot maps to a distinct section cluster"],
        qa_notes=[],
        metadata={"section_ids": ["architecture"], "angle_family": "architecture"},
    )

    prepared, style_id = BatchOrchestrator._prepare_script_for_acceptance(
        script,
        source_facts=script.source_facts_used,
        item_index=0,
        occupied_intro_style_ids=set(),
    )

    assert prepared == script
    assert style_id == "semantic:architecture"


def test_select_narrator_voice_rotates_across_batch():
    client = ElevenLabsAgentsClient.__new__(ElevenLabsAgentsClient)
    client.settings = Settings()
    client.client = None
    client._narrator_voice_profiles = [
        NarratorVoiceProfile(voice_id="voice-a", label="Voice A", source="test"),
        NarratorVoiceProfile(voice_id="voice-b", label="Voice B", source="test"),
        NarratorVoiceProfile(voice_id="voice-c", label="Voice C", source="test"),
    ]

    selected = [
        asyncio.run(
            client.select_narrator_voice(
                batch_id="batch-123",
                item_index=item_index,
                requested_count=5,
            )
        ).voice_id
        for item_index in range(5)
    ]

    assert len(set(selected)) >= 2


def test_validate_generated_bundle_enforces_word_count():
    service = AgentService.__new__(AgentService)
    service.settings = Settings()
    bundle = GeneratedBundle(
        source_brief=SourceBrief(
            canonical_title="Content Hub",
            summary="AI content personalization",
            facts=["Personalized captions"],
            entities=["Content Hub"],
            tone="energetic",
            do_not_drift=["Do not invent product features"],
            source_urls=["https://example.com/post"],
        ),
        angles=[],
        scripts=[
            ScriptDraft(
                title="Angle One",
                hook="This add-on fixes generic captions.",
                narration_text=" ".join(["word"] * 60),
                caption_text="caption",
                estimated_seconds=12,
                visual_beats=["beat"],
                music_tags=["music"],
                gameplay_tags=["gameplay"],
                source_facts_used=["fact"],
                qa_notes=[],
            )
        ],
    )

    try:
        service._validate_generated_bundle(bundle, requested_count=1)  # type: ignore[attr-defined]
    except RuntimeError as exc:
        assert "60 words" in str(exc)
    else:
        raise AssertionError("Expected producer bundle validation to fail for a short script.")


def test_validate_generated_bundle_rejects_generic_marketing_copy():
    service = AgentService.__new__(AgentService)
    service.settings = Settings()
    bundle = GeneratedBundle(
        source_brief=SourceBrief(
            canonical_title="Content Hub",
            summary="AI content personalization",
            facts=["Uses Adobe Express context", "Supports X, Instagram, and LinkedIn"],
            entities=["Content Hub", "Adobe Express"],
            tone="energetic",
            do_not_drift=["Do not invent product features"],
            source_urls=["https://example.com/post"],
        ),
        angles=[],
        scripts=[
            ScriptDraft(
                title="The Future of Content Creation",
                hook="What if AI could enhance your creativity?",
                narration_text=" ".join(["revolutionary"] + ["word"] * 79),
                caption_text="caption",
                estimated_seconds=26,
                visual_beats=["beat"],
                music_tags=["music"],
                gameplay_tags=["gameplay"],
                source_facts_used=["Adobe Express integration", "Thinking Mode"],
                qa_notes=[],
            )
        ],
    )

    try:
        service._validate_generated_bundle(bundle, requested_count=1)  # type: ignore[attr-defined]
    except RuntimeError as exc:
        message = str(exc)
        assert "generic hook starter" in message
        assert "generic marketing phrasing" in message
    else:
        raise AssertionError("Expected producer bundle validation to fail for generic marketing copy.")


def test_validate_generated_bundle_rejects_schema_leaks_in_source_facts():
    service = AgentService.__new__(AgentService)
    service.settings = Settings()
    bundle = GeneratedBundle(
        source_brief=SourceBrief(
            canonical_title="Content Hub",
            summary="AI content personalization",
            facts=["Editable captions", "Thinking Mode"],
            entities=["Content Hub"],
            tone="energetic",
            do_not_drift=["Do not invent product features"],
            source_urls=["https://example.com/post"],
        ),
        angles=[],
        scripts=[
            ScriptDraft(
                title="Editing Loop",
                hook="Content updates without a full rewrite.",
                narration_text=" ".join(["word"] * 80),
                caption_text="caption",
                estimated_seconds=26,
                visual_beats=["beat"],
                music_tags=["music"],
                gameplay_tags=["gameplay"],
                source_facts_used=["Editable captions", "qa_notes"],
                qa_notes=[],
            )
        ],
    )

    try:
        service._validate_generated_bundle(bundle, requested_count=1)  # type: ignore[attr-defined]
    except RuntimeError as exc:
        assert "malformed source_facts_used" in str(exc)
    else:
        raise AssertionError("Expected producer bundle validation to fail for schema leak facts.")


def test_normalize_generated_bundle_repairs_hook_grounding_and_facts():
    service = AgentService.__new__(AgentService)
    service.settings = Settings()
    bundle = GeneratedBundle(
        source_brief=SourceBrief(
            canonical_title="Content Hub",
            summary="AI content personalization",
            facts=["Thinking Mode inside Adobe Express", "Live editable captions for social posts"],
            entities=["Content Hub", "Adobe Express"],
            tone="energetic",
            do_not_drift=["Do not invent product features"],
            source_urls=["https://example.com/post"],
        ),
        angles=[
            AnglePlan(
                title="Editing Loop",
                hook_direction="feature-first",
                audience_frame="creators",
                energy_level="high",
                visual_mood="clean",
                music_mood="driving",
            )
        ],
        scripts=[
            ScriptDraft(
                title="Editing Loop",
                hook="This changes content creation fast.",
                narration_text=" ".join(["contenthub"] * 90),
                caption_text="caption",
                estimated_seconds=26,
                visual_beats=["beat"],
                music_tags=["music"],
                gameplay_tags=["gameplay"],
                source_facts_used=["qa_notes"],
                qa_notes=[],
            )
        ],
    )

    normalized, repair_stats = service._normalize_generated_bundle(bundle)  # type: ignore[attr-defined]

    assert repair_stats["hook_repairs"] == 1
    assert repair_stats["fact_repairs"] == 1
    assert repair_stats["narration_repairs"] == 0
    assert normalized.scripts[0].source_facts_used == [
        "Thinking Mode inside Adobe Express",
        "Live editable captions for social posts",
    ]
    assert normalized.scripts[0].hook == "Thinking Mode inside Adobe Express is where the source gets specific"
    service._validate_generated_bundle(normalized, requested_count=1)  # type: ignore[attr-defined]


def test_normalize_generated_bundle_preserves_existing_slot_identity():
    service = AgentService.__new__(AgentService)
    service.settings = Settings()
    bundle = GeneratedBundle(
        source_brief=SourceBrief(
            canonical_title="Content Hub",
            summary="AI content personalization",
            facts=[
                "Thinking Mode inside Adobe Express",
                "Live editable captions for social posts",
                "Use My Voice analyzes past posts",
            ],
            entities=["Content Hub", "Adobe Express"],
            tone="energetic",
            do_not_drift=["Do not invent product features"],
            source_urls=["https://example.com/post"],
        ),
        angles=[],
        scripts=[
            ScriptDraft(
                title=f"Angle {index}",
                hook=[
                    "Thinking Mode inside Adobe Express keeps the edit grounded",
                    "Live editable captions for social posts speed up packaging",
                    "Use My Voice analyzes past posts before rewriting",
                ][index],
                narration_text=f"Section {index} explains a different workflow detail. It keeps the rest of the workflow moving with real details from the source." + (" more" * 90),
                caption_text="caption",
                estimated_seconds=26,
                visual_beats=["beat"],
                music_tags=["music"],
                gameplay_tags=["gameplay"],
                source_facts_used=[
                    "Thinking Mode inside Adobe Express",
                    "Live editable captions for social posts",
                    "Use My Voice analyzes past posts",
                ],
                qa_notes=[],
                metadata={
                    "section_ids": [f"section-{index}"],
                    "angle_family": f"family-{index}",
                },
            )
            for index in range(3)
        ],
    )

    normalized, repair_stats = service._normalize_generated_bundle(bundle)  # type: ignore[attr-defined]

    hooks = [script.hook for script in normalized.scripts]
    openings = [script.narration_text.split(".")[0].strip() for script in normalized.scripts]
    assert len(set(hooks)) == 3
    assert len(set(openings)) == 3
    assert repair_stats["hook_repairs"] == 0
    assert normalized.scripts[0].metadata["section_ids"] == ["section-0"]
    assert normalized.scripts[0].metadata["angle_family"] == "family-0"


def test_custom_llm_chat_payload_is_normalized_for_openai():
    service = AgentService.__new__(AgentService)
    service.settings = type("SettingsStub", (), {"openai_model": "gpt-5"})()
    path, payload = service._normalize_custom_llm_payload(  # type: ignore[attr-defined]
        {
            "messages": [{"role": "user", "content": "hello"}],
            "model": "gpt-5",
            "stream": False,
            "user_id": "user-123",
            "elevenlabs_extra_body": {"batch_id": "batch-123"},
            "tools": [
                {
                    "type": "function",
                    "function": {
                        "name": "submit_script_bundle",
                        "parameters": {"type": "object"},
                    },
                }
            ],
        },
        endpoint_hint="chat_completions",
    )
    assert path == "/chat/completions"
    assert payload["stream"] is True
    assert payload["user"] == "user-123"
    assert "user_id" not in payload
    assert "elevenlabs_extra_body" not in payload
    assert payload["max_tokens"] == 16384
    assert "tool_choice" not in payload


def test_custom_llm_responses_payload_is_normalized_for_openai():
    service = AgentService.__new__(AgentService)
    service.settings = type("SettingsStub", (), {"openai_model": "gpt-5"})()
    path, payload = service._normalize_custom_llm_payload(  # type: ignore[attr-defined]
        {
            "input": "hello",
            "stream": False,
        },
        endpoint_hint="responses",
    )
    assert path == "/responses"
    assert payload["model"] == "gpt-5"
    assert payload["stream"] is True


def test_custom_llm_responses_drops_invalid_max_output_tokens():
    service = AgentService.__new__(AgentService)
    service.settings = type("SettingsStub", (), {"openai_model": "gpt-5"})()
    _, payload = service._normalize_custom_llm_payload(  # type: ignore[attr-defined]
        {
            "input": "hello",
            "max_output_tokens": 0,
        },
        endpoint_hint="responses",
    )
    assert "max_output_tokens" not in payload
