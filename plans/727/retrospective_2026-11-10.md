# Retrospective: a charger fault injected into the seed, and the first case built on it

**Date:** 2026-11-10
**Scope:** correcting the pass-threshold claim in the 2026-11-08 retrospective; injecting the first
new root-cause type into the demo seed (a fault on the working charger); rebuilding the pipeline;
checking the chat agent's answer against the data; and adding q019 to the dev set.
**Status:** The seed edits are committed in kwwhat (`265bb5b`, `ef12587`) and loaded into Snowflake
RAW and the demo DuckDB. q019 is appended to `golden_dataset.jsonl` (uncommitted). The other dev
references are stale and not yet re-verified.

This follows the [2026-11-08 retrospective](retrospective_2026-11-08.md).

---

## The pass-threshold claim, corrected

The 2026-11-08 retrospective said the placeholder Correctness threshold of 0.5 passes the
wrong-mechanism q018 answer and "must be at least 0.6". That used scores judged against the old list
reference (0.4, 0.5, 0.5, which pass two of three times, since a score equal to the threshold
passes). Against the prose reference q018 uses now, the wrong answer scored 0.4, 0.3, 0.3 and fails,
while the lowest right answer scored 0.7. So 0.5 separates them on q018, with a margin of 0.2 on
either side, measured on one case. The "at least 0.6" had no basis and was removed; the threshold is
still calibrated in Phase 4.

---

## Injecting a fault on the working charger

The demo data held about one phenomenon (CH-002's persistent ConnectorLockFailure plus a mix
shift). The first new type tried was a fault on CH-001, the charger that otherwise succeeds on every
visit, so that a charger's own rate falls rather than the mix changing.

### Iterations

| Version                                                   | CH-001 on Oct 6–7 | Site, Oct 6 / Oct 7 | Verdict                                                      |
| --------------------------------------------------------- | ----------------- | ------------------- | ------------------------------------------------------------ |
| One failure on Oct 6, `Faulted` after the stop            | 2/3, 4/4          | 20% / 40%           | Looks like noise; the failure carries no error code          |
| Every CH-001 visit failing on one or two days             | Not built         | 0%                  | A clear outage; considered, not chosen                       |
| One failure on Oct 6, two on Oct 7, fault before the stop | 2/3, 2/4          | 20% / 20%           | Chosen: a real signal at charger level, hidden at site level |

- **The count of failures decides whether it's a signal.** One failure among 3–4 visits a day
  can't be told from chance. Three failures in 7 visits, against 31 of 31 on CH-001's other days,
  has a chance of about 0.4% of landing on those two days at random (C(7,3)/C(38,3) = 35/8436).
- **The site rate hides it.** 20% on both days is inside the 10–40% the site moves through daily,
  so the fault only shows when the rate is split by charger. The mix was normal (3 of 10 and 4 of
  10 visits went to CH-001).
- **It pairs with Oct 13.** Oct 13 is also a low day (0%), but from a mix shift: every visit went
  to CH-002. Same kind of drop, different root cause.
- **It's a transient fault, not a fault onset.** CH-001 recovers on Oct 8. An onset would need the
  failures to continue to the end of the period.

### Making the failure diagnosable

In the first version, the `Faulted / WeakSignal` StatusNotification came one second after the
StopTransaction. `fact_charge_attempts` then gave transaction 1014 `next_status = 'Charging'` and no
error code; it failed only because its stop reason, `Other`, isn't a valid stop reason. The success
rule checks `next_status != 'Faulted'`, which suggests a post-stop fault is meant to count against
the charge attempt, but `next_status` doesn't see it.

The author moved each `Faulted / WeakSignal` before its StopTransaction (transactions 1014, 1016,
1018). All three failed charge attempts and their visits now carry `last_error_code = WeakSignal`.
An issue for the post-stop attribution was drafted for the kwwhat repo and not filed.

### Rebuilding the pipeline

- **Incremental models skip edited history.** The first `dbt build` passed but left transaction
  1014 as `EVDisconnected` and successful. `dbt build --full-refresh` was needed. Any seed edit to
  past dates needs a full refresh.
- **Two warehouses.** The author loads RAW in Snowflake, which feeds the dev dbt target. The chat
  agent reads the demo DuckDB, built from the CSV seed by `demo/run-demo.sh`. Both must be rebuilt,
  and references must be checked against the one the agent reads.
- **`dbt show` returns 5 rows by default.** A check of Oct 6–7 seemed to be missing transactions
  1016 and 1018 until `--limit` was raised.

