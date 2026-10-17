import hashlib
import json
from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class GEvalRubric:
    """A nao-owned GEval definition whose steps are explicit, reviewable and versioned."""

    name: str
    evaluation_steps: list[str]
    evaluation_params: list[str]
    default_threshold: float = 0.5

    def build_metric(self, judge: Any, threshold: float | None = None) -> Any:
        from deepeval.metrics import GEval
        from deepeval.test_case import SingleTurnParams

        return GEval(
            name=self.name,
            evaluation_steps=self.evaluation_steps,
            evaluation_params=[SingleTurnParams(param) for param in self.evaluation_params],
            model=judge,
            threshold=self.default_threshold if threshold is None else threshold,
        )

    def version(self) -> str:
        """Short content hash so scores from different rubrics are never compared as equals."""
        rubric = {
            "name": self.name,
            "evaluation_steps": self.evaluation_steps,
            "evaluation_params": self.evaluation_params,
        }
        digest = hashlib.sha256(json.dumps(rubric, sort_keys=True).encode()).hexdigest()
        return digest[:12]
