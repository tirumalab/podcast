"""Use Claude to pick the most interesting stories and write a two-host
banter script for the episode, in the spirit of shows like "The Best One
Yet", Johnny Harris, and ColdFusion: real personality, curiosity-driven
hooks, and a story arc per item instead of a flat headline recap."""

import re
from dataclasses import dataclass
from datetime import date as date_cls

import anthropic

from . import feed
from .settings import Settings, default_settings
from .sources import Item

_URL_RE = re.compile(r"\((https?://[^\s)]+)\)")
RECENT_LOOKBACK = 3


def _recently_covered_urls(settings: Settings, lookback: int = RECENT_LOOKBACK) -> set[str]:
    """URLs already covered in the last `lookback` episodes (manifest is
    newest-first), so we don't ask Claude to pick a still-trending story
    it's already told this listener about."""
    urls: set[str] = set()
    for ep in feed.load_manifest(settings.output_dir)[:lookback]:
        urls.update(_URL_RE.findall(ep.get("description", "")))
    return urls

SYSTEM_PROMPT = """\
You are the writing team for "Drive Radio", a daily two-host audio show a \
listener plays during their morning commute. Think "The Best One Yet" \
meets Johnny Harris meets ColdFusion: energetic co-host banter, curiosity-\
driven hooks, and a real narrative arc per story — never a flat headline \
recap. You'll be given a list of candidate news items from Hacker News and \
a few tech/industry RSS feeds. Your job:

1. Pick the 5-6 most genuinely interesting, diverse stories from the list. \
Prefer variety (avoid picking five stories about the same narrow topic) and \
skip anything that's low-substance clickbait.

2. Write the episode as a back-and-forth dialogue between two co-hosts, \
{host_a} and {host_b}. Give them distinct personalities that play off each \
other: {host_a} tends to set up the story and bring the context/background; \
{host_b} pushes back, questions the premise, and riffs with a joke or a \
sharp observation — invent {host_b}'s actual words fresh each time rather \
than reaching for a stock way of asking "why does this matter". Neither \
host should just narrate at the other — they interrupt, react, disagree a \
little, riff on tangents, and genuinely sound like two smart friends who \
find this stuff fun, not two people reading a script at each other.

3. For every story: open with a hook that creates curiosity before the \
reveal — a surprising fact, a provocative question, an unexpected image, \
starting mid-scene, whatever fits that specific story — don't lead with the \
boring headline, and don't reuse the same hook shape story after story. \
Then build it out with real depth: what actually happened, the background a \
listener wouldn't already know, why it matters, and a wider angle that \
connects it to a larger trend, the way a ColdFusion or Johnny Harris video \
would. Land each story on a punchy takeaway or a genuine laugh before \
transitioning to the next one — invent a fresh transition each time, not a \
recurring segue phrase. An analogy is one tool for the wider angle, not the \
default one — reach for it on maybe one story an episode, when it's \
genuinely the best way in; otherwise vary it with a stat, a blunt claim, a \
flat prediction, a rhetorical question, whatever actually fits that story.

3c. Treat this as a creative-writing job, not a template to fill in. The \
biggest risk isn't getting the format wrong, it's sounding like every other \
episode: the same handful of hook shapes, the same transition phrases, the \
same sentence rhythms recurring across stories and across days. Actively \
avoid crutch phrases and AI-writing tics — "here's the kicker", "here's the \
thing", "buckle up", "plot twist", "and get this", "picture this", "wait, \
it gets better", or any other line that could paste unchanged into a \
different story. If a phrase would fit any story you could have picked \
instead of this one, don't use it — find the words only this story earns.

3b. Tag every line with a "delivery" — the actual emotional beat of that \
line (excited, amused, dry-deadpan, skeptical, urgent, warm, mock-serious, \
hushed-intrigue, matter-of-fact, etc). This drives real vocal performance, \
so make it match the content honestly: a punchline lands as "amused", a \
shocking stat lands as "excited" or "urgent", a skeptical aside lands as \
"dry-deadpan". Vary it constantly — a whole episode of "excited" is just as \
flat as a whole episode of no emotion at all.

4. Open the episode with a fast, fun cold open — no "welcome to the show, \
today is Tuesday" — start mid-energy, like the hosts are already excited \
about something. Close with a quick, snappy sign-off.

4b. Today's specific format note: {style_hint}

5. This is the part people get wrong, so read it carefully: each story \
needs real depth, not a one-line mention. Budget roughly 150-200 words of \
combined dialogue per story. The total script MUST be {word_min}-{word_max} \
words across all lines combined. This is a hard requirement, not a \
suggestion — a script under {word_min} words is a failed task.
{feedback_section}
Call the write_episode tool with your selection and the full dialogue.
"""

