import json
import re
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from nao_core.commands.evals.client import AgentAnswer
from nao_core.commands.evals.cost import (
    JUDGE_PRICES,
    CostLimit,
    JudgeCost,
    Spend,
    TokenUsage,
    append_ledger,
    judge_cost,
    price_tokens,
    read_ledger,
    snapshot_usage,
    sum_judge_costs,
)
from nao_core.commands.evals.cost_report import summarize_ledger
from nao_core.commands.evals.rejudge import rejudge
from nao_core.commands.evals.runner import evals

PROVIDER_META = Path(__file__).parents[5] / "apps" / "backend" / "src" / "agents" / "provider-meta.ts"


class FakeJudge:
    def __init__(self, model_id: str = "claude-sonnet-4-6"):
        self.usage = TokenUsage()
        self._model_id = model_id

    def get_model_name(self) -> str:
        return self._model_id


class SpendingMetric:
    """Spends 1M input and 100k output tokens per measure: $3 + $1.50 at Sonnet 4.6 prices."""

    def __init__(self, judge: FakeJudge, score: float = 0.9):
        self.judge = judge
        self.threshold = 0.5
        self.score = score
        self.reason = "because"

    def measure(self, test_case):
        self.judge.usage.add(1_000_000, 100_000)


def test_judge_prices_match_the_backend_price_table():
    source = PROVIDER_META.read_text()
    for model_id, price in JUDGE_PRICES.items():
        entry = re.search(rf"id: '{re.escape(model_id)}',.*?costPerM: \{{([^}}]*)\}}", source, re.S)
        assert entry, f"{model_id} not found in provider-meta.ts"
        fields = dict(re.findall(r"(\w+): ([\d.]+)", entry.group(1)))
        assert float(fields["inputNoCache"]) == price.input_per_million
        assert float(fields["output"]) == price.output_per_million


def test_tokens_are_priced_per_million_and_unknown_models_are_unpriced():
    usage = TokenUsage(calls=2, input_tokens=2_000_000, output_tokens=100_000)

    assert price_tokens("claude-sonnet-4-6", usage) == 7.5
    assert price_tokens("some-unpriced-model", usage) is None


def test_judge_cost_counts_only_the_tokens_spent_by_this_metric():
    judge = FakeJudge()
    judge.usage.add(5_000_000, 0)
    before = snapshot_usage(judge)
    SpendingMetric(judge).measure(None)

    cost = judge_cost(judge, metric=None, usage_before=before)

    assert cost == JudgeCost(calls=1, input_tokens=1_000_000, output_tokens=100_000, cost_usd=4.5)


def test_judge_cost_falls_back_to_deepeval_evaluation_cost_and_otherwise_is_unknown():
    native_metric = MagicMock(evaluation_cost=0.25)

    assert judge_cost("gpt-4.1", native_metric, None) == JudgeCost(cost_usd=0.25)
    assert judge_cost("gpt-4.1", MagicMock(evaluation_cost=None), None) is None


def test_a_missing_metric_cost_makes_the_sum_unknown():
    total = sum_judge_costs([JudgeCost(calls=1, input_tokens=10, output_tokens=1, cost_usd=0.5), None])

    assert total.cost_usd is None
    assert total.calls == 1


def test_limit_stops_at_the_maximum_or_when_judge_cost_is_unknown():
    spend = Spend(agent_usd=1.0, judge_usd=0.9)

    assert CostLimit(None).should_stop(spend) is False
    assert CostLimit(2.0).should_stop(spend) is False
    limit = CostLimit(1.5)
    assert limit.should_stop(spend) is True
    assert limit.stopped is not None
    assert limit.stopped["reason"] == "max_cost"

    unknown = CostLimit(100.0)
    assert unknown.should_stop(Spend(judge_cost_unknown=1)) is True
    assert unknown.stopped is not None
    assert unknown.stopped["reason"] == "cost_unknown"


def test_unknown_agent_cost_is_counted_but_does_not_stop_the_run():
    spend = Spend()
    spend.add_agent(None)
    spend.add_agent({"totalCost": 0.25})

    assert spend.agent_cost_unknown == 1
    assert spend.agent_usd == 0.25
    assert CostLimit(10.0).should_stop(spend) is False


def test_ledger_appends_one_line_per_run_and_sums_per_experiment(tmp_path):
    append_ledger(tmp_path, {"experiment_id": "exp-1", "agent_usd": 1.0, "judge_usd": 0.5, "total_usd": 1.5})
    append_ledger(tmp_path, {"experiment_id": "exp-1", "agent_usd": 0.0, "judge_usd": 0.25, "total_usd": 0.25})
    append_ledger(tmp_path, {"experiment_id": None, "agent_usd": 2.0, "judge_usd": 0.0, "total_usd": 2.0})

    entries = read_ledger(tmp_path)
    totals = summarize_ledger(entries)

    assert len(entries) == 3
    assert all("timestamp" in entry for entry in entries)
    assert totals["exp-1"]["total_usd"] == 1.75
    assert totals["exp-1"]["runs"] == 2
    assert totals["(no experiment)"]["agent_usd"] == 2.0


