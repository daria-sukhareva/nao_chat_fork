# Golden Dataset Audit

Phase 1 of the [experiment plan](experiment_plan.md). Mode: **audit** of
`example/tests/evals/golden_dataset.jsonl` (8 cases) plus a **draft** of proposed
additions. The dataset file itself is unchanged.

Tags: `Confirmed` (read from an artifact), `Assumed` (safe default, override it),
`Needs decision`, `Not yet measurable`.

Evidence read:

- `kwwhat/demo/chat-bi/RULES.md` and `agent_instructions.md` (configured context);
- `kwwhat/models/semantic/semantic_models.yml` (defined metrics);
- `kwwhat/demo/chat-bi/tests/*.yml` (6 SQL tests) and `tests/outputs/results_*.json`
  (latest: 2026-09-25);
- `kwwhat/demo/chat-bi/tests/outputs/evals_*.json` (15 earlier RAG triad runs, 14 with scores).

---

## 1. Population the set appears to represent

> Single-turn questions from an EV charging network operator about network
> reliability (ports, uptime, downtime, error codes, visits), asked against the
> kwwhat demo project, where the answer depends on both the data and the configured
> context (`RULES.md`, semantic model).

`Assumed`: no production traces exist yet, so the population is inferred from the SQL
tests and the demo context, not measured. Stratum frequencies are therefore
`Not yet measurable`.

**Construct:** does the final answer follow configured context (definitions,
terminology, rules) while staying correct and grounded? **Non-use:** exact numeric
correctness (owned by `nao test` SQL tests), chart rendering, multi-turn behavior.

---

## 2. Coverage matrix

The objective is comparing context variants: the baseline against the baseline plus a
metrics tree. A case is useful only if its score can differ between the two. Every
rule and definition the context controls should have at least one case that fails
when the agent ignores it, and the metrics tree needs cases it could improve.

| Stratum                                                                     | Source of expected behavior     | Covered by                                                             | Status                                      |
| --------------------------------------------------------------------------- | ------------------------------- | ---------------------------------------------------------------------- | ------------------------------------------- |
| Numeric lookup, full history                                                | SQL tests                       | q004, q005, q006, q007                                                 | `Confirmed` covered                         |
| Semantic definition (troubled success)                                      | semantic model                  | q003                                                                   | `Confirmed` covered                         |
| Explanation / diagnosis                                                     | SQL test + agent answer         | q008                                                                   | covered, reference partly unverified        |
| Undefined metric → say so, offer closest                                    | RULES: "Do not make up metrics" | q002                                                                   | `Confirmed` covered                         |
| Terminology: never "session"                                                | RULES                           | none                                                                   | **gap**                                     |
| Default window: last 7 days                                                 | RULES                           | none (all cases say "full history" or are undated)                     | **gap**                                     |
| Rates as % with pp change                                                   | RULES                           | none checked; q005/q006 answers are percentages but references omit pp | **gap**                                     |
| "Metrics at a glance" table first                                           | RULES                           | none                                                                   | **gap**                                     |
| Primary reliability rates (first-attempt success, troubled success, failed) | semantic model                  | none                                                                   | **gap**                                     |
| Negative: ambiguous question → ask                                          | general                         | none                                                                   | **gap**                                     |
| Negative: out of scope → decline                                            | general                         | none                                                                   | **gap**                                     |
| Metric relationships / drivers (what the metrics tree adds)                 | metrics tree (not written yet)  | none                                                                   | **gap**: no headroom for the experiment     |
| Brand palette in charts                                                     | RULES                           | none                                                                   | `Not yet measurable` with text-only metrics |

Four of the eight cases are numeric lookups that `nao test` already covers
deterministically. Only q002 directly tests a `RULES.md` rule.

---

## 3. Per-item audit

