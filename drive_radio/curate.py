"""Use Claude to pick the most interesting stories and write a two-host
banter script for the episode, in the spirit of shows like "The Best One
Yet", Johnny Harris, and ColdFusion: real personality, curiosity-driven
hooks, and a story arc per item instead of a flat headline recap."""

from dataclasses import dataclass
from datetime import date as date_cls

import anthropic

from . import config
from .sources import Item

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
{host_b} reacts, asks the "wait, but why does this matter" questions, and \
riffs with a joke or a sharp observation. Neither host should just narrate \
at the other — they interrupt, react, disagree a little, riff on tangents, \
and genuinely sound like two smart friends who find this stuff fun, not two \
people reading a script at each other.

3. For every story: open with a hook that creates curiosity before the \
reveal (a surprising fact, a provocative question, a "you will not believe \
what just happened" beat) — don't lead with the boring headline. Then build \
it out with real depth: what actually happened, the background a listener \
wouldn't already know, why it matters, and a "here's the bigger picture" \
angle, the way a ColdFusion or Johnny Harris video connects a single story \
to a larger trend. Land each story on a punchy takeaway or a genuine laugh \
before transitioning to the next one.

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

Call the write_episode tool with your selection and the full dialogue.
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


def _style_for_date(episode_date: date_cls) -> str:
    return config.STYLE_VARIANTS[episode_date.toordinal() % len(config.STYLE_VARIANTS)]


def curate(items: list[Item], episode_date: date_cls | None = None, max_expand_attempts: int = 2) -> CurationResult:
    client = anthropic.Anthropic()
    episode_date = episode_date or date_cls.today()

    system = SYSTEM_PROMPT.format(
        host_a=config.HOST_A_NAME,
        host_b=config.HOST_B_NAME,
        style_hint=_style_for_date(episode_date),
        word_min=config.TARGET_WORD_COUNT_MIN,
        word_max=config.TARGET_WORD_COUNT_MAX,
    )
    min_acceptable = int(config.TARGET_WORD_COUNT_MIN * MIN_ACCEPTABLE_WORDS_FRACTION)

    messages = [{"role": "user", "content": _build_user_prompt(items)}]
    response, tool_use, data = _call_and_get_tool_use(client, system, messages)
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
                            f"{config.TARGET_WORD_COUNT_MIN} word minimum. Keep the same story "
                            "selection and the same banter style, but expand the dialogue with "
                            "more back-and-forth, more context, and more of the hosts' reactions "
                            f"so the full script reaches at least {config.TARGET_WORD_COUNT_MIN} "
                            "words. Call write_episode again with the complete expanded dialogue."
                        ),
                    },
                ],
            }
        )
        response, tool_use, data = _call_and_get_tool_use(client, system, messages)
        # Story selection doesn't change on an expand retry — only trust the
        # freshly returned segments, not whatever (if anything) came back in
        # "selected" this time.
        result = CurationResult(segments=data["segments"], selected=selected)

    return result


def _call_and_get_tool_use(client: anthropic.Anthropic, system: str, messages: list[dict]):
    response = client.messages.create(
        model=config.ANTHROPIC_MODEL,
        max_tokens=8192,
        system=system,
        tools=[WRITE_EPISODE_TOOL],
        tool_choice={"type": "tool", "name": "write_episode"},
        messages=messages,
    )
    tool_use = next(block for block in response.content if block.type == "tool_use")
    return response, tool_use, tool_use.input
