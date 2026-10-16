"""Offline checks of the configured benchmark and its provenance boundary."""

import re
import tomllib
from collections import Counter
from collections.abc import Iterator
from importlib.metadata import version
from pathlib import Path
from typing import Any

import pytest
import yaml
from agentdojo.agent_pipeline.agent_pipeline import AgentPipeline
from agentdojo.agent_pipeline.ground_truth_pipeline import GroundTruthPipeline
from agentdojo.attacks.important_instructions_attacks import ImportantInstructionsAttack
from agentdojo.functions_runtime import FunctionsRuntime
from agentdojo.task_suite.load_suites import get_suites
from agentdojo.types import get_text_content_as_str
from packaging.requirements import Requirement

ROOT = Path(__file__).resolve().parents[1]


def read_config(name: str) -> dict[str, Any]:
    return yaml.safe_load((ROOT / "configs" / name).read_text(encoding="utf-8"))


@pytest.mark.parametrize("name", ["w1_smoke.yaml", "w1_baseline.yaml"])
def test_config_selects_installed_benchmark(name: str) -> None:
    config = read_config(name)["agentdojo"]
    project = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))
    requirement = next(
        Requirement(item)
        for item in project["project"]["dependencies"]
        if Requirement(item).name == "agentdojo"
    )
    assert str(requirement.specifier) == f"=={config['package_version']}"
    assert version("agentdojo") == config["package_version"]
    assert config["benchmark_version"] == project["tool"]["bdigate"]["benchmark_version"]

    suite = get_suites(config["benchmark_version"])[config["suite"]]
    assert "v" + ".".join(map(str, suite.benchmark_version)) == config["benchmark_version"]
    for selection in (config["user_tasks"], config["attack"]["enabled_for"]):
        if selection != "all":
            assert set(selection) <= suite.user_tasks.keys()
    injections = config["attack"]["injection_tasks"]
    if injections != "all":
        assert set(injections) <= suite.injection_tasks.keys()


def test_workspace_tools_have_exactly_one_static_provenance_rule() -> None:
    config = read_config("w1_smoke.yaml")
    suite = get_suites(config["agentdojo"]["benchmark_version"])[config["agentdojo"]["suite"]]
    rules = ROOT / config["logging"]["provenance_rules_file"]
    tools: list[str] = []
    for line in rules.read_text(encoding="utf-8").splitlines():
        if line.startswith("| R-"):
            tools.extend(re.findall(r"`([^`]+)`", line.split("|")[3]))
    assert Counter(tools) == Counter(tool.name for tool in suite.tools)


def string_values(value: object) -> Iterator[str]:
    if isinstance(value, str):
        yield value
    elif isinstance(value, list):
        for item in value:
            yield from string_values(item)
    elif isinstance(value, dict):
        for item in value.values():
            yield from string_values(item)


@pytest.mark.parametrize(
    "injection_id", read_config("w1_smoke.yaml")["agentdojo"]["attack"]["injection_tasks"]
)
def test_configured_attack_payload_is_observable(injection_id: str) -> None:
    config = read_config("w1_smoke.yaml")
    suite = get_suites(config["agentdojo"]["benchmark_version"])[config["agentdojo"]["suite"]]
    pipeline = AgentPipeline([])
    pipeline.name = config["agent"]["pipeline_name"]
    attack = ImportantInstructionsAttack(suite, pipeline)
    assert attack.name == config["agentdojo"]["attack"]["attack_name"]
    user = suite.get_user_task_by_id(config["agentdojo"]["attack"]["enabled_for"][0])
    injection = suite.get_injection_task_by_id(injection_id)
    payloads = attack.attack(user, injection)
    environment = user.init_environment(suite.load_and_inject_default_environment(payloads))
    _, _, _, messages, _ = GroundTruthPipeline(user).query(
        user.PROMPT, FunctionsRuntime(suite.tools), environment
    )
    observed: list[str] = []
    for message in messages:
        if message["role"] == "tool":
            text = get_text_content_as_str(message["content"])
            observed.append(text)
            observed.extend(string_values(yaml.safe_load(text)))
    assert any(injection.GOAL in text for text in observed)
