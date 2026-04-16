from __future__ import annotations

import asyncio
import logging
from pathlib import Path

from brainrot_backend.config import Settings

logger = logging.getLogger(__name__)


class FFmpegRenderer:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings

    async def render(
        self,
        *,
        gameplay_path: Path,
        music_path: Path | None,
        narration_path: Path,
        subtitle_path: Path,
        fonts_dir: Path | None,
        output_path: Path,
    ) -> Path:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        subtitle_filter = build_subtitle_filter(subtitle_path, fonts_dir)

        if music_path is not None and music_path.exists():
            command = self._build_command_with_music(
                gameplay_path, music_path, narration_path, subtitle_filter, output_path,
            )
        else:
            logger.info("No music track provided, rendering without music")
            command = self._build_command_without_music(
                gameplay_path, narration_path, subtitle_filter, output_path,
            )

        logger.info("FFmpeg command: %s", " ".join(str(c) for c in command))
        process = await asyncio.create_subprocess_exec(
            *command,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        _, stderr = await process.communicate()
        if process.returncode != 0:
            error_text = stderr.decode("utf-8", errors="ignore")
            failure_summary = _format_ffmpeg_failure(process.returncode, error_text)
            logger.error("FFmpeg failed (rc=%d): %s", process.returncode, failure_summary)
            raise RuntimeError(f"FFmpeg render failed: {failure_summary}")
        logger.info("FFmpeg render complete: %s", output_path)
        return output_path

    def _build_command_with_music(
        self,
        gameplay_path: Path,
        music_path: Path,
        narration_path: Path,
        subtitle_filter: str,
        output_path: Path,
    ) -> list[str]:
        filter_complex = (
            "[1:a]volume=0.18,aloop=loop=-1:size=2147483647[music];"
            "[2:a]loudnorm=I=-16:TP=-1.5:LRA=11[narr];"
            "[music][narr]sidechaincompress=threshold=0.08:ratio=10:attack=15:release=250[ducked];"
            "[ducked][narr]amix=inputs=2:weights='0.45 1':duration=shortest[mix]"
        )
        return [
            self.settings.ffmpeg_bin,
            "-y",
            "-stream_loop", "-1",
            "-i", str(gameplay_path),
            "-stream_loop", "-1",
            "-i", str(music_path),
            "-i", str(narration_path),
            "-filter_complex", filter_complex,
            "-vf", f"scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920,{subtitle_filter}",
            "-map", "0:v:0",
            "-map", "[mix]",
            "-c:v", "libx264",
            "-preset", "veryfast",
            "-crf", "20",
            "-pix_fmt", "yuv420p",
            "-c:a", "aac",
            "-b:a", "192k",
            "-shortest",
            str(output_path),
        ]

    def _build_command_without_music(
        self,
        gameplay_path: Path,
        narration_path: Path,
        subtitle_filter: str,
        output_path: Path,
    ) -> list[str]:
        filter_complex = "[1:a]loudnorm=I=-16:TP=-1.5:LRA=11[narr]"
        return [
            self.settings.ffmpeg_bin,
            "-y",
            "-stream_loop", "-1",
            "-i", str(gameplay_path),
            "-i", str(narration_path),
            "-filter_complex", filter_complex,
            "-vf", f"scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920,{subtitle_filter}",
            "-map", "0:v:0",
            "-map", "[narr]",
            "-c:v", "libx264",
            "-preset", "veryfast",
            "-crf", "20",
            "-pix_fmt", "yuv420p",
            "-c:a", "aac",
            "-b:a", "192k",
            "-shortest",
            str(output_path),
        ]


def escape_filter_path(path: Path) -> str:
    return str(path).replace("\\", "\\\\").replace(":", "\\:").replace("'", "\\'")


def build_subtitle_filter(subtitle_path: Path, fonts_dir: Path | None) -> str:
    subtitle_arg = escape_filter_path(subtitle_path)
    if fonts_dir is None:
        return f"subtitles='{subtitle_arg}'"
    fonts_arg = escape_filter_path(fonts_dir)
    return f"subtitles='{subtitle_arg}':fontsdir='{fonts_arg}'"


def _format_ffmpeg_failure(returncode: int, error_text: str) -> str:
    clipped = error_text[-1200:].strip()
    if returncode < 0:
        signal_number = -returncode
        if clipped:
            return f"process was killed by signal {signal_number}. Last FFmpeg output: {clipped}"
        return f"process was killed by signal {signal_number}"
    return clipped or f"process exited with code {returncode}"
