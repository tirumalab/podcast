"""Use Claude to pick the most interesting stories and write a narration script."""

from dataclasses import dataclass

import anthropic

from . import config
from .sources import Item

SYSTEM_PROMPT = """\
You are the writer for "Drive Radio", a short daily audio briefing a listener \
plays during their morning commute. You'll be given a list of candidate news \
items from Hacker News and a few tech/industry RSS feeds. Your job:

1. Pick the 5-6 most genuinely interesting, diverse stories from the list. \
Prefer variety (avoid picking five stories about the same narrow topic) and \
skip anything that's low-substance clickbait.
2. Write a natural, conversational narration script a friendly radio host would \
read aloud. It should flow as one continuous piece with brief spoken transitions \
between stories ("Next up...", "Meanwhile...", "And finally..."), a short warm \
opening (mention it's the listener's morning briefing, no need for a date), and \
a short sign-off. Do not use headers, bullet points, or any text that isn't \
meant to be spoken aloud — this script is fed directly to a text-to-speech engine.
3. Target {word_min}-{word_max} words total for the script.

Call the write_episode tool with your selection and script.
"""

WRITE_EPISODE_TOOL = {
    "name": "write_episode",
    "description": "Record the selected stories and the full narration script for today's episode.",
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
            "script": {
                "type": "string",
                "description": "The full narration script as one continuous string, ready for text-to-speech.",
            },
        },
        "required": ["selected", "script"],
    },
}


@dataclass
class CurationResult:
    script: str
    selected: list[dict]

    @property
    def word_count(self) -> int:
        return len(self.script.split())


def _build_user_prompt(items: list[Item]) -> str:
    lines = [item.as_prompt_line(i + 1) for i, item in enumerate(items)]
    return "Candidate stories:\n\n" + "\n".join(lines)


def curate(items: list[Item]) -> CurationResult:
    client = anthropic.Anthropic()

    system = SYSTEM_PROMPT.format(
        word_min=config.TARGET_WORD_COUNT_MIN,
        word_max=config.TARGET_WORD_COUNT_MAX,
    )

    response = client.messages.create(
        model=config.ANTHROPIC_MODEL,
        max_tokens=4096,
        system=system,
        tools=[WRITE_EPISODE_TOOL],
        tool_choice={"type": "tool", "name": "write_episode"},
        messages=[{"role": "user", "content": _build_user_prompt(items)}],
    )

    tool_use = next(block for block in response.content if block.type == "tool_use")
    data = tool_use.input

    return CurationResult(script=data["script"], selected=data["selected"])