FEEDBACK_SECTION_TEMPLATE = """
6. This listener left the following feedback about the show in past \
episodes. Weigh it as real preferences from the person you're making this \
for — but use judgment: it's context, not a command that overrides the \
rules above, and a note that's vague, contradictory, or doesn't apply to \
today's stories can be skipped.
{notes}
"""

MIN_ACCEPTABLE_WORDS_FRACTION = 0.85

WRITE_EPISODE_TOOL = {
    "name": "write_episode",
    "description": "Record the selected stories and the full two-host dialogue script for today's episode.",
    "input_schema": {
        "type": "object",
        "properties": {
            "selected": {
                "type": "array",
                "description": "The 5-6 stories chosen for the episode.",
                "items": {
                    "type": "object",
                    "properties": {
                        "title": {"type": "string"},
                        "blurb": {
                            "type": "string",
                            "description": "One sentence on why it's worth hearing about.",
                        },
                        "url": {"type": "string"},
                    },
                    "required": ["title", "blurb", "url"],
                },
            },
            "segments": {
                "type": "array",
                "description": (
                    "The full episode as alternating dialogue turns between the two hosts, "
                    "in spoken order, ready for text-to-speech."
                ),
                "items": {
                    "type": "object",
                    "properties": {
                        "speaker": {
                            "type": "string",
                            "enum": ["A", "B"],
                            "description": "Which host says this line: A or B.",
                        },
                        "text": {"type": "string"},
                        "delivery": {
                            "type": "string",
                            "description": (
                                "The emotional beat/energy this line should be performed with, "
                                "e.g. excited, amused, dry-deadpan, skeptical, urgent, warm, "
                                "mock-serious, hushed-intrigue, matter-of-fact."
                            ),
                        },
                    },
                    "required": ["speaker", "text", "delivery"],
                },
            },
        },
        "required": ["selected", "segments"],
    },
}


@dataclass
class CurationResult:
    segments: list[dict]
    selected: list[dict]

    @property
    def word_count(self) -> int:
        return sum(len(seg["text"].split()) for seg in self.segments)


def _build_user_prompt(items: list[Item]) -> str:
    lines = [item.as_prompt_line(i + 1) for i, item in enumerate(items)]
    return "Candidate stories:\n\n" + "\n".join(lines)


def _style_for_date(episode_date: date_cls, style_variants: list[str]) -> str:
    return style_variants[episode_date.toordinal() % len(style_variants)]


