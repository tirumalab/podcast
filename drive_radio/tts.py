"""Turn the two-host dialogue into a single MP3 using Kokoro — a free,
open-weight, self-hosted TTS model (runs on CPU, no per-minute API cost).

Each speaker gets a distinct voice. Kokoro has no natural-language emotion
control, so each line's "delivery" tag is mapped to a speaking-speed
multiplier instead (Settings.delivery_speed_keywords) as a cruder proxy for
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

from .settings import Settings, default_settings

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


_pipelines: dict[str, object] = {}


def _get_pipeline(lang_code: str):
    """Build (once per language) and reuse the Kokoro pipeline — loading it is
    expensive, so it's cached rather than rebuilt per user. Deferred to first
    use so importing this module doesn't require espeak-ng to be installed."""
    if lang_code not in _pipelines:
        # Importing kokoro pulls in misaki, which points espeak-ng at a broken
        # bundled data path — repair it before constructing the pipeline.
        from kokoro import KPipeline

        _fix_espeak_paths()
        _pipelines[lang_code] = KPipeline(lang_code=lang_code)
    return _pipelines[lang_code]


def _speed_for_delivery(delivery: str, delivery_speed_keywords: dict[str, float]) -> float:
    delivery_lower = delivery.lower()
    matches = [
        multiplier
        for keyword, multiplier in delivery_speed_keywords.items()
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


def _synthesize_turn(speaker: str, text: str, delivery: str, settings: Settings) -> AudioSegment:
    voice = settings.host_a_voice if speaker == "A" else settings.host_b_voice
    speed = _speed_for_delivery(delivery, settings.delivery_speed_keywords)
    pipeline = _get_pipeline(settings.kokoro_lang_code)
    chunks = [result.audio for result in pipeline(text, voice=voice, speed=speed)]
    audio = np.concatenate(chunks) if len(chunks) > 1 else chunks[0]
    return _audio_array_to_segment(audio.numpy() if hasattr(audio, "numpy") else audio)


def _add_background_music(episode: AudioSegment, settings: Settings) -> AudioSegment:
    if not (settings.background_music and os.path.exists(settings.background_music)):
        return episode

    music = AudioSegment.from_file(settings.background_music) + settings.background_music_gain_db

    looped = AudioSegment.empty()
    while len(looped) < len(episode):
        looped += music
    looped = looped[: len(episode)].fade_out(min(3000, len(episode)))

    return looped.overlay(episode)


def synthesize_episode(
    segments: list[dict], output_path: str, settings: Settings | None = None
) -> tuple[str, int]:
    """Synthesize the two-host dialogue to speech, alternating voices and
    delivery-driven pacing per speaker with a short gap between turns, mix
    in a looped background music bed if configured, and stitch it (with
    optional intro/outro bumpers) into a single MP3 at output_path.

    Returns (output_path, duration_seconds).
    """
    settings = settings or default_settings()
    gap = AudioSegment.silent(duration=settings.turn_gap_ms)

    episode = AudioSegment.empty()

    if settings.intro_clip and os.path.exists(settings.intro_clip):
        episode += AudioSegment.from_file(settings.intro_clip)

    for i, seg in enumerate(segments):
        episode += _synthesize_turn(seg["speaker"], seg["text"], seg["delivery"], settings)
        if i < len(segments) - 1:
            episode += gap

    if settings.outro_clip and os.path.exists(settings.outro_clip):
        episode += AudioSegment.from_file(settings.outro_clip)

    episode = _add_background_music(episode, settings)

    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    episode.export(output_path, format="mp3", bitrate="96k")
    duration_seconds = len(episode) // 1000
    return output_path, duration_seconds
