import pytest

from bdigate.harness.plan import intention_diff, parse_plan, plan_changed


def test_valid_plan_preserves_raw_text_order_whitespace_and_duplicates() -> None:
    block = '<plan>{"steps": [" 메일 검색 ", "일정 생성", " 메일 검색 "]}</plan>'
    result = parse_plan(f"Thinking before the plan.\n{block}\nCalling a tool.")
    assert result.plan_present is True
    assert result.plan_parse_ok is True
    assert result.plan_raw == block
    assert result.parse_error is None
    assert result.steps == [" 메일 검색 ", "일정 생성", " 메일 검색 "]


def test_empty_steps_are_a_valid_completion_plan() -> None:
    result = parse_plan('<plan>{"steps": []}</plan>')
    assert result.plan_parse_ok is True
    assert result.steps == []
    assert plan_changed(None, result.steps) is True
    assert plan_changed([], result.steps) is False


@pytest.mark.parametrize(
    ("text", "present", "error"),
    [
        ("", False, "missing_plan"),
        ('Calling search_emails({"query":"meeting"}).', False, "missing_plan"),
        ('<plan>{"steps":["search"]', True, "malformed_plan_tag"),
        ('</plan>{"steps":[]}<plan>', True, "malformed_plan_tag"),
        ('<plan>{"steps":[]}</plan><plan>{"steps":["send"]}</plan>', True, "multiple_plan_blocks"),
        ('<plan>{"steps": [}</plan>', True, "invalid_json"),
        ('<plan>{"steps": []} trailing</plan>', True, "invalid_json"),
        ('<plan>{"steps": "search"}</plan>', True, "invalid_steps"),
        ('<plan>{"steps": ["search", 7]}</plan>', True, "invalid_steps"),
        ('<plan>{"steps": [], "attack_name": "hidden"}</plan>', True, "invalid_steps"),
        ('<plan>["search"]</plan>', True, "invalid_steps"),
    ],
)
def test_failed_plan_is_retained_without_a_proposed_intention(
    text: str, present: bool, error: str
) -> None:
    result = parse_plan(text)
    assert result.plan_present is present
    assert result.plan_parse_ok is False
    assert result.plan_raw == text
    assert result.parse_error == error
    assert result.steps is None


@pytest.mark.parametrize(
    ("previous", "proposed", "changed"),
    [
        (None, ["search"], True),
        (["search"], ["search"], False),
        (["search", "send"], ["send", "search"], True),
        (["search", "search"], ["search"], True),
        (["search"], [" search "], True),
    ],
)
def test_plan_comparison_preserves_sequence_semantics(
    previous: list[str] | None, proposed: list[str], changed: bool
) -> None:
    assert plan_changed(previous, proposed) is changed


@pytest.mark.parametrize(
    ("previous", "proposed", "expected"),
    [
        (None, ["a", "a"], {"added": ["a", "a"], "removed": [], "kept": []}),
        (["a", "a"], ["a", "b"], {"added": ["b"], "removed": ["a"], "kept": ["a"]}),
        (["a", "b"], ["b", "a"], {"added": [], "removed": [], "kept": ["b", "a"]}),
        (["a", "b", "a"], [], {"added": [], "removed": ["a", "b", "a"], "kept": []}),
        (["a"], ["a", "a"], {"added": ["a"], "removed": [], "kept": ["a"]}),
    ],
)
def test_diff_preserves_occurrence_counts_without_mutating_inputs(
    previous: list[str] | None, proposed: list[str], expected: dict[str, list[str]]
) -> None:
    original_previous = None if previous is None else previous.copy()
    original_proposed = proposed.copy()
    assert intention_diff(previous, proposed) == expected
    assert previous == original_previous
    assert proposed == original_proposed
