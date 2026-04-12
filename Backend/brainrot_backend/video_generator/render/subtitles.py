from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from brainrot_backend.shared.models.domain import WordTiming


@dataclass(frozen=True, slots=True)
class SubtitlePreset:
    id: str
    label: str
    animation: str
    family: str
    font_name: str
    font_path: Path
    font_size: int
    preferred_tags: tuple[str, ...]
    style_name: str
    selection_weight: int


@dataclass(frozen=True, slots=True)
class SubtitleTrack:
    path: Path
    preset: SubtitlePreset


def subtitle_presets(fonts_root: Path) -> tuple[SubtitlePreset, ...]:
    return (
        SubtitlePreset(
            id="karaoke_sweep",
            label="Karaoke Sweep",
            animation="phrase-karaoke",
            family="karaoke_sweep",
            font_name="Montserrat ExtraBold",
            font_path=fonts_root / "brainrot" / "top-used-subtitle-fonts" / "Montserrat-ExtraBold.ttf",
            font_size=68,
            preferred_tags=("analysis", "study", "strategy", "ambient", "story", "documentary"),
            style_name="KaraokeSweep",
            selection_weight=10,
        ),
        SubtitlePreset(
            id="single_word_pop",
            label="Single Word Pop",
            animation="single-word-pop",
            family="single_word_pop",
            font_name="Komika Axis",
            font_path=fonts_root / "brainrot" / "top-used-subtitle-fonts" / "KomikaAxis-Regular.ttf",
            font_size=112,
            preferred_tags=("minecraft", "subway", "parkour", "roblox", "arcade", "viral", "fast"),
            style_name="SingleWordPop",
            selection_weight=60,
        ),
        SubtitlePreset(
            id="single_word_pop_bebas",
            label="Single Word Pop · Bebas Neue",
            animation="single-word-pop",
            family="single_word_pop",
            font_name="Bebas Neue",
            font_path=fonts_root / "brainrot" / "top-used-subtitle-fonts" / "BebasNeue-Regular.ttf",
            font_size=126,
            preferred_tags=("news", "cinematic", "article", "slow", "dark", "headline"),
            style_name="SingleWordPopBebas",
            selection_weight=10,
        ),
        SubtitlePreset(
            id="single_word_pop_anton",
            label="Single Word Pop · Anton",
            animation="single-word-pop",
            family="single_word_pop",
            font_name="Anton",
            font_path=fonts_root / "brainrot" / "Anton-Regular.ttf",
            font_size=108,
            preferred_tags=("gta", "intense", "action", "shooter", "racing", "clutch", "fps"),
            style_name="SingleWordPopAnton",
            selection_weight=10,
        ),
        SubtitlePreset(
            id="single_word_pop_lilita",
            label="Single Word Pop · Lilita One",
            animation="single-word-pop",
            family="single_word_pop",
            font_name="Lilita One",
            font_path=fonts_root / "brainrot" / "LilitaOne-Regular.ttf",
            font_size=106,
            preferred_tags=("funny", "chaotic", "meme", "bright", "satisfying", "cartoon", "surfers"),
            style_name="SingleWordPopLilita",
            selection_weight=10,
        ),
    )


def build_subtitle_track(
    word_timings: list[WordTiming],
    destination: Path,
    *,
    preset: SubtitlePreset,
) -> SubtitleTrack:
    if not word_timings:
        raise ValueError("Cannot build subtitle track without word timings.")

    styles, events = _build_track_lines(word_timings, preset)
    lines = [
        "[Script Info]",
        "ScriptType: v4.00+",
        "PlayResX: 1080",
        "PlayResY: 1920",
        "ScaledBorderAndShadow: yes",
        "WrapStyle: 2",
        "",
        "[V4+ Styles]",
        "Format: Name,Fontname,Fontsize,PrimaryColour,SecondaryColour,OutlineColour,BackColour,Bold,Italic,Underline,StrikeOut,ScaleX,ScaleY,Spacing,Angle,BorderStyle,Outline,Shadow,Alignment,MarginL,MarginR,MarginV,Encoding",
        *styles,
        "",
        "[Events]",
        "Format: Layer,Start,End,Style,Name,MarginL,MarginR,MarginV,Effect,Text",
        *events,
    ]
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text("\n".join(lines), encoding="utf-8")
    return SubtitleTrack(path=destination, preset=preset)


def build_ass_karaoke(word_timings: list[WordTiming], destination: Path) -> Path:
    destination.parent.mkdir(parents=True, exist_ok=True)
    styles, events = _build_karaoke_lines(
        word_timings,
        style_name="BrainrotCenter",
        font_name="Arial",
        font_size=72,
    )
    lines = [
        "[Script Info]",
        "ScriptType: v4.00+",
        "PlayResX: 1080",
        "PlayResY: 1920",
        "",
        "[V4+ Styles]",
        "Format: Name,Fontname,Fontsize,PrimaryColour,SecondaryColour,OutlineColour,BackColour,Bold,Italic,Underline,StrikeOut,ScaleX,ScaleY,Spacing,Angle,BorderStyle,Outline,Shadow,Alignment,MarginL,MarginR,MarginV,Encoding",
        *styles,
        "",
        "[Events]",
        "Format: Layer,Start,End,Style,Name,MarginL,MarginR,MarginV,Effect,Text",
        *events,
    ]
    destination.write_text("\n".join(lines), encoding="utf-8")
    return destination