def write_dataset(tmp_path, count: int = 3):
    dataset = tmp_path / "tests" / "evals" / "golden_dataset.jsonl"
    dataset.parent.mkdir(parents=True)
    rows = [{"id": f"q00{index}", "input": "a", "expected_output": "b"} for index in range(1, count + 1)]
    dataset.write_text("\n".join(json.dumps(row) for row in rows))


@pytest.fixture
def spending_backend():
    judge = FakeJudge()
    answer = AgentAnswer(text="answer", model="anthropic:claude-sonnet-4-6", cost={"totalCost": 1.0})
    client = MagicMock()
    client.ask.return_value = answer
    client.describe_environment.return_value = None
    with (
        patch("nao_core.commands.evals.runner._build_authenticated_client", return_value=MagicMock()),
        patch("nao_core.commands.evals.runner.EvalsClient", return_value=client),
        patch("nao_core.commands.evals.runner.resolve_judge", return_value=judge),
        patch(
            "nao_core.commands.evals.runner._build_metrics",
            side_effect=lambda judge, options: [("Correctness", SpendingMetric(judge))],
        ),
    ):
        yield client


def test_evals_records_agent_and_judge_cost_per_record_and_per_run(tmp_path, monkeypatch, spending_backend):
    monkeypatch.chdir(tmp_path)
    write_dataset(tmp_path, count=1)

    evals(metrics=["correctness"])

    data = json.loads(next((tmp_path / "tests" / "outputs").glob("evals_results_*.json")).read_text())
    record = data["results"][0]
    assert record["metrics"][0]["judge_cost"]["cost_usd"] == 4.5
    assert record["judge_cost"]["calls"] == 1
    assert data["run"]["cost"]["agent_usd"] == 1.0
    assert data["run"]["cost"]["judge_usd"] == 4.5
    assert data["run"]["cost"]["total_usd"] == 5.5
    assert data["run"]["stopped"] is None
    [entry] = read_ledger(tmp_path / "tests" / "outputs")
    assert entry["command"] == "evals"
    assert entry["total_usd"] == 5.5
    assert entry["trials_run"] == entry["trials_planned"] == 1


def test_max_cost_stops_before_the_next_trial_and_saves_what_finished(tmp_path, monkeypatch, spending_backend):
    monkeypatch.chdir(tmp_path)
    write_dataset(tmp_path, count=3)

    with pytest.raises(SystemExit) as exc_info:
        evals(metrics=["correctness"], max_cost=10.0)

    assert exc_info.value.code == 1
    assert spending_backend.ask.call_count == 2
    data = json.loads(next((tmp_path / "tests" / "outputs").glob("evals_results_*.json")).read_text())
    assert len(data["results"]) == 2
    assert data["run"]["stopped"]["reason"] == "max_cost"
    assert data["run"]["trials_run"] == 2
    [entry] = read_ledger(tmp_path / "tests" / "outputs")
    assert entry["trials_planned"] == 3
    assert entry["stopped"]["reason"] == "max_cost"


def test_an_interrupted_run_still_saves_and_records_its_cost(tmp_path, monkeypatch, spending_backend):
    monkeypatch.chdir(tmp_path)
    write_dataset(tmp_path, count=3)
    answer = spending_backend.ask.return_value
    spending_backend.ask.side_effect = [answer, KeyboardInterrupt()]

    with pytest.raises(SystemExit):
        evals(metrics=["correctness"])

    [entry] = read_ledger(tmp_path / "tests" / "outputs")
    assert entry["stopped"]["reason"] == "interrupted"
    assert entry["trials_run"] == 1


def test_rejudge_records_judge_cost_in_the_shared_ledger_and_honours_max_cost(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    outputs = tmp_path / "tests" / "outputs" / "synthetic"
    outputs.mkdir(parents=True)
    record = {"id": "q018", "input": "?", "expected_output": "b", "actual_output": "a", "answer_id": "a-1"}
    results_file = outputs / "evals_results_x.json"
    results_file.write_text(
        json.dumps(
            {
                "run": {"run_id": "run-1", "experiment_id": "exp-1"},
                "config": {"metrics": ["correctness"]},
                "results": [record],
            }
        )
    )
    judge = FakeJudge()

    with (
        patch("nao_core.commands.evals.rejudge.resolve_judge", return_value=judge),
        patch(
            "nao_core.commands.evals.rejudge._build_metrics",
            side_effect=lambda judge, options: [("Correctness", SpendingMetric(judge))],
        ),
        pytest.raises(SystemExit),
    ):
        rejudge(results_file, judge_repeats=3, max_cost=5.0)

    [entry] = read_ledger(tmp_path / "tests" / "outputs")
    assert entry["command"] == "rejudge"
    assert entry["experiment_id"] == "exp-1"
    assert entry["trials_run"] == 2
    assert entry["judge_usd"] == 9.0
    assert entry["stopped"]["reason"] == "max_cost"
    saved = json.loads(next(outputs.glob("rejudge_results_*.json")).read_text())
    assert saved["judgments"][0]["judge_cost"]["cost_usd"] == 4.5
