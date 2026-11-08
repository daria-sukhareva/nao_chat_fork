import json
import os
import sys
import uuid
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from importlib.metadata import PackageNotFoundError, version
from pathlib import Path
from typing import Annotated, Any, Literal

import httpx
from cyclopts import Parameter

from nao_core.auth import get_auth_session
from nao_core.commands.test.runner import ModelConfig
from nao_core.ui import UI

from .arm import ArmManifest, ArmManifestError, find_arm_mismatches, load_arm_manifest
from .case import DatasetValidationError, EvalCase, dataset_path_for, load_cases, select_cases
from .client import DEFAULT_TIMEOUT_SECONDS, AgentAnswer, AgentBackendError, AgentTimeoutError, EvalsClient
from .completeness import COMPLETENESS_RUBRIC
from .correctness import CORRECTNESS_RUBRIC
from .cost import CostLimit, JudgeCost, Spend, append_ledger, judge_cost, snapshot_usage, sum_judge_costs
from .judge import describe_judge_settings, resolve_judge
from .provenance import changed_environment_parts, fingerprint_dataset, package_versions
from .rag import build_rag_metrics, describe_rag_metrics
from .rubric import GEvalRubric
from .run_context import RunContext, describe_run_context, save_run_context_files
from .schedule import RunLabels, Trial, new_run_labels, schedule_trials
from .tool_calls import build_retrieval_context, list_files_read

BACKEND_URL = os.getenv("NAO_EVAL_URL", os.getenv("BACKEND_URL", "http://localhost:5005"))
OUTPUTS_FOLDER = "tests/outputs"

os.environ.setdefault("DEEPEVAL_TELEMETRY_OPT_OUT", "YES")

MetricSuite = Literal["rag", "correctness", "completeness"]
ReferenceSuite = Literal["correctness", "completeness"]
ALL_SUITES: list[MetricSuite] = ["rag", "correctness", "completeness"]
REFERENCE_RUBRICS: dict[ReferenceSuite, GEvalRubric] = {
    "correctness": CORRECTNESS_RUBRIC,
    "completeness": COMPLETENESS_RUBRIC,
}

ErrorType = Literal["timeout", "backend_error", "context_error", "metric_error"]


@dataclass
class MetricResult:
    name: str
    score: float | None
    threshold: float
    passed: bool
    reason: str | None
    error: str | None = None
    judge_cost: JudgeCost | None = None


@dataclass
class EvalResult:
    id: str
    input: str
    expected_output: str | None
    run_id: str | None = None
    experiment_id: str | None = None
    arm: str | None = None
    block: int | None = None
    repetition: int = 1
    position: int = 0
    answer_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    started_at: str | None = None
    actual_output: str | None = None
    retrieval_context: list[str] = field(default_factory=list)
    context_read: list[str] = field(default_factory=list)
    tool_calls: list[dict] = field(default_factory=list)
    run_context: RunContext = field(default_factory=RunContext)
    raw_run_context: dict[str, Any] = field(default_factory=dict)
    agent_model: str | None = None
    judge_model: str | None = None
    judge_settings: dict[str, Any] = field(default_factory=dict)
    passed: bool = False
    metrics: list[MetricResult] = field(default_factory=list)
    usage: dict[str, Any] | None = None
    cost: dict[str, Any] | None = None
    judge_cost: JudgeCost | None = None
    duration_ms: int | None = None
    error_type: ErrorType | None = None
    error: str | None = None


