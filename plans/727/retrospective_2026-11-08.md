# Retrospective: metric roles, the reference format, the omission leak, and a verified dev set

**Date:** 2026-11-08
**Scope:** deciding the role of each metric and writing the hypotheses down; testing how q018's
reference format moves the Correctness judge; measuring the omission leak; starting Phase 3 with
an audit of the golden set; and re-verifying every dev case by SQL.
**Status:** Correctness rubric `fbda3f9f0f46` (replacing `0015f7a322a7`) is committed and running
in the demo image. Completeness is unchanged (`c493b2deacb0`). All 12 dev cases are checked by
SQL against the current seed and carry provenance (committed in `52ce941c`).
The seed is to be extended before the confirmatory set is built.

This follows the [2026-11-07 retrospective](retrospective_2026-11-07.md).

---

## Metric roles

The RAG triad's job is to explain a low Correctness score, not to make a claim:

| Correctness is low, and… | Likely cause                                        |
| ------------------------ | --------------------------------------------------- |
| ContextualRelevancy low  | The agent pulled the wrong or unfocused evidence    |
| Faithfulness low         | The answer went beyond or against what it saw       |
| AnswerRelevancy low      | The answer was about a different question           |
| All three fine           | Good evidence was read wrongly (grounded but wrong) |

Decided (in `experiment_plan.md`, commit `b08121d1` and later):

- **Faithfulness, ContextualRelevancy and AnswerRelevancy are troubleshooting only.** None is an
  endpoint or has a pass/fail threshold in the results, so none needs human-label validation.
  When one explains a failure, read its per-claim reasons and check them against the context,
  because the Faithfulness judge has misread dates in long contexts.
- **Strict Faithfulness (`penalize_ambiguous_claims=True`) is dropped.** It failed the best q018
  answer (0.57–0.70), called the correct conclusion a contradiction in two of three reasons, and
  dropped as much on an unmodified answer as on rule-breaking fakes.
- **Quantification is dropped.** The references' required claims carry the values, so
  Completeness and Correctness already cover them. A third scorer would add a comparison, reward
  longer answers, and need its own validation.
- **Completeness is a guardrail only**, with a non-inferiority margin set in the preregistration.
- **H3 is exploratory.** It is reported but not preregistered or counted in the multiplicity
  rule, because the triad varies as much within an answer as between answers.
- **The judge's context is described correctly.** A stale threat row said only `execute_sql`,
  `read` and `grep` reach the judge, with SQL cut to 20 rows. The code sends every tool result
  except `NON_EVIDENCE_TOOLS`, cut to the 40 rows the agent sees. The system prompt, including
  `RULES.md`, is not in it.

**Hypotheses table.** The plan now has three: C1 (the instruments stay quiet on N and detect D,
confirmatory, a gate for C2), C2 (B vs A on root cause Correctness, confirmatory, primary,
two-sided) and H3 (exploratory). Guardrails and the tree-read rate are reported with C2, not as
hypotheses of their own.

---

## The q018 reference and the Correctness judge

All rejudges below score saved answers with no agent calls. They cost about $0.008 per
judgment, far less than estimated: the dollars in earlier runs came from the RAG metrics' large
contexts, not from GEval.

### "Must not claim" didn't work with this judge

The 2026-11-07 tightening ("That CH-002 or any other charger got worse on Oct 5") made the
borderline `020913` answer worse:

| Rubric         | Reference                  | Correctness (3 judge repeats) | Completeness  |
| -------------- | -------------------------- | ----------------------------- | ------------- |
| `0015f7a322a7` | First "Must not claim"     | 0.8, 0.7, 0.5                 | 0.7 (1 run)   |
| `0015f7a322a7` | Tightened "Must not claim" | 0.3, 0.2, 0.3                 | 0.6, 0.5, 0.5 |
| `fbda3f9f0f46` | Tightened "Must not claim" | 0.5, 0.5, 0.6                 | 0.5, 0.6, 0.6 |

- Every reason quoted "The situation worsened on Oct 5 because 9 out of 10 visits landed on
  CH-002" as the forbidden claim, although the same answer says CH-002 was already broken on
  Oct 4.
- Completeness penalized the same item, so one misreading cost twice.
- The third row is a clean one-variable test: with the rubric step removed and the reference
  unchanged, the judge still cited "the 'Must not claim' requirement". **The reference text alone
  drives the misreading.** The rubric step only added the 0–2 cap.

The section was removed from the reference and the rubric. A wrong diagnosis is caught instead
because it contradicts a required claim, so each reference states the facts that rule out the
likely wrong diagnoses ("each charger's own success rate stayed the same").

### Five saved answers without "Must not claim"

Rubric `fbda3f9f0f46`, reference as a "Required:" list:

