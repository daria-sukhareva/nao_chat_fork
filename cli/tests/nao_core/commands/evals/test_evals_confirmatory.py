import json
from unittest.mock import MagicMock, patch

import pytest

from nao_core.commands.evals.arm import ArmManifest
from nao_core.commands.evals.client import AgentAnswer
from nao_core.commands.evals.confirmatory import problems_after_run, problems_before_run, problems_with_environment
from nao_core.commands.evals.runner import evals

CLEAN = "a" * 40
MANIFEST = ArmManifest(arm="B", files={"RULES.md": "r" * 64}, path="arm.json", sha256="m" * 64, study_commit=CLEAN)
ENVIRONMENT = {
    "nao": {"version": "dev", "commit": CLEAN, "dirty": None},
    "context": {"sha256": "c" * 64, "files": [{"path": "RULES.md", "sha256": "r" * 64}]},
    "repos": [{"name": "kwwhat", "commit": "b" * 40, "dirty": False}],
    "data": [],
}


def test_a_fully_labeled_run_on_a_clean_study_has_no_problems_before_it_starts():
    assert problems_before_run("exp-1", MANIFEST, 1, None) == []


@pytest.mark.parametrize(
    ("experiment_id", "manifest", "block", "select", "expected"),
    [
        (None, MANIFEST, 1, None, "needs --experiment"),
        ("exp-1", None, 1, None, "needs --experiment"),
        ("exp-1", MANIFEST, None, None, "needs --experiment"),
        ("exp-1", MANIFEST, 1, "q018", "--select isn't allowed"),
        ("exp-1", ArmManifest("B", {"a": "b"}, "arm.json", "m", f"{CLEAN}-dirty"), 1, None, "uncommitted study"),
    ],
)
def test_missing_labels_a_selected_case_or_a_dirty_study_are_refused(experiment_id, manifest, block, select, expected):
    problems = problems_before_run(experiment_id, manifest, block, select)

    assert any(expected in problem for problem in problems)


@pytest.mark.parametrize(
    "environment",
    [
        None,
        {**ENVIRONMENT, "nao": {"commit": f"{CLEAN}-dirty", "dirty": None}},
        {**ENVIRONMENT, "nao": {"commit": None, "dirty": None}},
        {**ENVIRONMENT, "repos": [{"name": "kwwhat", "commit": "b" * 40, "dirty": True}]},
    ],
)
def test_a_dirty_or_undescribed_environment_is_refused(environment):
    assert problems_with_environment(environment)


def test_a_clean_environment_has_no_problems():
    assert problems_with_environment(ENVIRONMENT) == []


def test_a_change_during_the_run_or_an_early_stop_invalidates_it():
    assert problems_after_run({"environment_changed": []}, None) == []
    assert problems_after_run({"environment_changed": ["dataset"]}, None)
    assert problems_after_run({"environment_changed": []}, {"reason": "max_cost"})


def write_project(tmp_path):
    dataset = tmp_path / "tests" / "evals" / "golden_dataset.jsonl"
    dataset.parent.mkdir(parents=True)
    dataset.write_text(json.dumps({"id": "q001", "input": "a", "expected_output": "b"}))
    (tmp_path / "RULES.md").write_text("rules")
    manifest = tmp_path / "arm.json"
    manifest.write_text(json.dumps({"arm": "B", "study_commit": CLEAN, "files": {"RULES.md": "r" * 64}}))
    return manifest, dataset


class PassingMetric:
    threshold = 0.5
    score = 0.9
    reason = "ok"

    def measure(self, test_case):
        pass


@pytest.fixture
def clean_backend():
    client = MagicMock()
    client.ask.return_value = AgentAnswer(text="answer", model="anthropic:claude-sonnet-4-6", cost={"totalCost": 0.1})
    client.describe_environment.return_value = ENVIRONMENT
    with (
        patch("nao_core.commands.evals.runner._build_authenticated_client", return_value=MagicMock()),
        patch("nao_core.commands.evals.runner.EvalsClient", return_value=client),
        patch("nao_core.commands.evals.runner.resolve_judge", return_value="judge"),
        patch("nao_core.commands.evals.runner._build_metrics", return_value=[("Correctness", PassingMetric())]),
    ):
        yield client


def read_results(tmp_path):
    return json.loads(next((tmp_path / "tests" / "outputs").glob("evals_results_*.json")).read_text())


def test_a_clean_confirmatory_run_is_recorded_as_valid(tmp_path, monkeypatch, clean_backend):
    monkeypatch.chdir(tmp_path)
    manifest, _ = write_project(tmp_path)

    evals(experiment="exp-1", arm_manifest=manifest, block=1, metrics=["correctness"], confirmatory=True)

    assert read_results(tmp_path)["run"]["confirmatory"] == {"valid": True, "problems": []}


def test_a_confirmatory_run_with_a_selected_case_stops_before_any_call(tmp_path, monkeypatch, clean_backend):
    monkeypatch.chdir(tmp_path)
    manifest, _ = write_project(tmp_path)

    with pytest.raises(SystemExit):
        evals(experiment="exp-1", arm_manifest=manifest, block=1, select="q001", confirmatory=True)

    clean_backend.ask.assert_not_called()


def test_a_confirmatory_run_on_a_dirty_build_stops_before_any_call(tmp_path, monkeypatch, clean_backend):
    monkeypatch.chdir(tmp_path)
    manifest, _ = write_project(tmp_path)
    clean_backend.describe_environment.return_value = {**ENVIRONMENT, "nao": {"commit": f"{CLEAN}-dirty"}}

    with pytest.raises(SystemExit):
        evals(experiment="exp-1", arm_manifest=manifest, block=1, metrics=["correctness"], confirmatory=True)

    clean_backend.ask.assert_not_called()


def test_a_dataset_edited_mid_run_is_flagged_and_invalidates_a_confirmatory_run(tmp_path, monkeypatch, clean_backend):
    monkeypatch.chdir(tmp_path)
    manifest, dataset = write_project(tmp_path)
    answer = clean_backend.ask.return_value

    def edit_dataset_then_answer(*args):
        dataset.write_text(json.dumps({"id": "q001", "input": "a", "expected_output": "edited"}))
        return answer

    clean_backend.ask.side_effect = edit_dataset_then_answer

    with pytest.raises(SystemExit):
        evals(experiment="exp-1", arm_manifest=manifest, block=1, metrics=["correctness"], confirmatory=True)

    data = read_results(tmp_path)
    assert "dataset" in data["provenance"]["environment_changed"]
    assert data["run"]["confirmatory"]["valid"] is False
