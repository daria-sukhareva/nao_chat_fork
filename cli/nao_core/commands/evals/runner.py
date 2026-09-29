import json
import os
import sys
from dataclasses import asdict, dataclass, field
from datetime import datetime
from importlib.metadata import PackageNotFoundError, version
from pathlib import Path
from typing import Annotated, Any, Literal

import httpx
from cyclopts import Parameter

from nao_core.auth import get_auth_session
from nao_core.commands.test.runner import ModelConfig
from nao_core.ui import UI

from .case import DatasetValidationError, EvalCase, dataset_path_for, load_cases, select_cases
from .client import DEFAULT_TIMEOUT_SECONDS, AgentAnswer, AgentBackendError, AgentTimeoutError, EvalsClient
from .correctness import (
    CORRECTNESS_METRIC_NAME,
    DEFAULT_CORRECTNESS_THRESHOLD,
    build_correctness_metric,
    correctness_rubric_version,
)
from .judge import resolve_judge
from .rag import build_rag_metrics, build_retrieval_context

BACKEND_URL = os.getenv("NAO_EVAL_URL", os.getenv("BACKEND_URL", "http://localhost:5005"))
OUTPUTS_FOLDER = "tests/outputs"

os.environ.setdefault("DEEPEVAL_TELEMETRY_OPT_OUT", "YES")

MetricSuite = Literal["rag", "correctness"]
ALL_SUITES: list[MetricSuite] = ["rag", "correctness"]

ErrorType = Literal["timeout", "backend_error", "metric_error"]


@dataclass
class MetricResult:
    name: str
    score: float | None
    threshold: float
    passed: bool
    reason: str | None
    error: str | None = None


@dataclass
class EvalResult:
    id: str
    input: str
    expected_output: str | None
    actual_output: str | None = None
    agent_model: str | None = None
    judge_model: str | None = None
    passed: bool = False
    metrics: list[MetricResult] = field(default_factory=list)
    usage: dict[str, Any] | None = None
    cost: dict[str, Any] | None = None
    duration_ms: int | None = None
    error_type: ErrorType | None = None
    error: str | None = None


@dataclass
class EvalOptions:
    suites: list[MetricSuite]
    model: ModelConfig | None
    judge_model: str | None
    correctness_threshold: float
    verbose: bool


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
    metrics: Annotated[
        list[MetricSuite] | None,
        Parameter(
            name=["--metrics"],
            help="Metric suites to run: rag (Faithfulness, ContextualRelevancy, AnswerRelevancy) "
            "and/or correctness (reference-based GEval). Defaults to both.",
        ),
    ] = None,
    threshold: Annotated[
        float,
        Parameter(name=["--threshold"], help="Minimum Correctness score required to pass."),
    ] = DEFAULT_CORRECTNESS_THRESHOLD,
    timeout: Annotated[
        float,
        Parameter(name=["--timeout"], help="Maximum seconds to wait for each agent answer."),
    ] = DEFAULT_TIMEOUT_SECONDS,
    verbose: Annotated[
        bool,
        Parameter(name=["-v", "--verbose"], help="Print metric reasons alongside scores."),
    ] = False,
):
    """Run LLM-as-judge evals: the RAG triad and reference-based Correctness.

    Examples:
        nao evals
        nao evals -m anthropic:claude-sonnet-4-6 -j anthropic:claude-sonnet-4-6
        nao evals --metrics correctness --threshold 0.7
        nao evals --metrics rag
        nao evals -s q001 --timeout 120
        nao evals -u user@example.com --password secret
        nao evals -v
    """
    suites = metrics or ALL_SUITES
    agent_model = _parse_model_option("--model", model)
    if model and agent_model is None:
        return
    if judge_model and _parse_model_option("--judge-model", judge_model) is None:
        return

    project_path = Path.cwd()
    cases = _load_selected_cases(project_path, select, require_expected_output="correctness" in suites)
    if not cases:
        return

    options = EvalOptions(
        suites=suites,
        model=agent_model,
        judge_model=judge_model,
        correctness_threshold=threshold,
        verbose=verbose,
    )
    _print_run_header(cases, options)

    http_client = _build_authenticated_client(
        username or os.environ.get("NAO_USERNAME"),
        password or os.environ.get("NAO_PASSWORD"),
    )
    if http_client is None:
        return

    with http_client:
        client = EvalsClient(http_client, timeout=timeout)
        results = [run_case(case, client, options) for case in cases]

    output_file = save_results(results, options, project_path / OUTPUTS_FOLDER)
    UI.print(f"[dim]Results saved to: {output_file}[/dim]\n")

    _print_summary(results)
    if any(not result.passed for result in results):
        sys.exit(1)