---

## The chat agent's answer

Asked about CH-001 on Oct 6–7, the agent (arm B, with the metrics tree) answered:

| Claim                                                               | Against the data                                                                                           |
| ------------------------------------------------------------------- | ---------------------------------------------------------------------------------------------------------- |
| Oct 6: first-attempt success fell from 100% to 33%                  | Right (1 of 3), but the 100% is one visit on Oct 5; 31 of 31 is the better baseline                        |
| Oct 7: 2 of 4 visits failed                                         | Right                                                                                                      |
| Oct 8: recovered, 67% first-attempt success                         | Right (3 of 3 succeeded, 2 on the first attempt)                                                           |
| "The charger was never faulted or offline"                          | Half right: the charger stayed in service, but port 1 reported `Faulted / WeakSignal` before every failure |
| Causes: "transaction failures, authorization errors, firmware…"     | A guess; the error code was one query away, and it only offered to check it                                |
| "A classic case of the uptime/reliability decoupling" from the tree | Right: uptime is unaffected by design while one port fails charge attempts                                 |

The main conclusion is right and the central cause is missing, which is the Correctness 3–5 band.
The tree gave the agent the right frame (reliability can fall while uptime holds), but the agent
stopped at the frame: it read "no downtime" as "no fault" and guessed causes instead of reading the
error codes.

**Resolved: a fault on one port isn't downtime (decided by the author, 2026-11-11).** Downtime is
recorded only when a charger can't serve a charge, meaning all its ports are faulted or offline at
the same time. CH-001 has two ports and only port 1 faulted, so `fact_downtime_daily` correctly has
no rows for Oct 6–7. A correct answer may say that uptime was unaffected; it must not say that
nothing faulted.

---

## q019 added to the dev set

> **Did CH-001's reliability change on Oct 6–7, 2025?**
>
> Yes. CH-001's reliability dropped on Oct 6–7, 2025: 3 of its 7 visits failed, against 31 of 31 on
> its other days, and it recovered on Oct 8. All three failed visits ended with the WeakSignal
> error, a wireless communication fault. The counts are small, 3 and 4 visits a day.

- Every claim checked by SQL against the chat's DuckDB on 2026-11-10.
- Drafted with Claude and edited by the author, who removed the sentence about a normal mix.
- Fingerprint: `fact_visits`, 139 rows, checksum `1293473797168323812778`.
- The question wording was chosen to fit the reference's "Yes."; the question actually asked of the
  chat wasn't recorded.

### What the injection broke

The fault was injected into LOC-001 between Oct 1 and Oct 14, 2025, against the plan's constraint
for extending the seed. CH-001 is now 35 of 38, not 38 of 38.

| Case       | Why it's stale                                               |
| ---------- | ------------------------------------------------------------ |
| q001       | States CH-001 succeeded on all 38 of its visits              |
| q015–q018  | State CH-001's 100% or 38/38; old `fact_visits` checksum     |
| q006       | Failed charge attempt rate (102 of 141) has likely changed   |
| q002, q003 | Old `fact_visits` checksum; q003's claim is expected to hold |

---

## Lessons

- **Check the injected scenario in the marts, not the seed.** The CSV edit looked right, but the
  first build kept the old values, and the first fault carried no error code.
- **A scenario needs enough failures to be a signal and an error code to be diagnosable.** Without
  both, the right answer is "noise" or "unknown cause", which doesn't test root cause analysis.
- **Check the agent's negative claims.** "Never faulted" was true of the charger's uptime and
  false of the port's status; the agent didn't say which it meant.
- **Every seed change invalidates fingerprints.** Re-verify the dev set after each one, not at the
  end.

---

## Still open

- Re-verify q001, q002, q003, q006 and q015–q018 by SQL, and update their fingerprints.
- File the kwwhat issue for a fault reported after a stop not being attached to the charge
  attempt, if wanted. (Whether a one-port fault counts as downtime is resolved: it doesn't.)
- Record the question asked of the chat for q019, or confirm the chosen wording.
- Whether the plan's constraint (leave LOC-001 Oct 1–14 untouched) still holds, given this
  injection.
- The remaining new root-cause types: a sustained fault onset, auth or driver-side failures, a
  demand change. And a fixed `as_of` date in `int_charger_commissioned_daily.sql`.
- Carried over: the generation rule and reference guide, the pilot and sizing, threshold
  calibration, arm D, the A/B pairing files, two misleading messages, `persist_docs`.
