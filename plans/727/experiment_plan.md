# Eval Experiment Plan

Roadmap for making `nao evals` trustworthy enough to compare context changes, for
[getnao/nao#727](https://github.com/getnao/nao/issues/727).

Builds on the [Correctness plan](correctness_plan.md) and the
[RAG triad plan](rag_triad_plan.MD). Both metric families already run **in tandem**:
every eval case gets one agent answer, and all five metrics score that same answer.

| Family          | Metrics                                            | Judges against                                       |
| --------------- | -------------------------------------------------- | ---------------------------------------------------- |
| RAG triad       | Faithfulness, ContextualRelevancy, AnswerRelevancy | retrieval context from tool calls, input             |
| Reference-based | Correctness, Completeness                          | `expected_output` (Completeness also sees the input) |

---

## Objective

Detect **context drift** that deterministic SQL tests miss: the agent returns a
numerically correct result while ignoring configured context (`RULES.md`, semantic
definitions, terminology, framing).

Scoring the same answer with both families makes their disagreements diagnostic:

- context fine, answer wrong → answer drifted from what the context supports;
- answer right, context irrelevant or unsupported → the answer is right for the wrong reasons;
- both fail → context change broke the agent.

---

## Order of Work

**Dataset → scorers → experiment design.** Each step depends on the one before:
scorers cannot be validated against unreliable references, and experiments cannot be
interpreted with unvalidated scorers.

### Phase 0: Make RAG scores reviewable

The results file stores answers and scores but not the retrieval context the RAG
metrics were judged on, so Faithfulness and ContextualRelevancy cannot be reviewed or
validated.

- Save `retrieval_context` per case in `evals_results_<timestamp>.json`.

**Exit:** every RAG score in a results file can be checked against exactly what the
judge saw.

### Phase 1: Dataset (`braintrust-build-eval-dataset`)

The dataset serves both families.

- **References (Correctness, Completeness):** every `expected_output` matches the
  current data snapshot. Numeric facts are traced to a deterministic SQL test in
  `kwwhat/demo/chat-bi/tests/*.yml` and its latest `nao test` result.
- **Provenance:** each case records where its reference came from and which data
  snapshot it matches, so stale references are detectable (e.g. the plan's
  4 decommissioned ports / 99.71% uptime were stale against current data: 2 / 99.87%).
- **Context-dependent cases (RAG):** questions whose answer depends on configured
  context (undefined metrics, terminology, `RULES.md` rules), not just number lookups.
- **Drift cases:** cases that should fail when context is removed or broken, so the
  evals have room to detect a regression.
- **Optional expected context:** which context each case should use (semantic model,
  `RULES.md`), enabling a later context-recall check.
- **Unverified facts** are either verified via SQL or removed from references
  (currently `q008`: "4 ports over 3 days", "ConnectorLockFailure on 1 port").

**Exit:** reviewed, versioned dataset with provenance per case; coverage of lookup,
context-dependent, and drift cases.

### Phase 2: Scorers (`braintrust-write-eval-scorer`, `braintrust-validate-eval-scorer`)

All five metrics are validated, not only the reference-based ones.

- Review the Correctness and Completeness rubrics (evaluation steps, handling of
  refusals, clarifying questions, extra detail).
- Treat `serialize_tool_result` as part of the RAG scorers: it limits context to
  `read`, `execute_sql`, `grep` and truncates SQL results to 20 rows.
- Collect human pass/fail labels on saved agent answers and measure judge agreement.
- Calibrate every threshold; all are currently placeholders:

    | Metric              | Current threshold |
    | ------------------- | ----------------: |
    | Faithfulness        |               0.7 |
    | ContextualRelevancy |               0.5 |
    | AnswerRelevancy     |               0.7 |
    | Correctness         |               0.5 |
    | Completeness        |               0.5 |

- Measure run-to-run variance of judge scores on identical answers.

**Exit:** each metric has a calibrated threshold, a known agreement rate with human
labels, and documented blind spots.

### Phase 3: Experiment design (`braintrust-design-eval-experiment`)

- Paired design: same cases, same data snapshot, one variable changed (e.g. a
  `RULES.md` edit, semantic model change, chat model).
- Repetitions per case to separate agent and judge variance from real effects.
- Pre-specified analysis: per-metric deltas, RAG vs. reference disagreement table,
  release rule (`braintrust-define-eval-release-gate`) before any CI gating.

**Exit:** a controlled comparison of a real context change, reported with
uncertainty.

---

## Open Decisions

- Where the canonical dataset lives: `example/tests/evals/` in the fork, the demo's
  `chat-bi/tests/evals/`, or one copied from the other.
- Whether provenance fields live in the JSONL rows (loader ignores unknown fields) or
  in a separate datasheet.
- Human labeling: who labels, and how many answers per metric.