| id   | Reference provenance                                    | Findings                                                                                                                                                                                                                                                                                                                                              |
| ---- | ------------------------------------------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| q001 | **Unknown**: no SQL test or run output backs it         | "CH001 was the only functional charger" cannot be traced. Question is a judgment ("wrong port"), so a single gold string is fragile. Never run in any saved eval output.                                                                                                                                                                              |
| q002 | Expert-authored (plan)                                  | Terminology: reference says **uptime**; the semantic model has semantic model `uptime`, measure `uptime_average`, metric `average_uptime` ("Average uptime"). `Needs decision`: which names count as correct. Historically fails RAG (ContextualRelevancy 0.0 in 4/4 runs) while Correctness passed in the plan: the most diagnostic case in the set. |
| q003 | User-authored from SQL test `troubled_error_code_check` | Numbers verified (WeakSignal, 1 visit). Uses "visit", consistent with the terminology rule.                                                                                                                                                                                                                                                           |
| q004 | SQL test `decommissioned_ports_check`                   | Verified (2). Plan's reference (4) was stale.                                                                                                                                                                                                                                                                                                         |
| q005 | SQL test `network_reliability_uptime`                   | Verified (99.87%). Plan's reference (99.71%) was stale. Reference omits the glance table and pp change that `RULES.md` requires (see finding F2).                                                                                                                                                                                                     |
| q006 | SQL test `lately_snapshot`                              | Verified (99.87%, 73.05%). Same F2 issue. Test name says "lately" but prompt says full history.                                                                                                                                                                                                                                                       |
| q007 | SQL test `total_ports`                                  | Verified (4), but the value changed 2 → 4 between the 2026-09-23 and 2026-09-25 runs.                                                                                                                                                                                                                                                                 |
| q008 | SQL test `why_downtime_check` + agent answer            | Minutes verified (1,080 / 333). "4 ports over 3 days" and "ConnectorLockFailure on 1 port" come **only from the agent's own answer**.                                                                                                                                                                                                                 |

---

## 4. Findings

**F1. Every label has one author and no agreement measure.** All references were
written by one person; no calibration sample was double-labeled. The label error rate
is `Not yet measurable`, so no score difference can yet be shown to exceed it.

**F2. References conflict with the configured rules (systematic).** `RULES.md` says
rate/uptime answers start with a "metrics at a glance" table and include pp change.
The references for q005 and q006 are single sentences without either. Correctness
penalizes "unsupported additions", so an agent that **follows** `RULES.md` loses
points, and an agent that ignores it scores better. This is the "script" pattern:
the reference records what the author expected, not what the configured context
requires. A context change that makes the agent follow its rules more closely could
score as worse.

**F3. Rule compliance cannot be expressed as one gold string.** Terminology, glance
table, pp change and default window are properties of an answer, not its wording.
They belong in a per-case **constraint list** judged separately, not folded into
`expected_output`.

**F4. Part of one reference comes from the system under test.** q008's unverified
facts were copied from an agent answer. A reference derived from the evaluated
system rewards repeating that system's mistakes.

**F5. References go stale when the data changes.** Three of eight references
changed or were found stale in one week (q004, q005, q007). Nothing records which
data snapshot a reference matches.

**F6. Earlier runs show large score swings on identical questions.** Across 14
earlier runs of the decommissioned-ports question, ContextualRelevancy ranged
0.06–1.0 and Faithfulness 0.17–1.0; uptime's ContextualRelevancy sat at 0.30–0.62
around its 0.5 threshold, flipping pass/fail. The runs are not controlled (code, data
and context changed between them), so this is a warning sign rather than a
measurement. Headroom and difficulty spread are `Not yet measurable` until Phase 2
runs repeat the same answers. For the metrics-tree experiment this matters twice:
cases already at ceiling in the baseline cannot improve, and swings this large would
hide a real improvement unless each case is repeated.

**F7. No dev/test separation.** With 8 cases a split is not meaningful yet.
`Assumed`: treat the whole set as dev until it grows; count every run used to tune a
threshold or rubric.

---

