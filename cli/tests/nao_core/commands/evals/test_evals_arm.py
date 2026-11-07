import hashlib
import json

import pytest

from nao_core.commands.evals.arm import ArmManifestError, find_arm_mismatches, load_arm_manifest

RULES_SHA = "r" * 64


def write_manifest(tmp_path, files: dict[str, str], arm: str = "B"):
    manifest_path = tmp_path / "arm.json"
    manifest_path.write_text(json.dumps({"arm": arm, "study_commit": "abc", "files": files}))
    return manifest_path


def environment(*files: tuple[str, str]):
    return {"context": {"sha256": "c" * 64, "files": [{"path": path, "sha256": sha} for path, sha in files]}}


def write_dataset(tmp_path, content: str = "{}") -> str:
    dataset = tmp_path / "tests" / "evals" / "golden_dataset.jsonl"
    dataset.parent.mkdir(parents=True)
    dataset.write_text(content)
    return hashlib.sha256(content.encode()).hexdigest()


def test_load_arm_manifest_reads_the_label_and_hashes_the_file(tmp_path):
    manifest = load_arm_manifest(write_manifest(tmp_path, {"RULES.md": RULES_SHA}))

    assert manifest.arm == "B"
    assert manifest.files == {"RULES.md": RULES_SHA}
    assert manifest.study_commit == "abc"
    assert len(manifest.sha256) == 64


@pytest.mark.parametrize(
    "content", ["not json", json.dumps({"arm": "B", "files": {}}), json.dumps({"files": {"a": "b"}})]
)
def test_load_arm_manifest_rejects_an_unusable_manifest(tmp_path, content):
    manifest_path = tmp_path / "arm.json"
    manifest_path.write_text(content)

    with pytest.raises(ArmManifestError):
        load_arm_manifest(manifest_path)


def test_matching_served_context_and_local_dataset_has_no_mismatches(tmp_path):
    dataset_sha = write_dataset(tmp_path)
    manifest = load_arm_manifest(
        write_manifest(tmp_path, {"RULES.md": RULES_SHA, "tests/evals/golden_dataset.jsonl": dataset_sha})
    )

    assert find_arm_mismatches(manifest, environment(("RULES.md", RULES_SHA), ("docs/x.md", "x")), tmp_path) == []


def test_a_different_or_missing_file_is_a_mismatch(tmp_path):
    write_dataset(tmp_path, "edited")
    manifest = load_arm_manifest(
        write_manifest(
            tmp_path,
            {
                "RULES.md": RULES_SHA,
                "docs/metrics_tree.md": "t" * 64,
                "tests/evals/golden_dataset.jsonl": "d" * 64,
            },
        )
    )

    mismatches = find_arm_mismatches(manifest, environment(("RULES.md", "other")), tmp_path)

    assert mismatches == [
        "RULES.md differs from the arm B build",
        "docs/metrics_tree.md is missing",
        "tests/evals/golden_dataset.jsonl differs from the arm B build",
    ]


def test_an_undescribed_environment_cannot_be_checked(tmp_path):
    manifest = load_arm_manifest(write_manifest(tmp_path, {"RULES.md": RULES_SHA}))

    assert find_arm_mismatches(manifest, None, tmp_path)
