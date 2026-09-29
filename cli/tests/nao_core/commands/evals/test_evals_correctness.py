from deepeval.models import DeepEvalBaseLLM
from deepeval.test_case import SingleTurnParams

from nao_core.commands.evals import correctness
from nao_core.commands.evals.correctness import (
    CORRECTNESS_EVALUATION_STEPS,
    build_correctness_metric,
    correctness_rubric_version,
)


class StubJudge(DeepEvalBaseLLM):
    def load_model(self):
        return None

    def generate(self, prompt: str) -> str:
        return ""

    async def a_generate(self, prompt: str) -> str:
        return ""

    def get_model_name(self) -> str:
        return "stub"


def test_correctness_metric_compares_only_actual_and_expected_output():
    metric = build_correctness_metric(judge=StubJudge(), threshold=0.7)

    assert metric.evaluation_params == [SingleTurnParams.ACTUAL_OUTPUT, SingleTurnParams.EXPECTED_OUTPUT]
    assert metric.evaluation_steps == CORRECTNESS_EVALUATION_STEPS
    assert metric.threshold == 0.7


def test_rubric_version_is_a_stable_short_hash():
    assert correctness_rubric_version() == correctness_rubric_version()
    assert len(correctness_rubric_version()) == 12


def test_rubric_version_changes_with_the_steps(monkeypatch):
    original = correctness_rubric_version()
    monkeypatch.setattr(
        correctness,
        "CORRECTNESS_EVALUATION_STEPS",
        [*CORRECTNESS_EVALUATION_STEPS, "Reward brevity."],
    )

    assert correctness_rubric_version() != original
