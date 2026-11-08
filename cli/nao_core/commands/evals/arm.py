import hashlib
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

DATASET_FOLDER = "tests/"
SHARED_PATHS = ("databases/", "repos/", "nao_config.yaml")


@dataclass
class ArmManifest:
    """The files `build-arm.sh` assembled for one arm, as written next to the arm's folder."""

    arm: str
    files: dict[str, str]
    path: str
    sha256: str
    study_commit: str | None = None


class ArmManifestError(Exception):
    pass


def load_arm_manifest(manifest_path: Path) -> ArmManifest:
    try:
        content = manifest_path.read_bytes()
        data = json.loads(content)
    except (OSError, json.JSONDecodeError) as e:
        raise ArmManifestError(f"Could not read arm manifest {manifest_path}: {e}") from e

    arm, files = data.get("arm"), data.get("files")
    if not isinstance(arm, str) or not arm or not isinstance(files, dict) or not files:
        raise ArmManifestError(f"Arm manifest {manifest_path} needs a non-empty 'arm' and 'files'")

    return ArmManifest(
        arm=arm,
        files={str(file): str(sha) for file, sha in files.items()},
        path=str(manifest_path),
        sha256=hashlib.sha256(content).hexdigest(),
        study_commit=data.get("study_commit"),
    )


def find_arm_mismatches(manifest: ArmManifest, environment: dict[str, Any] | None, project_path: Path) -> list[str]:
    """Compares what the backend serves with the files the arm should contain, both ways.

    The backend's context fingerprint skips `tests/`, so the dataset is hashed from the local project instead.
    Files every arm shares, synced from the data and repos or copied by the demo image, are not the arm's to list.
    """
    if environment is None:
        return ["the backend environment could not be described, so the arm cannot be checked"]

    served = {file["path"]: file["sha256"] for file in environment.get("context", {}).get("files", [])}
    return _find_wrong_arm_files(manifest, served, project_path) + _find_extra_served_files(manifest, served)


def _find_wrong_arm_files(manifest: ArmManifest, served: dict[str, str], project_path: Path) -> list[str]:
    mismatches = []
    for file, expected in sorted(manifest.files.items()):
        actual = _local_sha256(project_path / file) if file.startswith(DATASET_FOLDER) else served.get(file)
        if actual is None:
            mismatches.append(f"{file} is missing")
        elif actual != expected:
            mismatches.append(f"{file} differs from the arm {manifest.arm} build")
    return mismatches


def _find_extra_served_files(manifest: ArmManifest, served: dict[str, str]) -> list[str]:
    extra = sorted(file for file in served if file not in manifest.files and not file.startswith(SHARED_PATHS))
    return [f"{file} is served but is not part of arm {manifest.arm}" for file in extra]


def _local_sha256(file_path: Path) -> str | None:
    if not file_path.is_file():
        return None
    return hashlib.sha256(file_path.read_bytes()).hexdigest()
