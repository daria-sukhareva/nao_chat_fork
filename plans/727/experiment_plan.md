# Eval Experiment Plan

Plan for a public whitepaper on measuring context changes with `nao evals`, for
[getnao/nao#727](https://github.com/getnao/nao/issues/727). Revised 2026-11-05. This is
a map, not a contract: it goes stale when the agent, data, or context changes.

Builds on the [Correctness plan](https://github.com/getnao/nao/blob/4b02276f449ef35256cf9b04b06afcceb67b1d24/plans/727/correctness_plan.md)
and the [RAG triad plan](https://github.com/getnao/nao/blob/4b02276f449ef35256cf9b04b06afcceb67b1d24/plans/727/rag_triad_plan.MD)
from [PR #1092](https://github.com/getnao/nao/pull/1092). The PR has no maintainer reply
to its design questions, so nothing here may imply that nao endorses this work.

Tags: `Confirmed` (read from an artifact), `Assumed` (safe default, override it),
`Needs decision`, `Not yet measurable`.

---

## Claims

The paper makes two claims, in dependency order. The second is uninterpretable without
the first.

- **C1, measurement validity:** these instruments detect a known context degradation
  and stay quiet when nothing changed.
- **C2, effect:** on this project, for an agent that already has a generic root cause
  skill, adding the metrics tree, the `count-active-drivers` skill, and a rule pointing to
  the tree changes the quality of root cause answers by a stated amount, with uncertainty.

**Construct** `Needs decision`: quality of root cause answers. The issue and PR define
the broader construct as following configured context even when the number is right,
so the paper must say which one each result speaks to.

**Population** `Assumed`: single-turn questions from an EV network operator against the
kwwhat demo project.

- **H3, secondary hypothesis:** paired changes in the RAG triad track paired changes in
  Correctness and Completeness. This tests the assumption behind the referenceless plan in
  PR #1092; it is not taken as given.

**Non-claims:** other projects, other domains, real operator traffic (the seed data is
synthetic and covers 14 days), multi-turn use, chart rendering, or any part of the treatment on
its own. Exact numeric correctness stays with `nao test`.

---

## Arms

| Arm | Context                                                                           | Purpose                                    |
| --- | --------------------------------------------------------------------------------- | ------------------------------------------ |
| A   | Current context + root cause skill                                                | Baseline                                   |
| B   | Current context + root cause skill + metrics tree + `count-active-drivers` + rule | Treatment; the bundle is what C2 speaks to |
| N   | A, run as a separate block                                                        | Null control: false-positive rate for C1   |
| D   | A with known degradations (rules removed, a definition corrupted)                 | Positive control: sensitivity for C1       |

`plans/727/skills/root-cause-analysis.md` is shared by all arms and is the only root cause
procedure; it was moved out of the tree with its domain and tree references removed. C2
therefore measures what the tree's domain structure adds beyond a general method. It says nothing about adding the
tree to a project without that skill. The skill is tuned on dev cases only, then frozen.

`Confirmed`: there is no relevance filter. Every skill's name and description, and arm B's
rule, are always in the system prompt. The tree and skill bodies enter only when the agent
chooses to `read` them, and then in full. C2 therefore compares A with B as assigned,
whether or not an answer read the tree, and the read rate is reported as a treatment check.

`Confirmed`: the skill loader only finds `.md` files directly in `agent/skills/`
(`services/skill.ts`), so the skill must ship as `agent/skills/count-active-drivers.md`,
with its reference paths updated. The demo project has no `agent/` folder yet.

**Rule text** `Assumed` draft, one line added to `RULES.md`:

> For questions about why a metric changed or what drives it, read `docs/metrics_tree.md`
> and use it as the structure for your analysis.

The tree, both skills, the rule text, and the degradations are frozen and hashed before any run.

---

## Metric roles

| Metric                        | Role                                                   | Used for                                                                                                               |
| ----------------------------- | ------------------------------------------------------ | ---------------------------------------------------------------------------------------------------------------------- |
| Correctness, root cause cases | Primary (same generic rubric as lookup cases)          | Decides C2, once its rubric and references pass validation                                                             |
| Completeness                  | Key secondary and guardrail                            | Catches correct answers that became too thin                                                                           |
| Correctness, lookup cases     | Guardrail                                              | The treatment must not break what already works                                                                        |
| Quantification                | Secondary                                              | Do claims about size or change state a value, unit, and period? Not primary, because it can be gamed with more numbers |
| Faithfulness (strict)         | Secondary; troubleshooting; tested as a proxy under H3 | Does the answer stay within what the agent saw?                                                                        |
| ContextualRelevancy           | Troubleshooting; tested as a proxy under H3            | Did the agent pull focused context?                                                                                    |
| AnswerRelevancy               | Troubleshooting; tested as a proxy under H3            | Did the answer stay on the question?                                                                                   |
| Cost, latency, error rate     | Guardrails                                             | Limits are set in the preregistration                                                                                  |

---

## Threats to validity

| Threat                                                                                                                                | Status      | Control                                                                                                                  |
| ------------------------------------------------------------------------------------------------------------------------------------- | ----------- | ------------------------------------------------------------------------------------------------------------------------ |
| q015–q017 entered the dataset in the same commit as the tree (`9f0a7fff`), by the tree's author, so the cases may favor the treatment | `Confirmed` | All 12 current cases become dev only; the confirmatory set is authored independently of the tree                         |
| q015–q017 compare a ~2.3-day week with a full week; an agent following the root cause skill's step 1 may be penalized for flagging it | `Confirmed` | Recheck the references; a correct completeness caveat must not lose points                                               |
| ContextualRelevancy is coupled to the treatment: when the agent reads the tree, the whole ~20 KB file is scored as context            | `Assumed`   | Secondary diagnostic only; never the primary endpoint                                                                    |
| Faithfulness is coupled to the treatment: the tree adds context that can support more claims, and B can also lose support (below)     | `Assumed`   | Secondary diagnostic only; report how often the tree was read                                                            |
| Only `execute_sql`, `read`, and `grep` reach the judge, and SQL results are cut to 20 rows                                            | `Confirmed` | Capture all tool output in the record; state what the judge saw                                                          |
| The judge defaults to the agent's model, and `judge.py` sets no temperature                                                           | `Confirmed` | Pinned judge from a different vendor; measure rejudging variance on identical answers                                    |
| Rubric wording penalizes rule-following answers ("unsupported additions"; audit F2)                                                   | `Confirmed` | Separate fact, coverage, and rule-compliance criteria                                                                    |
| One person wrote the tree, the cases, and the labels, and no second person is available                                               | `Confirmed` | Rule-generated cases, SQL-computed references, blinded re-rating, published labels, disclosure; reported as a limitation |
| References go stale; the seed changed on 2026-11-03                                                                                   | `Confirmed` | Hash the data snapshot in every record; freeze before the baseline                                                       |
| The root cause skill and the trap rules share an author, so absolute scores can be inflated by teaching to the test                   | `Confirmed` | Report differences between arms, not absolute scores; check headroom on dev; publish the skill                           |
| Result depends on one synthetic project                                                                                               | `Confirmed` | State it in the claim; a second project would be a replication, not part of this study                                   |
| Searching across metrics and subgroups                                                                                                | `Assumed`   | One preregistered primary endpoint; everything else labeled exploratory; multiplicity rule stated                        |

---

## Order of work

Each phase consumes the previous phase's artifact. Exit criteria must be met before the
next phase starts.

### Phase 0: Instrumentation (`braintrust-design-eval-instrumentation`), next

Detailed in the [instrumentation plan](instrumentation_plan.md).

`Confirmed`: `retrieval_context` is saved, and `AgentRunResult` already holds every tool
call. Missing, and impossible to add to a finished run:

- arm label, repetition index, and block id;
- hashes of the dataset, `RULES.md`, the tree, the semantic model, and the data snapshot;
- `nao` commit, system prompt hash, and tool manifest;
- all tool calls and untruncated results, separate from what the judge was shown;
- a repeat option on `nao evals`, and rejudging of saved answers without rerunning the agent.

**Exit:** one case (q016) reconstructed from its record alone, on both arms.

### Phase 1: Objective and behavior spec (`braintrust-define-eval-objective`, `braintrust-write-agent-behavior-spec`)

Settle the construct, the primary endpoint, and the expected behavior of a root cause
answer, drawing on `RULES.md` and the root cause skill.

**Exit:** the objective card and a versioned `BEHAVIOR.md`.

### Phase 2: Criteria (`braintrust-elicit-eval-criteria`, `braintrust-map-eval-evidence`)

Write generic score bands with anchored examples, and a guide for authoring case
references, including traps such as a partial-period comparison. Map each construct to
observable signals and gaming paths.

**Exit:** score bands and a reference guide someone other than the author could apply.

### Phase 3: Dataset (`braintrust-build-eval-dataset`, `braintrust-size-eval-dataset`)

- Keep the current 12 cases as the dev set; recheck q001, q008, and q015–q018.
- Generate the confirmatory set by a preregistered rule rather than by choosing cases:
  for example, every metric and adjacent period pair above a stated change size, with
  references computed by SQL. Keep the answers unseen until the confirmatory run.
- Generate traps by rule too. Coverage is computed per period by SQL; where a period is
  partial, the reference requires saying so and forbids reporting the raw change as a
  finding. Measure headroom on dev, because the skill may already pass most traps.
- Pilot on dev only to estimate agent and judge variance, then size the confirmatory
  set and repetitions (at least 3 runs per case per arm).

**Exit:** a frozen, hashed confirmatory set, a datasheet, and a sizing rationale with
its assumptions.

### Phase 4: Scorers and human reference (`braintrust-write-eval-scorer`, `braintrust-design-human-eval-review`, `braintrust-validate-eval-scorer`)

- Keep one generic Correctness definition for all cases: `evaluation_steps` plus GEval's
  `rubric` score bands. Include both in `GEvalRubric.version()`. Extra claims that don't
  contradict the reference aren't penalized, because the judge can't see tool output.
- Put what a case requires in its reference, as required claims and claims it must not
  make, derived from the data and never from the tree. The rubric must not encode the tree,
  or arm B would win by construction.
- Run Faithfulness with `penalize_ambiguous_claims=True`, so "stays within the evidence"
  covers unverifiable claims as well as contradicted ones. By default DeepEval counts
  only contradictions against the answer. Check on dev runs that claims sourced from the
  system prompt aren't wrongly penalized.
- Report answers that pass Correctness but fail Faithfulness, since that is where invented
  additions would show up.
- Add a generic Quantification scorer and a separate rule-compliance scorer.
- One rater, so report intra-rater reliability and call it that; it is not inter-rater
  agreement. Rate a shuffled sample with arm labels and tool traces removed, then re-rate
  it after a gap of at least two weeks.
- Agreement with an LLM judge is scorer validation, not a second human rater.
- Report scorer agreement with uncertainty, severity confusion, and blind spots.
- Publish answers and labels so that others can re-rate them.
- Calibrate thresholds here; every current threshold is a placeholder.

**Exit:** a fitness verdict per scorer. A scorer that fails can only appear as exploratory.

### Phase 5: Preregistration (`braintrust-design-eval-experiment`, `braintrust-define-eval-release-gate`)

Commit and tag before any confirmatory run, ideally with an external timestamp:
hypotheses, primary endpoint, minimum meaningful effect, arms, variables held fixed,
randomized run order, exclusion and stopping rules, the analysis, and the rule for
concluding improvement, no effect, or harm.

**Exit:** a public tag that predates the first confirmatory result.

### Phase 6: Confirmatory run and analysis (`braintrust-analyze-eval-experiment`)

C1 is checked first using N and D. If the instruments fail C1, C2 is not reported as a
finding. Analysis is paired by case, with uncertainty that respects cases and repeats.
Every run is kept, including errors.

**Exit:** analysis matching the preregistration, with deviations listed.

### Phase 7: Whitepaper (`braintrust-report-eval-results`)

Claims stay within the evidence. Include null or negative results, the search
denominator, the single-author limitation in the title or abstract ("a preregistered
single-author case study"), authorship disclosure, and a package to rerun it: code, data, frozen
context, raw records, and pinned versions.

**Out of scope:** production monitoring, because there is no production traffic.

---

## Open decisions

1. **Rule text:** approve or change the draft above; its wording is part of the treatment.
2. **Primary endpoint:** Correctness on root cause cases. Still open: the minimum
   meaningful improvement and the guardrail limits.
3. **Case generation rule:** which metrics, periods, and minimum change size.
4. **Canonical dataset location and provenance format:** in the JSONL rows or a datasheet.
5. **Platform:** local records are enough; Braintrust is optional.
