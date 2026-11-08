import json
from typing import Any

AGENT_VISIBLE_QUERY_ROWS = 40
QUERY_RESULT_TOOLS = frozenset({"execute_sql", "execute_semantic_query", "read_query_result"})
NON_EVIDENCE_TOOLS = frozenset(
    {
        "clarification",
        "display_chart",
        "display_map",
        "list",
        "load_skill",
        "mcp_connect",
        "search",
        "story",
        "suggest_follow_ups",
        "write",
    }
)


def build_retrieval_context(tool_calls: list[dict]) -> list[str]:
    """Serialize the tool output the agent saw as evidence, which is exactly what the RAG judge receives.

    Tools are excluded by name rather than included, so a new content-bearing tool reaches the judge by default.
    """
    return [
        serialize_tool_result(call["toolName"], call.get("args") or {}, call["output"])
        for call in tool_calls
        if _is_evidence(call)
    ]


def list_files_read(tool_calls: list[dict]) -> list[str]:
    paths = {call["args"]["file_path"] for call in tool_calls if _is_successful_read(call)}
    return sorted(paths)


def serialize_tool_result(tool_name: str, args: dict, output: Any) -> str:
    if tool_name == "read":
        return _serialize_read(args, output)
    if tool_name in QUERY_RESULT_TOOLS:
        return _serialize_query_result(tool_name, output)
    if tool_name == "task":
        return _serialize_task(output)
    return f"[{tool_name}]\n{json.dumps(output, indent=2, default=str)}"


def _is_evidence(call: dict) -> bool:
    return call["toolName"] not in NON_EVIDENCE_TOOLS and call.get("output") is not None


def _is_successful_read(call: dict) -> bool:
    return call["toolName"] == "read" and call.get("output") is not None and "file_path" in (call.get("args") or {})


def _serialize_read(args: dict, output: Any) -> str:
    path = args.get("file_path", "unknown")
    content = output.get("content", "") if isinstance(output, dict) else str(output)
    return f"[File: {path}]\n{content}"


def _serialize_query_result(tool_name: str, output: Any) -> str:
    columns = output.get("columns", []) if isinstance(output, dict) else []
    rows = output.get("data", []) if isinstance(output, dict) else []
    visible_rows = rows if tool_name == "read_query_result" else rows[:AGENT_VISIBLE_QUERY_ROWS]

    header = " | ".join(str(column) for column in columns)
    body = "\n".join(_format_row(row, columns) for row in visible_rows)
    text = f"[SQL result]\nColumns: {', '.join(columns)}\n{header}\n{body}"

    hidden_rows = len(rows) - len(visible_rows)
    if hidden_rows > 0:
        text += f"\n({hidden_rows} more rows not shown)"
    return text


def _format_row(row: Any, columns: list[str]) -> str:
    if isinstance(row, dict):
        return " | ".join(str(row.get(column, "")) for column in columns)
    return " | ".join(str(value) for value in row)


def _serialize_task(output: Any) -> str:
    report = output.get("report", "") if isinstance(output, dict) else str(output)
    return f"[Subagent report]\n{report}"
