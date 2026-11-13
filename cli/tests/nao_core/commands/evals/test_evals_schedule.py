from nao_core.commands.evals.case import EvalCase
from nao_core.commands.evals.schedule import new_run_labels, schedule_trials

CASES = [EvalCase(id=f"q{index:03}", input="?") for index in range(1, 6)]


def order(trials):
    return [(trial.case.id, trial.repetition) for trial in trials]


def test_without_a_seed_trials_follow_the_dataset_order():
    trials = schedule_trials(CASES[:2], repeats=2, seed=None)

    assert order(trials) == [("q001", 1), ("q001", 2), ("q002", 1), ("q002", 2)]
    assert [trial.position for trial in trials] == [0, 1, 2, 3]


def test_a_seed_shuffles_every_repetition_reproducibly():
    first = schedule_trials(CASES, repeats=3, seed=7)
    second = schedule_trials(CASES, repeats=3, seed=7)

    assert order(first) == order(second)
    assert order(first) != order(schedule_trials(CASES, repeats=3, seed=None))
    assert sorted(order(first)) == sorted((case.id, repetition) for case in CASES for repetition in (1, 2, 3))


def test_experiment_runs_draw_and_record_a_seed():
    labels = new_run_labels("metrics-tree-001", "B", 1, repeats=3, seed=None)

    assert labels.seed is not None
    assert new_run_labels(None, None, None, repeats=1, seed=None).seed is None
    assert new_run_labels("metrics-tree-001", "B", 1, repeats=1, seed=5).seed == 5
