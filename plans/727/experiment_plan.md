# Eval Experiment Plan

Roadmap for using `nao evals` to measure whether a context change improves the agent, for
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

Measure whether a change to the project context makes the agent's answers better.
The first experiment:

1. **Baseline:** run the evals on the current context.
2. **Treatment:** add a **metrics tree** to the context, change nothing else.
3. **Compare:** per-metric score differences between the two runs, with uncertainty.

The question is "is the metrics tree better, on which metrics, and by how much",
not whether a single run passes.

Scoring the same answer with both families shows where a change acts:

- **RAG triad:** did the agent pull more relevant context and stay grounded in it?
- **Reference-based:** did the final answer get closer to the expected one?

A change can improve one family and not the other; both are reported.

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
- **Headroom cases:** questions a metrics tree could plausibly improve (metric
  relationships, drivers of a top-level metric, "why did X change"). Cases the
  baseline already answers perfectly cannot show an improvement.
- **Frozen before the baseline:** the dataset is versioned before the baseline run and
  not edited between arms; any change invalidates the comparison.
- **Optional expected context:** which context each case should use (semantic model,
  `RULES.md`), enabling a later context-recall check.
- **Unverified facts** are either verified via SQL or removed from references
  (currently `q008`: "4 ports over 3 days", "ConnectorLockFailure on 1 port").

**Exit:** reviewed, versioned dataset with provenance per case; coverage of lookup,
context-dependent, and headroom cases.

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

- **Arms:** A = current context (baseline), B = current context + metrics tree.
- **Held fixed:** cases, dataset version, data snapshot, chat model, judge model,
  rubric versions, `nao` build.
- **Paired design:** every case runs in both arms and is compared case by case.
- **Repetitions:** several runs per case per arm, to separate agent and judge
  variance from a real effect.
- **Decided before running:** which metrics define "better", the smallest
  improvement worth keeping the metrics tree for, and how per-case results are
  combined.

**Exit:** baseline and metrics-tree results compared with uncertainty, and a
keep-or-drop decision on the metrics tree.

---

## Open Decisions

- What the metrics tree contains and where it lives in the context (e.g. a section
  of the semantic model, or a separate document the agent reads).
- Which metrics count as "better", and the minimum improvement that matters.

- Where the canonical dataset lives: `example/tests/evals/` in the fork, the demo's
  `chat-bi/tests/evals/`, or one copied from the other.
- Whether provenance fields live in the JSONL rows (loader ignores unknown fields) or
  in a separate datasheet.
- Human labeling: who labels, and how many answers per metric.
