# Retrospective: Faithfulness doesn't check the skill, and the first clean A/B comparison

**Date:** 2026-11-19
**Scope:** arm B on q023 and q024 with the new completeness sentence in the root-cause skill; why
both q024 trials replaced the question's baseline anyway; and why Faithfulness scored one of them
1.0 even though the skill it had in its context said the opposite of the answer. Then arm B on
q022–q028 (3 trials each, Correctness and Completeness only), why q028 fails in every trial, and
arm A on the same cases: the first A/B comparison on an identical shared context.
**Status:** B ran from study commit `a7ae60ce` (the driver skill's inlined SQL and the completeness
edit), A from `f6fe2521`, which adds only this retrospective. Both manifests are clean, and the
served `root-cause-analysis.md` and `golden_dataset.jsonl` have the same hashes in both arms. The
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

## Arm B on q022–q028

Arm B ran each case 3 times with `--metrics correctness --metrics completeness`. With `000544`
(q023) and `001559` (q024) from earlier, all on `a7ae60ce`:

| Case | n   | Correctness | SD   | Range   | Completeness | SD   | Range   |
| ---- | --- | ----------- | ---- | ------- | ------------ | ---- | ------- |
| q022 | 5   | 0.82        | 0.11 | 0.7–0.9 | 0.74         | 0.05 | 0.7–0.8 |
| q023 | 5   | 0.72        | 0.13 | 0.5–0.8 | 0.64         | 0.05 | 0.6–0.7 |
| q024 | 5   | 0.48        | 0.11 | 0.4–0.6 | 0.40         | 0.07 | 0.3–0.5 |
| q025 | 3   | 0.63        | 0.23 | 0.5–0.9 | 0.63         | 0.15 | 0.5–0.8 |
| q026 | 3   | 0.70        | 0.00 | 0.7     | 0.40         | 0.00 | 0.4     |
| q027 | 3   | 0.73        | 0.15 | 0.6–0.9 | 0.93         | 0.12 | 0.8–1.0 |
| q028 | 3   | 0.10        | 0.00 | 0.1     | 0.00         | 0.00 | 0.0     |

The pooled SD within a case is 0.13 for Correctness and 0.08 for Completeness. Dropping the RAG
suite cut the judge's cost from about $0.5 to $0.04–0.06 per run.

The cases fall into three groups:

- **Fixed by the case, SD 0.** q028 fails the same way every time (below). q026's Completeness is
  capped at 0.4: the reference requires port-minutes and the 08:00 start for a question about
  chargers, and all three answers answered at the charger grain.
