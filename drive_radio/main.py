"""Orchestrates one run of the daily Drive Radio pipeline:

fetch candidate stories -> Claude picks & scripts the episode -> Kokoro
synthesizes it -> the episode manifest and RSS feed are updated.

Usage:
    python -m drive_radio.main             # full run, writes an MP3 + rss.xml
    python -m drive_radio.main --dry-run    # fetch + curate only, print the script
"""

import argparse
import os
import sys
from datetime import datetime, timezone

from . import config, feed, sources, tts
from .curate import curate


def _build_description(selected: list[dict]) -> str:
    lines = [f"- {item['title']}: {item['blurb']} ({item['url']})" for item in selected]
    return "Today's stories:\n" + "\n".join(lines)


def run(dry_run: bool = False) -> None:
    print("Fetching candidate stories...")
    items = sources.fetch_all()
    if not items:
        print("error: no candidate stories fetched from any source", file=sys.stderr)
        sys.exit(1)
    print(f"Fetched {len(items)} candidate stories.")

    now = datetime.now(timezone.utc)

    print("Asking Claude to curate and write today's dialogue...")
    result = curate(items, episode_date=now.date())
    print(f"Script ready: {result.word_count} words, {len(result.selected)} stories selected.")

    if dry_run:
        print("\n--- Selected stories ---")
        for item in result.selected:
            print(f"- {item['title']} ({item['url']})\n  {item['blurb']}")
        print("\n--- Dialogue ---\n")
        names = {"A": config.HOST_A_NAME, "B": config.HOST_B_NAME}
        for seg in result.segments:
            print(f"{names[seg['speaker']]} [{seg['delivery']}]: {seg['text']}")
        return

    date_str = now.strftime("%Y-%m-%d")
    mp3_filename = f"{date_str}.mp3"

    episodes_dir = os.path.join(config.OUTPUT_DIR, feed.EPISODES_DIR)
    os.makedirs(episodes_dir, exist_ok=True)
    mp3_path = os.path.join(episodes_dir, mp3_filename)

    print("Synthesizing audio with Kokoro...")
    mp3_path, duration_seconds = tts.synthesize_episode(result.segments, mp3_path)
    file_size_bytes = os.path.getsize(mp3_path)
    print(f"Audio ready: {duration_seconds // 60}m{duration_seconds % 60:02d}s, {file_size_bytes // 1024} KB.")

    title = f"{config.PODCAST_TITLE} — {now.strftime('%B %-d, %Y')}"
    description = _build_description(result.selected)

    print("Updating episode manifest and RSS feed...")
    episodes = feed.add_episode(
        output_dir=config.OUTPUT_DIR,
        mp3_filename=mp3_filename,
        title=title,
        description=description,
        pub_date_iso=now.isoformat(),
        duration_seconds=duration_seconds,
        file_size_bytes=file_size_bytes,
    )
    feed_path = feed.build_rss(config.OUTPUT_DIR, episodes)
    print(f"Wrote {feed_path} with {len(episodes)} episode(s).")


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate today's Drive Radio episode.")
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Fetch and curate only; print the script without calling TTS or touching the feed.",
    )
    args = parser.parse_args()
    run(dry_run=args.dry_run)


if __name__ == "__main__":
    main()
