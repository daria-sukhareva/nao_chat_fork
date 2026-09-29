import json
from unittest.mock import MagicMock, patch

import pytest

from nao_core.commands.evals.case import EvalCase
from nao_core.commands.evals.client import AgentAnswer, AgentBackendError, AgentTimeoutError
from nao_core.commands.evals.runner import EvalOptions, MetricSuite, evals, measure_metric, run_case, save_results

CASE = EvalCase(id="q001", input="How many ports are decommissioned?", expected_output="4 ports.")
ANSWER = AgentAnswer(text="There are 4 decommissioned ports.", model="anthropic:claude-sonnet-4-6")


class FakeMetric:
    def __init__(self, score: float | None = None, error: Exception | None = None, threshold: float = 0.5):
        self.threshold = threshold
        self.score = score
        self.reason = "because"
        self._error = error

    def measure(self, test_case):
        if self._error:
            raise self._error


def make_options(suites: list[MetricSuite] = ["correctness"], judge_model: str | None = None) -> EvalOptions:
    return EvalOptions(
        suites=suites,
        model=None,
        judge_model=judge_model,
        correctness_threshold=0.5,
        verbose=False,
    )


def make_client(answer=ANSWER, error: Exception | None = None):
    client = MagicMock()
    client.ask.side_effect = error
    client.ask.return_value = answer
    return client


@pytest.fixture
def fake_metrics():
    with (
        patch("nao_core.commands.evals.runner.resolve_judge", return_value="judge"),
        patch("nao_core.commands.evals.runner._build_metrics") as build_metrics,
    ):
        yield build_metrics


@pytest.mark.parametrize(
    ("error", "error_type"),
    [(AgentTimeoutError("slow"), "timeout"), (AgentBackendError("500 boom"), "backend_error")],
)
def test_agent_errors_skip_the_judge(error, error_type, fake_metrics):
    result = run_case(CASE, make_client(error=error), make_options())

    assert result.error_type == error_type
    assert result.passed is False
    assert result.actual_output is None
    fake_metrics.assert_not_called()


def test_passing_metrics_pass_the_case(fake_metrics):
    fake_metrics.return_value = [("Correctness", FakeMetric(score=0.9)), ("Faithfulness", FakeMetric(score=0.8))]

    result = run_case(CASE, make_client(), make_options())

    assert result.passed is True
    assert result.error_type is None
    assert result.actual_output == ANSWER.text
    assert [metric.score for metric in result.metrics] == [0.9, 0.8]


def test_score_below_threshold_is_a_normal_failure(fake_metrics):
    fake_metrics.return_value = [("Correctness", FakeMetric(score=0.3))]

    result = run_case(CASE, make_client(), make_options())

    assert result.passed is False
    assert result.error_type is None


def test_metric_exception_is_reported_as_metric_error(fake_metrics):
    fake_metrics.return_value = [
        ("Correctness", FakeMetric(error=RuntimeError("judge down"))),
        ("Faithfulness", FakeMetric(score=1.0)),
    ]

    result = run_case(CASE, make_client(), make_options())

    assert result.error_type == "metric_error"
    assert result.passed is False
    assert result.metrics[0].error == "judge down"
    assert result.metrics[1].passed is True


def test_judge_defaults_to_the_agent_model_unless_overridden(fake_metrics):
    fake_metrics.return_value = []

    default_judge = run_case(CASE, make_client(), make_options())
    explicit_judge = run_case(CASE, make_client(), make_options(judge_model="openai:gpt-4.1"))

    assert default_judge.judge_model == "anthropic:claude-sonnet-4-6"
    assert explicit_judge.judge_model == "openai:gpt-4.1"


def test_measure_metric_uses_the_metric_threshold():
    result = measure_metric("Correctness", FakeMetric(score=0.61234, threshold=0.6), test_case=None)

    assert result.score == 0.6123
    assert result.passed is True
    assert result.threshold == 0.6


def test_save_results_records_versions_and_summary(tmp_path, fake_metrics):
    fake_metrics.return_value = [("Correctness", FakeMetric(score=0.9))]
    options = make_options(suites=["rag", "correctness"])
    results = [
        run_case(CASE, make_client(), options),
        run_case(CASE, make_client(error=AgentTimeoutError("slow")), options),
    ]

    output_file = save_results(results, options, tmp_path)

    data = json.loads(output_file.read_text())
    assert output_file.name.startswith("evals_results_")
    assert data["config"]["metrics"] == ["rag", "correctness"]
    assert data["config"]["deepeval_version"]
    assert len(data["config"]["correctness"]["rubric_version"]) == 12
    assert data["summary"] == {"total": 2, "passed": 1, "failed": 0, "errored": 1}
    assert data["results"][1]["error_type"] == "timeout"


def write_dataset(tmp_path, *rows: dict):
    dataset = tmp_path / "tests" / "evals" / "golden_dataset.jsonl"
    dataset.parent.mkdir(parents=True)
    dataset.write_text("\n".join(json.dumps(row) for row in rows))


@pytest.fixture
def fake_backend():
    with (
        patch("nao_core.commands.evals.runner._build_authenticated_client", return_value=MagicMock()),
        patch("nao_core.commands.evals.runner.EvalsClient") as client_cls,
    ):
        client_cls.return_value = make_client()
        yield client_cls


def test_evals_exits_non_zero_when_a_case_fails(tmp_path, monkeypatch, fake_backend, fake_metrics):
    monkeypatch.chdir(tmp_path)
    write_dataset(tmp_path, {"id": "q001", "input": "a", "expected_output": "b"})
    fake_metrics.return_value = [("Correctness", FakeMetric(score=0.1))]

    with pytest.raises(SystemExit) as exc_info:
        evals()

    assert exc_info.value.code == 1


def test_evals_exits_zero_when_all_cases_pass(tmp_path, monkeypatch, fake_backend, fake_metrics):
    monkeypatch.chdir(tmp_path)
    write_dataset(tmp_path, {"id": "q001", "input": "a", "expected_output": "b"})
    fake_metrics.return_value = [("Correctness", FakeMetric(score=0.9))]

    evals()

    assert list((tmp_path / "tests" / "outputs").glob("evals_results_*.json"))


def test_invalid_dataset_fails_before_any_agent_call(tmp_path, monkeypatch, fake_backend):
    monkeypatch.chdir(tmp_path)
    write_dataset(tmp_path, {"id": "q001", "input": "a"})

    with pytest.raises(SystemExit) as exc_info:
        evals()

    assert exc_info.value.code == 1
    fake_backend.assert_not_called()


def test_rag_only_run_does_not_require_expected_output(tmp_path, monkeypatch, fake_backend, fake_metrics):
    monkeypatch.chdir(tmp_path)
    write_dataset(tmp_path, {"id": "q001", "input": "a"})
    fake_metrics.return_value = [("Faithfulness", FakeMetric(score=0.9))]

    evals(metrics=["rag"])

    fake_backend.return_value.ask.assert_called_once()
