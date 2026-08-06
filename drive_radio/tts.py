"""Turn the two-host dialogue into a single MP3 via OpenAI TTS.

Each speaker gets a distinct voice, and each line is synthesized with an
`instructions` prompt (persona + that line's tagged emotional delivery) so
gpt-4o-mini-tts actually performs it instead of reading it flat. A looped
background music bed can also be mixed in under the whole episode.
"""

import io
import os
import re

from openai import OpenAI
from pydub import AudioSegment

from . import config

MAX_CHARS_PER_REQUEST = 3500

VOICE_BY_SPEAKER = {
    "A": config.HOST_A_VOICE,
    "B": config.HOST_B_VOICE,
}

PERSONA_BY_SPEAKER = {
    "A": (config.HOST_A_NAME, config.HOST_A_PERSONA),
    "B": (config.HOST_B_NAME, config.HOST_B_PERSONA),
}


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


def _build_instructions(speaker: str, delivery: str) -> str:
    name, persona = PERSONA_BY_SPEAKER[speaker]
    return (
        f"You are {name}, {persona}. This one line is a single beat in a live, "
        f"unscripted-sounding podcast conversation. Perform it as genuinely {delivery} — "
        "actually sound that way, don't just read the words at a neutral pace. Vary your "
        "pitch and pace the way a real person talking does: speed up on excitement, slow "
        "down and land on key words for emphasis, let your pitch actually rise on a "
        "surprise or drop for something serious. Put a real micro-pause before a punchline "
        "or a surprising word instead of running straight through it. This should sound like "
        "a person reacting in the moment, not a voiceover artist narrating a script."
    )


def _synthesize_text(client: OpenAI, text: str, voice: str, instructions: str) -> AudioSegment:
    response = client.audio.speech.create(
        model=config.TTS_MODEL,
        voice=voice,
        input=text,
        instructions=instructions,
    )
    audio_bytes = response.read()
    return AudioSegment.from_file(io.BytesIO(audio_bytes), format="mp3")


def _synthesize_turn(client: OpenAI, speaker: str, text: str, delivery: str) -> AudioSegment:
    voice = VOICE_BY_SPEAKER[speaker]
    instructions = _build_instructions(speaker, delivery)
    turn = AudioSegment.empty()
    for chunk in _split_into_chunks(text):
        turn += _synthesize_text(client, chunk, voice, instructions)
    return turn


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
    delivery per speaker with a short gap between turns, mix in a looped
    background music bed if configured, and stitch it (with optional
    intro/outro bumpers) into a single MP3 at output_path.

    Returns (output_path, duration_seconds).
    """
    client = OpenAI()

    gap = AudioSegment.silent(duration=config.TURN_GAP_MS)

    episode = AudioSegment.empty()

    if config.INTRO_CLIP and os.path.exists(config.INTRO_CLIP):
        episode += AudioSegment.from_file(config.INTRO_CLIP)

    for i, seg in enumerate(segments):
        episode += _synthesize_turn(client, seg["speaker"], seg["text"], seg["delivery"])
        if i < len(segments) - 1:
            episode += gap

    if config.OUTRO_CLIP and os.path.exists(config.OUTRO_CLIP):
        episode += AudioSegment.from_file(config.OUTRO_CLIP)

    episode = _add_background_music(episode)

    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    episode.export(output_path, format="mp3", bitrate="96k")
    duration_seconds = len(episode) // 1000
    return output_path, duration_seconds