@dataclass
class EvalOptions:
    suites: list[MetricSuite]
    model: ModelConfig | None
    judge_model: str | None
    thresholds: dict[ReferenceSuite, float]
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
            help="Metric suites to run: rag (Faithfulness, ContextualRelevancy, AnswerRelevancy), "
            "correctness and/or completeness (reference-based GEval). Defaults to all three.",
        ),
    ] = None,
    correctness_threshold: Annotated[
        float,
        Parameter(name=["--correctness-threshold", "--threshold"], help="Minimum Correctness score required to pass."),
    ] = CORRECTNESS_RUBRIC.default_threshold,
    completeness_threshold: Annotated[
        float,
        Parameter(name=["--completeness-threshold"], help="Minimum Completeness score required to pass."),
    ] = COMPLETENESS_RUBRIC.default_threshold,
    timeout: Annotated[
        float,
        Parameter(name=["--timeout"], help="Maximum seconds to wait for each agent answer."),
    ] = DEFAULT_TIMEOUT_SECONDS,
    experiment: Annotated[
        str | None,
        Parameter(
            name=["--experiment"],
            help="Experiment ID. Requires --arm-manifest and --block, and shuffles the trial order.",
        ),
    ] = None,
    arm_manifest: Annotated[
        Path | None,
        Parameter(
            name=["--arm-manifest"],
            help="Manifest written by build-arm.sh. The run is labeled with its arm and stops if the served "
            "context does not match it.",
        ),
    ] = None,
    block: Annotated[
        int | None,
        Parameter(name=["--block"], help="Block number within the experiment."),
    ] = None,
    repeats: Annotated[
        int,
        Parameter(name=["--repeats"], help="Agent calls per case; each is judged and saved as its own record."),
    ] = 1,
    seed: Annotated[
        int | None,
        Parameter(name=["--seed"], help="Seed for the trial order. Drawn at random for experiment runs if omitted."),
    ] = None,
    max_cost: Annotated[
        float | None,
        Parameter(
            name=["--max-cost"],
            help="Stop before the next trial once agent and judge cost reach this many US dollars. "
            "Finished trials are saved.",
        ),
    ] = None,
    verbose: Annotated[
        bool,
        Parameter(name=["-v", "--verbose"], help="Print metric reasons alongside scores."),
    ] = False,
):
    """Run LLM-as-judge evals: the RAG triad and reference-based Correctness and Completeness.

    Examples:
        nao evals
        nao evals -m anthropic:claude-sonnet-4-6 -j anthropic:claude-sonnet-4-6
        nao evals --metrics correctness --correctness-threshold 0.7
        nao evals --metrics completeness
        nao evals --metrics rag
        nao evals -s q001 --timeout 120
        nao evals -s q018 --repeats 3
        nao evals --repeats 3 --max-cost 5
        nao evals --experiment metrics-tree-001 --arm-manifest /kwwhat/demo/chat-bi/arm.json --block 1 --repeats 3
        nao evals -u user@example.com --password secret
        nao evals -v
    """
    suites = metrics or ALL_SUITES
    agent_model = _parse_model_option("--model", model)
    if model and agent_model is None:
        return
    if judge_model and _parse_model_option("--judge-model", judge_model) is None:
        return

    if repeats < 1:
        UI.error("--repeats must be at least 1")
        sys.exit(1)
    if max_cost is not None and max_cost <= 0:
        UI.error("--max-cost must be greater than 0")
        sys.exit(1)
    if experiment and (arm_manifest is None or block is None):
        UI.error("--experiment requires --arm-manifest and --block")
        sys.exit(1)
    manifest = _load_arm_manifest(arm_manifest) if arm_manifest else None

    project_path = Path.cwd()
    cases = _load_selected_cases(
        project_path, select, require_expected_output=any(suite in REFERENCE_RUBRICS for suite in suites)
    )
    if not cases:
        return

    options = EvalOptions(
        suites=suites,
        model=agent_model,
        judge_model=judge_model,
        thresholds={"correctness": correctness_threshold, "completeness": completeness_threshold},
        verbose=verbose,
    )
    labels = new_run_labels(experiment, manifest.arm if manifest else None, block, repeats, seed)
    trials = schedule_trials(cases, repeats, labels.seed)
    _print_run_header(trials, options, labels)

    http_client = _build_authenticated_client(
        username or os.environ.get("NAO_USERNAME"),
        password or os.environ.get("NAO_PASSWORD"),
    )
    if http_client is None:
        return

    with http_client:
        client = EvalsClient(http_client, timeout=timeout)
        environment_start = _describe_environment(client)
        if manifest:
            _stop_unless_arm_matches(manifest, environment_start, project_path)
        spend, limit = Spend(), CostLimit(max_cost)
        results = run_trials(trials, client, options, labels, spend, limit)
        environment_end = _describe_environment(client)

    provenance = _build_provenance(dataset_path_for(project_path), environment_start, environment_end)
    run = {**_describe_run(labels, trials, manifest), **_describe_spend(spend, limit, len(results))}
    outputs_dir = project_path / OUTPUTS_FOLDER
    output_file = save_results(results, options, outputs_dir, provenance, run)
    append_ledger(outputs_dir, _ledger_entry("evals", output_file, labels, run, results))
    _warn_if_environment_changed(provenance)
    _report_spend(spend, limit, len(results), len(trials))
    UI.print(f"[dim]Results saved to: {output_file}[/dim]\n")

    _print_summary(results)
    if limit.stopped or any(not result.passed for result in results):
        sys.exit(1)


def run_trials(
    trials: list[Trial], client: EvalsClient, options: EvalOptions, labels: RunLabels, spend: Spend, limit: CostLimit
) -> list[EvalResult]:
    """Runs trials until done, over the cost limit, or interrupted; whatever finished is returned to be saved."""
    results: list[EvalResult] = []
    try:
        for trial in trials:
            if limit.should_stop(spend):
                break
            result = run_trial(trial, client, options, labels)
            results.append(result)
            spend.add_agent(result.cost)
            for metric in result.metrics:
                spend.add_judge(metric.judge_cost)
    except KeyboardInterrupt:
        limit.stopped = {"reason": "interrupted", "spent_usd": round(spend.total_usd, 6)}
    return results


