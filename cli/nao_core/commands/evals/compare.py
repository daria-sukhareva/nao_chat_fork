import json
import sys
from collections import Counter
from dataclasses import dataclass, field
from pathlib import Path
from typing import Annotated, Any

from cyclopts import Parameter

from nao_core.ui import UI

DATASET_FOLDER = "tests/"
SYNCED_DATABASES_FOLDER = "databases/"
PREVIEW_FILENAME = "preview.md"
RECORD_FIELDS = {
    "agent model": lambda record: record.get("agent_model"),
    "agent call settings": lambda record: (record.get("run_context") or {}).get("model_call_settings"),
    "tool manifest": lambda record: (record.get("run_context") or {}).get("tool_manifest_sha256"),
    "judge model": lambda record: record.get("judge_model"),
    "judge settings": lambda record: record.get("judge_settings"),
}


@dataclass
class RunSummary:
    """What a results file says about the conditions it ran under."""

    path: str
    experiment_id: str | None
    arm: str | None
    block: int | None
    confirmatory_valid: bool | None
    stopped: dict[str, Any] | None
    environment_changed: list[str]
    held_fixed: dict[str, Any]
    context_files: dict[str, str]
    arm_files: set[str]
    system_prompts: set[str]
    varies_within_run: list[str] = field(default_factory=list)


def compare(
    results_files: Annotated[list[Path], Parameter(help="Two or more results files written by `nao evals`.")],
    *,
    confirmatory: Annotated[
        bool,
        Parameter(name=["--confirmatory"], help="Also require every run to be a valid confirmatory run."),
    ] = False,
):
    """Check that runs held everything fixed except the arm, so their results can be paired or pooled.

    Examples:
        nao evals compare tests/outputs/evals_results_a.json tests/outputs/evals_results_b.json
        nao evals compare tests/outputs/evals_results_*.json --confirmatory
    """
    if len(results_files) < 2:
        UI.error("compare needs at least two results files")
        sys.exit(1)

    runs = [summarize_run(path) for path in results_files]
    problems = find_comparison_problems(runs, confirmatory)
    for run in runs:
        UI.print(f"[dim]{Path(run.path).name}: experiment {run.experiment_id}, arm {run.arm}, block {run.block}[/dim]")
    for note in find_tolerated_differences(runs):
        UI.warn(note)
    if problems:
        UI.error(f"These runs can't be paired ({len(problems)} problem(s)):")
        for problem in problems:
            UI.print(f"  [red]•[/red] {problem}")
        sys.exit(1)
    UI.success(f"{len(runs)} runs held everything fixed except the arm.")


def summarize_run(results_file: Path) -> RunSummary:
    try:
        data = json.loads(results_file.read_text())
    except (OSError, json.JSONDecodeError) as e:
        UI.error(f"Could not read results file {results_file}: {e}")
        sys.exit(1)

    run = data.get("run") or {}
    provenance = data.get("provenance") or {}
    environment = provenance.get("environment_start") or {}
    records = data.get("results") or []
    record_values = {name: _distinct(records, read) for name, read in RECORD_FIELDS.items()}

    return RunSummary(
        path=str(results_file),
        experiment_id=run.get("experiment_id"),
        arm=run.get("arm"),
        block=run.get("block"),
        confirmatory_valid=(run.get("confirmatory") or {}).get("valid"),
        stopped=run.get("stopped"),
        environment_changed=provenance.get("environment_changed") or [],
        held_fixed={
            "experiment": run.get("experiment_id"),
            "nao commit": (environment.get("nao") or {}).get("commit"),
            "dataset": (provenance.get("dataset") or {}).get("sha256"),
            "data": environment.get("data"),
            "linked repos": environment.get("repos"),
            "packages": provenance.get("packages"),
            "metric config": data.get("config"),
            **{name: values[0] if len(values) == 1 else values for name, values in record_values.items()},
        },
        context_files={file["path"]: file["sha256"] for file in (environment.get("context") or {}).get("files", [])},
        arm_files={
            file for file in ((run.get("arm_manifest") or {}).get("files") or {}) if not file.startswith(DATASET_FOLDER)
        },
        system_prompts=set(
            _distinct(records, lambda record: (record.get("run_context") or {}).get("system_prompt_stable_sha256"))
        ),
        varies_within_run=[name for name, values in record_values.items() if len(values) > 1],
    )


