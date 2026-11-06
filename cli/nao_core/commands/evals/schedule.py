import random
import uuid
from dataclasses import dataclass

from .case import EvalCase


@dataclass
class RunLabels:
    """What one `nao evals` invocation was, so its records can be pooled with other blocks and arms."""

    run_id: str
    experiment_id: str | None = None
    arm: str | None = None
    block: int | None = None
    repeats: int = 1
    seed: int | None = None


@dataclass
class Trial:
    case: EvalCase
    repetition: int
    position: int


def new_run_labels(
    experiment_id: str | None, arm: str | None, block: int | None, repeats: int, seed: int | None
) -> RunLabels:
    """Experiment runs are always shuffled; without a seed one is drawn and recorded."""
    if experiment_id and seed is None:
        seed = random.SystemRandom().randrange(2**32)
    return RunLabels(
        run_id=str(uuid.uuid4()), experiment_id=experiment_id, arm=arm, block=block, repeats=repeats, seed=seed
    )


def schedule_trials(cases: list[EvalCase], repeats: int, seed: int | None) -> list[Trial]:
    """Each repetition is its own trial; with a seed, cases and repetitions are interleaved in a shuffled order."""
    pairs = [(case, repetition) for case in cases for repetition in range(1, repeats + 1)]
    if seed is not None:
        random.Random(seed).shuffle(pairs)
    return [Trial(case=case, repetition=repetition, position=index) for index, (case, repetition) in enumerate(pairs)]