| Answer                                       | Before (`0015f7a322a7`) | After         |
| -------------------------------------------- | ----------------------- | ------------- |
| Right and complete (`3e532094`)              | 0.9, 0.9, 0.9           | 1.0, 0.9, 1.0 |
| Right, no CH-001 or "mix shift" (`51859685`) | 0.9, 0.9, 0.9           | 0.8, 0.9, 1.0 |
| Right, "the situation worsened" (`020913`)   | 0.8, 0.7, 0.5           | 0.9, 0.8, 0.9 |
| Right, no CH-001's 100% (`022022`)           | 0.8, 0.8, 0.8           | 0.7, 0.7, 0.7 |
| Wrong mechanism (`014925`)                   | 0.2, 0.2, 0.2           | 0.4, 0.5, 0.5 |

The wrong-mechanism answer rose into the 3–5 band. Its reasons identify the error exactly
("escalating fault frequency" contradicts "each charger's own success rate stayed the same"), and
3–5 is the band for "a central cause is wrong" while the main conclusion (CH-002,
ConnectorLockFailure) is right. The old 0.2 came from the "Must not claim" cap. The ranking holds,
but the placeholder pass threshold of 0.5 now passes this wrong answer; it must be at least 0.6 if
a pass rate is reported.

### The reference as a natural-language answer

q018's reference was rewritten from a list into prose with the same claims (`a602d0c1`), so it
reads like an answer rather than a checklist. Results are in the next section.

---

## The omission leak

The rubric says "Do not penalize omissions". To measure whether the judge follows it, the
complete answer `3e532094` was copied with the sentences carrying a required claim deleted and
nothing added (`synthetic/q018_omission_ablation.json` and `q018_prose_reference.json`):

| Version of the complete answer | Correctness, list reference | Correctness, prose reference | Completeness, prose |
| ------------------------------ | --------------------------- | ---------------------------- | ------------------- |
| Unchanged                      | 1.0, 1.0, 1.0               | 1.0, 1.0, 1.0                | 1.0, 1.0, 1.0       |
| Without CH-001's 100%          | 0.8, 0.8, 0.7               | 0.8, 0.7, 0.9                | 0.8, 0.7, 0.7       |
| Without "not new"              | 0.9, 0.9, 0.9               | 0.9, 0.9, 0.9                | 0.8, 0.8, 0.8       |
| Without both                   | 0.6, 0.9, 0.6               | 0.8, 0.8, 0.8                | 0.6, 0.7, 0.7       |

- **An omission costs 0.1 to 0.2 of Correctness** on top of its Completeness penalty. One reason
  reads: "a central claim in the expected output — though omissions are not penalized here", and
  then deducts anyway.
- **The reference format isn't the cause.** The list and prose references leak the same amount.
- **Prose separates right from wrong at least as well.** With it, the wrong diagnosis scored 0.4,
  0.3, 0.3 and the lowest right answer 0.7.
- **Reference wording alone moves scores by up to 0.2.** `020913` went from 0.9, 0.8, 0.9 to 0.7
  three times when only the format changed.

**Decision: left as a known limitation.** It is recorded in the plan's remaining issues and as a
`Confirmed` threat: an arm that writes shorter answers also loses some Correctness, so
Completeness is always reported beside it. Fixes considered and not taken: steps that go only
through the answer's own claims, or structured yes/no scoring with DeepEval's `DAGMetric`.

---

## Phase 3, step 1: auditing the golden set

### The population the cases represent

> Single-turn questions from an EV charging network operator about the reliability of their own
> small network: counts and rates, metric definitions, and "why" questions about a condition or a
> change, against the kwwhat demo project.

The cases were written about six months ago, while the author was developing the context, from
watching where the chat agent failed. That explains the stale references (they predate the
2026-11-03 seed change). It also means the cases were picked from failures, so almost any context
change will look like an improvement on them, partly by chance. They can only be dev cases.

### The data holds about one phenomenon

The demo data is 139 visits over 14 days, at one location with two chargers. CH-002 fails every
visit with ConnectorLockFailure, CH-001 succeeds on every visit, and every change in the success
rate is a mix shift between them. q015–q018 share one answer. A confirmatory set generated from
this data would be one case asked many ways: an effective sample near 1, and a C2 claim about one
mix shift.

| Root cause type                                   | In the demo data?               |
| ------------------------------------------------- | ------------------------------- |
| Persistent port fault plus a mix shift            | Yes                             |
| Offline outage (NoHeartbeat) lowering uptime      | Yes: 1,080 min, 4 ports, 3 days |
| Fault onset: a charger's own rate falls           | No                              |
| Driver or auth-side failures                      | No (confounded with charger)    |
| Demand change, reliability unchanged              | No                              |
| Partial period (trap)                             | Yes: the week of Oct 13         |
| No real change, noise on small numbers (negative) | Yes                             |
| False premise in the question (negative)          | Can be built                    |
| Undefined metric, ask or refuse (negative)        | Yes: q002                       |

