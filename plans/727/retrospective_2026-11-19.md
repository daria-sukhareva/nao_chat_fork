# Retrospective: Faithfulness doesn't check the skill, the first clean A/B comparison, and type 4

**Date:** 2026-11-19
**Scope:** arm B on q023 and q024 with the new completeness sentence in the root-cause skill; why
both q024 trials replaced the question's baseline anyway; and why Faithfulness scored one of them
1.0 even though the skill it had in its context said the opposite of the answer. Then arm B on
q022–q028 (3 trials each, Correctness and Completeness only), why q028 fails in every trial, and
arm A on the same cases: the first A/B comparison on an identical shared context. Last, the type 4
scenario (driver-side authorization failures): the generator change, the scenario, and the uptime
fix it needed, then q029–q031 and the first A/B run on them.
**Status:** B ran from study commit `a7ae60ce` (the driver skill's inlined SQL and the completeness
edit), A from `f6fe2521`, which adds only this retrospective. Both manifests are clean, and the
served `root-cause-analysis.md` and `golden_dataset.jsonl` have the same hashes in both arms. The
reserve baseline clause is drafted, not added. kwwhat #202 (uptime fix) and #203 (generator auth)
are merged to `staging`. The data now has scenario 4. The type 4 seeds are committed on `exp/metric_tree` (`6406656`, rebased onto
`staging`, so the branch now has #202). q029–q031 ran on both arms from `7ea2b6d8`; the older references have not been
re-verified against the extended data.

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
  ends, not where the outage ended. Trial 2 read it right: "still active as of 2025-11-03".

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

## Type 4 simulated: driver-side authorization failures

**The data now has scenario 4.** One eMSP's tokens expire on Nov 10, and visit success falls from
91.6% to 68.9% at both locations while every charger stays healthy. The cause shows up only when
visit success is split by driver and authorization status, so the case tests the tree's driver
branch; every earlier failure in the data was tied to a charger. With it, the data covers root-cause
types 1, 2, 4, 5 (LOC-002's demand drop, 2026-11-12), 6 and 7 from the experiment plan, and 8 and 9
are built into questions. Still missing: type 3, a fault onset (a charger's own success rate falls
and stays down).

The experiment plan's list of root-cause types still lacked type 4, driver or auth-side failures:
in the seed, auth problems happened on one charger only, so they couldn't be told apart from a
charger fault. q015 and q016 also need failures in a partial last week, and LOC-002 succeeded on
every visit. The author chose type 4 as the next scenario, generated with the OCPP log generator.

### The generator could not authorize (kwwhat #203, merged)

Before this change:

- **No Authorize:** every session went straight to StartTransaction.
- **No rejections:** the central system answered `Accepted` to every idTag.
- **No shared drivers:** each charger run drew 25 random idTags of its own, so no driver used two
  chargers, and every driver at a new charger was new.

Added on `feat/generator-auth`:

- `--id-tags-file`: one driver pool shared by every charger run.
- `--authorize-probability`: the charger sends Authorize before the transaction. Otherwise it starts
  from its local authorization cache.
- `server.py --auth-list`: idTag statuses from a `from_ts` on, with an optional `expiryDate`. The
  central system has no simulated clock, so it takes the latest timestamp the charger sent.
- **Two rejection paths:**
    - A rejected Authorize starts no transaction, and the driver leaves.
    - A rejection in StartTransaction.conf stops the transaction 1 to 3 seconds later with reason
      `DeAuthorized` and 0 Wh.

40 tests pass, 8 of them new. When every idTag is accepted, the output is byte-identical to the old
generator for the same seed. #85 (the generator itself) was squash-merged to `staging` first, and
#203 was rebased onto it.

### What dbt can see decided the design

dbt attaches an event to a charge attempt by `connector_id`, and OCPP 1.6 Authorize carries none
(`payload_extract_connector_id` skips it). `id_tag` is taken only from StartTransaction and
RemoteStartTransaction. So:

- **A rejected Authorize** shows in the marts as an ordinary failed attempt: no idTag, no status,
  the same as a driver who gave up.
- **A rejection in StartTransaction.conf** keeps the driver's idTag and `id_tag_status`
  (`Expired`).

Which path the simulation uses therefore decides whether "split by driver" can be answered. The
author chose both, with `--authorize-probability 0.7`: realistic, and about 30% of the failures carry
the evidence. The reference has to say that the cause is visible in only part of the data.

### The scenario

The rule is in `~/github/make_loc003_auth.py`, outside git like `make_loc002.py`. The seeds are
committed on kwwhat `exp/metric_tree` as `6406656` (first `3d3e5fc`, before the rebase onto
`staging`).

| Part      | Rule                                                                                                                                                                      |
| --------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Range     | Nov 3 07:56 to Wed Nov 19 12:00: a full baseline week (Nov 3–9), a full failure week (Nov 10–16), and a partial last week (Nov 17–19)                                     |
| Chargers  | CH-003 and CH-004 continue at LOC-002 (a boot right after their copied logs end). New LOC-003 with CH-005 and CH-006, laid out like CH-003, commissioned Nov 3 08:00      |
| Drivers   | One pool: LOC-002's 20 existing idTags (so its drivers return), 30 new idTags, and 15 idTags of one eMSP, prefixed `VLT`                                                  |
| Failure   | Every `VLT` idTag is `Expired` from Nov 10 00:00 on every charger. 70% of sessions authorize online, 30% start from the local cache                                       |
| Otherwise | The same on every charger: 3 arrivals per port per day, 5% failed attempts, 2% faults. One server process for all four runs, so transaction ids are unique; one seed each |

What the marts show (built in a separate compose project, `kwwhat-type4`, because the chat-bi
container was running on `demo_duckdb-data`):

| Week                | Visits | Success | Anonymous failed | Faults | `Expired` (DeAuthorized) | `VLT` visits succeeded |
| ------------------- | -----: | ------: | ---------------: | -----: | -----------------------: | ---------------------: |
| Nov 3–9             |    143 |   91.6% |               10 |      2 |                        0 |                     30 |
| Nov 10–16           |    148 |   68.9% |               33 |      3 |                       10 |                      0 |
| Nov 17–19 (partial) |     46 |   76.1% |               10 |      0 |                        1 |                      0 |

- **Both locations drop:** LOC-002 from 87.3% to 66.7%, LOC-003 from 95.0% to 71.6%.
- **Uptime is flat at 0.80,** because CH-002's 2 of 10 ports stay offline. No charger explains the
  drop.
- **The direct evidence:** 10 of the 13 known-driver failures in the failure week are `Expired`,
  all from one group of idTags, and that group has no successful visit after Nov 10. The other 3 are
  ordinary faults, as in the baseline week. The rest shows only as anonymous failed attempts
  tripling across all four chargers. In the raw logs, which the agent can't see, 25 Authorize
  requests were answered `Expired` that week.
- **Nothing moved before Nov 3:** visits by day, uptime by charger-day and drivers hash the same as
  in the eval volume. dbt passes 369 data tests and 100 unit tests.

### Uptime ends where the data ends (kwwhat #202, merged)

`int_charger_commissioned_daily` counted a charger still in commission up to
`dbt.current_timestamp()`, so `fact_uptime_daily` ran to today and the days after the logs read as
100% up. Earlier retrospectives planned a fixed `as_of` date for this. That idea is dropped: a fixed
date only sets the commissioned span, while offline outages already end at the newest log, so the
uptime denominator and the downtime would drift apart whenever the date and the data disagreed.

The author chose the latest OCPP log timestamp instead, as other models use, through a shared
macro. #202 adds `latest_ocpp_log_ts()`: `max(ingested_timestamp)` of `stg_ocpp_logs`.
`incremental_date_range` uses it in place of its inline query, with the same compiled SQL, and open
commissioned spans end there. `dbt.current_timestamp()` is gone. `fact_uptime_daily` is identical,
row for row, to a build with the end set by hand to Nov 19 12:00. On `staging`'s own seeds, it
now ends on Nov 3.

### What the extension breaks

- **Open-ended cases:** q001, q003, q004, q007, q008 and q021–q028 ask about the whole range, so
  their answers and unbounded fingerprints now cover Nov 3–19.
- **q008's reference is wrong:** CH-002's outage now runs to Nov 19, not "until the data ends on
  Nov 3", so its 54,720 minutes grows.
- **Outdated notes:** the notes on q022 and q024 ("questions stay before Nov 3").
- **Answers unaffected:** cases bounded before Nov 3, such as q006, q020 and the dated parts of
  q022–q028. Their fingerprints are stale anyway; see below.

### Why the fingerprints drifted

q006's fingerprint (`fact_uptime_daily`, Oct 1–14) has the same row count on the rebuilt data but a
different checksum, although no number in those rows moved. The checksum, `SUM(hash(t))`, hashes the
whole row, so any column counts. Three things can move a fingerprint:

| Cause                                                                                                                                 | Affects                                                                                                                        |
| ------------------------------------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------ |
| kwwhat #200 (Nov 18): `port_id` became `CH-002-1` instead of `1`, and the surrogate keys were rebuilt                                 | every fingerprint recorded before Nov 18, on any table with those ids, whatever its date filter. q006's was recorded on Nov 11 |
| #202 and the extension to Nov 19                                                                                                      | open-ended filters, and filters that reach the end of the data                                                                 |
| Unsorted arrays: DuckDB builds `charge_attempt_ids`, `charger_ids` and `id_tags` with `list_distinct(array_agg(x))`, without an order | `fact_visits` and `fact_charge_attempts`, only when a build orders a list differently                                          |

The array order hasn't changed anything yet. Two builds of the same data gave identical checksums on
every table, and both matched the live demo. But nothing guarantees the order: it can change with
threads, DuckDB version, data size or incremental merges. Only 3 visits have more than one element,
and one of them (Nov 7, on CH-005 and CH-006) falls inside the `fact_visits` fingerprints of
q029–q031. The fix belongs in kwwhat: sort inside `array_agg_distinct` and `array_distinct`, so the
same data always gives the same table.

### The cases: q029–q031

Drafted with Claude from SQL against the rebuilt demo (in the running chat-bi container, the
backend's own path) and fingerprinted after #200 and #202. The references below are the versions
both arms ran on (study commit `7ea2b6d8`, dataset `786d5112`).

**q029: "Why did visit success drop in the week of Nov 10, 2025 compared to the week of Nov 3?"**

- **Tests:** the tree's success branch. The whole drop is in first-attempt success, 91.6% to 68.9%,
  with visits level.
- **What the reference says:**
    - The equipment didn't change: uptime was the same in both weeks, and faults went from 2 to 3.
    - The drop is spread across both locations and every charger.
    - 10 failed visits by identified drivers had their token rejected as `Expired`, so the charge was
      stopped (`DeAuthorized`) before any energy flowed. All 10 came from 7 drivers; 6 of them
      visited in the week of Nov 3, and all 10 of those visits succeeded.
    - Failed visits without an idTag rose from 10 to 33.
    - The data limit: expired tokens explain at least 10 of the 34 extra failures, likely most of
      them, but the exact share can't be measured.

**q030: "Did more drivers charge successfully on the network in the week of Nov 10, 2025 than in the
week of Nov 3?"**

- **Tests:** the tree's demand branch, and its own warning about the anonymous-driver mix.
- **What the reference says:**
    - No: 57 identified drivers had a successful visit, then 41, and no anonymous visit succeeded in
      either week.
    - 6 drivers who charged in the week of Nov 3 had every visit in the week of Nov 10 rejected
      because their token had expired.
    - Total visits barely moved (143 to 148), and anonymous visits rose from 10 to 33, all failed
      plug-ins, likely more token rejections.
    - Counting anonymous visits as drivers (68 to 82 active drivers) would be a shift from
      identified to anonymous visits, not more people.

**q031: "Did visit success recover in the week of Nov 17, 2025?"**

- **Tests:** the partial-week trap (type 6) on top of type 4. This is where the q015–q017 move now
  lives.
- **What the reference says:**
    - The week is partial: 2.5 days, ending Wed Nov 19 at 12:00.
    - 76.1% looks better, but failed visits without an idTag are still 22% of visits, the same as
      the week of Nov 10 and three times the week of Nov 3.
    - The one failed visit by an identified driver was again a token rejected as `Expired`.
    - The higher rate rests on 11 failures (no faults, one visible rejection), too few to be a trend.

### How the references changed after arm A's first runs

Each change came from reading the judge's reasons, and each is recorded in the case's notes.

- **q029, two terms for the same events.** The reference named only the token status (`Expired`).
  The judge read answers that named the stop reason (`DeAuthorized`) for the same 10 visits as a
  contradiction. It now names both.
- **q029 and q030, a group only the prefix defines.** The references described "drivers whose idTags
  start with VLT", and q029 credited the group with 30 visits the week before. The judge scored the
  prefix as a required finding, though an agent can only see it by listing tags. The references now
  use what the marts show without the prefix: the 7 drivers rejected as `Expired`, 6 of whom
  charged the week before.
- **q030, a reference that needed the tree.** It opened "Not that the data can show" and required
  the 68 to 82 reading, which only an agent using the tree's MAD definition meets. A's answers ("No,
  58 to 49") scored 0.2. The answer is now "No", led by drivers who charged successfully.
- **q030, the word "charge".** A counted drivers with any visit (58 to 49), the reference drivers
  with a successful visit (57 to 41), and the judge marked A's numbers wrong. The question now says
  "charge successfully". 8 of the 49 identified drivers that week had only failed visits.
- **q029 and q031, a charger at another location.** "Apart from CH-002, which was offline" made the
  judge read a correct "no outages at LOC-002 and LOC-003" as a contradiction. CH-002 is at LOC-001
  and had no visits. The clause is gone; the references say uptime was the same.

### A/B on q029–q031

Both arms ran from study commit `7ea2b6d8` with the same served dataset (`786d5112`), 3 trials each,
Correctness and Completeness only. A: `190000`, `190110`, `190408`. B: `191539`, `191809`,
`192057`.

| Case | Correctness A | Correctness B | Completeness A | Completeness B | Method                                                                     |
| ---- | ------------: | ------------: | -------------: | -------------: | -------------------------------------------------------------------------- |
| q029 |          0.60 |          0.57 |           0.50 |           0.57 | Found `Expired`: A in 2 of 3 trials, B in none                             |
| q030 |          0.90 |          0.57 |           0.27 |           0.43 | A answers narrowly; B's driver skill leads to cohort and mix-shift stories |
| q031 |          0.20 |          0.13 |           0.23 |           0.20 | Both call a recovery in every trial but one of A's earlier runs            |
| Mean |          0.57 |          0.42 |           0.33 |           0.40 |                                                                            |

- **The score differences are within the noise.** 3 trials per arm, pooled SDs of 0.13–0.18 on
  earlier cases, and three judge misreads (below).
- **The method differences aren't noise.** On q029, A queried the rejected drivers' token status in
  2 of 3 trials and B in none. On q030, B loaded the driver skill in every trial and two of its
  three explanations were wrong.
- **q030's Correctness can't discriminate.** A scores 0.90 in every trial with a one-query answer.
  Only Completeness separates the arms, and it rewards explaining more than the question asked.
- **Neither arm handles the partial last week.** Every trial in both arms named the partial week,
  and all but one (A, in an earlier run) still called a recovery. No trial split the failures by
  kind, so none saw that failures without an idTag stayed at 22%.

### Finding: the tree has no node for authorization

B read `metrics_tree.md` and followed its structure: first-attempt versus troubled success, and
new versus returning versus anonymous drivers. Neither leads to authorization status. Under
`success_rate`, the tree offers only first-attempt and troubled success and the support
interventions, so the reference's key evidence, `id_tag_status = Expired`, sits outside the tree.

The tree's driver node also invited readings that are wrong in this scenario:

- **"New drivers collapsed (41 to 4), which explains most of the drop"** (q030, B trials 1 and 2).
  Nearly every driver was new in the week of Nov 3, because LOC-003 opened that day and most of the
  pool was new, so a week later they count as returning (17 to 45). That isn't churn.
- **"The anonymous visit surge is a mix shift that drags the rate down"** (q029 trial 1, q030 trial
  3). The anonymous visits are the failures themselves, rejected plug-ins with no idTag, not a
  segment with a lower rate. q030 trial 3 also reported active drivers "increased 68 to 82", the
  trap the case was built for.
- **"Failures concentrate on 4 specific chargers"** (q029 trial 3). Those are all the chargers in
  use.

A, without the tree, either answered narrowly (q030) or reached the token status more often (q029).
This is a finding about what the tree covers, not about B's variance. Adding an authorization node
now would tune arm B to the dev set; if it's tested, it has to be a pre-declared variant of B,
confirmed on held-out cases.

### Shared-skill change: a step to attribute the failures

Fixing the tree on these cases would tune arm B to the dev set. The author chose instead to add a
generic step to the shared root-cause skill, which both arms get, so the A/B comparison still
isolates the tree. It goes after "Separate mix from rate", as step 6 (the later steps become 7–9):

> **6. Attribute the failures.** When a success rate moved, check success criteria, error codes, stop reasons, authorization statuses, and attempts that never started a transaction to attribute the failures.

It addresses both gaps the runs showed: no trial in B, and only some in A, looked at the rejected
drivers' token status (q029), and no trial in either arm split failures by kind (q031). It doesn't
name the scenario. Like the Network Topology bullet, it's a shared-context change made on dev
evidence (A and B on q029–q031, runs above):

- q029–q031 stay dev-only, and the whitepaper says the shared skill was developed on them.
- On these cases the step removes the room a tree would need on an authorization cause, so they
  can't show a tree effect there anymore. The tree-coverage finding stands as recorded.
- A claim about driver-side causes needs held-out cases the skill wasn't written against.

### Three judge misreads

The Correctness judge misread a correct claim three times in these runs:

1. **q029, A (`184311`, trial 2):** "no outages at LOC-002 and LOC-003" read as contradicting
   "CH-002 was offline". CH-002 is at LOC-001. This led to the CH-002 clause being removed.
2. **q029, B (`191539`, trial 1):** the reason credits the answer with finding "that the same
   drivers who succeeded in Nov 3 failed in Nov 10". The answer says nothing about those drivers
   and doesn't mention `Expired`. Its 0.7 is too high.
3. **q030, B (`191809`, trial 2):** "≈ Anonymous drivers (successful): 0 / 0" read as "anonymous
   visits were 0 in both weeks… a significant factual error". The row is correct, and the
   reference says the same. Its 0.4 is likely too low.

One misread helped B and one hurt it, so they don't explain the direction of the means. They do
mean a difference of 0.1–0.2 between arms can't be trusted until the judge is checked on these
references. The judge also didn't catch q029 A trial 3 (`190000`) counting the same 10 visits twice
(23 + 10 + 10 presented as 34).

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
- **Check what the model can see before simulating a failure.** The same auth failure is
  attributable or invisible depending on the OCPP path, because dbt can't attach Authorize to a
  charge attempt.
- **End every span at the same point.** Uptime's denominator ended now and its downtime at the last
  log. Both now come from one macro.
- **A tree only guides where it has a node.** B followed the tree to the structure of the drop and
  never reached authorization status, which the tree doesn't name. A found it on its own more often.
- **Write the reference in the data's words.** The judge read `DeAuthorized` against `Expired`, and
  an unnamed prefix, as disagreements. It can't see the notes, so whatever must count has to be in
  the reference, in terms an agent can reach from the marts.
- **A reference mustn't need the method being tested.** q030's first reference required a number
  only the tree's definition produces, so it penalised the arm without the tree for answering the
  question.

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
- Type 4, in order:
    1. Bring `staging` (#202) into kwwhat `exp/metric_tree`. Until then that branch still ends
       uptime at the current timestamp.
    2. Rebuild `demo_duckdb-data` and both arms, and check that neither manifest is `-dirty`.
    3. Re-verify the open-ended cases by SQL and recompute their fingerprints: q001, q003, q004,
       q007, q008 and q021–q028. Rewrite q008, and the notes on q022 and q024.
    4. Review q029–q031, drafted with Claude and checked by SQL against the rebuilt demo: q029 (why
       success dropped in the week of Nov 10), q030 (the rise in active drivers is anonymous
       visits), q031 (the partial week of Nov 17 is no recovery). Then run the judge check on
       hand-written answers, the solvability check and arm A's headroom on them.
    5. Retire or rewrite q015–q017. q031 now holds the partial-week trap at the end of the range.
    6. Recompute every fingerprint recorded before Nov 18: #200's id changes made them all stale,
       whatever their dates. Do it after the array sort below, so they're computed only once.
- q029–q031: run the judge check (hand-written answers per case: correct, equipment-blaming,
  cohort or mix-shift, right cause with every failure claimed as `Expired`, and vague) before
  reading A/B differences. Then a hinted solvability run for the findings no trial reached: q029's
  "the same drivers succeeded the week before", q030's successful-driver count with the rejections,
  q031's failures by kind.
- Root-cause step 6 ("Attribute the failures"): commit it, rebuild both arms, rerun A and B on
  q029–q031 to see whether it's followed, and on q022–q027 to check nothing regresses.
- For a claim on type 4: 5 or more trials per arm, alternating A, B, B, A, with `rejudge
--judge-repeats 3`.
- If an authorization node is tested in the tree, pre-declare it as a variant of B and confirm it on
  held-out cases, not on q029–q031.
- kwwhat: sort the arrays in `array_agg_distinct` and `array_distinct` on every adapter (a PR off
  `staging`, like #202), then recompute q029–q031's fingerprints.
- `payload_extract_parent_id_tag` reads `idTagInfo.idTag` from Authorize.conf. OCPP 1.6 calls the
  field `parentIdTag`, so check whether `parent_id_tag` is always null.
- Remove the `kwwhat-type4` and `kwwhat-latest-log` docker volumes once they're no longer needed.
- Carried over from 2026-11-18: add the new-driver sentence to q027's reference; q026's reference
  grain. (The fixed `as_of` date is replaced by #202, and the q015–q017 move is in the type 4
  list.)