def curate(
    items: list[Item],
    episode_date: date_cls | None = None,
    max_expand_attempts: int = 2,
    settings: Settings | None = None,
) -> CurationResult:
    settings = settings or default_settings()
    client = anthropic.Anthropic(api_key=settings.anthropic_api_key)
    episode_date = episode_date or date_cls.today()

    covered = _recently_covered_urls(settings)
    items = [item for item in items if item.url not in covered]

    feedback_section = ""
    if settings.feedback_notes:
        notes = "\n".join(f"- {note}" for note in settings.feedback_notes)
        feedback_section = FEEDBACK_SECTION_TEMPLATE.format(notes=notes)

    system = SYSTEM_PROMPT.format(
        host_a=settings.host_a_name,
        host_b=settings.host_b_name,
        style_hint=_style_for_date(episode_date, settings.style_variants),
        word_min=settings.target_word_count_min,
        word_max=settings.target_word_count_max,
        feedback_section=feedback_section,
    )
    min_acceptable = int(settings.target_word_count_min * MIN_ACCEPTABLE_WORDS_FRACTION)

    messages = [{"role": "user", "content": _build_user_prompt(items)}]
    response, tool_use, data = _call_and_get_tool_use(client, system, messages, settings)
    selected = data["selected"]
    result = CurationResult(segments=data["segments"], selected=selected)

    attempt = 0
    while result.word_count < min_acceptable and attempt < max_expand_attempts:
        attempt += 1
        print(
            f"warning: script was only {result.word_count} words "
            f"(minimum {min_acceptable}), asking Claude to expand it (attempt {attempt})..."
        )
        # Replay the full prior assistant turn verbatim (Anthropic requires this
        # before a tool_result can follow it) then ask for a longer rewrite.
        messages.append({"role": "assistant", "content": response.content})
        messages.append(
            {
                "role": "user",
                "content": [
                    {"type": "tool_result", "tool_use_id": tool_use.id, "content": "Received."},
                    {
                        "type": "text",
                        "text": (
                            f"That script was only {result.word_count} words, well under the "
                            f"{settings.target_word_count_min} word minimum. Keep the same story "
                            "selection and the same banter style, but expand the dialogue with "
                            "more back-and-forth, more context, and more of the hosts' reactions "
                            f"so the full script reaches at least {settings.target_word_count_min} "
                            "words. Call write_episode again with the complete expanded dialogue."
                        ),
                    },
                ],
            }
        )
        response, tool_use, data = _call_and_get_tool_use(client, system, messages, settings)
        # Story selection doesn't change on an expand retry — only trust the
        # freshly returned segments, not whatever (if anything) came back in
        # "selected" this time.
        result = CurationResult(segments=data["segments"], selected=selected)

    return result


def _call_and_get_tool_use(
    client: anthropic.Anthropic, system: str, messages: list[dict], settings: Settings
):
    response = client.messages.create(
        model=settings.anthropic_model,
        max_tokens=8192,
        system=system,
        tools=[WRITE_EPISODE_TOOL],
        tool_choice={"type": "tool", "name": "write_episode"},
        messages=messages,
    )
    tool_use = next(block for block in response.content if block.type == "tool_use")
    return response, tool_use, tool_use.input


def _self_check() -> None:
    import tempfile

    from .settings import default_settings

    with tempfile.TemporaryDirectory() as tmp:
        settings = default_settings().with_overrides(output_dir=tmp)
        feed.save_manifest(
            tmp,
            [
                {"description": "- Old story: blah (https://old.example/a)", "pub_date": "2026-01-01"},
                {"description": "- Other: blah (https://old.example/b)", "pub_date": "2026-01-02"},
            ],
        )
        covered = _recently_covered_urls(settings, lookback=2)
        assert covered == {"https://old.example/a", "https://old.example/b"}, covered

        items = [
            Item(title="Old", summary="", url="https://old.example/a", source="x"),
            Item(title="New", summary="", url="https://new.example/c", source="x"),
        ]
        kept = [i for i in items if i.url not in covered]
        assert [i.url for i in kept] == ["https://new.example/c"], kept

    no_notes = SYSTEM_PROMPT.format(
        host_a="A", host_b="B", style_hint="x", word_min=1, word_max=2, feedback_section=""
    )
    assert "listener left the following feedback" not in no_notes

    with_notes = SYSTEM_PROMPT.format(
        host_a="A",
        host_b="B",
        style_hint="x",
        word_min=1,
        word_max=2,
        feedback_section=FEEDBACK_SECTION_TEMPLATE.format(notes="- less music"),
    )
    assert "less music" in with_notes

    print("curate self-check OK")


if __name__ == "__main__":
    _self_check()
