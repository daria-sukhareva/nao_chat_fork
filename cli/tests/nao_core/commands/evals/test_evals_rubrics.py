from dataclasses import replace

import pytest
from deepeval.models import DeepEvalBaseLLM
from deepeval.test_case import SingleTurnParams

from nao_core.commands.evals.completeness import COMPLETENESS_RUBRIC
from nao_core.commands.evals.correctness import CORRECTNESS_RUBRIC


class StubJudge(DeepEvalBaseLLM):
    def load_model(self):
        return None

    def generate(self, prompt: str) -> str:
        return ""

    async def a_generate(self, prompt: str) -> str:
        return ""

    def get_model_name(self) -> str:
        return "stub"


def test_correctness_compares_only_actual_and_expected_output():
    metric = CORRECTNESS_RUBRIC.build_metric(StubJudge(), threshold=0.7)

    assert metric.evaluation_params == [SingleTurnParams.ACTUAL_OUTPUT, SingleTurnParams.EXPECTED_OUTPUT]
    assert metric.evaluation_steps == CORRECTNESS_RUBRIC.evaluation_steps
    assert metric.threshold == 0.7


def test_completeness_also_sees_the_question():
    metric = COMPLETENESS_RUBRIC.build_metric(StubJudge())

    assert metric.evaluation_params == [
        SingleTurnParams.INPUT,
        SingleTurnParams.ACTUAL_OUTPUT,
        SingleTurnParams.EXPECTED_OUTPUT,
    ]
    assert metric.threshold == COMPLETENESS_RUBRIC.default_threshold


@pytest.mark.parametrize("rubric", [CORRECTNESS_RUBRIC, COMPLETENESS_RUBRIC])
def test_rubric_version_is_a_stable_short_hash(rubric):
    assert rubric.version() == rubric.version()
    assert len(rubric.version()) == 12


def test_rubric_version_changes_with_the_steps():
    edited = replace(CORRECTNESS_RUBRIC, evaluation_steps=[*CORRECTNESS_RUBRIC.evaluation_steps, "Reward brevity."])

    assert edited.version() != CORRECTNESS_RUBRIC.version()
    assert COMPLETENESS_RUBRIC.version() != CORRECTNESS_RUBRIC.version()