## 5. Proposed additions (draft, not applied)

Each fills a gap in section 2. `constraints` is a proposed optional field (F3): the
loader already ignores unknown fields, so adding it does not break current runs, but
nothing scores it yet (`Needs decision`, see section 7).

| id   | Stratum                | input                                                   | expected_output                                                                                              | constraints                                                                                       |
| ---- | ---------------------- | ------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------ | ------------------------------------------------------------------------------------------------- |
| q009 | Terminology            | How many charging sessions failed?                      | States the number of failed visits.                                                                          | Never uses the word "session"; uses "visit" or "charge attempt".                                  |
| q010 | Default window         | What is our first attempt success rate?                 | Reports first attempt success rate for the last 7 days.                                                      | States the window is the last 7 days; percentage; pp change vs. prior 7 days; glance table first. |
| q011 | Primary rate + pp      | What is the troubled success rate for the full history? | Troubled success rate as a percentage, defined as successful visits needing more than one attempt.           | Percentage; uses the semantic model definition; glance table first.                               |
| q012 | Undefined metric (2nd) | What is our mean time between failures?                 | Says MTBF is not defined in the semantic model and names the closest defined metric.                         | Does not compute an invented metric.                                                              |
| q013 | Negative: ambiguous    | How are we doing?                                       | Asks which metric or period the user means, or gives the primary reliability metrics with the window stated. | Does not invent metrics.                                                                          |
| q014 | Negative: out of scope | What will energy prices be next month?                  | Says this is outside the available data.                                                                     | No fabricated numbers.                                                                            |
| q015 | Metric drivers         | What drives our overall charging reliability?           | Depends on the metrics tree (`Needs decision`).                                                              | Names the drivers from the metrics tree, not invented ones.                                       |

q015 stands for a set of metrics-tree cases; their references can only be written
once the tree exists, and must be written **before** the treatment run. Values for
q010 and q011 need SQL tests first (`Needs decision`): the dataset's
latest date determines whether "last 7 days" returns data at all.

---

## 6. Datasheet (skeleton)

- **Motivation:** measure whether a context change (first: a metrics tree) improves
  final answers compared with a baseline.
- **Composition:** 8 cases (5 SQL-backed lookups, 1 definition, 1 refusal,
  1 explanation); proposed +6 rule and negative cases.
- **Collection:** expert-authored from SQL tests, `RULES.md`, and the semantic model;
  no production traces.
- **Labeling:** one author; no agreement measured (F1).
- **Provenance fields (proposed per row):** `source` (sql test name / expert / plan),
  `data_snapshot` (date of the `nao test` result used), `label_provenance`
  (verified_sql / expert / agent_derived), `stratum`.
- **Recommended use:** dev set for calibrating the five metrics; paired baseline vs.
  treatment comparisons of context changes.
- **Discouraged use:** CI gate or model comparison claims before Phase 2 calibration.
- **Refresh:** re-check every SQL-backed reference against the latest `nao test`
  results before each eval run (F5).

---

## 7. Decisions needed

1. **Metrics-tree cases:** which questions the metrics tree should improve, and
   their references, written before the treatment run.
2. **Constraints field (F3):** add `constraints` to the JSONL schema and score it
   with a third GEval rubric ("Rule compliance"), or fold rule requirements into
   `expected_output`? Recommended: the separate field, so Correctness stays about
   facts and rule compliance is measured on its own.
3. **q005/q006 references (F2):** rewrite them to include the glance table and
   pp change, or move those requirements to `constraints`?
4. **q001:** find a SQL-backed source for "CH001 was the only functional charger",
   or drop the case.
5. **q008:** verify "4 ports over 3 days" and "ConnectorLockFailure on 1 port" with
   SQL, or remove them from the reference.
6. **Uptime naming (q002):** accept `uptime`, `average_uptime`, or "Average uptime"?
7. **Second labeler:** who can independently label a calibration sample (F1)?
