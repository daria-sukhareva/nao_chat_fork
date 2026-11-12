# Retrospective: a new location, an offline charger, and cases along the metrics tree

**Date:** 2026-11-12 (covers work from 2026-11-11 and 2026-11-12)
**Scope:** adding q020 (an idle charger that wasn't down); designing, generating and loading LOC-002,
the first scenario added outside LOC-001's Oct 1–14 data; rebuilding both warehouses; adding q021
(a churn claim the data can't support); keeping CH-002's silence after Oct 15 as an offline
scenario; adding q022–q027 along the metrics tree; and re-verifying the whole dev set.
**Status:** LOC-002 is committed in kwwhat (`807c80f`, `75eaca3`), loaded into Snowflake RAW and the
demo DuckDB, and built in both (`ANALYTICS.DBT_CLI_DARIA` and the chat's `analytics.duckdb`). The
dev set has 21 cases, all re-verified by SQL on 2026-11-12 with matching fingerprints (committed in `e9196d4e`).

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

The LOC-002 cases are q024–q027 below.

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

The churn claim isn't the agent's invention: the metrics tree states it as a coupling ("failed
visits → MAD. Drivers whose visit failed are less likely to come back."). So q021 also tests
whether the agent passes a tree assertion off as a finding.

---

## CH-002 goes silent on Oct 15

A chat answer said network uptime "collapsed on Oct 15–19 (0–50%) and stabilized at ~66.7% from Oct
20 onward", because CH-002 was offline. Checking it showed what LOC-002 had changed:

- CH-002's logs end on Oct 15 at 07:55, where the original 14-day data set ends. Before LOC-002,
  that was also the latest message anywhere, so the silence never showed.
- LOC-002 moved the latest message to Nov 3 at 07:55. The model counts a commissioned charger's
  silence as OFFLINE up to the latest message in the data, so CH-002 is now OFFLINE for 19 days.
- The model closes the outage at that latest message (`outage_to_ts` Nov 3, 07:55:00.1) and counts
  every later day as 100% up, through the build date.

I first read the 89% on Nov 3 and the 100% after it as CH-002 coming back, and said the chat's
"from Oct 20 onward" was wrong. The author corrected this: CH-002 sent nothing after Oct 15, so
it never came back, and the chat was right within the data. The chat's "OFFLINE for the entire
month" was still wrong for Oct 1–14, when CH-002's heartbeats arrived normally.

**Decided (author, 2026-11-12): keep it as an intended scenario.** CH-002 stopped communicating on
Oct 15 at 07:55, the same moment CH-001 was decommissioned. Questions about it stop before Nov 3.
The model's handling of an outage still open when the data ends is a kwwhat issue: a silent
charger should stay OFFLINE, or later days should be excluded, until a message says otherwise.

---

## Cases along the metrics tree

The first drafts built on the CH-002 scenario ("Was CH-002 offline for all of October?") were
rejected by the author as having "nothing to do with metrics tree". The replacements each test a
branch of `plans/727/study/arm-b/docs/metrics_tree.md`:

| Case | Question                                                          | Tree branch                                             | The point                                                                                                           |
| ---- | ----------------------------------------------------------------- | ------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------- |
| q022 | Why were there no charging visits from Oct 15 to Oct 19, 2025?    | Supply side of `total_visits`; "unobserved demand"      | No charger was available; turned-away drivers leave no record, so lost demand is unknown                            |
| q023 | Why was network uptime so low from Oct 15 to Oct 19, 2025?        | `uptime_ratio`                                          | 12.38%, all from CH-002 OFFLINE; a decommissioning removes commissioned minutes, it isn't downtime                  |
| q024 | Why did the number of successful visits go up after Oct 19, 2025? | `total_successful_visits = total_visits × success_rate` | "Because supply came back": new chargers, not better reliability (network uptime 65.37%)                            |
| q025 | Why were there more drivers after Oct 19, 2025?                   | `monthly_active_drivers = new + returning + anonymous`  | 20 + 0 + 0: new supply brought new drivers, not returning demand                                                    |
| q026 | Why were there more chargers after Oct 19, 2025?                  | `total_commissioned_minutes`                            | LOC-002 commissioned Oct 20; the data records the commissioning, not the reason                                     |
| q027 | Why did visits at LOC-002 drop in the week of Oct 27, 2025?       | Demand: `monthly_active_drivers × visits_per_driver`    | 38 → 12 with 100% success and uptime above 99.6%: fewer drivers (20 → 8), coming less often (1.9 → 1.5 visits each) |

The author singled out the sentences that make a reference good, now the house style for the
reference guide:

- the cause first, in a few words ("Because supply came back.");
- the distinction the obvious reading gets wrong ("that removed its ports from commissioned minutes
  rather than adding downtime");
- what the data can't measure ("Drivers who came while CH-002 was offline leave no record, so
  demand in those days can't be measured");
- the decomposition in plain words ("Active drivers fell from 20 to 8, and those who came, came
  less often");
- nothing outside the question's period, and no detail that wouldn't scale to a real network.

For q027, fewer drivers account for ln(8/20) ÷ ln(12/38) ≈ 79% of the drop on the tree's log scale.

---

## The dev set re-verified after LOC-002

A fingerprint check showed that every case relying on `fact_visits`, `fact_charge_attempts`,
`fact_downtime_daily`, `dim_chargers` or `dim_ports` was stale. Claim by claim:

| Case                        | Result                                                                                                                  |
| --------------------------- | ----------------------------------------------------------------------------------------------------------------------- |
| q007                        | Changed to "There are 6 commissioned ports." The author's rule: count what's commissioned now, and give the count alone |
| q008                        | Rewritten: CH-002's outage from Oct 15 is 54,720 of 55,961 downtime minutes; the 1 FAULTED minute stays                 |
| q001                        | Holds; "CH-002 is still in service" kept, since it means not decommissioned                                             |
| q003, q004, q006, q015–q020 | Hold; fingerprints only                                                                                                 |

- **The FAULTED minute is real.** On Oct 1, both connectors of CH-002 port 1 reported
  ConnectorLockFailure from 08:11:08 to 08:12:37, so the whole port was faulted. CH-002's other 100
  ConnectorLockFailures were on connector 1 only, so they aren't downtime: a port is down only when
  all its connectors are.
- **Fingerprints are now scoped to each case's period** (for example `visit_start_ts <
'2025-10-15'`), so seed additions outside it don't make them stale. All-time cases keep
  unfiltered fingerprints.

---

## Lessons

- **Check what a copy brings with it.** The copied period carried its OFFLINE periods, its
  overlapping charge attempts, and its single driver. Each one changed the result.
- **A visit depends on driver identity.** Copying the same driver to two chargers, or keeping one
  driver per charger, changes how charge attempts are grouped into visits.
- **Asides need cases of their own.** An unsupported claim inside a longer answer isn't penalized
  unless a reference addresses it.
- **Name the schema in every check.** A fully qualified query ignores `use schema`.
- **Extending the data's time range changes old answers.** LOC-002 moved the end of the data, and
  CH-002's silence turned into an outage. Any later seed extension must be checked against every
  all-time reference.
- **Read silence carefully.** A day with no messages isn't a day of uptime; I took the model's 100%
  after Nov 3 as a recovery, and it wasn't.
- **Cases should test the tree, not facts about the data.** A case earns its place when a branch of
  the tree decides the right answer.

---

## Still open

- The exploratory run of q019 and q022–q027 on arms A and B (both arms must be rebuilt: the
  current arm still carries the 12-case dataset).
- The kwwhat issue for an outage still open when the data ends (closed at the latest message, later
  days counted as 100% up).
- The remaining new types: a sustained fault onset, auth or driver-side failures. And a fixed
  `as_of` date in `int_charger_commissioned_daily.sql`.
- A `--full-refresh` of `DBT_PROD`, if prod is used.
- The kwwhat issue for a fault reported after a stop, if wanted.
- Carried over: the generation rule and reference guide, the pilot and sizing, threshold
  calibration, arm D, the A/B pairing files, two misleading messages, `persist_docs`.
