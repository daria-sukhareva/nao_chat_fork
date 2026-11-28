from nao_core.commands.evals.tool_calls import (
    AGENT_VISIBLE_QUERY_ROWS,
    build_retrieval_context,
    list_files_read,
    serialize_tool_result,
)


def make_call(tool_name: str, output, args: dict | None = None) -> dict:
    return {"toolName": tool_name, "toolCallId": f"call_{tool_name}", "args": args or {}, "output": output}


def query_output(row_count: int) -> dict:
    return {"columns": ["n"], "data": [{"n": index} for index in range(row_count)]}


def test_navigation_and_instruction_tools_never_reach_the_judge():
    calls = [
        make_call("list", [{"path": "docs"}]),
        make_call("search", [{"path": "docs/tree.md"}]),
        make_call("load_skill", {"name": "excel", "body": "How to build a workbook"}),
        make_call("suggest_follow_ups", {"suggestions": ["Next?"]}),
    ]

    assert build_retrieval_context(calls) == []


def test_unknown_tools_reach_the_judge_by_default():
    context = build_retrieval_context([make_call("mcp_call", {"text": "42 open tickets"})])

    assert len(context) == 1
    assert "42 open tickets" in context[0]


def test_failed_calls_without_output_are_skipped():
    assert build_retrieval_context([make_call("execute_sql", None)]) == []


def test_query_results_show_the_rows_the_agent_saw():
    text = serialize_tool_result("execute_sql", {}, query_output(AGENT_VISIBLE_QUERY_ROWS + 5))

    assert f"\n{AGENT_VISIBLE_QUERY_ROWS - 1}\n" in text
    assert f"\n{AGENT_VISIBLE_QUERY_ROWS}\n" not in text
    assert text.endswith("(5 more rows not shown)")


def test_semantic_queries_are_serialized_like_sql():
    assert serialize_tool_result("execute_semantic_query", {}, query_output(2)) == serialize_tool_result(
        "execute_sql", {}, query_output(2)
    )


def test_read_query_result_keeps_every_row_it_fetched():
    text = serialize_tool_result("read_query_result", {}, query_output(AGENT_VISIBLE_QUERY_ROWS + 5))

    assert "more rows not shown" not in text


def test_rows_as_lists_are_serialized():
    text = serialize_tool_result("execute_sql", {}, {"columns": ["a", "b"], "data": [[1, 2]]})

    assert text.endswith("a | b\n1 | 2")


def test_subagents_contribute_only_their_report():
    output = {"report": "Uptime is defined in fact_uptime.", "steps": [{"tool": "read", "summary": "secret.md"}]}

    assert serialize_tool_result("task", {}, output) == "[Subagent report]\nUptime is defined in fact_uptime."


def test_list_files_read_returns_each_read_file_once_in_order():
    calls = [
        make_call("read", {"content": "tree"}, {"file_path": "docs/metrics_tree.md"}),
        make_call("read", {"content": "skill"}, {"file_path": "agent/skills/root-cause-analysis.md"}),
        make_call("read", {"content": "tree"}, {"file_path": "docs/metrics_tree.md"}),
        make_call("read", None, {"file_path": "missing.md"}),
        make_call("grep", {"matches": []}, {"pattern": "uptime"}),
    ]

    assert list_files_read(calls) == ["agent/skills/root-cause-analysis.md", "docs/metrics_tree.md"]
