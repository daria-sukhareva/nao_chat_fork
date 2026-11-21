import json
from typing import Any

import pytest

from nao_core.commands.evals.compare import compare, find_comparison_problems, find_tolerated_differences, summarize_run

COMMON_FILES = {"databases/fact_visits/columns.md": "c1", "docs/glossary.md": "g1"}


def results(tmp_path, name: str, *, arm: str, block: int, context: dict[str, str], arm_files: list[str], **overrides):
    record = {
        "agent_model": "anthropic:claude-sonnet-4-6",
        "judge_model": "anthropic:claude-sonnet-4-6",
        "judge_settings": {"temperature": 0.0, "max_tokens": 4096},
        "run_context": {
            "tool_manifest_sha256": "t" * 64,
            "system_prompt_stable_sha256": overrides.pop("prompt", f"prompt-{arm}"),
            "model_call_settings": {},
        },
    }
    data: dict[str, Any] = {
        "run": {
            "experiment_id": "exp-1",
            "arm": arm,
            "block": block,
            "confirmatory": {"valid": True, "problems": []},
            "stopped": None,
            "arm_manifest": {"files": {file: "x" for file in arm_files} | {"tests/evals/golden_dataset.jsonl": "d"}},
        },
        "config": {"metrics": ["correctness"], "correctness": {"rubric_version": "0015f7a322a7"}},
        "provenance": {
            "dataset": {"sha256": "d" * 64},
            "packages": {"deepeval": "4.2.3"},
            "environment_changed": [],
            "environment_start": {
                "nao": {"commit": "a" * 40},
                "repos": [{"name": "kwwhat", "commit": "k" * 40, "dirty": False}],
                "data": [{"databaseId": "duckdb", "tables": [{"table": "fact_visits", "checksum": "1"}]}],
                "context": {"files": [{"path": path, "sha256": sha} for path, sha in context.items()]},
            },
        },
        "results": [record],
    }
    for key, value in overrides.items():
        section, field = key.split("__")
        data[section][field] = value
    path = tmp_path / f"{name}.json"
    path.write_text(json.dumps(data))
    return path


def arm_a(tmp_path, name="a1", block=1, **overrides):
    context = {**COMMON_FILES, "RULES.md": "rules-a", "agent/skills/root-cause-analysis.md": "rca"}
    return results(
        tmp_path,
        name,
        arm="A",
        block=block,
        context=context,
        arm_files=["RULES.md", "agent/skills/root-cause-analysis.md"],
        **overrides,
    )


def arm_b(tmp_path, name="b1", block=2, context_overrides=None, **overrides):
    context = {
        **COMMON_FILES,
        "RULES.md": "rules-b",
        "agent/skills/root-cause-analysis.md": "rca",
        "docs/metrics_tree.md": "tree",
        **(context_overrides or {}),
    }
    files = ["RULES.md", "agent/skills/root-cause-analysis.md", "docs/metrics_tree.md"]
    return results(tmp_path, name, arm="B", block=block, context=context, arm_files=files, **overrides)


def problems(*paths, confirmatory=False):
    return find_comparison_problems([summarize_run(path) for path in paths], confirmatory)


def test_arms_that_differ_only_in_their_own_files_can_be_paired(tmp_path):
    assert problems(arm_a(tmp_path), arm_b(tmp_path), confirmatory=True) == []


def test_a_file_outside_both_arms_that_differs_is_refused(tmp_path):
    found = problems(arm_a(tmp_path), arm_b(tmp_path, context_overrides={"docs/glossary.md": "g2"}))

    assert found == ["a1.json and b1.json: docs/glossary.md differs, and it isn't one of either arm's files"]


def test_two_blocks_of_the_same_arm_must_have_identical_context_and_prompt(tmp_path):
    first = arm_a(tmp_path, "a1", block=1)
    second = results(
        tmp_path,
        "a2",
        arm="A",
        block=4,
        context={**COMMON_FILES, "RULES.md": "edited", "agent/skills/root-cause-analysis.md": "rca"},
        arm_files=["RULES.md"],
        prompt="prompt-edited",
    )

    found = problems(first, second)

    assert "a1.json and a2.json: same arm A, but RULES.md differs" in found
    assert "a1.json and a2.json: same arm A, but the system prompt differs" in found


def test_a_run_without_an_arm_label_is_refused_even_when_its_change_is_in_an_arm_file(tmp_path):
    unlabeled = arm_b(
        tmp_path, "b2", block=3, context_overrides={"RULES.md": "edited"}, run__arm=None, run__arm_manifest=None
    )

    found = problems(arm_b(tmp_path), unlabeled)

    assert found == ["b2.json: no arm label, so its context can't be checked against an arm (run with --arm-manifest)"]


def test_anything_held_fixed_that_differs_is_refused(tmp_path):
    found = problems(arm_a(tmp_path), arm_b(tmp_path, provenance__packages={"deepeval": "4.3.0"}))

    assert found == ["packages differs from a1.json in b1.json"]


def test_a_changed_environment_a_stopped_run_and_a_repeated_block_are_refused(tmp_path):
    found = problems(
        arm_a(tmp_path, block=1, provenance__environment_changed=["data"]),
        arm_b(tmp_path, block=1, run__stopped={"reason": "max_cost"}),
    )

    assert "a1.json: the environment changed during the run (data)" in found
    assert "b1.json: the run stopped early (max_cost)" in found
    assert "block 1 appears in 2 runs" in found


def test_confirmatory_comparison_requires_every_run_to_be_valid(tmp_path):
    invalid = arm_b(tmp_path, run__confirmatory={"valid": False, "problems": ["x"]})

    assert problems(arm_a(tmp_path), invalid) == []
    assert problems(arm_a(tmp_path), invalid, confirmatory=True) == ["b1.json: not a valid confirmatory run"]


def test_compare_exits_non_zero_when_runs_cant_be_paired(tmp_path):
    with pytest.raises(SystemExit) as exc_info:
        compare([arm_a(tmp_path), arm_b(tmp_path, context_overrides={"docs/glossary.md": "g2"})])

    assert exc_info.value.code == 1


def test_compare_needs_two_files(tmp_path):
    with pytest.raises(SystemExit):
        compare([arm_a(tmp_path)])


PREVIEW = "databases/type=duckdb/database=analytics/schema=MARTS/table=fact_visits/preview.md"


def test_a_resampled_preview_of_identical_data_is_tolerated_but_reported(tmp_path):
    first = arm_a(tmp_path)
    second = arm_b(tmp_path, context_overrides={PREVIEW: "other sample"})
    runs = [summarize_run(first), summarize_run(second)]

    assert find_comparison_problems(runs, False) == []
    [note] = find_tolerated_differences(runs)
    assert "1 preview.md file(s) show different sample rows" in note


def test_a_preview_that_differs_along_with_the_data_is_not_tolerated(tmp_path):
    changed_data = [{"databaseId": "duckdb", "tables": [{"table": "fact_visits", "checksum": "2"}]}]
    first = arm_a(tmp_path)
    second = arm_b(tmp_path, context_overrides={PREVIEW: "other sample"})
    data = json.loads(second.read_text())
    data["provenance"]["environment_start"]["data"] = changed_data
    second.write_text(json.dumps(data))

    found = problems(first, second)

    assert "data differs from a1.json in b1.json" in found
    assert any(PREVIEW in problem for problem in found)
