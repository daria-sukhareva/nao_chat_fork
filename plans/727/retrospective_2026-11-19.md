# Retrospective: Faithfulness doesn't check the skill

**Date:** 2026-11-19 (runs from just after midnight)
**Scope:** arm B on q023 and q024 with the new completeness sentence in the root-cause skill; why
both q024 trials replaced the question's baseline anyway; and why Faithfulness scored one of them
1.0 even though the skill it had in its context said the opposite of the answer.
**Status:** both runs used study commit `a7ae60ce` (the driver skill's inlined SQL and the
completeness edit), so the manifest is clean. Arm A has still not run on this context. The
reserve baseline clause is drafted, not added.

This follows the [2026-11-18 retrospective](retrospective_2026-11-18.md).

---

## The finding: Faithfulness doesn't check whether the answer followed the skill

In q024 trial 2 (`evals_results_20261119_001559.json`) the agent wrote:

> Oct 15–19 had **zero visits** (a data gap, not zero activity). The meaningful boundary is Oct
> 1–14 vs Oct 20+.

The skill it had just read says the opposite:

> If a period is partial, flag it. Data can only be partial before it starts, after it ends, or
> where a load failed; inside the data's range, a period with no activity is a real zero, not
> missing data.

**Faithfulness scored this answer 1.00:** "perfectly faithful to the retrieval context with no
contradictions found".

### The skill was in the judge's context

The judge's context is built from the agent's tool output (`build_retrieval_context` in
`cli/nao_core/commands/evals/tool_calls.py`), and `read` calls are included. For this trial it had
11 documents, about 103k characters:

| #    | Document                                                   | Characters     |
| ---- | ---------------------------------------------------------- | -------------- |
| 0    | `[File: /agent/skills/root-cause-analysis.md]`             | 3,430          |
| 1    | `[File: docs/metrics_tree.md]`                             | 19,038         |
| 2    | `[File: repos/kwwhat/models/marts/marts.yml]`              | 54,183         |
| 3    | `[File: repos/kwwhat/models/semantic/semantic_models.yml]` | 20,407         |
| 4–10 | SQL results                                                | 339–2,331 each |

So the skill reaches the judge. The judge can't use it, because of how DeepEval's Faithfulness
scores.

### How Faithfulness scores

From the installed DeepEval (`deepeval/metrics/faithfulness/`):

1. **It turns the whole context into a list of "truths", in one prompt.** The prompt asks for
   "FACTUAL, undisputed truths", with the example "Einstein won the noble prize for his discovery
   of the photoelectric effect in 1968". A skill is mostly instructions: "If a period is partial,
   flag it", "a period with no activity is a real zero". Those are rules, not facts, so they are
   the first thing this step drops. They also compete with 54k characters of `marts.yml` and 20k
   of semantic YAML in the same prompt.
2. **It checks the answer's claims only against those truths, not against the raw context**
   (`retrieval_context="\n\n".join(self.truths)`). Anything step 1 dropped is invisible from then
   on.
3. **It fails a claim only if a truth "DIRECTLY CONTRADICTS" it.** Everything else is `idk`, and
   `idk` isn't penalized. "A data gap, not zero activity" contradicts a rule, not a fact, so even if
   the rule had been extracted, a judge working on facts would most likely mark it `idk`.
4. **It never looks at the question.** Replacing the question's Oct 15–19 with Oct 1–14 breaks
   the question, not the context. Every Oct 1–14 number in the answer is real, so every claim is
   grounded.

The run file saves only the score, reason and cost for each metric, not the extracted truths or
the verdicts. So step 1 dropping the rule is inferred from the prompt and the code, not observed.
To confirm it, save `metric.truths` and `metric.verdicts` in `rag.py` and rejudge this file with
`--metrics rag`.

### The other RAG metrics took the agent's side

| Trial | Faithfulness | AnswerRelevancy | ContextualRelevancy | Correctness | Completeness |
| ----- | ------------ | --------------- | ------------------- | ----------- | ------------ |
| 1     | 0.92         | 1.00            | 0.65                | 0.4         | 0.4          |
| 2     | 1.00         | 0.91            | 0.76                | 0.4         | 0.3          |

- **AnswerRelevancy marked trial 2 down for the one correct thing it said:** "a factually incorrect
  characterization of Oct 15–19 as confirmed zero visits rather than a data gap". Trial 1, which
  swapped the baseline the same way, got 1.00.
- **ContextualRelevancy marked the context down because it "critically lacks the baseline data
  needed for a fair comparison, as 'The data contains no records for Oct 15–19'".**
- Trial 1's 0.08 off Faithfulness came from two small slips (OFFLINE versus total downtime, and
  CH-002 placed at LOC-002), not from the swap.

The RAG judges read an empty period as missing data, just as the agent did.

### What caught it

Only the reference-based metrics. Trial 2's Completeness reason: "The actual output incorrectly
treats Oct 15–19 as a 'data gap' and compares Oct 1–14 vs Oct 20+." They caught it because q024's
reference states the consequence of the rule (no supply from Oct 15 to 19, then 38 successful
visits in the week of Oct 20). They don't check the rule itself: a rule the reference doesn't spell
out would go unchecked here too.

