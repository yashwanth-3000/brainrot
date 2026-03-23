from brainrot_backend.models.domain import AssetRecord, ScriptDraft
from brainrot_backend.models.enums import AssetKind
from brainrot_backend.render.assets import AssetSelector


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