def chunk_word_timings(
    word_timings: list[WordTiming],
    max_words: int = 7,
    *,
    max_duration: float = 2.4,
    max_gap_seconds: float = 0.32,
) -> list[list[WordTiming]]:
    chunks: list[list[WordTiming]] = []
    current: list[WordTiming] = []
    for word in word_timings:
        if current:
            gap = max(0.0, word.start - current[-1].end)
            if gap >= max_gap_seconds:
                chunks.append(current)
                current = []
        current.append(word)
        duration = current[-1].end - current[0].start
        if (
            len(current) >= max_words
            or duration >= max_duration
            or word.text.endswith((".", "!", "?", ","))
        ):
            chunks.append(current)
            current = []
    if current:
        chunks.append(current)
    return chunks


def format_ass_time(value: float) -> str:
    total_cs = int(round(value * 100))
    cs = total_cs % 100
    total_seconds = total_cs // 100
    seconds = total_seconds % 60
    total_minutes = total_seconds // 60
    minutes = total_minutes % 60
    hours = total_minutes // 60
    return f"{hours}:{minutes:02d}:{seconds:02d}.{cs:02d}"


def escape_ass(value: str) -> str:
    return value.replace("\\", "\\\\").replace("{", "\\{").replace("}", "\\}")


def _build_track_lines(
    word_timings: list[WordTiming],
    preset: SubtitlePreset,
) -> tuple[list[str], list[str]]:
    if preset.family == "single_word_pop":
        return _build_single_word_pop_lines(word_timings, preset)
    return _build_karaoke_lines(
        word_timings,
        style_name=preset.style_name,
        font_name=preset.font_name,
        font_size=preset.font_size,
    )


def _build_karaoke_lines(
    word_timings: list[WordTiming],
    *,
    style_name: str,
    font_name: str,
    font_size: int,
) -> tuple[list[str], list[str]]:
    styles = [
        f"Style: {style_name},{font_name},{font_size},&H00FFFFFF,&H0000E5FF,&H0012141A,&H64000000,1,0,0,0,100,100,0,0,1,5,0,5,90,90,220,1",
    ]
    events: list[str] = []
    for segment in chunk_word_timings(
        word_timings,
        max_words=5,
        max_duration=1.9,
        max_gap_seconds=0.28,
    ):
        karaoke = _build_wrapped_karaoke_text(segment)
        segment_end = max(segment[0].start + 0.1, segment[-1].end - 0.05)
        events.append(
            f"Dialogue: 0,{format_ass_time(segment[0].start)},{format_ass_time(segment_end)},{style_name},,0,0,0,,{karaoke}"
        )
    return styles, events


def _build_wrapped_karaoke_text(
    segment: list[WordTiming],
    *,
    max_words_per_line: int = 3,
    max_characters_per_line: int = 18,
) -> str:
    lines: list[list[str]] = [[]]
    current_characters = 0
    for word in segment:
        cleaned_text = escape_ass(word.text.upper())
        rendered_word = f"{{\\k{max(1, int((word.end - word.start) * 100))}}}{cleaned_text}"
        projected_characters = current_characters + len(word.text) + (1 if lines[-1] else 0)
        if lines[-1] and (
            len(lines[-1]) >= max_words_per_line
            or projected_characters > max_characters_per_line
        ):
            lines.append([])
            current_characters = 0
        lines[-1].append(rendered_word)
        current_characters += len(word.text) + (1 if len(lines[-1]) > 1 else 0)

    return "\\N".join(" ".join(line).strip() for line in lines if line).strip()


def _build_single_word_pop_lines(
    word_timings: list[WordTiming],
    preset: SubtitlePreset,
) -> tuple[list[str], list[str]]:
    styles = [
        f"Style: {preset.style_name},{preset.font_name},{preset.font_size},&H00FFFFFF,&H00B8A8FF,&H00140E1F,&H500A0614,1,0,0,0,100,100,0,0,1,7,0,5,60,60,250,1",
    ]
    events = [
        (
            "Dialogue: 0,"
            f"{format_ass_time(word.start)},{format_ass_time(word.end)},{preset.style_name},,0,0,0,,"
            "{\\an5\\fad(20,50)\\blur0.4\\fscx92\\fscy92"
            "\\t(0,90,\\fscx122\\fscy122)\\t(90,200,\\fscx100\\fscy100)}"
            f"{escape_ass(word.text.upper())}"
        )
        for word in word_timings
    ]
    return styles, events
