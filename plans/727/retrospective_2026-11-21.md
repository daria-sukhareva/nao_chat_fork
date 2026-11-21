# Retrospective: the failure modes go into the semantic layer, and A/B on q029–q031 after kwwhat #204

**Date:** 2026-11-21
**Scope:** arm B on q029–q031 with the new root-cause step 6 ("Attribute the failures"); why it
still didn't reach the expired tokens; kwwhat #204, which puts authorization in the success criteria,
adds `failure_reason`, makes attempts in progress neutral and exposes both in the semantic layer; a
build from the wrong checkout; and both arms on q029–q031 on the #204 build.
**Status:** all runs are 3 trials per case, Correctness and Completeness only, dataset `786d5112`,
study commit `79d201f8` (step 6), clean manifests. B on step 6 alone: `20261119_210727`, `211005`,
`211321`. On the #204 build: B `20261121_154658`, `154900`, `155127`; A `160149`, `160259`,
`160459`. kwwhat #204 is merged to `staging` (`0a9b3c1`) and is in `exp/metric_tree`, which was
rebased onto `staging` (type 4 seeds now `bd04570`). A was never run on step 6 alone, so A's #204
runs carry two changes at once.

This follows the [2026-11-19 retrospective](retrospective_2026-11-19.md).

---

## Step 6 on B: followed in form, one level short

Step 6 of the shared root-cause skill, as the author wrote it: "When a success rate moved, check
success criteria, error codes, stop reasons, authorization statuses, and attempts that never started
a transaction to attribute the failures."

| B, step 6 alone | Correctness | Completeness | What happened                                                                                            |
| --------------- | ----------: | -----------: | -------------------------------------------------------------------------------------------------------- |
| q029            |        0.53 |         0.50 | every trial split failures by kind; none went past the stop reason `DeAuthorized`                        |
| q030            |        0.57 |         0.53 | root-cause skill not loaded (driver skill only); two trials opened "Yes, more active drivers (68 to 82)" |
| q031            |        0.20 |         0.20 | step 6 never reached; every trial called a recovery                                                      |

On q029 the step made B consistent (0.5–0.6, against 0.4–0.7 before) but not more right: 0 of 3
trials found `Expired`, the same as before.

## Why it stopped: the semantic layer didn't name the field

`Expired` is in `fact_charge_attempts.id_tag_status`, the status the central system returned in
StartTransaction.conf. B's trial 1 had joined the right tables on the visit's last attempt and
grouped failed visits by `transaction_stop_reason` and `next_status`. One column more gives the
answer:

| Week   | Stop reason    | Next status | `id_tag_status` | Visits | Drivers |
| ------ | -------------- | ----------- | --------------- | -----: | ------: |
| Nov 10 | `DeAuthorized` | Finishing   | `Expired`       |     10 |       7 |
| Nov 10 | `Other`        | Charging    | Accepted        |      3 |       3 |
| Nov 10 | (none)         | Available   | (null)          |     33 |       0 |

The `charge_attempts` semantic model exposed `transaction_stop_reason` and `next_status` as
dimensions, but not `id_tag_status`, and attempts had no driver entity. Both arms read
`semantic_models.yml` to see what failures can be split by, so they split by stop reason, found
`DeAuthorized`, and stopped there. Step 6 names "authorization statuses", but the agent had no
dimension for them.

## kwwhat #204: the success criteria, made explicit

Built with Claude on `feat/attempt-failure-reason` off `staging`, each design point decided by the
author; merged as `0a9b3c1`, with ADRs 0013 and 0014.

**Authorization is a success criterion.** An attempt whose `id_tag_status` is anything but
`Accepted` is not successful. An attempt that never tried to authenticate has a null status, which
is neither rejected nor accepted; the condition says so explicitly (`is not null and != 'Accepted'`)
rather than relying on SQL's null comparison.

**`failure_reason`** on `fact_charge_attempts`: the most specific criterion the attempt failed, and
`is_successful` is derived from it. The author set the order so that `NO_TRANSACTION`, the least
descriptive, comes last:

