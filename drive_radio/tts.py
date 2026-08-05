"""Turn the narration script into a single MP3 via OpenAI TTS."""

import io
import os
import re

from openai import OpenAI
from pydub import AudioSegment

from . import config

MAX_CHARS_PER_REQUEST = 3500


def _split_into_chunks(text: str, max_chars: int = MAX_CHARS_PER_REQUEST) -> list[str]:
    """Split on sentence boundaries, keeping each chunk under max_chars."""
    sentences = re.split(r"(?<=[.!?])\s+", text.strip())

    chunks: list[str] = []
    current = ""
    for sentence in sentences:
        candidate = f"{current} {sentence}".strip()
        if len(candidate) > max_chars and current:
            chunks.append(current)
            current = sentence
        else:
            current = candidate
    if current:
        chunks.append(current)
    return chunks


def _synthesize_chunk(client: OpenAI, text: str) -> AudioSegment:
    response = client.audio.speech.create(
        model=config.TTS_MODEL,
        voice=config.TTS_VOICE,
        input=text,
    )
    audio_bytes = response.read()
    return AudioSegment.from_file(io.BytesIO(audio_bytes), format="mp3")


def synthesize_episode(script: str, output_path: str) -> tuple[str, int]:
    """Synthesize the full script to speech and stitch it (with optional
    intro/outro bumpers) into a single MP3 at output_path.

    Returns (output_path, duration_seconds).
    """
    client = OpenAI()

    chunks = _split_into_chunks(script)
    segments = [_synthesize_chunk(client, chunk) for chunk in chunks]

    episode = AudioSegment.empty()

    if config.INTRO_CLIP and os.path.exists(config.INTRO_CLIP):
        episode += AudioSegment.from_file(config.INTRO_CLIP)

    for segment in segments:
        episode += segment

    if config.OUTRO_CLIP and os.path.exists(config.OUTRO_CLIP):
        episode += AudioSegment.from_file(config.OUTRO_CLIP)

    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    episode.export(output_path, format="mp3", bitrate="96k")
    duration_seconds = len(episode) // 1000
    return output_path, duration_seconds
