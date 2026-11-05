# Instrumentation Plan

Phase 0 of the [experiment plan](experiment_plan.md). Revised 2026-11-05. Nothing here is
implemented yet.

**Exit:** q016 can be reconstructed from its saved record alone, on arms A and B, and a
comparison between two runs refuses to pair them if anything except the arm differs.

---

## 1. Capture the system prompt

**Done (2026-11-05).** `generate()` now returns a `runContext` holding the final system
prompt, the number of memories injected, and every tool's name, description, and input
schema. `/api/evals/chat` returns it as `run_context`.

Each record stores, under `run_context`:

| Field                         | Meaning                                                                          |
| ----------------------------- | -------------------------------------------------------------------------------- |
| `system_prompt_sha256`        | Hash of the exact prompt                                                         |
| `system_prompt_stable_sha256` | Hash with the date replaced by `<date>`, so runs on different days compare equal |
| `prompt_date`                 | The date the prompt gave the agent, e.g. `Wednesday, November 5, 2026 (UTC)`     |
| `memory_count`                | Memories injected; any value above 0 fails the case as `context_error`, unjudged |
| `tool_manifest_sha256`        | Hash of all tool names, descriptions, and schemas, independent of order          |
| `tool_names`                  | The tools the agent had                                                          |

Each distinct prompt is saved once as `prompts/<sha256>.txt`, and each tool manifest as
`tool_manifests/<sha256>.json`, next to the results file. A backend test pins the date
line's format, because the stable hash depends on it.

Still to do: interleave arms A and B within one day, which belongs to step 2.

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

**Done (2026-11-05),** except the `--confirmatory` mode and the compare step, which come
after arms and repetition.

The backend describes its own environment at `GET /api/evals/environment`
(`services/eval-environment.service.ts`), because in Docker it reads `/app/kwwhat`, not the
CLI's folder. The CLI fetches it before the first case and after the last, and saves both
under `provenance` in the results file.

| Field                             | How it is computed                                                                                                                                           |
| --------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| `dataset.sha256`, `dataset.rows`  | Hash of the JSONL file, and of each row by id, so a comparison can tell which case changed                                                                   |
| `context.sha256`, `context.files` | Hash of every project file except `tests/` and hidden files, and each file's hash; covers `RULES.md`, skills, the tree, and synced `repos/` and `databases/` |
| `data`                            | Row count and a checksum (sum of a hash of every row) for each table of each DuckDB database, through the same SQL path the agent uses                       |
| `repos`                           | Commit and dirty flag of each linked repo with a local path, such as `/kwwhat`                                                                               |
| `nao`                             | The `APP_COMMIT` build argument in Docker; outside Docker, the checkout's commit and dirty flag                                                              |
| `packages`                        | Installed versions of `nao-core`, `deepeval`, `anthropic`, and `openai`                                                                                      |
| `config.rag`                      | Each RAG metric's DeepEval class and threshold                                                                                                               |
| `judge_settings` (per record)     | Temperature and max tokens; the Claude judge is now pinned to temperature 0                                                                                  |
| `run_context.model_call_settings` | The agent's temperature, top-p, top-k, and max output tokens                                                                                                 |

`environment_changed` lists any of `nao`, `context`, `repos`, or `data` that differed
between the start and the end of the run, and the CLI warns that those results aren't
comparable. A backend without the endpoint is recorded as `null`, and the run continues.

Not covered: the Docker image digest, which the container can't see. Record it with the
arm manifest in step 2.

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
2. System prompt. Done.
3. Version fields and the manifest. Done, except the compare step.
4. Arm, repetition, block, and rejudge.
5. Cost tracking and `--max-cost`.
6. Compare step and `--confirmatory`.
7. Verify: run q016 on A and B and reconstruct both from their records; confirm a changed
   `RULES.md` makes the compare step refuse; confirm a mismatched `--arm` stops the run.

Tests go in `cli/tests/nao_core/commands/evals/`. Finish with `make lint` for the CLI and
`npm run lint` for the backend.

**Not included:** Braintrust export. Local records are enough, and they can be imported later.