**Decision: the author will extend the seed** with the missing types, generated by rule from a
source independent of the tree (for example the OCPP 1.6 taxonomy in `dim_error_codes`). Real
operator traffic is already a non-claim, so synthetic scenarios don't weaken the paper.

### The database changes every day

`int_charger_commissioned_daily.sql` uses the current date, and the demo rebuilds
`analytics.duckdb` when the container starts. `fact_uptime_daily` runs from 2025-09-15 to the
build day and gains 4 rows a day:

- "Full history" uptime drifted from 99.87% when q005 was written to 99.91% on 2026-11-08.
- The run-level data checksum differs between days, so `compare` will refuse to pair blocks run on
  different days.

To fix in the seed extension: a fixed `as_of` date instead of the current date.

### Every dev case re-verified

| Case       | Change                                                                                                                                                                                                                                  |
| ---------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| q001       | Reworded: CH-001, the only working charger (38 of 38), was decommissioned; it should have been CH-002 (0 of 101). "Port" in the question is a deliberate user slip: only a whole charger is decommissioned                              |
| q002       | Unchanged; checked that no availability-index metric exists (`semantic_layer_checked`)                                                                                                                                                  |
| q003       | Reworded: WeakSignal is the only error on troubled-success visits, one occurrence, in one of the 2 visits                                                                                                                               |
| q004, q007 | Unchanged; verified                                                                                                                                                                                                                     |
| q005, q006 | Fixed date range Oct 1–14, 2025: uptime 98.64% (78,599 of 79,680 port-minutes), failed attempts 72.34% (102 of 141). The old "full history" figures were diluted by a year of outage-free days                                          |
| q008       | OFFLINE share corrected from 76% to 99.9% (1,080 of 1,081 minutes)                                                                                                                                                                      |
| q015–q017  | The question's "18%" corrected to 12pp (31.9% to 20.0%). Stale numbers (19 vs 66 visits, 28.79% to 10.53%) replaced. Now partial-week traps: Oct 13–19 has 2 days of data, and the drop is a mix shift plus a persistent CH-002 failure |
| q018       | Prose reference, as above                                                                                                                                                                                                               |

Every row now has `source`, `label_provenance` (who wrote it, from what, and the queries that
checked it) and `data_fingerprint`, computed with the backend's own checksum SQL. Two new forms:
a fingerprint can be a list of tables, and a table can carry a `filter` when the table grows
daily (q005, q006). References drafted with Claude say so.

---

## Lessons

- **The reference steers the judge more than the rubric.** With the "Must not claim" step gone
  from the rubric, the judge still enforced the item from the reference text.
- **A judge can agree with an instruction and still not follow it.** "Though omissions are not
  penalized here", followed by a deduction. Telling it "don't" isn't enough; only scoring that
  gives an omission no path into the score would fix it.
- **A synthetic ablation isolates scorer behavior cheaply.** Deleting true sentences from a
  known-good answer measured the leak for about $0.20, with nothing else changing.
- **Build test copies from the committed file, and check before running.** The five-answer and
  ablation copies were built from a working file before the author's commit removed the
  "Required:" heading, so they tested a reference that was never committed. Compare a copy's
  reference with the dataset before spending on a run.
- **Change one thing per run.** Rejudging the old copy with the new rubric looked like a mistake,
  but it was the only run that separated the rubric's effect from the reference's.
- **Fingerprints catch staleness only for what they cover.** `fact_visits` matched while the
  uptime table moved under q005 and q006. Fingerprint every table a reference uses, and give
  questions fixed date ranges.
- **Cases picked from failures can't support a claim.** They regress toward the mean under any
  change.
- **`docker exec` starts in `/app`.** Use `-w /app/kwwhat` so paths match the recorded ones.

## Still open

- Extend the seed: new locations, chargers or periods with the missing root-cause types, leaving
  LOC-001 between Oct 1 and Oct 14, 2025 untouched so the dev set stays valid; and a fixed `as_of`
  date in `int_charger_commissioned_daily.sql`.
- Then Phase 3: the generation rule and reference guide, the pilot on dev, and sizing
  (`braintrust-size-eval-dataset`).
- The Correctness pass threshold (0.5) passes the wrong-mechanism answer; calibrate in Phase 4.
- Arm D's degradations.
- Review the A/B pairing run's results files (from 2026-11-07).
- Two misleading messages: `compare` says "except the arm" for runs of the same arm, and a run
  stopped by `--max-cost` ends with "✓ All N eval(s) passed".
- `persist_docs`; optionally, record failed tool calls with their error message.
