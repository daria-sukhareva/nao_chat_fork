import hashlib
import json
from importlib.metadata import PackageNotFoundError, version
from pathlib import Path
from typing import Any

TRACKED_PACKAGES = ("nao-core", "deepeval", "anthropic", "openai")
ENVIRONMENT_PARTS = ("nao", "context", "repos", "data")


def fingerprint_dataset(dataset_path: Path) -> dict[str, Any]:
    """Hashes the file and each row, so a comparison can tell which cases changed, not only that one did."""
    content = dataset_path.read_bytes()
    rows = [json.loads(line) for line in content.decode().splitlines() if line.strip()]
    return {
        "path": str(dataset_path),
        "sha256": hashlib.sha256(content).hexdigest(),
        "rows": {str(row.get("id")): _sha256_json(row) for row in rows},
    }


def package_versions() -> dict[str, str | None]:
    return {package: _installed_version(package) for package in TRACKED_PACKAGES}


def changed_environment_parts(start: dict[str, Any] | None, end: dict[str, Any] | None) -> list[str]:
    if start is None or end is None:
        return []
    return [part for part in ENVIRONMENT_PARTS if _comparable(start, part) != _comparable(end, part)]


def _comparable(environment: dict[str, Any], part: str) -> Any:
    value = environment.get(part)
    if part == "context" and isinstance(value, dict):
        return value.get("sha256")
    return value


def _sha256_json(value: Any) -> str:
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


def _installed_version(package: str) -> str | None:
    try:
        return version(package)
    except PackageNotFoundError:
        return None