def run_case(case: EvalCase, client: EvalsClient, options: EvalOptions) -> EvalResult:
    UI.print(f"[bold]Running:[/bold] {case.id} [dim]{case.input[:80]}[/dim]")
    result = EvalResult(id=case.id, input=case.input, expected_output=case.expected_output)

    try:
        answer = client.ask(case.input, options.model)
    except AgentTimeoutError as e:
        return _fail_with_error(result, "timeout", str(e))
    except AgentBackendError as e:
        return _fail_with_error(result, "backend_error", str(e))

    _record_answer(result, answer)
    result.judge_model = options.judge_model or answer.model

    try:
        judge = resolve_judge(result.judge_model)
        named_metrics = _build_metrics(judge, options)
    except Exception as e:
        return _fail_with_error(result, "metric_error", f"Could not build judge metrics: {e}")

    test_case = _build_test_case(case, answer)
    result.metrics = [measure_metric(name, metric, test_case, options.verbose) for name, metric in named_metrics]

    if any(metric.error for metric in result.metrics):
        result.error_type = "metric_error"
    result.passed = result.error_type is None and all(metric.passed for metric in result.metrics)
    UI.print("")
    return result


def measure_metric(name: str, metric: Any, test_case: Any, verbose: bool = False) -> MetricResult:
    threshold = metric.threshold
    try:
        metric.measure(test_case)
    except Exception as e:
        UI.print(f"  [red]![/red] {name}: [red]error[/red] [dim]{e}[/dim]")
        return MetricResult(name=name, score=None, threshold=threshold, passed=False, reason=None, error=str(e))

    score = round(metric.score, 4) if metric.score is not None else None
    passed = score is not None and score >= threshold
    reason = getattr(metric, "reason", None)

    status = "[green]✓[/green]" if passed else "[red]✗[/red]"
    UI.print(f"  {status} {name}: {score}")
    if verbose and reason:
        UI.print(f"    [dim]{reason}[/dim]")

    return MetricResult(name=name, score=score, threshold=threshold, passed=passed, reason=reason)


def save_results(results: list[EvalResult], options: EvalOptions, output_dir: Path) -> Path:
    output_dir.mkdir(parents=True, exist_ok=True)
    now = datetime.now()
    output_file = output_dir / f"evals_results_{now.strftime('%Y%m%d_%H%M%S')}.json"

    data = {
        "timestamp": now.isoformat(),
        "config": _describe_config(options),
        "results": [asdict(result) for result in results],
        "summary": _summarize(results),
    }
    output_file.write_text(json.dumps(data, indent=2))
    return output_file


def _parse_model_option(flag: str, value: str | None) -> ModelConfig | None:
    if not value:
        return None
    try:
        return ModelConfig.parse(value)
    except ValueError as e:
        UI.error(f"{flag}: {e}")
        return None


