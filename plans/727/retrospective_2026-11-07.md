# Retrospective: why Correctness overlaps Completeness

**Date:** 2026-11-07
**Scope:** tracing the Correctness/Completeness overlap from the first run with repetitions
back to the rubrics, and recording it as a decision.
**Status:** recorded as [open decision 4](experiment_plan.md#open-decisions) in the experiment
plan. The rubrics are unchanged. A rejudge of `evals_results_20261106_222427.json` with
`--judge-repeats 3` is running, to measure the current rubric's reproducibility before anything
changes.

This follows the [2026-11-06 retrospective](retrospective_2026-11-06.md), whose first live run
found the overlap.

---

## Context

In the first run with repetitions (q018, arm B), repetition 2 stated nothing false but left out
CH-001's 100% success rate and the words "mix shift". It scored Correctness 0.7 and Completeness
0.9, and the two judge reasons were nearly the same text. The question was whether the judge
misapplied the rubric or followed it.

It followed it. The overlap is written into the Correctness rubric.

---

## The Correctness rubric

From `cli/nao_core/commands/evals/correctness.py`:

```python
CORRECTNESS_RUBRIC = GEvalRubric(
    name="Correctness",
    evaluation_steps=[
        "Compare the actual output directly with the expected output for factual accuracy.",
        "Verify that every required fact, entity, value, and relationship is present and correctly represented.",
        "Verify that the required naming, terminology, and framing are used.",
        "Penalize contradictions, unsupported additions, and misleading details.",
    ],
    evaluation_params=["actual_output", "expected_output"],
)
```

The judge sees only the answer and the reference. It doesn't see the question or the tool
output. The default threshold is 0.5, and `GEvalRubric.version()` hashes the name, steps and
params into `rubric_version`.

Step by step:

| Step                                                            | What it checks                                             | Construct                                                                                             |
| --------------------------------------------------------------- | ---------------------------------------------------------- | ----------------------------------------------------------------------------------------------------- |
| 1. "…for factual accuracy"                                      | Whether what the answer says is true                       | **Correctness**                                                                                       |
| 2. "every required fact … is present and correctly represented" | "Present" is coverage; "correctly represented" is accuracy | **Completeness** and Correctness                                                                      |
| 3. "required naming, terminology, and framing"                  | Wording                                                    | **Neither.** It rewards matching the reference's words.                                               |
| 4a. "contradictions"                                            | Wrong claims                                               | **Correctness**                                                                                       |
| 4b. "unsupported additions"                                     | Extra claims                                               | Conflicts with the plan, which says extra claims that don't contradict the reference aren't penalized |
| 4c. "misleading details"                                        | Claims that are true but misleading                        | **Correctness**                                                                                       |

## The Completeness rubric, for comparison

From `cli/nao_core/commands/evals/completeness.py`:

```python
COMPLETENESS_RUBRIC = GEvalRubric(
    name="Completeness",
    evaluation_steps=[
        "Identify every distinct part of the question in the input and every required element of the expected output.",
        "Check whether the actual output addresses each part of the question and covers each required element.",
        "Heavily penalize omitted parts, partial answers, and answers that defer or deflect instead of answering.",
        "Do not penalize correct additional detail; judge only coverage, not wording or accuracy of extra content.",
    ],
    evaluation_params=["input", "actual_output", "expected_output"],
)
```

Completeness's step 2 and Correctness's step 2 both check that required elements are covered.
That shared step is the overlap the q018 run showed. Step 3 of Correctness explains the rest:
repetition 2 described the mechanism ("3 more drivers chose the faulty port") without the
reference's words ("mix shift"), and lost points for it.

## Two more gaps

- **Neither metric uses the "Must not claim" list explicitly.** The references have that
  section, but Correctness never mentions it. The judge only catches a violation through
  "contradictions" or "misleading details".
- **There are no score bands.** The plan calls for `evaluation_steps` plus GEval's `rubric`
  score bands, but only the steps are built. So the judge picks a score from 0 to 10 without
  anchors for what, say, 7 means. That's another reason a borderline answer can land on 0.7 or
  0.8.

---

## Why it matters

Correctness is the primary endpoint. As written, it partly measures coverage and wording, so a
Correctness effect of the tree can't be read apart from Completeness. Step 3 is the more
serious part for this study. If the metrics tree teaches the agent the reference's vocabulary,
arm B would score higher on Correctness for wording alone, which is the judgment contamination
the 2026-11-05 retrospective warned about, entering through the rubric instead of the reference.

## Decision recorded

[Open decision 4](experiment_plan.md#open-decisions) lists three options:

- **Separate the constructs (recommended).** Correctness keeps steps 1, 4a and 4c, adds an
  explicit "Must not claim" check, and drops steps 2, 3 and 4b. It also gets score bands.
  Completeness scores coverage of the "Required" list. How often the two disagree is reported
  as a check that they now measure different things.
- **Keep both as they are** and report them as overlapping.
- **Merge them** into one reference-based score, losing the split between wrong and missing.

Whichever is chosen changes `rubric_version`, so it has to be settled before any run that
counts. A matching bullet was added to Phase 4 in the plan.

## Order of work

The new rubric is drafted only after the rejudge finishes. The rejudge measures the current
rubric's reproducibility on fixed answers; changing the rubric first would leave nothing to
compare against. Once a draft exists, `nao evals rejudge --metrics correctness` can score the
same saved answers with it, so comparing the two rubrics costs no agent calls.

## Lessons

- **Read the rubric before blaming the judge.** The judge's reasons looked like a judging
  error. They were the rubric's own steps, applied faithfully.
- **Two answers to one case exposed what one answer couldn't.** With a single answer, a 0.7
  looks like a quality score. With a second, better-scored answer next to it, the difference
  could be traced to what each rubric step rewards.
- **Wording in a rubric is a contamination path.** Asking for "the required terminology" lets
  whichever arm shares the reference's vocabulary win.

## Still open

- The rejudge result, and what it says about the 1.0 versus 0.7 gap.
- Open decision 4: choose an option, then draft the rubric with score bands.
- Step 5: cost ledger and `--max-cost`. The judge's cost is still not recorded.
- The compare step and `--confirmatory`.
- Arm D's degradations.
- Rechecking q015–q017 (the "18% drop" premise is 11.9 pp in the data).
- Whether to tighten q018's reference, including the awkward "Oct 1 to Oct 14" criterion.
- `persist_docs`.
- Optionally, record failed tool calls with their error message.
