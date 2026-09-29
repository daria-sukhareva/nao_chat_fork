import hashlib
import json
from typing import Any

CORRECTNESS_METRIC_NAME = "Correctness"
DEFAULT_CORRECTNESS_THRESHOLD = 0.5

CORRECTNESS_EVALUATION_STEPS = [
    "Compare the actual output directly with the expected output for factual accuracy.",
    "Verify that every required fact, entity, value, and relationship is present and correctly represented.",
    "Verify that the required naming, terminology, and framing are used.",
    "Penalize contradictions, unsupported additions, and misleading details.",
]

CORRECTNESS_EVALUATION_PARAMS = ["actual_output", "expected_output"]


def build_correctness_metric(judge: Any, threshold: float = DEFAULT_CORRECTNESS_THRESHOLD) -> Any:
    """Reference-based GEval: INPUT and retrieval context are intentionally excluded."""
    from deepeval.metrics import GEval
    from deepeval.test_case import SingleTurnParams

    return GEval(
        name=CORRECTNESS_METRIC_NAME,
        evaluation_steps=CORRECTNESS_EVALUATION_STEPS,
        evaluation_params=[SingleTurnParams(param) for param in CORRECTNESS_EVALUATION_PARAMS],
        model=judge,
        threshold=threshold,
    )


def correctness_rubric_version() -> str:
    """Short content hash so scores from different rubrics are never compared as equals."""
    rubric = {
        "name": CORRECTNESS_METRIC_NAME,
        "evaluation_steps": CORRECTNESS_EVALUATION_STEPS,
        "evaluation_params": CORRECTNESS_EVALUATION_PARAMS,
    }
    digest = hashlib.sha256(json.dumps(rubric, sort_keys=True).encode()).hexdigest()
    return digest[:12]