def _load_selected_cases(project_path: Path, select: str | None, require_expected_output: bool) -> list[EvalCase]:
    dataset_path = dataset_path_for(project_path)
    if not dataset_path.exists():
        UI.warn(f"No golden dataset found: {dataset_path}")
        return []

    try:
        cases = load_cases(dataset_path, require_expected_output=require_expected_output)
    except DatasetValidationError as e:
        UI.error(f"Invalid golden dataset ({len(e.errors)} error(s)):")
        for error in e.errors:
            UI.print(f"  [red]•[/red] {error}")
        sys.exit(1)

    selected = select_cases(cases, select)
    if not selected:
        UI.error(f"No record found with id: {select}")
    return selected


def _build_authenticated_client(email: str | None, password: str | None) -> httpx.Client | None:
    session = get_auth_session(BACKEND_URL, email=email, password=password)
    cookie_header = "; ".join(f"{name}={value}" for name, value in session.cookies.items())
    if not cookie_header:
        UI.error("Authentication failed — no session cookie obtained.")
        return None
    return httpx.Client(base_url=BACKEND_URL, headers={"Cookie": cookie_header})


def _build_metrics(judge: Any, options: EvalOptions) -> list[tuple[str, Any]]:
    named_metrics: list[tuple[str, Any]] = []
    if "rag" in options.suites:
        named_metrics.extend(build_rag_metrics(judge))
    if "correctness" in options.suites:
        named_metrics.append((CORRECTNESS_METRIC_NAME, build_correctness_metric(judge, options.correctness_threshold)))
    return named_metrics


def _build_test_case(case: EvalCase, answer: AgentAnswer) -> Any:
    from deepeval.test_case import LLMTestCase

    retrieval_context = build_retrieval_context(answer.tool_results)
    return LLMTestCase(
        input=case.input,
        actual_output=answer.text,
        expected_output=case.expected_output,
        retrieval_context=retrieval_context or None,  # type: ignore[arg-type]
    )


def _record_answer(result: EvalResult, answer: AgentAnswer) -> None:
    result.actual_output = answer.text
    result.agent_model = answer.model
    result.usage = answer.usage
    result.cost = answer.cost
    result.duration_ms = answer.duration_ms


def _fail_with_error(result: EvalResult, error_type: ErrorType, message: str) -> EvalResult:
    UI.print(f"  [red]![/red] {error_type}: [dim]{message}[/dim]\n")
    result.error_type = error_type
    result.error = message
    result.passed = False
    return result


def _describe_config(options: EvalOptions) -> dict[str, Any]:
    config: dict[str, Any] = {
        "metrics": options.suites,
        "model": str(options.model) if options.model else None,
        "judge_model": options.judge_model,
        "deepeval_version": _deepeval_version(),
    }
    if "correctness" in options.suites:
        config["correctness"] = {
            "threshold": options.correctness_threshold,
            "rubric_version": correctness_rubric_version(),
        }
    return config


def _deepeval_version() -> str | None:
    try:
        return version("deepeval")
    except PackageNotFoundError:
        return None


def _summarize(results: list[EvalResult]) -> dict[str, int]:
    errored = sum(1 for result in results if result.error_type)
    passed = sum(1 for result in results if result.passed)
    return {
        "total": len(results),
        "passed": passed,
        "failed": len(results) - passed - errored,
        "errored": errored,
    }


def _print_run_header(cases: list[EvalCase], options: EvalOptions) -> None:
    UI.info(f"\n🧪 Running nao evals ({len(cases)} record(s))...\n")
    UI.print(f"[dim]Metrics: {', '.join(options.suites)}[/dim]")
    if options.model:
        UI.print(f"[dim]Model: {options.model}[/dim]")
    if options.judge_model:
        UI.print(f"[dim]Judge: {options.judge_model}[/dim]")
    UI.print("")


def _print_summary(results: list[EvalResult]) -> None:
    summary = _summarize(results)
    if summary["passed"] == summary["total"]:
        UI.success(f"All {summary['total']} eval(s) passed")
        return
    UI.print(
        f"[green]{summary['passed']} passed[/green], [red]{summary['failed']} failed[/red], "
        f"[yellow]{summary['errored']} errored[/yellow], {summary['total']} total"
    )
