"""Fetch and normalize candidate stories from Hacker News and RSS feeds."""

import re
from dataclasses import dataclass

import feedparser
import requests

from .settings import Settings, default_settings

HN_FRONT_PAGE_URL = "https://hn.algolia.com/api/v1/search?tags=front_page"

_TAG_RE = re.compile(r"<[^>]+>")


@dataclass
class Item:
    title: str
    summary: str
    url: str
    source: str

    def as_prompt_line(self, index: int) -> str:
        summary = self.summary.strip()
        if summary:
            return f"{index}. [{self.source}] {self.title} — {summary}\n   Link: {self.url}"
        return f"{index}. [{self.source}] {self.title}\n   Link: {self.url}"


def _strip_html(text: str) -> str:
    if not text:
        return ""
    return _TAG_RE.sub("", text).strip()


def fetch_hacker_news(count: int) -> list[Item]:
    resp = requests.get(HN_FRONT_PAGE_URL, timeout=15)
    resp.raise_for_status()
    hits = resp.json().get("hits", [])

    hits.sort(key=lambda h: h.get("points") or 0, reverse=True)

    items = []
    for hit in hits[:count]:
        title = hit.get("title")
        url = hit.get("url") or f"https://news.ycombinator.com/item?id={hit.get('objectID')}"
        if not title:
            continue
        points = hit.get("points") or 0
        comments = hit.get("num_comments") or 0
        summary = f"{points} points, {comments} comments on Hacker News."
        items.append(Item(title=title, summary=summary, url=url, source="Hacker News"))
    return items


def fetch_rss_feed(feed_url: str, max_items: int = 8) -> list[Item]:
    parsed = feedparser.parse(feed_url)
    source_name = parsed.feed.get("title", feed_url)

    items = []
    for entry in parsed.entries[:max_items]:
        title = entry.get("title")
        if not title:
            continue
        summary = _strip_html(entry.get("summary", ""))
        url = entry.get("link", "")
        items.append(Item(title=title, summary=summary, url=url, source=source_name))
    return items


def fetch_all(settings: Settings | None = None) -> list[Item]:
    """Fetch Hacker News plus every configured RSS feed. Feeds that fail to
    load are skipped rather than aborting the whole run."""
    settings = settings or default_settings()
    items: list[Item] = []

    try:
        items.extend(fetch_hacker_news(settings.hn_story_count))
    except requests.RequestException as exc:
        print(f"warning: failed to fetch Hacker News: {exc}")

    for feed_url in settings.rss_feeds:
        try:
            items.extend(fetch_rss_feed(feed_url))
        except Exception as exc:  # noqa: BLE001 - a single bad feed shouldn't kill the run
            print(f"warning: failed to fetch feed {feed_url}: {exc}")

    return items