def run_trial(trial: Trial, client: EvalsClient, options: EvalOptions, labels: RunLabels) -> EvalResult:
    result = EvalResult(
        id=trial.case.id,
        input=trial.case.input,
        expected_output=trial.case.expected_output,
        run_id=labels.run_id,
        experiment_id=labels.experiment_id,
        arm=labels.arm,
        block=labels.block,
        repetition=trial.repetition,
        position=trial.position,
    )
    return run_case(trial.case, client, options, result)


def run_case(case: EvalCase, client: EvalsClient, options: EvalOptions, result: EvalResult | None = None) -> EvalResult:
    result = result or EvalResult(id=case.id, input=case.input, expected_output=case.expected_output)
    repetition = f" [dim](repetition {result.repetition})[/dim]" if result.repetition > 1 else ""
    UI.print(f"[bold]Running:[/bold] {case.id}{repetition} [dim]{case.input[:80]}[/dim]")
    result.started_at = datetime.now(timezone.utc).isoformat()

    try:
        answer = client.ask(case.input, options.model)
    except AgentTimeoutError as e:
        return _fail_with_error(result, "timeout", str(e))
    except AgentBackendError as e:
        return _fail_with_error(result, "backend_error", str(e))

    _record_answer(result, answer)
    if result.run_context.memory_count:
        message = f"{result.run_context.memory_count} user memories were injected into the system prompt"
        return _fail_with_error(result, "context_error", message)

    result.judge_model = options.judge_model or answer.model
    result.judge_settings = describe_judge_settings(result.judge_model)

    try:
        judge = resolve_judge(result.judge_model)
        named_metrics = _build_metrics(judge, options)
    except Exception as e:
        return _fail_with_error(result, "metric_error", f"Could not build judge metrics: {e}")

    test_case = _build_test_case(result)
    result.metrics = [measure_metric(name, metric, test_case, options.verbose, judge) for name, metric in named_metrics]
    result.judge_cost = sum_judge_costs([metric.judge_cost for metric in result.metrics])

    if any(metric.error for metric in result.metrics):
        result.error_type = "metric_error"
    result.passed = result.error_type is None and all(metric.passed for metric in result.metrics)
    UI.print("")
    return result


def measure_metric(name: str, metric: Any, test_case: Any, verbose: bool = False, judge: Any = None) -> MetricResult:
    threshold = metric.threshold
    usage_before = snapshot_usage(judge)
    try:
        metric.measure(test_case)
    except Exception as e:
        UI.print(f"  [red]![/red] {name}: [red]error[/red] [dim]{e}[/dim]")
        return MetricResult(
            name=name,
            score=None,
            threshold=threshold,
            passed=False,
            reason=None,
            error=str(e),
            judge_cost=judge_cost(judge, metric, usage_before),
        )

    score = round(metric.score, 4) if metric.score is not None else None
    passed = score is not None and score >= threshold
    reason = getattr(metric, "reason", None)

    status = "[green]✓[/green]" if passed else "[red]✗[/red]"
    UI.print(f"  {status} {name}: {score}")
    if verbose and reason:
        UI.print(f"    [dim]{reason}[/dim]")

    return MetricResult(
        name=name,
        score=score,
        threshold=threshold,
        passed=passed,
        reason=reason,
        judge_cost=judge_cost(judge, metric, usage_before),
    )


def save_results(
    results: list[EvalResult],
    options: EvalOptions,
    output_dir: Path,
    provenance: dict[str, Any] | None = None,
    run: dict[str, Any] | None = None,
) -> Path:
    output_dir.mkdir(parents=True, exist_ok=True)
    now = datetime.now()
    output_file = output_dir / f"evals_results_{now.strftime('%Y%m%d_%H%M%S')}.json"

    records = [asdict(result) for result in results]
    save_run_context_files([record.pop("raw_run_context") for record in records], output_dir)

    data = {
        "timestamp": now.isoformat(),
        "run": run,
        "config": _describe_config(options),
        "provenance": provenance,
        "results": records,
        "summary": _summarize(results),
    }
    output_file.write_text(json.dumps(data, indent=2))
    return output_file


def _load_arm_manifest(manifest_path: Path) -> ArmManifest:
    try:
        return load_arm_manifest(manifest_path)
    except ArmManifestError as e:
        UI.error(str(e))
        sys.exit(1)


def _stop_unless_arm_matches(manifest: ArmManifest, environment: dict[str, Any] | None, project_path: Path) -> None:
    mismatches = find_arm_mismatches(manifest, environment, project_path)
    if not mismatches:
        return
    UI.error(f"The served project is not arm {manifest.arm} as built in {manifest.path}:")
    for mismatch in mismatches:
        UI.print(f"  [red]•[/red] {mismatch}")
    UI.print("[dim]Rebuild the demo image from the arm, or pass the manifest of the arm it was built from.[/dim]")
    sys.exit(1)


