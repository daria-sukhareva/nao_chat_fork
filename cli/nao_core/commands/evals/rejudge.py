import hashlib
import json
import sys
from dataclasses import asdict, dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Annotated, Any

from cyclopts import Parameter

from nao_core.ui import UI

from .cost import CostLimit, JudgeCost, Spend, append_ledger, sum_judge_costs
from .judge import describe_judge_settings, resolve_judge
from .runner import (
    ALL_SUITES,
    OUTPUTS_FOLDER,
    REFERENCE_RUBRICS,
    EvalOptions,
    EvalResult,
    MetricResult,
    MetricSuite,
    _build_metrics,
    _build_test_case,
    _describe_config,
    measure_metric,
)

UNJUDGEABLE_ERRORS = ("timeout", "backend_error", "context_error")


@dataclass
class Judgment:
    answer_id: str
    id: str
    arm: str | None
    block: int | None
    repetition: int
    judge_repetition: int
    judge_model: str
    judge_settings: dict[str, Any]
    metrics: list[MetricResult] = field(default_factory=list)
    judge_cost: JudgeCost | None = None
    error: str | None = None


def rejudge(
    results_file: Annotated[Path, Parameter(help="A results file written by `nao evals`.")],
    *,
    judge_repeats: Annotated[
        int,
        Parameter(name=["--judge-repeats"], help="How many times the judge scores each saved answer."),
    ] = 3,
    judge_model: Annotated[
        str | None,
        Parameter(
            name=["-j", "--judge-model"],
            help="Judge model (format: provider:model_id). Defaults to the judge each answer was scored with.",
        ),
    ] = None,
    metrics: Annotated[
        list[MetricSuite] | None,
        Parameter(name=["--metrics"], help="Metric suites to rescore. Defaults to the suites of the original run."),
    ] = None,
    max_cost: Annotated[
        float | None,
        Parameter(
            name=["--max-cost"],
            help="Stop before the next judgment once judge cost reaches this many US dollars. "
            "Finished judgments are saved.",
        ),
    ] = None,
    verbose: Annotated[
        bool,
        Parameter(name=["-v", "--verbose"], help="Print metric reasons alongside scores."),
    ] = False,
):
    """Rescore saved answers without calling the agent, to measure judge variance apart from agent variance.

    Examples:
        nao evals rejudge tests/outputs/evals_results_20261106_022022.json
        nao evals rejudge tests/outputs/evals_results_20261106_022022.json --judge-repeats 5 --metrics correctness
    """
    if judge_repeats < 1:
        UI.error("--judge-repeats must be at least 1")
        sys.exit(1)
    if max_cost is not None and max_cost <= 0:
        UI.error("--max-cost must be greater than 0")
        sys.exit(1)

    source = _load_results(results_file)
    options = _options_from_source(source["data"], metrics, judge_model, verbose)
    answers = [
        (_answer_id(record, index, source["sha256"]), record)
        for index, record in enumerate(source["data"].get("results", []))
    ]
    judgeable = [(answer_id, record) for answer_id, record in answers if _is_judgeable(record)]
    skipped = [
        {"answer_id": answer_id, "id": record.get("id"), "reason": _skip_reason(record)}
        for answer_id, record in answers
        if not _is_judgeable(record)
    ]

    UI.info(f"\n⚖️  Rejudging {len(judgeable)} answer(s) × {judge_repeats} from {results_file.name}...\n")
    if skipped:
        UI.print(f"[dim]Skipping {len(skipped)} answer(s) the agent did not produce.[/dim]\n")

    planned = [
        (answer_id, record, judge_repetition)
        for answer_id, record in judgeable
        for judge_repetition in range(1, judge_repeats + 1)
    ]
    spend, limit = Spend(), CostLimit(max_cost)
    judgments = judge_planned(planned, options, spend, limit)

    run = {"cost": spend.describe(), "max_cost_usd": max_cost, "stopped": limit.stopped}
    output_file = _save_judgments(results_file, source, options, judge_repeats, judgments, skipped, run)
    append_ledger(Path.cwd() / OUTPUTS_FOLDER, _ledger_entry(output_file, source, run, len(planned), judgments))
    UI.print(f"[dim]Judge cost: ${spend.judge_usd:.2f}[/dim]")
    if limit.stopped:
        UI.warn(f"Stopped after {len(judgments)} of {len(planned)} judgment(s): {limit.stopped['reason']}.")
    UI.print(f"[dim]Judgments saved to: {output_file}[/dim]\n")
    failed = any(judgment.error or any(metric.error for metric in judgment.metrics) for judgment in judgments)
    if limit.stopped or failed:
        sys.exit(1)


def judge_planned(
    planned: list[tuple[str, dict[str, Any], int]], options: EvalOptions, spend: Spend, limit: CostLimit
) -> list[Judgment]:
    """Judges until done, over the cost limit, or interrupted; whatever finished is returned to be saved."""
    judgments: list[Judgment] = []
    try:
        for answer_id, record, judge_repetition in planned:
            if limit.should_stop(spend):
                break
            judgment = judge_answer(record, answer_id, judge_repetition, options)
            judgments.append(judgment)
            for metric in judgment.metrics:
                spend.add_judge(metric.judge_cost)
    except KeyboardInterrupt:
        limit.stopped = {"reason": "interrupted", "spent_usd": round(spend.total_usd, 6)}
    return judgments


