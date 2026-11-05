# Instrumentation Plan

Phase 0 of the [experiment plan](experiment_plan.md). Revised 2026-11-05. Nothing here is
implemented yet.

**Exit:** q016 can be reconstructed from its saved record alone, on arms A and B, and a
comparison between two runs refuses to pair them if anything except the arm differs.

---

## 1. Capture the system prompt

`Confirmed`: `AgentManager` already holds the final prompt in `_systemPrompt`
(`services/agent.ts:602`), including `RULES.md`, skill names and descriptions, and the
system prompt override. It just isn't returned.

1. Add `systemPrompt: this._systemPrompt` to `AgentRunResult` and return it from
   `generate()`. The field is additive, so other callers are unaffected.
2. Return it as `system_prompt` from `/api/evals/chat`. This stays in the fork, so no
   opt-in flag is needed.
3. Add `system_prompt` to `AgentAnswer` in `client.py`.
4. Save each distinct prompt once as `prompts/<sha256>.txt` beside the results, and store
   the hash on each record.
5. Store two hashes, because the prompt contains today's date (`system-prompt.tsx:87`):
    - `system_prompt_sha256`: the exact text;
    - `system_prompt_stable_sha256`: the same text with the date line removed.

Also record, because they shape the run but aren't in the prompt text:

- the date the run used, since "last 7 days" depends on it; run A and B interleaved within one day;
- the memory count, which must be 0 for the `test` user; the run fails otherwise;
- the tool manifest: tool names and a hash of their descriptions and input schemas.

---

## 2. Arm label, repetition, and block

```bash
nao evals --experiment metrics-tree-001 --arm B --block 1 --repeats 3 --arm-manifest arms.yaml
```

1. Add `--experiment`, `--arm`, `--block`, and `--repeats`. Each repetition is a separate
   agent call and a separate record; scores are never averaged in the file.
2. Add to each record: `experiment_id`, `arm`, `block`, `case_id`, `repetition`,
   `answer_id`, and `run_id`.
3. Check the label instead of trusting it. `arms.yaml` maps each arm to its expected
   context hash, and the run stops if the live project doesn't match:

    ```yaml
    A: { context_sha256: '...' }
    B: { context_sha256: '...' }
    ```

4. Shuffle case order within each block using a recorded seed, so time and provider drift
   don't line up with particular cases.
5. Interleave arms by block (A, B, B, A), because one backend serves one project folder at a time.
6. Add `nao evals rejudge <results.json> --judge-repeats 3`, which rescores saved answers
   without calling the agent. Each score records `answer_id` and `judge_repetition`, which
   separates agent variance from judge variance.
7. Keep every record, including errors. Errors stay labeled and count against the arm's
   completion rate.

---

## 3. Dataset, context, data, and code versions

The backend must report the context hash, since it reads its own project folder, which
may not be the folder the CLI runs from (the demo runs in Docker).

| Field              | How it is computed                                                                                                     | Why                                                                                                                               |
| ------------------ | ---------------------------------------------------------------------------------------------------------------------- | --------------------------------------------------------------------------------------------------------------------------------- |
| `dataset_sha256`   | Hash of the JSONL file, plus a hash per row                                                                            | Shows the cases didn't change                                                                                                     |
| `context_sha256`   | Hash of sorted path and content hashes for the project, excluding `tests/` and outputs                                 | Shows only the treatment changed                                                                                                  |
| `context_files`    | The per-file hashes                                                                                                    | Shows which file differs between arms                                                                                             |
| `data_fingerprint` | Row count and a content checksum per `fact_*` and `dim_*` table, plus seed CSV hash                                    | Shows the data didn't change; hashing the DuckDB file itself is unreliable because its bytes can change without the data changing |
| `kwwhat_commit`    | Commit and dirty flag of the dbt project                                                                               | Links the data to its models                                                                                                      |
| `nao_commit`       | Commit and dirty flag, passed into the image as a build argument because `.git` isn't copied in; plus the image digest | Pins the agent and tools                                                                                                          |
| Scorer versions    | Existing rubric hash, plus DeepEval metric class and version for the RAG metrics                                       | RAG metrics have no version today                                                                                                 |
| Models             | Exact agent and judge model ids and settings, including temperature                                                    | The judge sets no temperature today                                                                                               |
| Lockfile           | Hash of `cli/uv.lock`                                                                                                  | `pyproject.toml` allows `deepeval>=2.0`                                                                                           |

