"""Maintain the episode manifest and regenerate the podcast RSS feed from it.

The manifest (manifest.json) is the source of truth for what episodes exist.
Each run appends the new episode, drops anything past the retention window
(deleting its MP3 too, so GitHub Pages storage doesn't grow unbounded), then
regenerates rss.xml fully from what's left. This keeps the feed correct even
though every workflow run starts from a fresh checkout.
"""

import json
import os

from dateutil import parser as date_parser
from feedgen.feed import FeedGenerator

from .settings import Settings, default_settings

MANIFEST_FILENAME = "manifest.json"
FEED_FILENAME = "rss.xml"
EPISODES_DIR = "episodes"


def load_manifest(output_dir: str) -> list[dict]:
    path = os.path.join(output_dir, MANIFEST_FILENAME)
    if not os.path.exists(path):
        return []
    with open(path) as f:
        return json.load(f)


def save_manifest(output_dir: str, episodes: list[dict]) -> None:
    path = os.path.join(output_dir, MANIFEST_FILENAME)
    with open(path, "w") as f:
        json.dump(episodes, f, indent=2)


def add_episode(
    output_dir: str,
    mp3_filename: str,
    title: str,
    description: str,
    pub_date_iso: str,
    duration_seconds: int,
    file_size_bytes: int,
    settings: Settings | None = None,
) -> list[dict]:
    """Add today's episode to the manifest, prune anything past the retention
    window (deleting the dropped MP3s), and return the kept list.

    Replaces any existing entry with the same mp3_filename instead of
    appending alongside it, so a same-day re-run (a manual workflow_dispatch
    landing on top of the scheduled cron, an Actions retry, etc.) converges
    to one manifest entry per day instead of duplicating it — the mp3 file
    itself already gets overwritten by such a re-run, so the old manifest
    entry would otherwise point at audio that no longer matches it."""
    settings = settings or default_settings()
    episodes = [e for e in load_manifest(output_dir) if e["mp3_filename"] != mp3_filename]
    episodes.append(
        {
            "mp3_filename": mp3_filename,
            "title": title,
            "description": description,
            "pub_date": pub_date_iso,
            "duration_seconds": duration_seconds,
            "file_size_bytes": file_size_bytes,
        }
    )
    episodes.sort(key=lambda e: e["pub_date"], reverse=True)

    kept = episodes[: settings.max_episodes_in_feed]
    dropped = episodes[settings.max_episodes_in_feed :]

    for old in dropped:
        old_path = os.path.join(output_dir, EPISODES_DIR, old["mp3_filename"])
        if os.path.exists(old_path):
            os.remove(old_path)

    save_manifest(output_dir, kept)
    return kept


def _format_duration(seconds: int) -> str:
    hours, remainder = divmod(int(seconds), 3600)
    minutes, secs = divmod(remainder, 60)
    return f"{hours:02d}:{minutes:02d}:{secs:02d}"


def build_rss(output_dir: str, episodes: list[dict], settings: Settings | None = None) -> str:
    settings = settings or default_settings()
    fg = FeedGenerator()
    fg.load_extension("podcast")
    fg.title(settings.podcast_title)
    fg.link(href=settings.podcast_base_url, rel="alternate")
    fg.link(href=f"{settings.podcast_base_url}/{FEED_FILENAME}", rel="self")
    fg.description(settings.podcast_description)
    fg.language("en")
    fg.podcast.itunes_author(settings.podcast_author)
    fg.podcast.itunes_category(cat="Technology")
    fg.podcast.itunes_explicit("no")

    # feedgen renders entries in the order they're added, so add most-recent
    # first (episodes is already sorted that way by add_episode).
    for ep in episodes:
        fe = fg.add_entry()
        mp3_url = f"{settings.podcast_base_url}/{EPISODES_DIR}/{ep['mp3_filename']}"
        fe.id(mp3_url)
        fe.title(ep["title"])
        fe.description(ep["description"])
        fe.enclosure(mp3_url, str(ep["file_size_bytes"]), "audio/mpeg")
        fe.pubDate(date_parser.isoparse(ep["pub_date"]))
        fe.podcast.itunes_duration(_format_duration(ep["duration_seconds"]))

    feed_path = os.path.join(output_dir, FEED_FILENAME)
    fg.rss_file(feed_path)
    return feed_path