def judge_answer(record: dict[str, Any], answer_id: str, judge_repetition: int, options: EvalOptions) -> Judgment:
    """Fresh metric objects per judgment, so no state carries over between repetitions."""
    model = options.judge_model or record.get("judge_model") or record.get("agent_model")
    UI.print(
        f"[bold]Judging:[/bold] {record['id']} [dim](answer {answer_id[:8]}, judge repetition {judge_repetition})[/dim]"
    )
    judgment = Judgment(
        answer_id=answer_id,
        id=record["id"],
        arm=record.get("arm"),
        block=record.get("block"),
        repetition=record.get("repetition", 1),
        judge_repetition=judge_repetition,
        judge_model=model or "",
        judge_settings=describe_judge_settings(model),
    )
    try:
        judge = resolve_judge(model or "")
        named_metrics = _build_metrics(judge, options)
    except Exception as e:
        judgment.error = f"Could not build judge metrics: {e}"
        UI.print(f"  [red]![/red] metric_error: [dim]{judgment.error}[/dim]\n")
        return judgment

    test_case = _build_test_case(_saved_answer(record))
    judgment.metrics = [
        measure_metric(name, metric, test_case, options.verbose, judge) for name, metric in named_metrics
    ]
    judgment.judge_cost = sum_judge_costs([metric.judge_cost for metric in judgment.metrics])
    UI.print("")
    return judgment


def _load_results(results_file: Path) -> dict[str, Any]:
    try:
        content = results_file.read_bytes()
        data = json.loads(content)
    except (OSError, json.JSONDecodeError) as e:
        UI.error(f"Could not read results file {results_file}: {e}")
        sys.exit(1)
    return {"data": data, "sha256": hashlib.sha256(content).hexdigest()}


def _options_from_source(
    data: dict[str, Any], metrics: list[MetricSuite] | None, judge_model: str | None, verbose: bool
) -> EvalOptions:
    config = data.get("config", {})
    suites: list[MetricSuite] = metrics or config.get("metrics") or ALL_SUITES
    thresholds = {
        suite: config.get(suite, {}).get("threshold", rubric.default_threshold)
        for suite, rubric in REFERENCE_RUBRICS.items()
    }
    _warn_if_rubric_changed(config, suites)
    return EvalOptions(suites=suites, model=None, judge_model=judge_model, thresholds=thresholds, verbose=verbose)


def _warn_if_rubric_changed(config: dict[str, Any], suites: list[MetricSuite]) -> None:
    for suite, rubric in REFERENCE_RUBRICS.items():
        original = config.get(suite, {}).get("rubric_version")
        if suite in suites and original and original != rubric.version():
            UI.warn(f"{rubric.name} rubric changed since the run ({original} → {rubric.version()}).")


def _is_judgeable(record: dict[str, Any]) -> bool:
    return record.get("actual_output") is not None and record.get("error_type") not in UNJUDGEABLE_ERRORS


def _skip_reason(record: dict[str, Any]) -> str:
    return record.get("error_type") or "no answer"


def _answer_id(record: dict[str, Any], index: int, source_sha256: str) -> str:
    """Files written before answer IDs existed get one derived from the file and the record's position."""
    return record.get("answer_id") or f"{source_sha256[:12]}:{index}"


def _saved_answer(record: dict[str, Any]) -> EvalResult:
    return EvalResult(
        id=record["id"],
        input=record["input"],
        expected_output=record.get("expected_output"),
        actual_output=record.get("actual_output"),
        retrieval_context=record.get("retrieval_context") or [],
    )


def _save_judgments(
    results_file: Path,
    source: dict[str, Any],
    options: EvalOptions,
    judge_repeats: int,
    judgments: list[Judgment],
    skipped: list[dict[str, Any]],
    run: dict[str, Any] | None = None,
) -> Path:
    now = datetime.now()
    output_file = results_file.parent / f"rejudge_results_{now.strftime('%Y%m%d_%H%M%S')}.json"
    data = {
        "timestamp": now.isoformat(),
        "source": {
            "path": str(results_file),
            "sha256": source["sha256"],
            "run": source["data"].get("run"),
        },
        "config": {**_describe_config(options), "judge_repeats": judge_repeats},
        "run": run,
        "judgments": [asdict(judgment) for judgment in judgments],
        "skipped": skipped,
    }
    output_file.write_text(json.dumps(data, indent=2))
    return output_file


def _ledger_entry(
    output_file: Path, source: dict[str, Any], run: dict[str, Any], planned: int, judgments: list[Judgment]
) -> dict[str, Any]:
    source_run = source["data"].get("run") or {}
    return {
        "command": "rejudge",
        "results_file": output_file.name,
        "run_id": source_run.get("run_id"),
        "experiment_id": source_run.get("experiment_id"),
        "arm": source_run.get("arm"),
        "block": source_run.get("block"),
        "trials_planned": planned,
        "trials_run": len(judgments),
        "errored": sum(1 for judgment in judgments if judgment.error),
        **run["cost"],
        "stopped": run["stopped"],
    }