- **Consistently mediocre.** q024: all 5 trials replaced Oct 15–19 ("not apples-to-apples", "a data
  gap", "the comparison the question implies is between a data gap and the post-gap period").
- **Noisy.** q025 (0.5–0.9): the driver skill and its `periods` SQL were used in all 3 trials, and
  the spread is in the framing. The 0.9 trial says "zero visits and zero drivers is not missing
  data"; a 0.5 trial says "a data gap caused by charger decommissioning". q027: the driver skill
  was opened in 1 of 3 trials (0 of 2 on 2026-11-18).

q026 also showed the agent loading the skill with `load_skill` in 2 of 3 trials instead of `read`.
`load_skill` is on the judge's denylist (`NON_EVIDENCE_TOOLS`), so with the RAG suite on, a skill
loaded that way would not reach the Faithfulness judge at all.

### q028: the method never starts

"Did charging demand recover in the week of Oct 20, 2025, compared to the week of Oct 6?" The
reference: the data can't show it, because the two weeks cover different sites.

All three trials did the same thing: read `marts.yml` and the semantic model, ran one network-wide
query, and charted it. None opened the root-cause skill, none queried `dim_chargers`, none split by
location. On one query the weeks look like the same network (69 visits against 38, 27.5% success
against 100%), so the answers said "Yes — charging demand **recovered meaningfully**", or "the
**reliability problem was resolved** … which may reflect drivers who gave up after repeated
failures".

The Network Topology bullet lives only inside the skill, and nothing opened the skill:

- The skill's description triggers on "why did X drop", "what caused this change", "is this
  concentrated somewhere". "Did demand recover?" is a yes/no comparison.
- Arm B's `RULES.md` does cover it ("For any question about whether, why, or where a metric
  changed, read `agent/skills/root-cause-analysis.md` before querying"), and was ignored in 3 of 3
  trials, while the `marts.yml` rule was followed in all 3.

Every why-question tonight opened the skill and ran the lookup; the one whether-question did
neither, and scored lowest. Getting the method into context mattered more than its wording.

---

## The first clean A/B comparison

Arm A ran the same loop: q022–q028, 3 trials each, the same metrics. Only the arm-specific files
differ: B has `docs/metrics_tree.md`, the `count-active-drivers` skill and two `RULES.md` lines.

| Case     | Correctness A | Correctness B | B − A     | Completeness A | Completeness B | B − A     |
| -------- | ------------- | ------------- | --------- | -------------- | -------------- | --------- |
| q022     | 0.87 ± 0.06   | 0.82 ± 0.11   | −0.05     | 0.70 ± 0.00    | 0.74 ± 0.05    | +0.04     |
| q023     | 0.67 ± 0.15   | 0.72 ± 0.13   | +0.05     | 0.53 ± 0.06    | 0.64 ± 0.05    | +0.11     |
| q024     | 0.53 ± 0.15   | 0.48 ± 0.11   | −0.05     | 0.43 ± 0.06    | 0.40 ± 0.07    | −0.03     |
| q025     | 0.57 ± 0.29   | 0.63 ± 0.23   | +0.07     | 0.53 ± 0.15    | 0.63 ± 0.15    | +0.10     |
| q026     | 0.60 ± 0.26   | 0.70 ± 0.00   | +0.10     | 0.33 ± 0.06    | 0.40 ± 0.00    | +0.07     |
| q027     | 0.60 ± 0.17   | 0.73 ± 0.15   | +0.13     | 0.57 ± 0.38    | 0.93 ± 0.12    | +0.37     |
| q028     | 0.10 ± 0.00   | 0.10 ± 0.00   | 0.00      | 0.00 ± 0.00    | 0.00 ± 0.00    | 0.00      |
| **Mean** | **0.56**      | **0.60**      | **+0.04** | **0.44**       | **0.54**       | **+0.09** |

Mean ± SD per case; A has 3 trials per case, B 3–5. Runs: A `010634`, `010956`, `011319`,
`011650`, `123719`, `124104`, `124335`.

- **Correctness: no difference beyond the noise.** A's pooled SD within a case is 0.18, B's 0.13.
  With 3 trials per arm, the standard error of each case's difference is about 0.12–0.2, and no
  Correctness difference exceeds it.
- **Completeness leans to B, not yet a result.** B is ahead on 5 of the 6 cases that can differ (a
  sign test of p ≈ 0.1, one-sided, on 6 cases). Most of the gap is q027 (+0.37), where A scored 1.0,
  0.4 and 0.3. A's two low trials left out the 1.9 → 1.5 visits per driver and the 80/20 split,
  the decomposition the tree spells out: the one place a tree effect is plausible. q023 (+0.11, SDs
  of 0.05–0.06) is the most consistent gap.
- **B is less variable.** Pooled SD 0.13 against 0.18 on Correctness, 0.08 against 0.16 on
  Completeness. q026 is the clearest: B scored 0.7 three times, A 0.7, 0.8 and 0.3 (the 0.3 left out
  CH-001's decommissioning). A hypothesis worth testing: the tree makes answers more consistent
  rather than better on average.
- **Three cases can't discriminate.** q028 is 0.1/0.0 in all six trials: neither arm opens the
  skill, so B's RULES line didn't help. q026's Completeness is capped by its reference in both arms.
  q024's baseline swap happens in both arms alike.
- **The shared changes work in both arms.** A opens the shared root-cause skill too and queried
  `dim_chargers` in every trial of q025–q027. The Network Topology bullet is a shared-context
  effect, not a tree effect.
- **A never addressed new versus returning drivers in q027,** so it neither made B's novelty error
  of 2026-11-18 nor got it right. q027's reference doesn't check it either way.

## Lessons

- **A grounding metric can't see a method error.** Faithfulness checks claims against facts. An
  instruction isn't a fact, and the question isn't in its context, so an answer that breaks both
  can score 1.0.
- **"In the judge's context" doesn't mean "judged against".** Check what a metric does with its
  context, not only what it receives.
- **Naming the error isn't fixing the choice.** The agent repeated the new sentence word for word
  and made the same swap.
- **A method only helps if it gets loaded.** The topology check worked in every trial that opened the
  skill and was absent in every trial that didn't. Check what triggers a skill, not only what it
  says.
- **A case with SD 0 measures the case.** q028 and q026's Completeness score the same whatever the
  agent does. Fix such a case before counting it in an A/B mean.
- **Look at the spread, not only the mean.** The clearest difference between the arms so far is in
  variance, not in the average.

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
- q028: widen the root-cause skill's description to "any comparison of a metric between periods:
  why it changed, whether it changed or recovered, or where" (shared, both arms). If that doesn't
  hold, move the topology check into `RULES.md`. Also find out why B's "whether, why, or where" RULES
  line is ignored. Test on q028 and q021.
- Fix q026's reference grain (ask about capacity, or stop requiring port-minutes).
- For an A/B claim: 5 or more trials per case per arm, alternating A, B, B, A with `--experiment`
  and `--block`, then `rejudge --judge-repeats 3`. Pool across cases for the headline, and test the
  variance difference as well as the mean.
- Delete `evals_results_20261119_001618.json` (0 trials, interrupted).
- Carried over from 2026-11-18: fix `as_of` and move q015–q017 to the end of the range; add the
  new-driver sentence to q027's reference; q026's reference grain.
