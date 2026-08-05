import os

# Default set of tech/industry RSS feeds. Add or remove URLs here to change
# what the show pulls from — no code changes needed elsewhere.
RSS_FEEDS = [
    "https://techcrunch.com/feed/",
    "https://www.theverge.com/rss/index.xml",
    "https://feeds.arstechnica.com/arstechnica/index",
]

# How many top Hacker News stories (via the Algolia API) to pull as candidates,
# on top of the RSS feeds above.
HN_STORY_COUNT = 15

# Target spoken length of the episode.
TARGET_WORD_COUNT_MIN = 2200
TARGET_WORD_COUNT_MAX = 2700

# Claude model used to pick stories and write the narration script.
ANTHROPIC_MODEL = "claude-sonnet-5"

# OpenAI TTS settings.
TTS_MODEL = "tts-1"
TTS_VOICE = "onyx"

# Optional royalty-free bumper clips stitched onto the front/back of the
# episode. Set to None (or delete the files) to skip bumpers entirely.
INTRO_CLIP = "assets/intro.mp3"
OUTRO_CLIP = "assets/outro.mp3"

# Base URL the podcast feed and audio files are published at, e.g.
# "https://<github-username>.github.io/<repo-name>". Update this once the
# GitHub Pages site exists — the RSS feed's enclosure URLs are built from it.
PODCAST_BASE_URL = os.environ.get("PODCAST_BASE_URL", "https://example.github.io/drive-radio")

PODCAST_TITLE = "Drive Radio"
PODCAST_DESCRIPTION = "A personal morning briefing of tech and industry news."
PODCAST_AUTHOR = "Drive Radio"

# How many past episodes to keep listed in the RSS feed.
MAX_EPISODES_IN_FEED = 14

OUTPUT_DIR = "out"
