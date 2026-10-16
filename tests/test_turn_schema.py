import json
from pathlib import Path

import pytest
from jsonschema import Draft202012Validator

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture(scope="module")
def turn_validator() -> Draft202012Validator:
    schema = json.loads((ROOT / "schemas" / "turn.schema.json").read_text(encoding="utf-8"))
    Draft202012Validator.check_schema(schema)
    return Draft202012Validator(schema)


def committed_turn() -> dict[str, object]:
    return {
        "run_id": "run-1",
        "episode_id": "opaque-episode",
        "turn_index": 0,
        "message_index": 2,
        "plan_present": True,
        "plan_parse_ok": True,
        "plan_raw": '<plan>{"steps":["search"]}</plan>',
        "parse_error": None,
        "is_commit": True,
        "commit_index": 0,
    }


@pytest.mark.parametrize(
    ("changes", "valid"),
    [
        ({}, True),
        ({"is_commit": False, "commit_index": None}, True),
        (
            {
                "plan_present": False,
                "plan_parse_ok": False,
                "plan_raw": "Calling a tool without a plan.",
                "parse_error": "missing_plan",
                "is_commit": False,
                "commit_index": None,
            },
            True,
        ),
        (
            {
                "plan_parse_ok": False,
                "plan_raw": "<plan>{broken}</plan>",
                "parse_error": "invalid_json",
                "is_commit": False,
                "commit_index": None,
            },
            True,
        ),
        ({"plan_raw": '<plan>{"steps":["read the security report"]}</plan>'}, True),
        ({"plan_parse_ok": False, "parse_error": "invalid_json"}, False),
        ({"is_commit": False}, False),
        ({"commit_index": None}, False),
        ({"plan_present": False}, False),
        ({"parse_error": "invalid_json"}, False),
        ({"plan_parse_ok": False, "is_commit": False, "commit_index": None}, False),
        (
            {
                "plan_parse_ok": False,
                "parse_error": "",
                "is_commit": False,
                "commit_index": None,
            },
            False,
        ),
        ({"turn_index": -1}, False),
        ({"message_index": 0.5}, False),
        ({"commit_index": True}, False),
        ({"attack_name": "important_instructions"}, False),
    ],
)
def test_turn_schema_enforces_observable_state_contract(
    turn_validator: Draft202012Validator, changes: dict[str, object], valid: bool
) -> None:
    record = committed_turn() | changes
    assert turn_validator.is_valid(record) is valid


def test_turn_schema_rejects_missing_failure_status(turn_validator: Draft202012Validator) -> None:
    record = committed_turn()
    del record["parse_error"]
    assert turn_validator.is_valid(record) is False
