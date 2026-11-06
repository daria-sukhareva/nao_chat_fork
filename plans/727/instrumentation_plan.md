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

**Done (2026-11-06).**

```bash
nao evals --experiment metrics-tree-001 --arm-manifest /kwwhat/demo/chat-bi/arm.json --block 1 --repeats 3
```

1. `--experiment`, `--arm-manifest`, `--block`, `--repeats`, and `--seed`. Each repetition is a
   separate agent call and a separate record; scores are never averaged in the file.
2. Each record has `run_id`, `experiment_id`, `arm`, `block`, `id` (the case), `repetition`,
   `position` (its place in the run's order), `answer_id`, and `started_at`. The file's `run`
   section repeats the labels and adds the seed, the full order, and the arm manifest.
3. The label is checked, not trusted. There is no `--arm` flag: `build-arm.sh` writes
   `arm.json` next to the arm, with the arm, the study commit, and each file's hash, and the
   run takes its arm from there. Before the first agent call, every file in the manifest is
   compared with the context the backend serves. The dataset is compared with the local
   project instead, because the backend's fingerprint skips `tests/`. Any difference stops the run.
   This replaces the `arms.yaml` sketched earlier, which would have needed each arm's context
   hash copied in by hand after every rebuild.
4. Experiment runs shuffle cases and repetitions together with a seed, so drift in the
   provider's latency, load or serving during a block lands randomly on cases instead of always
   on the last ones in the dataset. The seed is drawn at random unless `--seed` is passed, and it
   is recorded either way. Unlabeled runs keep the dataset order. See the
   [runbook](running_evals.md#why-the-order-is-shuffled).
5. Arms are interleaved by block (A, B, B, A). That is a procedure, not code: one backend serves
   one project folder at a time, so each block is one run against one built arm. See the
   [runbook](running_evals.md#runs-that-count).
6. `nao evals rejudge <results.json> --judge-repeats 3` rescores saved answers without calling
   the agent. Each judgment records `answer_id` and `judge_repetition`, which separates agent
   variance from judge variance. It writes a separate `rejudge_results_*.json` that points to the
   source file by path and hash. Files from before answer IDs existed get an ID made from the
   file hash and the record's position. With the judge at temperature 0, judge repetitions
   measure only the provider's leftover nondeterminism, so a spread near zero is the expected
   result, not a sign the command is broken.
7. Every record is kept, including errors. Errors stay labeled and count against the arm's
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

### Provenance per case

The run-level hashes show that a dataset changed. Each row also records where its
reference came from, so a stale or self-derived reference can be found. The loader ignores
these fields, so they never affect scoring.

| Field              | Meaning                                                                                     |
| ------------------ | ------------------------------------------------------------------------------------------- |
| `source`           | How the reference was established: `sql_verified`, `sql_test`, `expert`, or `agent_derived` |
| `label_provenance` | Who proposed the reference, who accepted it, and how and when it was checked                |
| `data_fingerprint` | Row count and checksum of the table the reference was checked against                       |
| `notes`            | Anything a reviewer needs to judge the reference, such as a confound                        |

Example, q018 (2026-11-05):

| Field              | Value                                                                                                                                                         |
| ------------------ | ------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `source`           | `sql_verified`                                                                                                                                                |
| `label_provenance` | Diagnosis proposed by the agent in `evals_results_20261105_211639.json`, accepted by the author, and checked claim by claim with SQL on 2026-11-05            |
| `data_fingerprint` | `fact_visits`: 139 rows, checksum `1300261096287823253527`                                                                                                    |
| `notes`            | On Oct 4–5, charger and authentication split the visits identically; the charger explanation is preferred because every failure carries a hardware error code |

When the data changes, a `data_fingerprint` that no longer matches the run's `data`
fingerprint shows that the reference needs rechecking. A reference proposed by the agent
counts as `sql_verified` only when every required claim was checked, and claims that weren't
checked are left out of it.

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
