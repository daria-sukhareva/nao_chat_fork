import hashlib
import json
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

PROMPT_DATE_PATTERN = re.compile(r"Today's date is \*\*(?P<date>[^*\n]+)\*\*")
PROMPT_DATE_PLACEHOLDER = "Today's date is **<date>**"
PROMPTS_FOLDER = "prompts"
TOOL_MANIFESTS_FOLDER = "tool_manifests"


@dataclass
class RunContext:
    """What the agent was given besides the question, identified by content hashes."""

    system_prompt_sha256: str | None = None
    system_prompt_stable_sha256: str | None = None
    prompt_date: str | None = None
    memory_count: int | None = None
    tool_manifest_sha256: str | None = None
    tool_names: list[str] = field(default_factory=list)
    model_call_settings: dict[str, Any] = field(default_factory=dict)


def describe_run_context(raw: dict[str, Any]) -> RunContext:
    """The stable hash ignores the date line, so prompts from different days compare equal when nothing else changed."""
    prompt = raw.get("system_prompt")
    tools = _sorted_tools(raw.get("tools") or [])
    date_match = PROMPT_DATE_PATTERN.search(prompt) if prompt else None
    return RunContext(
        system_prompt_sha256=_sha256(prompt) if prompt else None,
        system_prompt_stable_sha256=_sha256(stable_prompt(prompt)) if prompt else None,
        prompt_date=date_match.group("date") if date_match else None,
        memory_count=raw.get("memory_count"),
        tool_manifest_sha256=_sha256(_canonical_json(tools)) if tools else None,
        tool_names=[tool["name"] for tool in tools],
        model_call_settings=raw.get("call_settings") or {},
    )


def stable_prompt(prompt: str) -> str:
    return PROMPT_DATE_PATTERN.sub(PROMPT_DATE_PLACEHOLDER, prompt)


def save_run_context_files(raw_contexts: list[dict[str, Any]], output_dir: Path) -> None:
    """Writes each distinct prompt and tool manifest once, named by the hash the records refer to."""
    for raw in raw_contexts:
        context = describe_run_context(raw)
        if context.system_prompt_sha256:
            _write_once(output_dir / PROMPTS_FOLDER / f"{context.system_prompt_sha256}.txt", raw["system_prompt"])
        if context.tool_manifest_sha256:
            manifest = _canonical_json(_sorted_tools(raw["tools"]))
            _write_once(output_dir / TOOL_MANIFESTS_FOLDER / f"{context.tool_manifest_sha256}.json", manifest)


def _sorted_tools(tools: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return sorted(tools, key=lambda tool: tool["name"])


def _canonical_json(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"))


def _sha256(text: str) -> str:
    return hashlib.sha256(text.encode()).hexdigest()


def _write_once(path: Path, content: str) -> None:
    if path.exists():
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content)
