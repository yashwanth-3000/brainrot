import pytest

from brainrot_backend.config import Settings
from brainrot_backend.models.domain import WordTiming
from brainrot_backend.render.subtitles import build_ass_karaoke, build_subtitle_track, subtitle_presets
from brainrot_backend.workers.orchestrator import BatchOrchestrator


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
