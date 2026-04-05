import asyncio
from pathlib import Path

import pytest

from brainrot_backend.config import Settings
from brainrot_backend.shared.models.domain import AssetRecord, WordTiming
from brainrot_backend.shared.models.enums import AssetKind
from brainrot_backend.video_generator.render.subtitles import SubtitlePreset, build_ass_karaoke, build_subtitle_track, subtitle_presets
from brainrot_backend.video_generator.services.assets import AssetService
from brainrot_backend.shared.storage.memory import InMemoryRepository, LocalBlobStore
from brainrot_backend.video_generator.workers.orchestrator import BatchOrchestrator


def test_build_ass_karaoke_writes_dialogue(tmp_path):
    timings = [
        WordTiming(text="This", start=0.0, end=0.3),
        WordTiming(text="is", start=0.3, end=0.5),
        WordTiming(text="fine.", start=0.5, end=0.9),
    ]
    output = build_ass_karaoke(timings, tmp_path / "captions.ass")
    text = output.read_text(encoding="utf-8")
    assert "Dialogue:" in text
    assert "{\\k" in text


def test_subtitle_presets_use_local_font_library():
    presets = subtitle_presets(Settings().assets_dir / "fonts")
    assert [preset.id for preset in presets] == [
        "karaoke_sweep",
        "single_word_pop",
        "single_word_pop_bebas",
        "single_word_pop_anton",
        "single_word_pop_lilita",
    ]
    assert {preset.animation for preset in presets} == {"phrase-karaoke", "single-word-pop"}
    for preset in presets:
        assert preset.font_path.exists()


@pytest.mark.parametrize(
    ("preset_id", "marker"),
    [
        ("single_word_pop", "\\t(0,90"),
        ("single_word_pop_bebas", "\\t(0,90"),
        ("single_word_pop_anton", "\\t(0,90"),
        ("single_word_pop_lilita", "\\t(0,90"),
    ],
)
def test_build_subtitle_track_writes_animation_specific_overrides(tmp_path, preset_id, marker):
    timings = [
        WordTiming(text="One", start=0.0, end=0.35),
        WordTiming(text="two", start=0.35, end=0.7),
        WordTiming(text="three", start=0.7, end=1.1),
        WordTiming(text="four", start=1.1, end=1.45),
    ]
    presets = {preset.id: preset for preset in subtitle_presets(Settings().assets_dir / "fonts")}
    track = build_subtitle_track(timings, tmp_path / f"{preset_id}.ass", preset=presets[preset_id])
    text = track.path.read_text(encoding="utf-8")
    assert "Dialogue:" in text
    assert marker in text


def test_karaoke_sweep_splits_on_silence_gap(tmp_path):
    presets = {preset.id: preset for preset in subtitle_presets(Settings().assets_dir / "fonts")}
    timings = [
        WordTiming(text="One", start=0.0, end=0.3),
        WordTiming(text="idea", start=0.3, end=0.6),
        WordTiming(text="Multiple", start=1.25, end=1.55),
        WordTiming(text="posts", start=1.55, end=1.9),
    ]
    track = build_subtitle_track(timings, tmp_path / "karaoke.ass", preset=presets["karaoke_sweep"])
    text = track.path.read_text(encoding="utf-8")
    assert text.count("Dialogue:") == 2
    assert "0:00:00.55" in text


def test_subtitle_quota_map_biases_single_word_pop_komika():
    presets = list(subtitle_presets(Settings().assets_dir / "fonts"))
    quota_map = BatchOrchestrator._build_subtitle_quota_map(presets, 10)
    assert quota_map == {
        "karaoke_sweep": 1,
        "single_word_pop": 6,
        "single_word_pop_bebas": 1,
        "single_word_pop_anton": 1,
        "single_word_pop_lilita": 1,
    }


def test_auto_seed_font_assets_uploads_font_library(tmp_path):
    settings = Settings(
        project_root=tmp_path,
        assets_dir=tmp_path / "assets",
        data_dir=tmp_path / "data",
        temp_dir=tmp_path / "tmp",
        supabase_url=None,
        supabase_service_role_key=None,
        supabase_public_url=None,
    )
    fonts_dir = settings.assets_dir / "fonts" / "brainrot" / "top-used-subtitle-fonts"
    fonts_dir.mkdir(parents=True, exist_ok=True)
    (fonts_dir / "KomikaAxis-Regular.ttf").write_bytes(b"komika")
    (fonts_dir / "Montserrat-ExtraBold.ttf").write_bytes(b"montserrat")

    repository = InMemoryRepository()
    blob_store = LocalBlobStore(tmp_path / "blob")
    service = AssetService(settings, repository, blob_store)

    seeded = asyncio.run(service.auto_seed_font_assets())
    font_assets = asyncio.run(repository.list_assets(AssetKind.FONT))

    assert seeded == 2
    assert sorted(Path(asset.path).name for asset in font_assets) == [
        "KomikaAxis-Regular.ttf",
        "Montserrat-ExtraBold.ttf",
    ]
    assert all((tmp_path / "blob" / settings.font_bucket / asset.path).exists() for asset in font_assets)


def test_stage_subtitle_font_materializes_from_blob_store_when_local_font_is_missing(tmp_path):
    settings = Settings(
        project_root=tmp_path,
        assets_dir=tmp_path / "assets",
        data_dir=tmp_path / "data",
        temp_dir=tmp_path / "tmp",
        supabase_url=None,
        supabase_service_role_key=None,
        supabase_public_url=None,
    )
    repository = InMemoryRepository()
    blob_store = LocalBlobStore(tmp_path / "blob")
    source_path = "assets/fonts/brainrot/top-used-subtitle-fonts/KomikaAxis-Regular.ttf"
    blob_path = "fonts/brainrot/top-used-subtitle-fonts/KomikaAxis-Regular.ttf"
    asyncio.run(
        blob_store.upload_bytes(
            settings.font_bucket,
            blob_path,
            b"komika-axis",
            content_type="font/ttf",
        )
    )
    asyncio.run(
        repository.create_asset(
            AssetRecord(
                kind=AssetKind.FONT,
                bucket=settings.font_bucket,
                path=blob_path,
                metadata={
                    "filename": "KomikaAxis-Regular.ttf",
                    "source_path": source_path,
                },
            )
        )
    )
    preset = SubtitlePreset(
        id="single_word_pop",
        label="Single Word Pop",
        animation="single-word-pop",
        family="single_word_pop",
        font_name="Komika Axis",
        font_path=settings.project_root / source_path,
        font_size=112,
        preferred_tags=(),
        style_name="SingleWordPop",
        selection_weight=60,
    )
    orchestrator = BatchOrchestrator(
        settings=settings,
        repository=repository,
        blob_store=blob_store,
        events=object(),
        firecrawl=object(),
        agent_service=object(),
        chat_service=object(),
        asset_selector=object(),
        renderer=object(),
    )

    font_dir = asyncio.run(orchestrator._stage_subtitle_font(tmp_path / "job", preset))

    assert (font_dir / "KomikaAxis-Regular.ttf").read_bytes() == b"komika-axis"