def _describe_run(labels: RunLabels, trials: list[Trial], manifest: ArmManifest | None) -> dict[str, Any]:
    return {
        **asdict(labels),
        "order": [[trial.case.id, trial.repetition] for trial in trials],
        "arm_manifest": asdict(manifest) if manifest else None,
    }


def _describe_spend(spend: Spend, limit: CostLimit, trials_run: int) -> dict[str, Any]:
    return {"cost": spend.describe(), "max_cost_usd": limit.max_usd, "trials_run": trials_run, "stopped": limit.stopped}


def _ledger_entry(
    command: str, output_file: Path, labels: RunLabels, run: dict[str, Any], results: list[EvalResult]
) -> dict[str, Any]:
    return {
        "command": command,
        "results_file": output_file.name,
        "run_id": labels.run_id,
        "experiment_id": labels.experiment_id,
        "arm": labels.arm,
        "block": labels.block,
        "trials_planned": len(run["order"]),
        "trials_run": run["trials_run"],
        "errored": sum(1 for result in results if result.error_type),
        **run["cost"],
        "stopped": run["stopped"],
    }


def _report_spend(spend: Spend, limit: CostLimit, trials_run: int, trials_planned: int) -> None:
    UI.print(f"[dim]Cost: ${spend.total_usd:.2f} (agent ${spend.agent_usd:.2f}, judge ${spend.judge_usd:.2f})[/dim]")
    if spend.agent_cost_unknown or spend.judge_cost_unknown:
        UI.warn(
            f"Cost is incomplete: {spend.agent_cost_unknown} agent call(s) and "
            f"{spend.judge_cost_unknown} judge metric(s) reported no cost."
        )
    if limit.stopped:
        UI.warn(f"Stopped after {trials_run} of {trials_planned} trial(s): {limit.stopped['reason']}.")


def _describe_environment(client: EvalsClient) -> dict[str, Any] | None:
    try:
        return client.describe_environment()
    except AgentBackendError as e:
        UI.warn(f"Could not describe the backend environment: {e}")
        return None


def _build_provenance(
    dataset_path: Path, environment_start: dict[str, Any] | None, environment_end: dict[str, Any] | None
) -> dict[str, Any]:
    return {
        "dataset": fingerprint_dataset(dataset_path),
        "packages": package_versions(),
        "environment_start": environment_start,
        "environment_end": environment_end,
        "environment_changed": changed_environment_parts(environment_start, environment_end),
    }


def _warn_if_environment_changed(provenance: dict[str, Any]) -> None:
    changed = provenance["environment_changed"]
    if changed:
        UI.warn(f"The environment changed during the run ({', '.join(changed)}); its results are not comparable.")


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
    for suite, rubric in REFERENCE_RUBRICS.items():
        if suite in options.suites:
            named_metrics.append((rubric.name, rubric.build_metric(judge, options.thresholds[suite])))
    return named_metrics


def _build_test_case(result: EvalResult) -> Any:
    from deepeval.test_case import LLMTestCase

    return LLMTestCase(
        input=result.input,
        actual_output=result.actual_output or "",
        expected_output=result.expected_output,
        retrieval_context=result.retrieval_context or None,  # type: ignore[arg-type]
    )


def _record_answer(result: EvalResult, answer: AgentAnswer) -> None:
    result.actual_output = answer.text
    result.tool_calls = answer.tool_results
    result.retrieval_context = build_retrieval_context(answer.tool_results)
    result.context_read = list_files_read(answer.tool_results)
    result.agent_model = answer.model
    result.usage = answer.usage
    result.cost = answer.cost
    result.duration_ms = answer.duration_ms
    result.raw_run_context = answer.run_context
    result.run_context = describe_run_context(answer.run_context)


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
    if "rag" in options.suites:
        config["rag"] = describe_rag_metrics()
    for suite, rubric in REFERENCE_RUBRICS.items():
        if suite in options.suites:
            config[suite] = {"threshold": options.thresholds[suite], "rubric_version": rubric.version()}
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


def _print_run_header(trials: list[Trial], options: EvalOptions, labels: RunLabels) -> None:
    UI.info(f"\n🧪 Running nao evals ({len(trials)} trial(s))...\n")
    if labels.experiment_id:
        UI.print(f"[dim]Experiment: {labels.experiment_id}, arm {labels.arm}, block {labels.block}[/dim]")
    elif labels.arm:
        UI.print(f"[dim]Arm: {labels.arm}[/dim]")
    if labels.repeats > 1:
        UI.print(f"[dim]Repeats: {labels.repeats}[/dim]")
    if labels.seed is not None:
        UI.print(f"[dim]Order seed: {labels.seed}[/dim]")
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
