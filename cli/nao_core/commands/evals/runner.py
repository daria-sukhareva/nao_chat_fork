import json
import os
import sys
from dataclasses import asdict, dataclass
from datetime import datetime
from pathlib import Path
from typing import Annotated, Any

import httpx
from cyclopts import Parameter

from nao_core.auth import get_auth_session
from nao_core.commands.test.runner import ModelConfig
from nao_core.ui import UI

BACKEND_URL = os.getenv("NAO_EVAL_URL", os.getenv("BACKEND_URL", "http://localhost:5005"))
EVALS_FOLDER = "tests/evals"

os.environ.setdefault("DEEPEVAL_TELEMETRY_OPT_OUT", "YES")

FAITHFULNESS_THRESHOLD = 0.7
CONTEXT_RELEVANCY_THRESHOLD = 0.5  # chat agents fetch broad schema context by design, not just query-scoped chunks
ANSWER_RELEVANCY_THRESHOLD = 0.7


@dataclass
class MetricResult:
    name: str
    score: float | None
    threshold: float
    passed: bool
    reason: str | None


@dataclass
class EvalResult:
    id: str
    input: str
    actual_output: str
    passed: bool
    metrics: list[MetricResult]


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


def make_judge(model_id: str) -> "Any":
    from deepeval.models import DeepEvalBaseLLM

    if model_id.startswith("claude"):
        import anthropic

        class _ClaudeJudge(DeepEvalBaseLLM):
            def load_model(self):
                return anthropic.Anthropic()

            def generate(self, prompt: str) -> str:
                client = self.load_model()
                resp = client.messages.create(
                    model=model_id,
                    max_tokens=4096,
                    messages=[{"role": "user", "content": prompt}],
                )
                return resp.content[0].text

            async def a_generate(self, prompt: str) -> str:
                return self.generate(prompt)

            def get_model_name(self) -> str:
                return model_id

        return _ClaudeJudge()
    return model_id


def run_eval(
    record: dict, client: httpx.Client, model: str | None, judge_model: str | None = None, verbose: bool = False
) -> EvalResult:
    from deepeval.metrics import AnswerRelevancyMetric, ContextualRelevancyMetric, FaithfulnessMetric
    from deepeval.test_case import LLMTestCase

    UI.print(f"[bold]Running:[/bold] {record['id']} [dim]{record['input'][:80]}[/dim]")

    payload: dict = {"input": record["input"]}
    if model:
        provider, _, model_id = model.partition(":")
        payload["model"] = {"provider": provider, "modelId": model_id}

    resp = client.post("/api/evals/chat", json=payload)
    resp.raise_for_status()
    data = resp.json()

    tool_results = data.get("tool_results", [])
    retrieval_context = [
        serialize_tool_result(tr["toolName"], tr.get("args", {}), tr.get("output")) for tr in tool_results
    ]

    test_case = LLMTestCase(
        input=record["input"],
        actual_output=data["text"],
        retrieval_context=retrieval_context or None,  # type: ignore[arg-type]
    )

    judge = make_judge(judge_model or data["model_id"])
    metric_specs = [
        ("Faithfulness", FaithfulnessMetric, FAITHFULNESS_THRESHOLD),
        ("ContextualRelevancy", ContextualRelevancyMetric, CONTEXT_RELEVANCY_THRESHOLD),
        ("AnswerRelevancy", AnswerRelevancyMetric, ANSWER_RELEVANCY_THRESHOLD),
    ]

    metric_results = []
    for name, metric_class, threshold in metric_specs:
        metric = metric_class(threshold=threshold, model=judge, include_reason=True)
        metric.measure(test_case)
        score = round(metric.score, 4) if metric.score is not None else None
        passed = score is not None and score >= threshold
        metric_results.append(
            MetricResult(
                name=name,
                score=score,
                threshold=threshold,
                passed=passed,
                reason=getattr(metric, "reason", None),
            )
        )
        status = "[green]✓[/green]" if passed else "[red]✗[/red]"
        UI.print(f"  {status} {metric_results[-1].name}: {score}")
        if verbose and metric_results[-1].reason:
            UI.print(f"    [dim]{metric_results[-1].reason}[/dim]")

    return EvalResult(
        id=record["id"],
        input=record["input"],
        actual_output=data["text"],
        passed=all(r.passed for r in metric_results),
        metrics=metric_results,
    )


