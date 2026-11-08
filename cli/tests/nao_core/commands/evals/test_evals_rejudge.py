import json
from unittest.mock import patch

import pytest

from nao_core.commands.evals.rejudge import rejudge

ANSWERED = {
    "id": "q018",
    "input": "Why did visits drop?",
    "expected_output": "Required: CH-002 outage.",
    "actual_output": "CH-002 was down.",
    "retrieval_context": ["[SQL result]\nColumns: visits"],
    "answer_id": "answer-1",
    "arm": "B",
    "block": 1,
    "repetition": 2,
    "judge_model": "anthropic:claude-sonnet-4-6",
    "error_type": None,
}


class FakeMetric:
    def __init__(self, score: float = 0.7, error: Exception | None = None):
        self.threshold = 0.5
        self.score = score
        self.reason = "because"
        self._error = error
        self.judged_test_cases = []

    def measure(self, test_case):
        self.judged_test_cases.append(test_case)
        if self._error:
            raise self._error


def write_results(tmp_path, *records: dict, config: dict | None = None):
    results_file = tmp_path / "evals_results_20261106_000000.json"
    results_file.write_text(
        json.dumps(
            {
                "run": {"run_id": "run-1", "arm": "B"},
                "config": config or {"metrics": ["correctness"], "correctness": {"threshold": 0.6}},
                "results": list(records),
            }
        )
    )
    return results_file


def read_judgments(tmp_path):
    return json.loads(next(tmp_path.glob("rejudge_results_*.json")).read_text())


@pytest.fixture(autouse=True)
def project_folder(tmp_path, monkeypatch):
    """rejudge writes the cost ledger under the current project's tests/outputs."""
    monkeypatch.chdir(tmp_path)


@pytest.fixture
def built_metrics():
    created = []

    def build(judge, options):
        metric = FakeMetric()
        created.append((judge, options, metric))
        return [("Correctness", metric)]

    with (
        patch("nao_core.commands.evals.rejudge.resolve_judge", side_effect=lambda model: f"judge:{model}"),
        patch("nao_core.commands.evals.rejudge._build_metrics", side_effect=build),
    ):
        yield created


def test_each_answer_is_judged_once_per_judge_repetition_with_fresh_metrics(tmp_path, built_metrics):
    rejudge(write_results(tmp_path, ANSWERED), judge_repeats=3)

    data = read_judgments(tmp_path)
    judgments = data["judgments"]
    assert [judgment["judge_repetition"] for judgment in judgments] == [1, 2, 3]
    assert {(j["answer_id"], j["arm"], j["block"], j["repetition"]) for j in judgments} == {("answer-1", "B", 1, 2)}
    assert [j["metrics"][0]["score"] for j in judgments] == [0.7, 0.7, 0.7]
    assert len({id(metric) for _, _, metric in built_metrics}) == 3
    assert data["source"]["run"]["run_id"] == "run-1"
    assert len(data["source"]["sha256"]) == 64
    assert data["config"]["judge_repeats"] == 3


def test_saved_answer_and_context_are_what_the_judge_sees(tmp_path, built_metrics):
    rejudge(write_results(tmp_path, ANSWERED), judge_repeats=1)

    _, options, metric = built_metrics[0]
    test_case = metric.judged_test_cases[0]
    assert test_case.actual_output == "CH-002 was down."
    assert test_case.expected_output == "Required: CH-002 outage."
    assert test_case.retrieval_context == ["[SQL result]\nColumns: visits"]
    assert options.suites == ["correctness"]
    assert options.thresholds["correctness"] == 0.6


def test_judge_defaults_to_the_original_judge_unless_overridden(tmp_path, built_metrics):
    results_file = write_results(tmp_path, ANSWERED)

    rejudge(results_file, judge_repeats=1)
    rejudge(results_file, judge_repeats=1, judge_model="openai:gpt-4.1")

    assert [judge for judge, _, _ in built_metrics] == [
        "judge:anthropic:claude-sonnet-4-6",
        "judge:openai:gpt-4.1",
    ]


def test_answers_the_agent_never_produced_are_skipped_and_listed(tmp_path, built_metrics):
    timed_out = {**ANSWERED, "answer_id": "answer-2", "actual_output": None, "error_type": "timeout"}
    metric_failed = {**ANSWERED, "answer_id": "answer-3", "error_type": "metric_error"}

    rejudge(write_results(tmp_path, ANSWERED, timed_out, metric_failed), judge_repeats=1)

    data = read_judgments(tmp_path)
    assert [judgment["answer_id"] for judgment in data["judgments"]] == ["answer-1", "answer-3"]
    assert data["skipped"] == [{"answer_id": "answer-2", "id": "q018", "reason": "timeout"}]


def test_records_without_an_answer_id_get_a_stable_one(tmp_path, built_metrics):
    legacy = {key: value for key, value in ANSWERED.items() if key != "answer_id"}

    rejudge(write_results(tmp_path, legacy, legacy), judge_repeats=1)

    answer_ids = [judgment["answer_id"] for judgment in read_judgments(tmp_path)["judgments"]]
    assert answer_ids[0].endswith(":0")
    assert answer_ids[1].endswith(":1")


def test_a_metric_error_is_recorded_and_exits_non_zero(tmp_path):
    with (
        patch("nao_core.commands.evals.rejudge.resolve_judge", return_value="judge"),
        patch(
            "nao_core.commands.evals.rejudge._build_metrics",
            return_value=[("Correctness", FakeMetric(error=RuntimeError("judge down")))],
        ),
        pytest.raises(SystemExit) as exc_info,
    ):
        rejudge(write_results(tmp_path, ANSWERED), judge_repeats=1)

    assert exc_info.value.code == 1
    assert read_judgments(tmp_path)["judgments"][0]["metrics"][0]["error"] == "judge down"


def test_unreadable_results_file_stops(tmp_path):
    with pytest.raises(SystemExit):
        rejudge(tmp_path / "missing.json")
