from collections import defaultdict
from pathlib import Path
from typing import Annotated, Any

from cyclopts import Parameter

from nao_core.ui import UI

from .cost import LEDGER_FILENAME, read_ledger
from .runner import OUTPUTS_FOLDER

UNLABELED = "(no experiment)"


def cost(
    *,
    experiment: Annotated[
        str | None,
        Parameter(name=["--experiment"], help="Show only this experiment's runs."),
    ] = None,
    budget: Annotated[
        float | None,
        Parameter(name=["--budget"], help="Budget in US dollars to report the remainder against."),
    ] = None,
):
    """Sum the cost of every `nao evals` and `nao evals rejudge` run recorded in the cost ledger.

    Examples:
        nao evals cost
        nao evals cost --experiment metrics-tree-001 --budget 200
    """
    outputs_dir = Path.cwd() / OUTPUTS_FOLDER
    entries = read_ledger(outputs_dir)
    if experiment:
        entries = [entry for entry in entries if entry.get("experiment_id") == experiment]
    if not entries:
        UI.warn(f"No runs recorded in {outputs_dir / LEDGER_FILENAME}")
        return

    totals = summarize_ledger(entries)
    for name, total in totals.items():
        UI.print(
            f"{name}: ${total['total_usd']:.2f} over {total['runs']} run(s) "
            f"[dim](agent ${total['agent_usd']:.2f}, judge ${total['judge_usd']:.2f})[/dim]"
        )
        if total["agent_cost_unknown"] or total["judge_cost_unknown"]:
            UI.warn(
                f"  Incomplete: {total['agent_cost_unknown']} agent call(s) and "
                f"{total['judge_cost_unknown']} judge metric(s) reported no cost."
            )

    spent = sum(total["total_usd"] for total in totals.values())
    UI.print(f"\nTotal: ${spent:.2f}")
    if budget is not None:
        UI.print(f"Remaining of ${budget:.2f}: ${budget - spent:.2f}")


def summarize_ledger(entries: list[dict[str, Any]]) -> dict[str, dict[str, float]]:
    totals: dict[str, dict[str, float]] = defaultdict(
        lambda: {
            "runs": 0,
            "agent_usd": 0.0,
            "judge_usd": 0.0,
            "total_usd": 0.0,
            "agent_cost_unknown": 0,
            "judge_cost_unknown": 0,
        }
    )
    for entry in entries:
        total = totals[entry.get("experiment_id") or UNLABELED]
        total["runs"] += 1
        for key in ("agent_usd", "judge_usd", "total_usd", "agent_cost_unknown", "judge_cost_unknown"):
            total[key] += entry.get(key) or 0
    return dict(totals)
