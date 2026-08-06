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

# OpenAI TTS settings. The episode is a two-host banter dialogue (think "The
# Best One Yet"), each host synthesized with its own distinct voice.
# gpt-4o-mini-tts (unlike tts-1) supports an "instructions" prompt that
# steers tone/energy/pacing per request, which is how each line gets real
# delivery instead of a flat reading. Pick any two voices: alloy, ash,
# ballad, coral, echo, fable, nova, onyx, sage, shimmer, verse, marin, cedar.
TTS_MODEL = "gpt-4o-mini-tts"
HOST_A_NAME = "Turbo"
HOST_A_VOICE = "onyx"
HOST_A_PERSONA = (
    "a confident, quick-talking podcast co-host who sets up stories with context and momentum"
)
HOST_B_NAME = "Nova"
HOST_B_VOICE = "coral"  # OpenAI describes coral as its "energetic" voice
HOST_B_PERSONA = (
    "a witty, reactive podcast co-host who riffs, jokes, and asks the questions the listener "
    "is thinking"
)

# Silence inserted between speaker turns, for a natural hand-off feel.
TURN_GAP_MS = 250

# Optional royalty-free bumper clips stitched onto the front/back of the
# episode. Set to None (or delete the files) to skip bumpers entirely.
INTRO_CLIP = "assets/intro.mp3"
OUTRO_CLIP = "assets/outro.mp3"

# Optional background music bed, looped under the whole episode (including
# the bumpers) at a reduced volume so it sits behind the dialogue instead of
# competing with it. Set to None (or delete the file) to skip it entirely.
BACKGROUND_MUSIC = "assets/background_music.mp3"
BACKGROUND_MUSIC_GAIN_DB = -22

# Base URL the podcast feed and audio files are published at, e.g.
# "https://<github-username>.github.io/<repo-name>". Update this once the
# GitHub Pages site exists — the RSS feed's enclosure URLs are built from it.
PODCAST_BASE_URL = os.environ.get("PODCAST_BASE_URL", "https://example.github.io/drive-radio")

PODCAST_TITLE = "Drive Radio"
PODCAST_DESCRIPTION = "A personal morning briefing of tech and industry news."
PODCAST_AUTHOR = "Drive Radio"

# How many past episodes to keep listed in the RSS feed.
MAX_EPISODES_IN_FEED = 14

# Daily rotation of energy/format for the script, so consecutive mornings
# don't all sound the same. Picked deterministically from the date, add as
# many variants as you like.
STYLE_VARIANTS = [
    "Fast-paced and rapid-fire today: quick hits, lots of back-and-forth, don't dwell too long on any single point.",
    "Lean into an investigative-mystery vibe on the biggest story today — build suspense before the reveal — then move briskly through the rest.",
    "Give it a laid-back story-time feel today: more scene-setting, more color commentary, a slower burn before each punchline or reveal.",
    "Make today a friendly debate: have the hosts stake out slightly different takes on at least one story and push back on each other before finding common ground.",
    "Today has a 'can you believe this' energy throughout — treat the stories like juicy gossip the hosts are excited to share.",
]

OUTPUT_DIR = "out"
