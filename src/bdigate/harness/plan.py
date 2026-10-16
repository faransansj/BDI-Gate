"""Parse observable plan blocks without modifying or approving their steps."""

import json
import re
from collections import Counter
from dataclasses import dataclass
from typing import TypedDict

_PLAN_TAG = re.compile(r"</?plan>")


@dataclass(frozen=True, slots=True)
class PlanParseResult:
    plan_present: bool
    plan_parse_ok: bool
    plan_raw: str
    parse_error: str | None
    steps: list[str] | None


class IntentionDiff(TypedDict):
    added: list[str]
    removed: list[str]
    kept: list[str]


def parse_plan(text: str) -> PlanParseResult:
    """Return a failure record instead of dropping missing or malformed plans."""
    tags = list(_PLAN_TAG.finditer(text))
    if not tags:
        return PlanParseResult(False, False, text, "missing_plan", None)
    if len(tags) > 2:
        return PlanParseResult(True, False, text, "multiple_plan_blocks", None)
    if len(tags) != 2 or tags[0].group() != "<plan>" or tags[1].group() != "</plan>":
        return PlanParseResult(True, False, text, "malformed_plan_tag", None)

    start, end = tags
    try:
        value = json.loads(text[start.end() : end.start()])
    except (ValueError, RecursionError):
        return PlanParseResult(True, False, text, "invalid_json", None)
    if (
        not isinstance(value, dict)
        or set(value) != {"steps"}
        or not isinstance(value["steps"], list)
        or not all(isinstance(step, str) for step in value["steps"])
    ):
        return PlanParseResult(True, False, text, "invalid_steps", None)
    return PlanParseResult(True, True, text[start.start() : end.end()], None, value["steps"])


def plan_changed(previous: list[str] | None, proposed: list[str]) -> bool:
    """The first plan (including []) commits; exact repeats do not."""
    return previous != proposed


def intention_diff(previous: list[str] | None, proposed: list[str]) -> IntentionDiff:
    """Preserve duplicate occurrences and list order; do not infer causality."""
    remaining_previous = Counter(previous or [])
    added: list[str] = []
    kept: list[str] = []
    for step in proposed:
        if remaining_previous[step]:
            kept.append(step)
            remaining_previous[step] -= 1
        else:
            added.append(step)

    removed: list[str] = []
    for step in previous or []:
        if remaining_previous[step]:
            removed.append(step)
            remaining_previous[step] -= 1
    return {"added": added, "removed": removed, "kept": kept}
