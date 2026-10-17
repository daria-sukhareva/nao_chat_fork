import json

import pytest

from nao_core.commands.evals.case import DatasetValidationError, EvalCase, load_cases, select_cases


def write_dataset(tmp_path, *lines: str):
    path = tmp_path / "golden_dataset.jsonl"
    path.write_text("\n".join(lines) + "\n")
    return path


def row(**fields) -> str:
    return json.dumps(fields)


def test_load_cases_parses_valid_rows_and_skips_blank_lines(tmp_path):
    path = write_dataset(
        tmp_path,
        row(id="q001", input="How many ports?", expected_output="4 ports."),
        "",
        row(id="q002", input="Uptime?", expected_output="99.71%."),
    )

    cases = load_cases(path, require_expected_output=True)

    assert cases == [
        EvalCase(id="q001", input="How many ports?", expected_output="4 ports."),
        EvalCase(id="q002", input="Uptime?", expected_output="99.71%."),
    ]


def test_load_cases_reports_every_error_with_its_line(tmp_path):
    path = write_dataset(
        tmp_path,
        row(id="q001", input="ok", expected_output="ok"),
        "{not json",
        row(input="missing id", expected_output="x"),
        row(id="q001", input="dup", expected_output="x"),
        row(id="q004", input="", expected_output="x"),
        "[1, 2]",
    )

    with pytest.raises(DatasetValidationError) as exc_info:
        load_cases(path, require_expected_output=True)

    errors = exc_info.value.errors
    assert len(errors) == 5
    assert errors[0].startswith("golden_dataset.jsonl:2: invalid JSON")
    assert errors[1] == "golden_dataset.jsonl:3: missing required field 'id'"
    assert errors[2] == "golden_dataset.jsonl:4: duplicate id 'q001' (first seen on line 1)"
    assert errors[3] == "golden_dataset.jsonl:5: field 'input' must be a non-empty string"
    assert errors[4] == "golden_dataset.jsonl:6: row must be a JSON object"


def test_expected_output_is_required_only_for_correctness(tmp_path):
    path = write_dataset(tmp_path, row(id="q001", input="Uptime?"))

    assert load_cases(path, require_expected_output=False) == [EvalCase(id="q001", input="Uptime?")]
    with pytest.raises(DatasetValidationError, match="missing required field 'expected_output'"):
        load_cases(path, require_expected_output=True)


def test_select_cases_filters_by_id():
    cases = [EvalCase(id="q001", input="a"), EvalCase(id="q002", input="b")]

    assert select_cases(cases, None) == cases
    assert select_cases(cases, "q002") == [cases[1]]
    assert select_cases(cases, "missing") == []
