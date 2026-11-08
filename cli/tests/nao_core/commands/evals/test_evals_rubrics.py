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


def test_correctness_score_bands_cover_the_whole_scale_without_gaps():
    bands = CORRECTNESS_RUBRIC.score_bands

    assert bands[0].low == 0
    assert bands[-1].high == 10
    assert all(later.low == earlier.high + 1 for earlier, later in zip(bands, bands[1:]))


def test_correctness_bands_reach_the_judge_prompt():
    metric = CORRECTNESS_RUBRIC.build_metric(StubJudge())

    assert [rubric.score_range for rubric in metric.rubric] == [(0, 2), (3, 5), (6, 8), (9, 10)]
    assert metric.score_range == (0, 10)


def test_completeness_has_no_bands_and_keeps_its_version():
    metric = COMPLETENESS_RUBRIC.build_metric(StubJudge())

    assert metric.rubric is None
    assert COMPLETENESS_RUBRIC.version() == "c493b2deacb0"


def test_correctness_judges_claims_not_coverage_or_wording():
    steps = " ".join(CORRECTNESS_RUBRIC.evaluation_steps)

    assert "Must not claim" in steps
    assert "Do not penalize omissions" in steps
    assert "Do not penalize wording" in steps
    assert "is present" not in steps
    assert "terminology, and framing are used" not in steps
    assert "unsupported additions" not in steps


def test_rubric_version_changes_with_the_score_bands():
    edited = replace(CORRECTNESS_RUBRIC, score_bands=CORRECTNESS_RUBRIC.score_bands[:-1])

    assert edited.version() != CORRECTNESS_RUBRIC.version()
    assert CORRECTNESS_RUBRIC.version() != "c8b36757a66f"
