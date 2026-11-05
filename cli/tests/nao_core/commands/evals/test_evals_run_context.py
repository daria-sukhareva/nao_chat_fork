from nao_core.commands.evals.run_context import describe_run_context, save_run_context_files, stable_prompt

TOOLS = [
    {"name": "read", "description": "Read a file.", "inputSchema": {"type": "object"}},
    {"name": "execute_sql", "description": "Run SQL.", "inputSchema": {"type": "object"}},
]


def make_raw(date: str = "Wednesday, November 5, 2026 (UTC)", rules: str = "Never say session.", tools=TOOLS) -> dict:
    prompt = f"You are nao.\nToday's date is **{date}**.\nYou have access to files.\n{rules}"
    return {"system_prompt": prompt, "memory_count": 0, "tools": tools}


def test_prompt_date_is_extracted():
    assert describe_run_context(make_raw()).prompt_date == "Wednesday, November 5, 2026 (UTC)"


def test_stable_hash_ignores_the_date_but_the_exact_hash_does_not():
    today = describe_run_context(make_raw())
    tomorrow = describe_run_context(make_raw(date="Thursday, November 6, 2026 (UTC)"))

    assert today.system_prompt_stable_sha256 == tomorrow.system_prompt_stable_sha256
    assert today.system_prompt_sha256 != tomorrow.system_prompt_sha256


def test_stable_hash_changes_when_the_rules_change():
    before = describe_run_context(make_raw())
    after = describe_run_context(make_raw(rules="Never say session.\nRead docs/metrics_tree.md."))

    assert before.system_prompt_stable_sha256 != after.system_prompt_stable_sha256


def test_stable_prompt_replaces_only_the_date():
    assert stable_prompt("Today's date is **Monday, May 4, 2026**. Rest.") == "Today's date is **<date>**. Rest."


def test_tool_manifest_hash_ignores_tool_order():
    in_order = describe_run_context(make_raw())
    reversed_order = describe_run_context(make_raw(tools=list(reversed(TOOLS))))

    assert in_order.tool_manifest_sha256 == reversed_order.tool_manifest_sha256
    assert in_order.tool_names == ["execute_sql", "read"]


def test_tool_manifest_hash_changes_with_a_description():
    changed = [{**TOOLS[0], "description": "Read any file."}, TOOLS[1]]

    assert (
        describe_run_context(make_raw()).tool_manifest_sha256
        != describe_run_context(make_raw(tools=changed)).tool_manifest_sha256
    )


def test_missing_run_context_yields_empty_hashes():
    context = describe_run_context({})

    assert context.system_prompt_sha256 is None
    assert context.tool_manifest_sha256 is None
    assert context.memory_count is None


def test_each_distinct_prompt_and_manifest_is_saved_once(tmp_path):
    raw = make_raw()
    context = describe_run_context(raw)

    save_run_context_files([raw, raw, {}], tmp_path)

    assert [path.name for path in (tmp_path / "prompts").iterdir()] == [f"{context.system_prompt_sha256}.txt"]
    assert (tmp_path / "prompts" / f"{context.system_prompt_sha256}.txt").read_text() == raw["system_prompt"]
    assert [path.name for path in (tmp_path / "tool_manifests").iterdir()] == [f"{context.tool_manifest_sha256}.json"]
