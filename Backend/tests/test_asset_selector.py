from brainrot_backend.config import Settings
from brainrot_backend.shared.models.domain import AssetRecord, ScriptDraft
from brainrot_backend.shared.models.enums import AssetKind
from brainrot_backend.video_generator.render.assets import AssetSelector
from brainrot_backend.video_generator.services.assets import filter_allowed_gameplay_assets


def test_asset_selector_prefers_tag_overlap():
    selector = AssetSelector()
    script = ScriptDraft(
        title="Test",
        hook="Hook",
        narration_text="Narration",
        caption_text="Caption",
        estimated_seconds=27,
        visual_beats=[],
        music_tags=["intense"],
        gameplay_tags=["fast", "parkour"],
        source_facts_used=[],
    )
    slow = AssetRecord(kind=AssetKind.GAMEPLAY, bucket="gameplay", path="slow.mp4", tags=["slow"])
    fast = AssetRecord(kind=AssetKind.GAMEPLAY, bucket="gameplay", path="fast.mp4", tags=["fast", "parkour"])
    chosen = selector.choose_gameplay(script, [slow, fast])
    assert chosen.path == "fast.mp4"


def test_asset_selector_respects_used_asset_ids_when_scores_tie():
    selector = AssetSelector()
    script = ScriptDraft(
        title="Test",
        hook="Hook",
        narration_text="Narration",
        caption_text="Caption",
        estimated_seconds=27,
        visual_beats=[],
        music_tags=[],
        gameplay_tags=["fast"],
        source_facts_used=[],
    )
    first = AssetRecord(kind=AssetKind.GAMEPLAY, bucket="gameplay", path="one.mp4", tags=["fast"])
    second = AssetRecord(kind=AssetKind.GAMEPLAY, bucket="gameplay", path="two.mp4", tags=["fast"])
    chosen = selector.choose_gameplay(script, [first, second], used_asset_ids={first.id})
    assert chosen.id == second.id


def test_filter_allowed_gameplay_assets_excludes_midnight_massacre():
    settings = Settings(
        supabase_url=None,
        supabase_service_role_key=None,
        supabase_public_url=None,
    )
    allowed = AssetRecord(
        kind=AssetKind.GAMEPLAY,
        bucket="gameplay",
        path="gameplay/minecraft/minecraft_clip_01.mp4",
        metadata={"game": "minecraft"},
    )
    blocked = AssetRecord(
        kind=AssetKind.GAMEPLAY,
        bucket="gameplay",
        path="gameplay/midnight-massacre/midnight-massacre_clip_01.mp4",
        metadata={"game": "midnight-massacre"},
    )

    filtered = filter_allowed_gameplay_assets(settings, [allowed, blocked])

    assert [asset.path for asset in filtered] == [allowed.path]
