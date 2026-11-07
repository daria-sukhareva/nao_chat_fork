import hashlib
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

DATASET_FOLDER = "tests/"


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
    """Compares each file the arm should contain with what the backend serves.

    The backend's context fingerprint skips `tests/`, so the dataset is hashed from the local project instead.
    """
    if environment is None:
        return ["the backend environment could not be described, so the arm cannot be checked"]

    served = {file["path"]: file["sha256"] for file in environment.get("context", {}).get("files", [])}
    mismatches = []
    for file, expected in sorted(manifest.files.items()):
        actual = _local_sha256(project_path / file) if file.startswith(DATASET_FOLDER) else served.get(file)
        if actual is None:
            mismatches.append(f"{file} is missing")
        elif actual != expected:
            mismatches.append(f"{file} differs from the arm {manifest.arm} build")
    return mismatches


def _local_sha256(file_path: Path) -> str | None:
    if not file_path.is_file():
        return None
    return hashlib.sha256(file_path.read_bytes()).hexdigest()