def find_comparison_problems(runs: list[RunSummary], require_confirmatory: bool) -> list[str]:
    return [
        *_problems_within_runs(runs, require_confirmatory),
        *_problems_with_held_fixed(runs),
        *_problems_with_blocks(runs),
        *_problems_with_arm_context(runs),
    ]


def find_tolerated_differences(runs: list[RunSummary]) -> list[str]:
    """Differences accepted but reported, so the whitepaper can state them."""
    notes = []
    for index, run in enumerate(runs):
        for other in runs[index + 1 :]:
            previews = sorted(file for file in _differing_files(run, other) if _is_resampled_preview(file, run, other))
            if previews:
                notes.append(
                    f"{Path(run.path).name} and {Path(other.path).name}: {len(previews)} preview.md file(s) show "
                    "different sample rows of identical data (nao sync samples previews without ORDER BY)"
                )
    return notes


def _problems_within_runs(runs: list[RunSummary], require_confirmatory: bool) -> list[str]:
    problems = []
    for run in runs:
        name = Path(run.path).name
        if not run.arm:
            problems.append(
                f"{name}: no arm label, so its context can't be checked against an arm (run with --arm-manifest)"
            )
        if run.environment_changed:
            problems.append(f"{name}: the environment changed during the run ({', '.join(run.environment_changed)})")
        if run.stopped:
            problems.append(f"{name}: the run stopped early ({run.stopped.get('reason')})")
        for field_name in run.varies_within_run:
            problems.append(f"{name}: {field_name} varies between records of the same run")
        if require_confirmatory and run.confirmatory_valid is not True:
            problems.append(f"{name}: not a valid confirmatory run")
    return problems


def _problems_with_held_fixed(runs: list[RunSummary]) -> list[str]:
    first = runs[0]
    problems = []
    for field_name, expected in first.held_fixed.items():
        differing = [Path(run.path).name for run in runs[1:] if run.held_fixed.get(field_name) != expected]
        if differing:
            problems.append(f"{field_name} differs from {Path(first.path).name} in {', '.join(differing)}")
    return problems


def _problems_with_blocks(runs: list[RunSummary]) -> list[str]:
    counts = Counter((run.experiment_id, run.block) for run in runs if run.block is not None)
    return [f"block {block} appears in {count} runs" for (_, block), count in counts.items() if count > 1]


def _problems_with_arm_context(runs: list[RunSummary]) -> list[str]:
    """Runs of the same arm must have identical context; different arms may differ only in their arms' files."""
    problems = []
    for index, run in enumerate(runs):
        for other in runs[index + 1 :]:
            problems.extend(_problems_between(run, other))
    return problems


def _problems_between(run: RunSummary, other: RunSummary) -> list[str]:
    pair = f"{Path(run.path).name} and {Path(other.path).name}"
    differing_files = {file for file in _differing_files(run, other) if not _is_resampled_preview(file, run, other)}
    if run.arm == other.arm:
        problems = [f"{pair}: same arm {run.arm}, but {file} differs" for file in sorted(differing_files)]
        if run.system_prompts != other.system_prompts:
            problems.append(f"{pair}: same arm {run.arm}, but the system prompt differs")
        return problems

    allowed = run.arm_files | other.arm_files
    return [
        f"{pair}: {file} differs, and it isn't one of either arm's files" for file in sorted(differing_files - allowed)
    ]


def _differing_files(run: RunSummary, other: RunSummary) -> set[str]:
    return {
        file
        for file in run.context_files.keys() | other.context_files.keys()
        if run.context_files.get(file) != other.context_files.get(file)
    }


def _is_resampled_preview(file: str, run: RunSummary, other: RunSummary) -> bool:
    """A preview may differ only when the data is provably the same, so the difference can only be sampling."""
    is_preview = file.startswith(SYNCED_DATABASES_FOLDER) and file.endswith(f"/{PREVIEW_FILENAME}")
    same_data = run.held_fixed.get("data") is not None and run.held_fixed.get("data") == other.held_fixed.get("data")
    return is_preview and same_data


def _distinct(records: list[dict[str, Any]], read: Any) -> list[Any]:
    values: list[Any] = []
    for record in records:
        value = read(record)
        if value not in (None, "", {}, []) and value not in values:
            values.append(value)
    return values
