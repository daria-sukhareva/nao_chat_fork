import json
from dataclasses import dataclass
from pathlib import Path

EVALS_FOLDER = "tests/evals"
DATASET_FILENAME = "golden_dataset.jsonl"


@dataclass
class EvalCase:
    """A single golden record loaded from the eval dataset."""

    id: str
    input: str
    expected_output: str | None = None


class DatasetValidationError(Exception):
    """Raised when one or more dataset rows are invalid, listing every error at once."""

    def __init__(self, errors: list[str]):
        self.errors = errors
        super().__init__("\n".join(errors))


def dataset_path_for(project_path: Path) -> Path:
    return project_path / EVALS_FOLDER / DATASET_FILENAME


def load_cases(dataset_path: Path, require_expected_output: bool) -> list[EvalCase]:
    """Parse and validate every row before any paid agent or judge call is made."""
    cases: list[EvalCase] = []
    errors: list[str] = []
    seen_ids: dict[str, int] = {}

    for line_number, line in enumerate(dataset_path.read_text().splitlines(), start=1):
        if not line.strip():
            continue

        location = f"{dataset_path.name}:{line_number}"
        row_errors, case = _parse_row(line, require_expected_output)
        errors.extend(f"{location}: {error}" for error in row_errors)
        if case is None:
            continue

        if case.id in seen_ids:
            errors.append(f"{location}: duplicate id '{case.id}' (first seen on line {seen_ids[case.id]})")
            continue

        seen_ids[case.id] = line_number
        cases.append(case)

    if errors:
        raise DatasetValidationError(errors)
    return cases


def select_cases(cases: list[EvalCase], select: str | None) -> list[EvalCase]:
    if not select:
        return cases
    return [case for case in cases if case.id == select]


def _parse_row(line: str, require_expected_output: bool) -> tuple[list[str], EvalCase | None]:
    try:
        row = json.loads(line)
    except json.JSONDecodeError as e:
        return [f"invalid JSON ({e.msg})"], None

    if not isinstance(row, dict):
        return ["row must be a JSON object"], None

    errors = [
        *_validate_string_field(row, "id", required=True),
        *_validate_string_field(row, "input", required=True),
        *_validate_string_field(row, "expected_output", required=require_expected_output),
    ]
    if errors:
        return errors, None

    return [], EvalCase(id=row["id"], input=row["input"], expected_output=row.get("expected_output"))


def _validate_string_field(row: dict, field: str, required: bool) -> list[str]:
    value = row.get(field)
    if value is None:
        return [f"missing required field '{field}'"] if required else []
    if not isinstance(value, str) or not value.strip():
        return [f"field '{field}' must be a non-empty string"]
    return []