### What it means

- **Faithfulness is a grounding check on the data, not a check on the method.** It asks whether the
  numbers came from the query results. It doesn't ask whether the agent followed its skill, answered
  the question it was asked, or used the right comparison. A faithful answer to the wrong comparison
  scores near perfect.
- **Having a skill in the judge's context isn't the same as judging against it.** The 2026-11-07
  test of `RULES.md` found that the rules never reach the judge. Skills do reach it, but are
  filtered out at truth extraction. Either way, no judge checks the instructions.
- **Rule and skill compliance is still out of scope.** If it comes into scope, it needs its own
  check, not Faithfulness: a GEval whose criteria are the skill's step 1, or deterministic checks on
  the trace, such as whether the comparison period in the answer is the one in the question.
- **`--metrics correctness completeness` is the right setting for these runs.** The RAG suite costs
  most of the judge spend (about $0.75 of $1.05 for q022 on 2026-11-18) and, on this failure, scored
  in the wrong direction.

---

## The completeness sentence, tested

Both runs served the committed skill, whose Data completeness bullet ends "If a period is partial,
flag it. Data can only be partial before it starts, after it ends, or where a load failed; inside
the data's range, a period with no activity is a real zero, not missing data."

### q023 (`000544`): unchanged, and not a test of the edit

Scores were 0.8/0.7 and 0.7/0.7, against 0.7/0.7 twice in `200458` on the old wording. Both runs
named CH-002's NoHeartbeat outage and CH-001's decommissioning, and neither called Oct 15–19 a gap,
before or after the change. q023 never had this misreading, so it can't show the edit working.

Errors outside the period, checked against the demo DuckDB:

- Trial 2: "Before Oct 15, uptime was ≥99.7% every day". Oct 1 was 78.73%, Oct 2 99.31% and Oct 11
  99.65%.
- Trial 2: "15,365 downtime-minutes per port". It was 27,360 per port from Oct 15 to Nov 3.
- Trial 1: "Outage end: Nov 3, 07:55 UTC (lasted ~19 days)". Nov 3 at 07:55 is where the data
  ends, not where the outage ended: the `as_of` problem in an answer. Trial 2 read it right: "still
  active as of 2025-11-03".

### q024 (`001559`): the swap persists

| Run                        | Correctness | Completeness | Baseline used | What it called Oct 15–19                                    |
| -------------------------- | ----------- | ------------ | ------------- | ----------------------------------------------------------- |
| `201432` (old wording), t1 | 0.5         | 0.5          | Oct 1–14      | not labelled                                                |
| `201432` (old wording), t2 | 0.8         | 0.7          | Oct 10–14     | "the question's 'baseline' period has no data"              |
| `001559` (new wording), t1 | 0.4         | 0.4          | Oct 1–14      | "a data gap … a real absence of activity, not missing data" |
| `001559` (new wording), t2 | 0.4         | 0.3          | Oct 1–14      | "a data gap, not zero activity"                             |

- **Trial 1 repeated the rule and swapped anyway.** It now knows the period is a real zero, but
  doesn't treat a real zero as a usable baseline.
- **Trial 2 inverted the rule.**
- **Neither said CH-002 was offline.** Both described it as live but broken, from Oct 1–14's
  ConnectorLockFailure: the cause of a different comparison.
- Trial 1 also counted two weeks after Oct 20 (50 successful visits, 25 per charger) and gave
  100% uptime, against 99.69%.

For "why did X go up compared to a period where X was zero", the literal answer is short: there
were no chargers, then there were. The agent seems to find that too trivial and looks for a "real"
comparison. The completeness bullet is about labelling the period, not about choosing it.

---

## Lessons

- **A grounding metric can't see a method error.** Faithfulness checks claims against facts. An
  instruction isn't a fact, and the question isn't in its context, so an answer that breaks both
  can score 1.0.
- **"In the judge's context" doesn't mean "judged against".** Check what a metric does with its
  context, not only what it receives.
- **Naming the error isn't fixing the choice.** The agent repeated the new sentence word for word
  and made the same swap.

---

## Still open

- Add the baseline clause to step 1 of the root-cause skill: "When the question names the
  comparison period, compare against that period, even if it has no activity. Another baseline may
  be added as labelled context, after the answer to the question asked." Then run q024 and q025.
- Save Faithfulness's `truths` and `verdicts` in `rag.py` and rejudge `001559` with
  `--metrics rag`, to confirm that truth extraction drops the skill's rules.
- Add the mechanism to proposal 6 in `upstream_proposals.md` ("State Faithfulness's limits"):
  skills reach the judge, but truth extraction keeps facts and drops instructions, and the question
  is never checked.
- Run arm A on this context, q022–q028, with `--metrics correctness completeness`.
- Carried over from 2026-11-18: fix `as_of` and move q015–q017 to the end of the range; add the
  new-driver sentence to q027's reference; q026's reference grain.
