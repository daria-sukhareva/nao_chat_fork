from typing import Any

FAITHFULNESS_THRESHOLD = 0.7
CONTEXT_RELEVANCY_THRESHOLD = 0.5  # chat agents fetch broad schema context by design, not just query-scoped chunks
ANSWER_RELEVANCY_THRESHOLD = 0.7


RAG_THRESHOLDS = {
    "Faithfulness": FAITHFULNESS_THRESHOLD,
    "ContextualRelevancy": CONTEXT_RELEVANCY_THRESHOLD,
    "AnswerRelevancy": ANSWER_RELEVANCY_THRESHOLD,
}


def describe_rag_metrics() -> dict[str, dict[str, Any]]:
    return {
        name: {"deepeval_class": f"{name}Metric", "threshold": threshold} for name, threshold in RAG_THRESHOLDS.items()
    }


def build_rag_metrics(judge: Any) -> list[tuple[str, Any]]:
    from deepeval.metrics import AnswerRelevancyMetric, ContextualRelevancyMetric, FaithfulnessMetric

    return [
        ("Faithfulness", FaithfulnessMetric(threshold=FAITHFULNESS_THRESHOLD, model=judge, include_reason=True)),
        (
            "ContextualRelevancy",
            ContextualRelevancyMetric(threshold=CONTEXT_RELEVANCY_THRESHOLD, model=judge, include_reason=True),
        ),
        (
            "AnswerRelevancy",
            AnswerRelevancyMetric(threshold=ANSWER_RELEVANCY_THRESHOLD, model=judge, include_reason=True),
        ),
    ]