| Order | `failure_reason`      | The attempt failed because                                                             |
| ----: | --------------------- | -------------------------------------------------------------------------------------- |
|     1 | `AUTH_REJECTED`       | the central system rejected the id_tag in StartTransaction.conf                        |
|     2 | `FAULTED_AFTER`       | the connector's next status after Preparing was `Faulted`                              |
|     3 | (neutral)             | its transaction is open: not failed, not successful                                    |
|     4 | `INVALID_STOP_REASON` | its transaction stopped with a reason other than `Local`, `Remote` or `EVDisconnected` |
|     5 | `LOW_KWH`             | its transaction's energy is missing or at most 0.1 kWh                                 |
|     6 | `NO_TRANSACTION`      | the connector left Preparing without a transaction, and nothing more specific applies  |

**Attempts in progress are neutral** (row 3 above, and a second case after row 6): `is_successful` and
`failure_reason` are both null while the transaction is open, and, from the author's criterion,
while there is no transaction and the connector hasn't left Preparing (`next_status` null). Once the
charger reports its next status, something happened or didn't, and the attempt can be judged. A
rejection or a fault still fails an attempt in progress. A first draft labelled open transactions
`NOT_STOPPED` and failed them; the author ruled that an open transaction is neutral.

**Reliability rates may not add up to 1** (ADR 0014). With neutral visits in the denominator,
`first_attempt_success_rate + troubled_success_rate + failed_rate` can be less than 1. A first draft
added a `completed_visits` denominator to keep them exhaustive. The author rejected it: a
denominator of known outcomes hides a subset of attempts that never reaches one, and a gap that
doesn't close also surfaces bad metric design, such as cutting rates by when attempts started.

**Aggregate by when things stop.** Visits already used `visit_end_ts`; the author made it the rule,
and `charge_attempts` moved from `charge_attempt_start_ts` to `charge_attempt_stop_ts`. All four
timestamps now say which to use.

**Semantic model.** `failure_reason` and `id_tag_status` are dimensions of `charge_attempts`, and
visits reach them through `charge_attempt` (the last attempt). `is_successful` reads the column
instead of repeating the expression, and failed counts use `not is_successful`.

**Tests.** 10 new unit tests and `failure_reason` asserted in 6 existing ones; two consistency tests
replace the `not_null` tests on `is_successful`. The demo build passed with 31 models, 370 data tests
and 110 unit tests on `staging`'s seeds and on the type 4 seeds. MetricFlow showed no new issues (4
`location_id` dimension errors on `ports` and `connectors` are already on `staging`). sqlfluff wasn't
run: its dbt templater needs the Snowflake profile.

**On the type 4 data,** no attempt changed outcome, but the failures now read:

