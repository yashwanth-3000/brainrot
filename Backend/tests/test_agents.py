import json

from brainrot_backend.config import Settings
from brainrot_backend.video_generator.integrations.elevenlabs import (
    build_narrator_override,
    build_producer_dynamic_variables,
)
from brainrot_backend.shared.models.domain import GeneratedBundle, IngestedSource, ScriptDraft, SourceBrief
from brainrot_backend.shared.models.domain import AnglePlan
from brainrot_backend.shared.models.enums import SourceKind
from brainrot_backend.video_generator.services.agents import AgentService


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
    assert normalized.scripts[0].hook == "Thinking Mode inside Adobe Express"
    service._validate_generated_bundle(normalized, requested_count=1)  # type: ignore[attr-defined]


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
