"""All per-episode configuration bundled into one object.

`config.py` remains the single-user source of truth and supplies the defaults;
`Settings.from_config()` snapshots them. This exists so one process can
generate episodes for several people in a row, each with their own sources,
voices, and length — a multi-tenant caller builds its own `Settings` per user
rather than mutating module-level globals.
"""

from dataclasses import dataclass, replace

from . import config


@dataclass
class Settings:
    # Where candidate stories come from
    rss_feeds: list[str]
    hn_story_count: int

    # Script generation
    anthropic_model: str
    anthropic_api_key: str | None
    target_word_count_min: int
    target_word_count_max: int
    style_variants: list[str]
    host_a_name: str
    host_b_name: str

    # Voice synthesis
    kokoro_lang_code: str
    host_a_voice: str
    host_b_voice: str
    delivery_speed_keywords: dict[str, float]
    turn_gap_ms: int

    # Audio production
    intro_clip: str | None
    outro_clip: str | None
    background_music: str | None
    background_music_gain_db: int

    # Feed / output
    podcast_base_url: str
    podcast_title: str
    podcast_description: str
    podcast_author: str
    max_episodes_in_feed: int
    output_dir: str

    @classmethod
    def from_config(cls) -> "Settings":
        """Snapshot the defaults from config.py. Mutable values are copied so
        one caller's Settings can never mutate another's."""
        return cls(
            rss_feeds=list(config.RSS_FEEDS),
            hn_story_count=config.HN_STORY_COUNT,
            anthropic_model=config.ANTHROPIC_MODEL,
            anthropic_api_key=None,  # None => the Anthropic SDK reads ANTHROPIC_API_KEY
            target_word_count_min=config.TARGET_WORD_COUNT_MIN,
            target_word_count_max=config.TARGET_WORD_COUNT_MAX,
            style_variants=list(config.STYLE_VARIANTS),
            host_a_name=config.HOST_A_NAME,
            host_b_name=config.HOST_B_NAME,
            kokoro_lang_code=config.KOKORO_LANG_CODE,
            host_a_voice=config.HOST_A_VOICE,
            host_b_voice=config.HOST_B_VOICE,
            delivery_speed_keywords=dict(config.DELIVERY_SPEED_KEYWORDS),
            turn_gap_ms=config.TURN_GAP_MS,
            intro_clip=config.INTRO_CLIP,
            outro_clip=config.OUTRO_CLIP,
            background_music=config.BACKGROUND_MUSIC,
            background_music_gain_db=config.BACKGROUND_MUSIC_GAIN_DB,
            podcast_base_url=config.PODCAST_BASE_URL,
            podcast_title=config.PODCAST_TITLE,
            podcast_description=config.PODCAST_DESCRIPTION,
            podcast_author=config.PODCAST_AUTHOR,
            max_episodes_in_feed=config.MAX_EPISODES_IN_FEED,
            output_dir=config.OUTPUT_DIR,
        )

    def with_overrides(self, **overrides) -> "Settings":
        """Return a copy with some fields changed — how a multi-tenant caller
        layers one user's preferences over the defaults."""
        return replace(self, **overrides)


_default: Settings | None = None


def default_settings() -> Settings:
    """The single-user Settings built from config.py, created once and reused.

    Every pipeline function takes `settings=None` and falls back to this, so
    the existing single-user entry point works unchanged.
    """
    global _default
    if _default is None:
        _default = Settings.from_config()
    return _default