| `failure_reason`      | Attempts | Of which                                                                         |
| --------------------- | -------: | -------------------------------------------------------------------------------- |
| `FAULTED_AFTER`       |      102 | CH-002's 101 ConnectorLockFailures, before filed as no transaction; 1 WeakSignal |
| `NO_TRANSACTION`      |       53 | 10, 33 and 10 in the three type 4 weeks, all Preparing to Available              |
| `AUTH_REJECTED`       |       11 | all `Expired`                                                                    |
| `INVALID_STOP_REASON` |        8 | stop reason `Other` (the generator's faults)                                     |

## A build from the wrong checkout

The first run on #204 failed with `Unknown command "evals"`. The kwwhat main checkout was on
`staging`, where the chat-bi Dockerfile is `FROM getnao/nao:latest` (upstream nao-core 0.4.6,
without `evals`) and has no `COPY arm/`; the study branch is `FROM nao:study`. The rebuilt data was
`staging`'s too: last visit Nov 2, 189 visits. Switching back to `exp/metric_tree` and rebuilding
the data, the arm and the image fixed it. The demo mounts the checkout, so the agent sees whatever
branch it's on.

## A/B on q029–q031 after #204

| Case | Correctness A | Correctness B | Completeness A | Completeness B | Method                                                                    |
| ---- | ------------: | ------------: | -------------: | -------------: | ------------------------------------------------------------------------- |
| q029 |          0.57 |          0.67 |           0.57 |           0.60 | both found `Expired` in 3 of 3, by `failure_reason` then `id_tag_status`  |
| q030 |          0.97 |          0.50 |           0.27 |           0.47 | A answers in one query; B's driver skill adds context inside wrong frames |
| q031 |          0.23 |          0.20 |           0.23 |           0.23 | both call a recovery in every trial; neither splits failures              |
| Mean |          0.59 |          0.46 |           0.36 |           0.43 |                                                                           |

Against the last build before step 6 (`7ea2b6d8`: Correctness A 0.57, B 0.42; Completeness A 0.33,
B 0.40):

- **#204 fixed q029's method in both arms.** `Expired` went from 2 of 3 trials (A) and 0 of 3 (B)
  to 3 of 3 in each. Every trial grouped failures by `failure_reason` early. The scores moved within
  the noise (B 0.57 to 0.67, A flat).
- **The pattern between the arms is unchanged.** A is more correct, B more complete. A shared fix
  helps both arms; it doesn't create a tree effect.
- **q030 doesn't reach the new fields.** B answers it with the driver skill only and A with one
  query; neither asks why drivers failed. B's misreadings persist: "new drivers collapsed (40 to 3)"
  (they were nearly all new the week before, so they now count as returning), and a made-up
  "driver success rate" of 57/68 to 41/82 that mixes identified and anonymous drivers.
- **q031 is untouched.** 0 of 18 trials across both arms and three builds held back from calling a
  recovery. Every trial named the short week (46 visits, data to Nov 19) and none split failures.
  One B trial even offered "drill into failure reasons" as a follow-up.
- **What's left on q029 is shared.** No trial checked that the rejected drivers had charged the week
  before, and none connected the `NO_TRANSACTION` surge to the rejections: all called the two
  "independent". One A trial came close, quoting the new `marts.yml` note that a rejected Authorize
  can't be attached to an attempt. One B trial (0.4) blamed the surge on hardware, which the
  equipment data rules out.

### A fourth judge misread

A's q029 trial 1 (`160149`): the Completeness reason credits the answer with noting "that 6 of 7
affected drivers had successful visits the prior week". It doesn't; the only nearby 6 is "LOC-002 (6
rejections)". So no run in either arm has reached that finding. With the three in the 2026-11-19
retrospective, that's four misreads on these three cases.

## Lessons

- **An agent splits by what the semantic layer names.** Step 6 listed authorization statuses, but
  without a dimension the agent stopped at the stop reason the layer did expose.
- **Fix the definition, not the prompt.** One column, `failure_reason`, did what a skill step
  couldn't, and did it for both arms.
- **A shared fix doesn't create a tree effect.** #204 moved A and B together on q029. Only
  arm-specific context can show what the tree adds.
- **A method change only helps the questions that reach it.** q029 ("why did it drop") reaches the
  failure split; q030 and q031 ("did more drivers", "did it recover") don't.
- **Unknown is not failed.** An attempt in progress is neutral, and rates that don't add up to 1
  show what is still undecided instead of hiding it.
- **Check the checkout before the build.** The demo builds and mounts whatever branch the kwwhat
  checkout is on.

---

## Still open

- q029: no trial has found that the rejected drivers charged the week before, or linked the
  `NO_TRANSACTION` surge to the rejections. Run the hinted solvability check before keeping both in
  the reference.
- q031: no change in the shared context reaches it. Consider a shared rule for a rate that rises in
  a partial period: compare failure modes, not the headline rate. Pre-declare it, as with step 6.
- q030: Correctness can't discriminate (A at 0.97). Record it as a case only Completeness separates.
- Run the judge check on hand-written answers for q029–q031 before reading A/B differences: four
  misreads so far.
- Re-verify the references and recompute every fingerprint on `fact_charge_attempts` and
  `fact_visits`, q029–q031 included: #204 adds columns and relabels CH-002's failures as
  `FAULTED_AFTER`, which q022–q028's answers will now show. Do the kwwhat array sort first.
- Record that A never ran on step 6 alone, so step 6's and #204's effects on A can't be separated.
- kwwhat, from #204: unit tests for a fault during an open transaction, a stopped transaction with no
  stop reason, and the `Blocked`, `Invalid` and `ConcurrentTx` statuses; whether a missing stop
  reason should count as `Local` (OCPP 1.6 allows omitting it); the 4 MetricFlow `location_id`
  errors on `ports` and `connectors`; sqlfluff with a working profile.
- Remove the `kwwhat-type4`, `kwwhat-latest-log` and `kwwhat-fr` docker volumes and the
  `kwwhat-failure-reason`, `kwwhat-latest-log` and `kwwhat-generator-auth` worktrees once no longer
  needed.
- Carried over from 2026-11-19: everything in its Still open list not done here, including the
  baseline clause, Faithfulness truths, the q028 trigger, q026's grain, the array sort, the A/B
  protocol (at least 5 trials per arm, alternating), and keeping any tree authorization node as a
  pre-declared variant of B.