Controls:

1. Compute all of this at the start of the run and again at the end. The run is marked
   invalid if anything changed midway.
2. Add `--confirmatory`, which refuses to start on a dirty tree, on a dataset whose hash
   isn't in the preregistration, or without the arm manifest.
3. Add a compare step that pairs two arms only if every field above matches, apart from
   the context files the arm manifest says should differ. It reports the difference and stops otherwise.

---

## 4. Tool output

**Record everything; show the judge what counts as evidence.** The record and the judge's
context become two separate fields.

| Tool                                                                                 | In the record   | Shown to the judge | Reason                                                    |
| ------------------------------------------------------------------------------------ | --------------- | ------------------ | --------------------------------------------------------- |
| `execute_sql`                                                                        | Yes             | Yes, first 40 rows | Evidence; matches what the agent sees                     |
| `read`, `grep`                                                                       | Yes             | Yes                | Evidence                                                  |
| `execute_semantic_query`                                                             | Yes             | Yes                | Same shape as SQL; only active with a semantic layer mode |
| `read_query_result`                                                                  | Yes             | Yes                | The rows beyond the first 40                              |
| `task`                                                                               | Yes, with steps | Report only        | The main agent only sees the report                       |
| `execute_python`, `execute_sandboxed_code`, `web_search`, `mcp_call`, `query_app_db` | Yes             | Yes, if enabled    | Evidence                                                  |
| `load_skill`                                                                         | Yes             | No                 | Built-in instructions, not evidence                       |
| `list`, `search`                                                                     | Yes             | No                 | Paths only, as PR #1092 argued                            |
| Display and follow-up tools                                                          | Yes             | No                 | Not evidence                                              |

**Done (2026-11-05):**

1. The route returns every tool call with its `toolCallId`, in step order.
2. The judge's selection moved to `cli/nao_core/commands/evals/tool_calls.py`. Tools are
   excluded by name, so a new tool, including any MCP tool, reaches the judge by default.
   Calls that failed without output are skipped.
3. Query results show the agent's 40 rows and note how many were hidden;
   `read_query_result` keeps every row it fetched.
4. Each record saves `tool_calls` (everything, untruncated), `retrieval_context` (the exact
   text the judge received), and `context_read` (each file the agent read). Whether the
   tree or a skill was read is computed from `context_read` at analysis time.

The RAG scores change as a result, so the 16 older `evals_*.json` runs can't be pooled with
new ones. No baseline exists yet, so nothing is lost.

---

## 5. Cost

The study has a $200 budget, but only the agent's cost is recorded today. The judge's
cost isn't.

1. Record the judge's token usage and cost per metric call, from the response in
   `ClaudeJudge.generate`.
2. Add `--max-cost`, which stops the run once agent and judge cost together reach the
   limit. Cases already finished are saved, and the stop is recorded.
3. Add a ledger file that sums cost across all runs of the experiment, including the pilot
   and runs that errored.

---

## Order and verification

1. Tool output, since it is the largest validity risk. Done.
2. System prompt.
3. Version fields and the manifest.
4. Arm, repetition, block, and rejudge.
5. Cost tracking and `--max-cost`.
6. Compare step and `--confirmatory`.
7. Verify: run q016 on A and B and reconstruct both from their records; confirm a changed
   `RULES.md` makes the compare step refuse; confirm a mismatched `--arm` stops the run.

Tests go in `cli/tests/nao_core/commands/evals/`. Finish with `make lint` for the CLI and
`npm run lint` for the backend.

**Not included:** Braintrust export. Local records are enough, and they can be imported later.
