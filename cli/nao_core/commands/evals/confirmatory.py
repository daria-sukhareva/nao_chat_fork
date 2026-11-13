from typing import Any

from .arm import ArmManifest

DIRTY_SUFFIX = "-dirty"


def problems_before_run(
    experiment_id: str | None, manifest: ArmManifest | None, block: int | None, select: str | None
) -> list[str]:
    """What makes a run unfit to count, known before contacting the backend."""
    problems = []
    if not experiment_id or manifest is None or block is None:
        problems.append("a confirmatory run needs --experiment, --arm-manifest and --block")
    if select:
        problems.append("a confirmatory run uses the whole dataset, so --select isn't allowed")
    if manifest is not None and _is_dirty_commit(manifest.study_commit):
        problems.append(f"the arm was built from an uncommitted study ({manifest.study_commit or 'unknown commit'})")
    return problems


def problems_with_environment(environment: dict[str, Any] | None) -> list[str]:
    if environment is None:
        return ["the backend environment could not be described"]
    problems = []
    nao = environment.get("nao") or {}
    if _is_dirty_revision(nao):
        problems.append(f"the nao build is not a clean commit ({nao.get('commit') or 'unknown commit'})")
    for repo in environment.get("repos") or []:
        if _is_dirty_revision(repo):
            problems.append(f"linked repo {repo.get('name')} is not a clean commit ({repo.get('commit') or 'unknown'})")
    return problems


def problems_after_run(provenance: dict[str, Any], stopped: dict[str, Any] | None) -> list[str]:
    problems = []
    changed = provenance.get("environment_changed") or []
    if changed:
        problems.append(f"the environment changed during the run ({', '.join(changed)})")
    if stopped:
        problems.append(f"the run stopped early ({stopped.get('reason')})")
    return problems


def _is_dirty_revision(revision: dict[str, Any]) -> bool:
    return revision.get("dirty") is True or _is_dirty_commit(revision.get("commit"))


def _is_dirty_commit(commit: str | None) -> bool:
    return not commit or commit == "unknown" or commit.endswith(DIRTY_SUFFIX)
