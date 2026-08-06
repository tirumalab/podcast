"""Turn the two-host dialogue into a single MP3 using Kokoro — a free,
open-weight, self-hosted TTS model (runs on CPU, no per-minute API cost).

Each speaker gets a distinct voice. Kokoro has no natural-language emotion
control, so each line's "delivery" tag is mapped to a speaking-speed
multiplier instead (config.DELIVERY_SPEED_KEYWORDS) as a cruder proxy for
energy. A looped background music bed can also be mixed in under the whole
episode.

Kokoro's dependency chain (via `misaki`) misconfigures its espeak-ng
phonemizer backend at import time on some platforms — see
_fix_espeak_paths() below, which must run after `from kokoro import
KPipeline` to take effect.
"""

import ctypes.util
import glob
import os

import numpy as np
from pydub import AudioSegment

from . import config

SAMPLE_RATE = 24000


def _find_espeak_library() -> str | None:
    found = ctypes.util.find_library("espeak-ng")
    if found:
        return found
    candidates = (
        glob.glob("/opt/homebrew/Cellar/espeak-ng/*/lib/libespeak-ng.dylib")
        + glob.glob("/usr/local/Cellar/espeak-ng/*/lib/libespeak-ng.dylib")
        + glob.glob("/usr/lib/*/libespeak-ng.so*")
        + glob.glob("/usr/lib/libespeak-ng.so*")
    )
    return candidates[0] if candidates else None


def _find_espeak_data() -> str | None:
    candidates = (
        glob.glob("/opt/homebrew/Cellar/espeak-ng/*/share/espeak-ng-data")
        + glob.glob("/usr/local/Cellar/espeak-ng/*/share/espeak-ng-data")
        + glob.glob("/usr/lib/*/espeak-ng-data")
        + glob.glob("/usr/share/espeak-ng-data")
    )
    return candidates[0] if candidates else None


def _fix_espeak_paths() -> None:
    """Kokoro's `misaki` dependency points espeak-ng at its own bundled data
    directory at import time, which is broken on some platforms/versions.
    Re-point it at a real system espeak-ng install (brew on macOS, apt-get
    on Ubuntu/CI) after import so it actually resolves."""
    from phonemizer.backend.espeak.wrapper import EspeakWrapper

    library = _find_espeak_library()
    data = _find_espeak_data()
    if not library or not data:
        raise RuntimeError(
            "espeak-ng not found. Install it first: `brew install espeak-ng` (macOS) "
            "or `apt-get install espeak-ng` (Linux/CI)."
        )
    EspeakWrapper.set_library(library)
    EspeakWrapper.set_data_path(data)


from kokoro import KPipeline  # noqa: E402 (must precede the espeak path fix)

_fix_espeak_paths()

_pipeline = KPipeline(lang_code=config.KOKORO_LANG_CODE)

VOICE_BY_SPEAKER = {
    "A": config.HOST_A_VOICE,
    "B": config.HOST_B_VOICE,
}


def _speed_for_delivery(delivery: str) -> float:
    delivery_lower = delivery.lower()
    matches = [
        multiplier
        for keyword, multiplier in config.DELIVERY_SPEED_KEYWORDS.items()
        if keyword in delivery_lower
    ]
    return sum(matches) / len(matches) if matches else 1.0


def _audio_array_to_segment(audio: np.ndarray) -> AudioSegment:
    pcm16 = (np.clip(audio, -1.0, 1.0) * 32767).astype(np.int16)
    return AudioSegment(
        data=pcm16.tobytes(),
        sample_width=2,
        frame_rate=SAMPLE_RATE,
        channels=1,
    )


def _synthesize_turn(speaker: str, text: str, delivery: str) -> AudioSegment:
    voice = VOICE_BY_SPEAKER[speaker]
    speed = _speed_for_delivery(delivery)
    chunks = [result.audio for result in _pipeline(text, voice=voice, speed=speed)]
    audio = np.concatenate(chunks) if len(chunks) > 1 else chunks[0]
    return _audio_array_to_segment(audio.numpy() if hasattr(audio, "numpy") else audio)


def _add_background_music(episode: AudioSegment) -> AudioSegment:
    if not (config.BACKGROUND_MUSIC and os.path.exists(config.BACKGROUND_MUSIC)):
        return episode

    music = AudioSegment.from_file(config.BACKGROUND_MUSIC) + config.BACKGROUND_MUSIC_GAIN_DB

    looped = AudioSegment.empty()
    while len(looped) < len(episode):
        looped += music
    looped = looped[: len(episode)].fade_out(min(3000, len(episode)))

    return looped.overlay(episode)


def synthesize_episode(segments: list[dict], output_path: str) -> tuple[str, int]:
    """Synthesize the two-host dialogue to speech, alternating voices and
    delivery-driven pacing per speaker with a short gap between turns, mix
    in a looped background music bed if configured, and stitch it (with
    optional intro/outro bumpers) into a single MP3 at output_path.

    Returns (output_path, duration_seconds).
    """
    gap = AudioSegment.silent(duration=config.TURN_GAP_MS)

    episode = AudioSegment.empty()

    if config.INTRO_CLIP and os.path.exists(config.INTRO_CLIP):
        episode += AudioSegment.from_file(config.INTRO_CLIP)

    for i, seg in enumerate(segments):
        episode += _synthesize_turn(seg["speaker"], seg["text"], seg["delivery"])
        if i < len(segments) - 1:
            episode += gap

    if config.OUTRO_CLIP and os.path.exists(config.OUTRO_CLIP):
        episode += AudioSegment.from_file(config.OUTRO_CLIP)

    episode = _add_background_music(episode)

    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    episode.export(output_path, format="mp3", bitrate="96k")
    duration_seconds = len(episode) // 1000
    return output_path, duration_seconds