def save_results(results: list[EvalResult], output_dir: Path) -> Path:
    output_dir.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_file = output_dir / f"evals_{timestamp}.json"

    passed = sum(1 for r in results if r.passed)
    data = {
        "timestamp": datetime.now().isoformat(),
        "results": [asdict(r) for r in results],
        "summary": {
            "total": len(results),
            "passed": passed,
            "failed": len(results) - passed,
        },
    }
    output_file.write_text(json.dumps(data, indent=2))
    return output_file


def evals(
    model: Annotated[
        str | None,
        Parameter(
            name=["-m", "--model"],
            help="Model to use for the agent (format: provider:model_id). Defaults to project setting.",
        ),
    ] = None,
    username: Annotated[
        str | None,
        Parameter(
            name=["-u", "--username"],
            help="Email for authentication. Falls back to NAO_USERNAME env var.",
        ),
    ] = None,
    password: Annotated[
        str | None,
        Parameter(
            name=["--password"],
            help="Password for authentication. Falls back to NAO_PASSWORD env var.",
        ),
    ] = None,
    select: Annotated[
        str | None,
        Parameter(
            name=["-s", "--select"],
            help="Run only the eval with this ID.",
        ),
    ] = None,
    judge_model: Annotated[
        str | None,
        Parameter(
            name=["-j", "--judge-model"],
            help="Model to use as the eval judge (format: provider:model_id). Defaults to the agent model.",
        ),
    ] = None,
    verbose: Annotated[
        bool,
        Parameter(name=["-v", "--verbose"], help="Print metric reasons alongside scores."),
    ] = False,
):
    """Run LLM-as-judge RAG triad evals.

    Examples:
        nao evals
        nao evals -m anthropic:claude-sonnet-4-6
        nao evals -j openai:gpt-4.1
        nao evals -u user@example.com --password secret
        nao evals -s q001
        nao evals -v
    """
    email = username or os.environ.get("NAO_USERNAME")
    pwd = password or os.environ.get("NAO_PASSWORD")
    backend_url = BACKEND_URL

    for flag, value in [("--model", model), ("--judge-model", judge_model)]:
        if value:
            try:
                ModelConfig.parse(value)
            except ValueError as e:
                UI.error(f"{flag}: {e}")
                return

    project_path = Path.cwd()
    evals_dir = project_path / EVALS_FOLDER
    dataset_path = evals_dir / "golden_dataset.jsonl"

    if not dataset_path.exists():
        UI.warn(f"No golden dataset found: {dataset_path}")
        return

    records = [json.loads(line) for line in dataset_path.read_text().splitlines() if line.strip()]
    if select:
        records = [r for r in records if r["id"] == select]
        if not records:
            UI.error(f"No record found with id: {select}")
            return

    UI.info(f"\n🧪 Running nao evals ({len(records)} record(s))...\n")
    if model:
        UI.print(f"[dim]Model: {model}[/dim]")
    if judge_model:
        UI.print(f"[dim]Judge: {judge_model}[/dim]")

    session = get_auth_session(backend_url, email=email, password=pwd)
    cookie_str = "; ".join(f"{k}={v}" for k, v in session.cookies.items())
    if not cookie_str:
        UI.error("Authentication failed — no session cookie obtained.")
        return

    headers = {"Cookie": cookie_str}
    results: list[EvalResult] = []

    with httpx.Client(base_url=backend_url, headers=headers, timeout=300.0) as client:
        for record in records:
            result = run_eval(record, client, model, judge_model=judge_model, verbose=verbose)
            results.append(result)
            UI.print("")

    output_file = save_results(results, project_path / "tests" / "outputs")
    UI.print(f"[dim]Results saved to: {output_file}[/dim]\n")

    passed = sum(1 for r in results if r.passed)
    failed = len(results) - passed
    total = len(results)

    if failed == 0:
        UI.success(f"All {total} eval(s) passed")
    else:
        UI.print(f"[green]{passed} passed[/green], [red]{failed} failed[/red], {total} total")
        sys.exit(1)
