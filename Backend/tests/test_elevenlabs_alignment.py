import io
import wave

from brainrot_backend.integrations.elevenlabs import (
    normalize_conversation_audio,
    trim_wav_trailing_padding,
    word_timings_from_alignment,
)


def test_word_timings_from_alignment_groups_characters_into_words():
    timings = word_timings_from_alignment(
        {
            "characters": list("hello world"),
            "character_start_times_seconds": [0.0, 0.1, 0.2, 0.3, 0.4, 0.45, 0.5, 0.6, 0.7, 0.8, 0.9],
            "character_end_times_seconds": [0.1, 0.2, 0.3, 0.4, 0.45, 0.5, 0.6, 0.7, 0.8, 0.9, 1.0],
        }
    )
    assert [item.text for item in timings] == ["hello", "world"]
    assert timings[0].start == 0.0
    assert timings[1].end == 1.0


def test_normalize_conversation_audio_wraps_raw_pcm_into_wav():
    pcm_bytes = b"\x00\x00\x10\x00\x20\x00\x30\x00"
    audio_bytes, audio_format, mime_type = normalize_conversation_audio(pcm_bytes)
    assert audio_format == "wav"
    assert mime_type == "audio/wav"
    assert audio_bytes.startswith(b"RIFF")


def test_trim_wav_trailing_padding_cuts_excess_audio():
    wav_buffer = io.BytesIO()
    with wave.open(wav_buffer, "wb") as wav_file:
        wav_file.setnchannels(1)
        wav_file.setsampwidth(2)
        wav_file.setframerate(16000)
        wav_file.writeframes(b"\x01\x00" * 16000 * 3)

    trimmed, trimmed_seconds = trim_wav_trailing_padding(
        wav_buffer.getvalue(),
        target_duration_seconds=2.0,
        min_excess_seconds=0.5,
    )
    assert trimmed_seconds >= 0.9
    with wave.open(io.BytesIO(trimmed), "rb") as wav_file:
        duration = wav_file.getnframes() / wav_file.getframerate()
    assert duration == 2.0
