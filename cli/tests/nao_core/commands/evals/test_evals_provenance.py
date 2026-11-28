import json

from nao_core.commands.evals.provenance import changed_environment_parts, fingerprint_dataset

ENVIRONMENT = {
    "nao": {"version": "dev", "commit": "a", "dirty": False},
    "context": {"sha256": "c", "files": [{"path": "RULES.md", "sha256": "r"}]},
    "repos": [],
    "data": [
        {"databaseId": "duckdb_analytics", "tables": [{"table": "fact_visits", "rowCount": "85", "checksum": "1"}]}
    ],
}


def write_rows(path, *rows):
    path.write_text("\n".join(json.dumps(row) for row in rows) + "\n\n")


def test_dataset_fingerprint_identifies_which_row_changed(tmp_path):
    dataset = tmp_path / "golden_dataset.jsonl"
    write_rows(dataset, {"id": "q001", "input": "a"}, {"id": "q002", "input": "b"})
    before = fingerprint_dataset(dataset)
    write_rows(dataset, {"id": "q001", "input": "a"}, {"id": "q002", "input": "changed"})
    after = fingerprint_dataset(dataset)

    assert before["sha256"] != after["sha256"]
    assert before["rows"]["q001"] == after["rows"]["q001"]
    assert before["rows"]["q002"] != after["rows"]["q002"]


def test_row_hash_ignores_key_order(tmp_path):
    first = tmp_path / "first.jsonl"
    second = tmp_path / "second.jsonl"
    first.write_text('{"id": "q001", "input": "a"}')
    second.write_text('{"input": "a", "id": "q001"}')

    assert fingerprint_dataset(first)["rows"] == fingerprint_dataset(second)["rows"]


def test_unchanged_environment_reports_no_changes():
    assert changed_environment_parts(ENVIRONMENT, json.loads(json.dumps(ENVIRONMENT))) == []


def test_changed_data_and_code_are_reported():
    changed_table = [
        {"databaseId": "duckdb_analytics", "tables": [{"table": "fact_visits", "rowCount": "86", "checksum": "2"}]}
    ]
    end = {**ENVIRONMENT, "nao": {"version": "dev", "commit": "b", "dirty": False}, "data": changed_table}

    assert changed_environment_parts(ENVIRONMENT, end) == ["nao", "data"]


def test_context_is_compared_by_its_hash():
    end = {**ENVIRONMENT, "context": {"sha256": "c", "files": []}}

    assert changed_environment_parts(ENVIRONMENT, end) == []


def test_missing_environment_reports_no_changes():
    assert changed_environment_parts(None, ENVIRONMENT) == []
