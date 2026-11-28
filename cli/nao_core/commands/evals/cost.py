import json
from dataclasses import asdict, dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any

LEDGER_FILENAME = "cost_ledger.jsonl"


@dataclass(frozen=True)
class ModelPrice:
    input_per_million: float
    output_per_million: float


# Mirrors `costPerM` (inputNoCache, output) in apps/backend/src/agents/provider-meta.ts, so judge and
# agent costs come from the same prices. A test fails if the two drift apart.
JUDGE_PRICES: dict[str, ModelPrice] = {
    "claude-sonnet-4-6": ModelPrice(input_per_million=3.0, output_per_million=15.0),
}


@dataclass
class TokenUsage:
    calls: int = 0
    input_tokens: int = 0
    output_tokens: int = 0

    def add(self, input_tokens: int, output_tokens: int) -> None:
        self.calls += 1
        self.input_tokens += input_tokens
        self.output_tokens += output_tokens

    def since(self, earlier: "TokenUsage") -> "TokenUsage":
        return TokenUsage(
            calls=self.calls - earlier.calls,
            input_tokens=self.input_tokens - earlier.input_tokens,
            output_tokens=self.output_tokens - earlier.output_tokens,
        )


@dataclass
class JudgeCost:
    """What the judge spent on one metric. `cost_usd` is None when the judge model has no known price."""

    calls: int | None = None
    input_tokens: int | None = None
    output_tokens: int | None = None
    cost_usd: float | None = None


@dataclass
class Spend:
    agent_usd: float = 0.0
    judge_usd: float = 0.0
    agent_cost_unknown: int = 0
    judge_cost_unknown: int = 0

    @property
    def total_usd(self) -> float:
        return self.agent_usd + self.judge_usd

    def add_agent(self, cost: dict[str, Any] | None) -> None:
        """A trial that timed out or failed in the backend still cost money, but returns no cost; it's counted."""
        amount = agent_cost_usd(cost)
        if amount is None:
            self.agent_cost_unknown += 1
            return
        self.agent_usd += amount

    def add_judge(self, cost: JudgeCost | None) -> None:
        if cost is None or cost.cost_usd is None:
            self.judge_cost_unknown += 1
            return
        self.judge_usd += cost.cost_usd

    def describe(self) -> dict[str, Any]:
        return {**asdict(self), "total_usd": round(self.total_usd, 6)}


@dataclass
class CostLimit:
    """Stops a run before the next trial once spending reaches the limit; the trial in flight may overshoot it.

    A judge with no known price makes the limit unenforceable, so it stops the run too.
    """

    max_usd: float | None
    stopped: dict[str, Any] | None = field(default=None)

    def should_stop(self, spend: Spend) -> bool:
        if self.max_usd is None:
            return False
        if spend.judge_cost_unknown:
            self.stopped = {"reason": "cost_unknown", "spent_usd": round(spend.total_usd, 6)}
            return True
        if spend.total_usd >= self.max_usd:
            self.stopped = {"reason": "max_cost", "spent_usd": round(spend.total_usd, 6), "max_usd": self.max_usd}
            return True
        return False


def judge_cost(judge: Any, metric: Any, usage_before: TokenUsage | None) -> JudgeCost | None:
    """Our Claude judge counts its own tokens; DeepEval's built-in judges report `evaluation_cost` instead."""
    usage = getattr(judge, "usage", None)
    if isinstance(usage, TokenUsage) and usage_before is not None:
        spent = usage.since(usage_before)
        return JudgeCost(
            calls=spent.calls,
            input_tokens=spent.input_tokens,
            output_tokens=spent.output_tokens,
            cost_usd=price_tokens(judge.get_model_name(), spent),
        )
    evaluation_cost = getattr(metric, "evaluation_cost", None)
    if evaluation_cost is not None:
        return JudgeCost(cost_usd=float(evaluation_cost))
    return None


def snapshot_usage(judge: Any) -> TokenUsage | None:
    usage = getattr(judge, "usage", None)
    if not isinstance(usage, TokenUsage):
        return None
    return TokenUsage(calls=usage.calls, input_tokens=usage.input_tokens, output_tokens=usage.output_tokens)


def price_tokens(model_id: str, usage: TokenUsage) -> float | None:
    price = JUDGE_PRICES.get(model_id)
    if price is None:
        return None
    cost = usage.input_tokens * price.input_per_million + usage.output_tokens * price.output_per_million
    return round(cost / 1_000_000, 6)


def agent_cost_usd(cost: dict[str, Any] | None) -> float | None:
    total = (cost or {}).get("totalCost")
    return float(total) if total is not None else None


def sum_judge_costs(costs: list[JudgeCost | None]) -> JudgeCost:
    known = [cost for cost in costs if cost is not None]
    priced = [cost.cost_usd for cost in known if cost.cost_usd is not None]
    return JudgeCost(
        calls=sum(cost.calls or 0 for cost in known),
        input_tokens=sum(cost.input_tokens or 0 for cost in known),
        output_tokens=sum(cost.output_tokens or 0 for cost in known),
        cost_usd=round(sum(priced), 6) if len(priced) == len(costs) else None,
    )


def append_ledger(outputs_dir: Path, entry: dict[str, Any]) -> Path:
    """One line per run of `nao evals` or `nao evals rejudge`, so cost can be summed across the experiment."""
    outputs_dir.mkdir(parents=True, exist_ok=True)
    ledger = outputs_dir / LEDGER_FILENAME
    with ledger.open("a") as file:
        file.write(json.dumps({"timestamp": datetime.now().isoformat(), **entry}) + "\n")
    return ledger


def read_ledger(outputs_dir: Path) -> list[dict[str, Any]]:
    ledger = outputs_dir / LEDGER_FILENAME
    if not ledger.exists():
        return []
    return [json.loads(line) for line in ledger.read_text().splitlines() if line.strip()]
