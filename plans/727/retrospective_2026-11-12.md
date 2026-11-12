# Retrospective: a demand drop at a new location, and two cases from the existing data

**Date:** 2026-11-12 (covers work from 2026-11-11 and 2026-11-12)
**Scope:** adding q020 (an idle charger that wasn't down); designing, generating and loading LOC-002,
the first scenario added outside LOC-001's Oct 1–14 data; rebuilding both warehouses; and adding
q021 (a churn claim the data can't support).
**Status:** LOC-002 is committed in kwwhat (`807c80f`, `75eaca3`), loaded into Snowflake RAW and the
demo DuckDB, and built in both (`ANALYTICS.DBT_CLI_DARIA` and the chat's `analytics.duckdb`). q020
is committed in `23748f23`; q021 is uncommitted. The dev set's fingerprints are not yet re-checked
after the LOC-002 rebuild.

This follows the [2026-11-10 retrospective](retrospective_2026-11-10.md).

---

## q020: idle isn't down

The author noticed that CH-001 had no visits on Oct 13, 2025. That's not a demand change at the
site level, since the site had 10 visits as usual; all 10 went to CH-002. But it tests a step no
other case does: checking availability before explaining zero use.

- CH-001 was in service all day: 288 heartbeats, status `Available` from Oct 12 at 19:11 until
  its next visit, 100% uptime on both ports, and no downtime rows.
- CH-001 takes 27% of visits (38 of 139), so none of 10 has a chance of 0.73^10, about 4%.
- It succeeded on all 4 of its visits on Oct 14.

> **Was CH-001 down on Oct 13, 2025?**
>
> No. CH-001 was in service all day on Oct 13, 2025: both of its ports had 100% uptime and no fault
> or offline time. It simply had no visits; all 10 visits that day went to CH-002, which failed
> every one, so the site's success rate was 0%. CH-001 takes about a quarter of visits, so getting
> none of 10 is unusual but can happen by chance, and the data doesn't show why drivers chose
> CH-002. CH-001 succeeded on all 4 of its visits the next day.

It needed no seed change, and it overlaps q015–q017's partial week, of which Oct 13 is the most
extreme day of the mix shift.

---

## LOC-002: a demand drop with reliability unchanged

### The design

| Choice                                          | Why                                                                                                                                |
| ----------------------------------------------- | ---------------------------------------------------------------------------------------------------------------------------------- |
| A new location, LOC-002, with CH-003 and CH-004 | LOC-001 stays as it is; its broken CH-002 would turn any demand change into another mix shift                                      |
| Oct 20 – Nov 2, 2025, commissioned Oct 20       | Two full weeks starting on a Monday; clear of every Oct 1–14 reference, and of `fact_uptime_daily` for Oct 1–14                    |
| Questions scoped to LOC-002                     | Network-level questions would mix in LOC-001's end of data on Oct 14 and the empty Oct 15–19                                       |
| The cause of the drop isn't in the data         | The correct answer is "demand fell, reliability didn't, and the data can't say why"; the agent must not invent a reliability cause |

### The generation rule

The author proposed copying a clean CH-001 period rather than writing messages by hand. Every
committed version of the seed has CH-002 failing every visit, so only CH-001 was copied, from
`f7ec32d`, the version before any injected failures, to both new chargers:

- Shifted by 19 days (Oct 1–15 becomes Oct 20–Nov 3).
- Message IDs, `idTag` and `transactionId` get a suffix per charger (`-ch003`, `-ch004`).
  `transactionId` is cast to a string in the models, and `fact_charge_attempts.transaction_id`
  has a uniqueness test, so the suffix is required.
- Week of Oct 27: only the first visit of each day is kept. Every other visit's messages and their
  responses are removed; heartbeats are always kept, so week 2 shows no OFFLINE time.
- Reference rows (chargers, connectors, ports) copied from CH-001's.

The script, `make_loc002.py`, lives outside the repo (`~/github/`), appends to the seed CSVs
matching each file's line endings (CRLF for the logs, LF for the rest), and refuses to run twice.
The author loaded RAW in Snowflake; the reference rows were inserted with SQL that skips chargers
already present.

### What went wrong along the way

- **Overlapping charge attempts.** On Oct 8, a second Preparing came before transaction 1021
  stopped, and transaction 1023's meter values and stop came after the first Available. The first
  rule, which removed messages between Preparing and Available, left an orphaned StopTransaction.
  The rule now also removes every message carrying a dropped transaction's ID.
- **One driver per charger merged two visits.** CH-001 in `f7ec32d` has a single `idTag`, so each
  copy had one driver. Two successful attempts 34 minutes apart on Oct 25 became one visit, and a
  troubled success, which would have changed q003. The author gave CH-003 and CH-004 ten unique
  `idTag`s each, with no overlap; the visits separated again.
- **The wrong Snowflake schema.** A check of `dbt_prod.fact_charge_attempts` returned 141 rows,
  because the query named `DBT_PROD`; dev builds go to `ANALYTICS.DBT_CLI_DARIA`. `DBT_PROD` needs
  its own `--full-refresh` to pick up the CH-001 edits of 2026-11-10.

### The result

Both warehouses match: 191 charge attempts and 189 visits.

| Charger | Oct 20–26                             | Oct 27–Nov 2                        | Uptime, wk 1 / wk 2 |
| ------- | ------------------------------------- | ----------------------------------- | ------------------- |
| CH-003  | 19 visits, all successful, 10 drivers | 6 visits, all successful, 4 drivers | 99.69% / 99.90%     |
| CH-004  | 19, all successful, 10 drivers        | 6, all successful, 4 drivers        | 99.69% / 99.90%     |

- Visits fell from 38 to 12 (−68%), with 100% success in both weeks and fewer drivers.
- Uptime isn't identical: the copy carries the model's small OFFLINE periods from Oct 1, 2 and 11
  (20, 10 and 10 minutes per port). A reference should say uptime stayed above 99.6%.
- Nov 1 has no visits, because Oct 13 had none on CH-001.
- LOC-001 is unchanged: CH-001 35 of 38, CH-002 0 of 101.
- LOC-002's uptime rows run to the build date, as LOC-001's do; questions need fixed date ranges.

No LOC-002 case has been written yet.

---

## q021: a churn claim the data can't support

In a chat answer, the agent added: "drivers with failed visits are less likely to return". It's
domain knowledge stated as a finding. As an aside, it gets past Correctness, which doesn't penalize
claims the reference neither supports nor contradicts; a direct question makes it gradable.

- 101 of LOC-001's 104 failed visits, all on CH-002, have no driver ID: ConnectorLockFailure
  happens before the driver is identified.
- The other 3, on CH-001 on Oct 6–7, belong to three drivers who all came back (3, 2 and 1 times)
  and charged successfully.

> **Are drivers with failed visits at LOC-001 less likely to return?**
>
> The data can't show that. 101 of the 104 failed visits at LOC-001, all on CH-002, have no driver
> ID, because they failed before the driver was identified, so whether those drivers came back is
> unknown. The other 3 failed visits, on CH-001 on Oct 6–7, 2025, belonged to three different
> drivers, and all three came back and charged successfully later in the period. Three drivers are
> too few to say anything about churn, and the data covers only Oct 1–14, 2025.

Drafted with Claude and accepted by the author as is.

---

## Lessons

- **Check what a copy brings with it.** The copied period carried its OFFLINE periods, its
  overlapping charge attempts, and its single driver. Each one changed the result.
- **A visit depends on driver identity.** Copying the same driver to two chargers, or keeping one
  driver per charger, changes how charge attempts are grouped into visits.
- **Asides need cases of their own.** An unsupported claim inside a longer answer isn't penalized
  unless a reference addresses it.
- **Name the schema in every check.** A fully qualified query ignores `use schema`.

---

## Still open

- Re-run the fingerprint check on the dev set after the LOC-002 rebuild; re-verify what changed.
  q007 (4 ports becomes 8) is expected to change, and the fingerprints of q019 and q020 are stale.
- Write the LOC-002 cases: why visits dropped in the week of Oct 27, 2025, and whether the drop was
  a reliability problem.
- The small exploratory run of q019 on arms A and B.
- The remaining new types: a sustained fault onset, auth or driver-side failures. And a fixed
  `as_of` date in `int_charger_commissioned_daily.sql`.
- A `--full-refresh` of `DBT_PROD`, if prod is used.
- The kwwhat issue for a fault reported after a stop, if wanted.
- Carried over: the generation rule and reference guide, the pilot and sizing, threshold
  calibration, arm D, the A/B pairing files, two misleading messages, `persist_docs`.
