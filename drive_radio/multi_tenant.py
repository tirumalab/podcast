"""Generate today's episode for every active user in Supabase, one after
another.

Each user's generation is isolated in its own try/except so one person's
dead RSS feed or exhausted expand-retry doesn't take down everyone else's
run. Every user is published to their own subtree (out/u/<user_id>/...),
each with its own manifest + rss.xml, reusing feed.py's existing
retention-pruning logic per user.

Only user_id (a UUID) is ever logged — never an email address or episode
content, since this runs in this repo's public Actions logs. Once
per-user API keys exist (BYOK, a later phase), anything pulled from
Supabase that could be a credential must be registered with
`::add-mask::` before use — nothing fetched here is a credential yet, so
that isn't needed for this script as written.
"""

import os
import sys
from datetime import datetime, timezone

import requests

from . import feed, sources, tts
from .curate import curate
from .settings import Settings, default_settings

REQUEST_TIMEOUT = 15


def _supabase_headers() -> dict:
    key = os.environ["SUPABASE_SERVICE_ROLE_KEY"]
    return {
        "apikey": key,
        "Authorization": f"Bearer {key}",
        "Content-Type": "application/json",
    }


def fetch_active_users() -> list[dict]:
    supabase_url = os.environ["SUPABASE_URL"]
    resp = requests.get(
        f"{supabase_url}/rest/v1/user_preferences",
        headers=_supabase_headers(),
        params={"select": "*"},
        timeout=REQUEST_TIMEOUT,
    )
    resp.raise_for_status()
    return resp.json()


FEEDBACK_LOOKBACK = 10


def fetch_recent_feedback(user_id: str) -> list[str]:
    """Best-effort: a feedback-fetch failure should degrade to "no notes
    this run", not take down that user's whole episode."""
    supabase_url = os.environ["SUPABASE_URL"]
    try:
        resp = requests.get(
            f"{supabase_url}/rest/v1/feedback",
            headers=_supabase_headers(),
            params={
                "user_id": f"eq.{user_id}",
                "select": "text",
                "order": "created_at.desc",
                "limit": str(FEEDBACK_LOOKBACK),
            },
            timeout=REQUEST_TIMEOUT,
        )
        resp.raise_for_status()
        return [row["text"] for row in resp.json()]
    except requests.RequestException as exc:
        print(f"warning: failed to fetch feedback for user {user_id}: {exc}")
        return []


def settings_for_user(row: dict) -> Settings:
    base = default_settings()
    user_id = row["user_id"]
    return base.with_overrides(
        rss_feeds=row["rss_feeds"],
        hn_story_count=row["hn_story_count"],
        target_word_count_min=row["target_word_count_min"],
        target_word_count_max=row["target_word_count_max"],
        host_a_voice=row["host_a_voice"],
        host_b_voice=row["host_b_voice"],
        feedback_notes=fetch_recent_feedback(user_id),
        output_dir=os.path.join(base.output_dir, "u", user_id),
        podcast_base_url=f"{base.podcast_base_url}/u/{user_id}",
    )


def record_episode(user_id: str, mp3_filename: str, title: str, description: str, url: str,
                    pub_date_iso: str, duration_seconds: int, file_size_bytes: int) -> None:
    """Best-effort metadata log in Supabase, for observability across users
    without digging through per-user files on gh-pages. A failure here must
    never break the actual RSS publish, which is what subscribers depend on.

    Upserts on (user_id, mp3_filename) — see schema.sql's
    episodes_user_id_mp3_filename_idx — so a same-day re-run (manual
    workflow_dispatch landing on top of the scheduled cron, an Actions
    retry) replaces that day's row instead of inserting a duplicate."""
    supabase_url = os.environ["SUPABASE_URL"]
    headers = _supabase_headers() | {"Prefer": "resolution=merge-duplicates"}
    try:
        resp = requests.post(
            f"{supabase_url}/rest/v1/episodes",
            headers=headers,
            params={"on_conflict": "user_id,mp3_filename"},
            json={
                "user_id": user_id,
                "mp3_filename": mp3_filename,
                "title": title,
                "description": description,
                "url": url,
                "pub_date": pub_date_iso,
                "duration_seconds": duration_seconds,
                "file_size_bytes": file_size_bytes,
            },
            timeout=REQUEST_TIMEOUT,
        )
        resp.raise_for_status()
    except requests.RequestException as exc:
        print(f"warning: failed to record episode metadata in Supabase: {exc}")


def generate_for_user(row: dict) -> bool:
    user_id = row["user_id"]
    print(f"--- generating episode for user {user_id} ---")
    settings = settings_for_user(row)

    items = sources.fetch_all(settings)
    if not items:
        print(f"user {user_id}: no candidate stories fetched from any source, skipping")
        return False

    now = datetime.now(timezone.utc)
    result = curate(items, episode_date=now.date(), settings=settings)
    print(f"user {user_id}: script ready — {result.word_count} words, {len(result.selected)} stories")

    date_str = now.strftime("%Y-%m-%d")
    mp3_filename = f"{date_str}.mp3"
    episodes_dir = os.path.join(settings.output_dir, feed.EPISODES_DIR)
    os.makedirs(episodes_dir, exist_ok=True)
    mp3_path = os.path.join(episodes_dir, mp3_filename)

    mp3_path, duration_seconds = tts.synthesize_episode(result.segments, mp3_path, settings)
    file_size_bytes = os.path.getsize(mp3_path)
    print(f"user {user_id}: audio ready — {duration_seconds}s, {file_size_bytes // 1024} KB")

    title = f"{settings.podcast_title} — {now.strftime('%B %-d, %Y')}"
    description = "\n".join(
        f"- {item['title']}: {item['blurb']} ({item['url']})" for item in result.selected
    )

    episodes = feed.add_episode(
        output_dir=settings.output_dir,
        mp3_filename=mp3_filename,
        title=title,
        description=description,
        pub_date_iso=now.isoformat(),
        duration_seconds=duration_seconds,
        file_size_bytes=file_size_bytes,
        settings=settings,
    )
    feed.build_rss(settings.output_dir, episodes, settings)

    mp3_url = f"{settings.podcast_base_url}/{feed.EPISODES_DIR}/{mp3_filename}"
    record_episode(
        user_id, mp3_filename, title, description, mp3_url,
        now.isoformat(), duration_seconds, file_size_bytes,
    )

    print(f"user {user_id}: done")
    return True


def run() -> None:
    users = fetch_active_users()
    print(f"found {len(users)} active user(s)")

    succeeded = 0
    failed = 0
    for row in users:
        try:
            if generate_for_user(row):
                succeeded += 1
            else:
                failed += 1
        except Exception as exc:  # noqa: BLE001 - one user's failure must not stop the rest
            print(f"user {row.get('user_id', '?')}: FAILED — {type(exc).__name__}: {exc}")
            failed += 1

    print(f"multi-tenant run complete: {succeeded} succeeded, {failed} failed")
    if users and succeeded == 0:
        sys.exit(1)


if __name__ == "__main__":
    run()
