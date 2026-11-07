import hashlib
import json
from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class ScoreBand:
    """What a score in this range means, so the judge picks a score against anchors instead of a bare 0–10 scale."""

    low: int
    high: int
    outcome: str


@dataclass(frozen=True)
class GEvalRubric:
    """A nao-owned GEval definition whose steps are explicit, reviewable and versioned."""

    name: str
    evaluation_steps: list[str]
    evaluation_params: list[str]
    score_bands: list[ScoreBand] = field(default_factory=list)
    default_threshold: float = 0.5

    def build_metric(self, judge: Any, threshold: float | None = None) -> Any:
        from deepeval.metrics import GEval
        from deepeval.metrics.g_eval.utils import Rubric
        from deepeval.test_case import SingleTurnParams

        return GEval(
            name=self.name,
            evaluation_steps=self.evaluation_steps,
            evaluation_params=[SingleTurnParams(param) for param in self.evaluation_params],
            rubric=[
                Rubric(score_range=(band.low, band.high), expected_outcome=band.outcome) for band in self.score_bands
            ]
            or None,
            model=judge,
            threshold=self.default_threshold if threshold is None else threshold,
        )

    def version(self) -> str:
        """Short content hash so scores from different rubrics are never compared as equals.

        Score bands are hashed only when present, so a rubric without bands keeps the version it always had.
        """
        rubric: dict[str, Any] = {
            "name": self.name,
            "evaluation_steps": self.evaluation_steps,
            "evaluation_params": self.evaluation_params,
        }
        if self.score_bands:
            rubric["score_bands"] = [[band.low, band.high, band.outcome] for band in self.score_bands]
        digest = hashlib.sha256(json.dumps(rubric, sort_keys=True).encode()).hexdigest()
        return digest[:12]
