import json
from typing import Any

FAITHFULNESS_THRESHOLD = 0.7
CONTEXT_RELEVANCY_THRESHOLD = 0.5  # chat agents fetch broad schema context by design, not just query-scoped chunks
ANSWER_RELEVANCY_THRESHOLD = 0.7


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


def build_retrieval_context(tool_results: list[dict]) -> list[str]:
    return [
        serialize_tool_result(result["toolName"], result.get("args", {}), result.get("output"))
        for result in tool_results
    ]


def serialize_tool_result(tool_name: str, args: dict, output: Any) -> str:
    if tool_name == "read":
        path = args.get("file_path", "unknown")
        content = output.get("content", "") if isinstance(output, dict) else str(output)
        return f"[File: {path}]\n{content}"
    if tool_name == "execute_sql":
        cols = output.get("columns", []) if isinstance(output, dict) else []
        rows = output.get("data", []) if isinstance(output, dict) else []
        header = " | ".join(str(c) for c in cols)
        body = "\n".join(" | ".join(str(r.get(c, "")) for c in cols) for r in rows[:20])
        return f"[SQL result]\nColumns: {', '.join(cols)}\n{header}\n{body}"
    return f"[{tool_name}]\n{json.dumps(output, indent=2)}"
