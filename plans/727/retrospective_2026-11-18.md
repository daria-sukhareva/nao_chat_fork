# Retrospective: unique port and connector ids, and arm B on four layout cases

**Date:** 2026-11-18
**Scope:** kwwhat #195 landed (network-unique `port_id` and `connector_id`); a check that the demo
serves the new ids; arm B re-run on q022, q023, q024 and q026, the cases where the agent had
misread the network's layout; what each answer said.
**Status:** No study files changed except this retrospective. kwwhat is at `3e22382` on
`exp/metric_tree`, on top of `c13c68b` (#195, via #200). The arm was rebuilt with study commit
`28bbc8e1`, whose `study/` folder matches `55bdd743`. Arm A has not run on this build. Snowflake
hasn't been rebuilt, so the references' `data_fingerprint` values are unchecked against the new
ids.

This follows the [2026-11-13 retrospective](retrospective_2026-11-13.md).

---

## The change

kwwhat [#195](https://github.com/appspace/kwwhat/issues/195), merged as #200 (`c13c68b`):

- `port_id` and `connector_id` are now `<charger_id>-<number>`: `CH-002-1`, `CH-002-3`. Connector
  0 is `<charger_id>-0`. The OCPP number is kept as `connector_number`; there is no `port_number`.
- Surrogate key hashes no longer include `charger_id` separately. `fact_downtime_daily` gains
  `location_id`.
- It needs `--full-refresh`.

`port_key` values didn't change: the old key hashed `'CH-002'` and `'1'` joined by `-`, the same
string as the new `port_id`. q016's reference, which quotes `3fce2a9a…`, is still right.

## The demo serves the new ids

Checked in the running container (`demo-chat-bi-run`, started 16:46):

- `/kwwhat` is at `3e22382` and has `macros/network_scoped_id.sql`; `analytics.duckdb` was
  rebuilt at 16:46 after `docker compose down -v`.
- `dim_ports` has 8 rows, `CH-001-1` … `CH-004-2`; `COUNT(DISTINCT port_id)` is 8, where it was 2.
- `dim_connectors` has `CH-001-1` … `CH-004-4`, with `connector_number` 1–4.
- `fact_visits` has 189 rows, `first_port_id` `CH-001-1` (38), `CH-002-1` (101), `CH-003-1` (25),
  `CH-004-1` (25): the counts are unchanged.
- Every `*port_id` and `*connector_id` column in the mart tables has 0 values without the charger
  prefix. The staging views over RAW weren't readable from a read-only connection; the tables
  built from them are all scoped.
- The synced context the agent reads (`/app/kwwhat/databases/…`) shows `"port_id": "CH-002-1"`.

## Results

Arm B, 2 trials per case, `--metrics correctness --metrics completeness`, judged once. Files
`evals_results_20261118_165447` (q022), `165707` (q023), `170047` (q024), `170207` (q026). All 8
trials read the root-cause skill. Cost $1.76.

Correctness/Completeness per trial, against rebuilt B on the old ids (`55bdd743`, 2026-11-13):

| Case | Old ids          | Unique ids           | Queried `dim_chargers` |
| ---- | ---------------- | -------------------- | ---------------------- |
| q022 | 0.4/0.4, 0.5/0.5 | **0.7/0.7, 0.7/0.6** | both                   |
| q023 | 0.3/0.5, 0.8/0.6 | 0.5/0.5, 0.5/0.4     | neither                |
| q024 | 0.6/0.4, 0.5/0.5 | 0.6/0.5, 0.6/0.6     | trial 2                |
| q026 | 0.7/0.5, 0.8/0.6 | 0.8/0.5, 0.7/0.5     | both                   |

With noise of about 0.07 between runs of one arm (see 2026-11-13), only q022 moved by more than
that, and its queries show why.

## What the agent answered

### q022: "Why were there no charging visits from Oct 15 to Oct 19, 2025?"

Reference: no charger was available. CH-001 was decommissioned at 07:55 on Oct 15, and CH-002,
the only charger still commissioned, went OFFLINE (NoHeartbeat) at the same moment. Uptime was 0%
from Oct 16 to Oct 19. The last visit ended at 20:38 on Oct 14. Demand in those days can't be
measured, since drivers who came while CH-002 was offline leave no record.

- **Trial 1 (0.7/0.7):** "a complete OFFLINE outage of charger CH-002 … Simultaneously, CH-001 was
  decommissioned on Oct 15 at 07:55 … there was no supply available for any driver." Names both
  CH-002 ports (CH-002-1, CH-002-2), 0% uptime Oct 16–19 with one charger in inventory, and
  LOC-002's CH-003 and CH-004 restoring supply on Oct 20. Then overreaches: "Not a demand drop —
  visit volume on Oct 20 (8 visits, 100% success) confirms latent demand was present." No 20:38.
- **Trial 2 (0.7/0.6):** "the entire operational fleet went offline simultaneously." A table of
  exactly 2 chargers and 4 ports: CH-001-1 and CH-001-2 decommissioned at 07:55, CH-002-1 and
  CH-002-2 OFFLINE (NoHeartbeat) to Nov 3; "decommissioning is not counted as downtime." Says
  "No data is missing — there were genuinely zero available ports," which contradicts the
  reference's limit on measuring demand, and guesses that LOC-002 succeeds because it is "new
  hardware that had no pre-existing failure patterns." No 20:38.

Both still used `COUNT(DISTINCT port_id)`, and it now returned 4 ports on 2 chargers before Oct 15
and 2 during Oct 16–19. On the old ids the same query returned 2 and led to "CH-002 came back".
Neither answer says that. What's left is the evidence's limits, not the layout.

### q023: "Why was network uptime so low from Oct 15 to Oct 19, 2025?"

Reference: 12.38% (1,900 of 15,350 commissioned port-minutes) against 98.64% over Oct 1–14.
CH-002's OFFLINE outage from 07:55 on Oct 15 accounts for all 13,450 downtime minutes. CH-001 was
decommissioned at the same moment, which removed its ports from commissioned minutes instead of
adding downtime. Uptime was 0% each day from Oct 16 to Oct 19.

- **Trial 1 (0.5/0.5):** "caused entirely by a single charger — CH-002 at LOC-001 — going
  OFFLINE." A day-by-day table: 100% on Oct 10–14, 49.6% on Oct 15, 0% on Oct 16–19 with 2 ports
  reporting, 56–67% from Oct 20 with 6 ports. Gets CH-002's two ports, NoHeartbeat and the ~19-day
  duration right. On CH-001: "The other charger contributed no records, suggesting it may not have
  been commissioned or tracked during that window." Concludes it "points to a network/power
  outage at the charger site" without labeling it a hypothesis. No period figure, no baseline.
- **Trial 2 (0.5/0.4):** "charger CH-002 … went completely offline at 07:55 on Oct 15 … a single
  continuous outage lasting 27,360 minutes (~19 days)." The same day-by-day table, then a charger
  split: CH-002 13,450 downtime of 14,400 commissioned minutes, CH-001 0 of 950, "CH-001 was
  unaffected throughout." Notes the outage end (`2025-11-03T07:55:00.1`) looks like a placeholder
  and that CH-002 had two short OFFLINE outages on Oct 1 and 2. No period figure, no baseline, and
  CH-001's 950 minutes aren't connected to its decommissioning.

The port counts are now right (4, then 2, then 6). The failure is that neither trial looked up
`dim_chargers`, so neither explained why CH-001's minutes stop, and neither reported the period's
rate against a baseline the question doesn't name.

### q024: "Why did the number of successful visits go up after Oct 19, 2025, compared to Oct 15–19?"

Reference: supply came back. Oct 15–19 had no successful visits (CH-001 decommissioned, CH-002
offline). On Oct 20, LOC-002's CH-003 and CH-004 added 4 ports, up 99.69% of the week of Oct 20.
That week had 38 successful visits, 19 per charger, all first-attempt, all 20 drivers new.

- **Trial 1 (0.6/0.5):** "not a reliability improvement at the same site — it is a complete
  population change." Sets the named baseline aside: "Oct 15–19 had zero visits … The natural
  comparison is Oct 1–14 (before) vs Oct 20+ (after)", then compares success rates, 25.2% (35 of 139) against 100% (50 of 50). Shows locations as hashed keys (`5d994177…`, `75f699e7…`). On Oct
  15: "CH-001 was partially commissioned on Oct 15 (950 min …) then disappears", without naming the
  decommissioning. Offers as a hypothesis that Oct 15–19 was a planned off-service window linked to
  LOC-002.
- **Trial 2 (0.6/0.6):** "a complete location substitution." Also: "Oct 15–19 is a gap, not a
  baseline … The question should really be framed against the last active period." Gets CH-001's
  decommissioning at 07:55 on Oct 15 and LOC-002's chargers at 08:00 on Oct 20, but says "LOC-001
  goes offline with 100% OFFLINE downtime", which is CH-002's outage put on the site. Decomposes
  successful visits as visits × success rate per the tree, and blames LOC-001's 74% failure on
  "CH-001/CH-002" when it was all CH-002. Reports 48 successful visits over Oct 20–31. No 4 ports,
  99.69% or 20 new drivers.

Neither answer is a layout error now. Both repeat q025's pattern from 2026-11-13: a period with no
activity, named in the question as the baseline, gets called a data gap and replaced by Oct 1–14.

### q026: "Why were there more chargers after Oct 19, 2025?"

Reference: LOC-002 was commissioned at 08:00 on Oct 20 with CH-003 and CH-004, 2 ports each. Oct
16–19 had one commissioned charger, CH-002, since CH-001 was decommissioned on Oct 15. From Oct 20
there were three chargers and six ports; commissioned port-minutes rose from 2,880 a day to 8,640
from Oct 21 (6,720 on Oct 20). The data records the commissioning, not its reason. CH-002 still
counts as commissioned, though offline.

- **Trial 1 (0.8/0.5):** "two new chargers being commissioned on October 20, 2025 — CH-003 and
  CH-004, both at LOC-002. This added 4 new ports." A timeline: CH-002 from Sep 15 (1 charger, 2
  ports), CH-001 from Oct 1 (2, 4), CH-001 decommissioned Oct 15 (1, 2), Oct 20 (3, 6).
- **Trial 2 (0.7/0.5):** the same counts: 2 chargers and 4 ports before Oct 15, 1 and 2 on Oct
  15–19, 3 and 6 from Oct 20; "decommissioning removes the charger from the inventory entirely";
  "a fleet expansion event."

Both get the layout fully right. They lose completeness on what the reference adds: port-minutes,
that the data doesn't record why, and that CH-002 counts as commissioned while offline.

## Findings

- **The rename fixed q022's layout error.** The query that misled the agent is unchanged; its
  answer is now right. That is the mechanism #195 predicted, which makes the +0.25 more than noise
  even on two trials.
- **The remaining failures aren't about ids.**
    - q023: no `dim_chargers` lookup, so CH-001's minutes stopping goes unexplained or is misread.
    - q022: overclaiming about demand.
    - q024 (and q025 before it): the named empty baseline swapped for Oct 1–14.
- **This is a before/after on arm B, not an A/B result.** The common context changed. The earlier
  arm A run on the old ids can't be paired with these.

## Lessons

- **Read the queries before the scores.** The scores moved by a noise-sized amount on three of four
  cases; the queries showed exactly which error disappeared and which remained.
- **A data fix removes a class of error; it doesn't teach the method.** Unique ids stopped the
  agent from miscounting, but not from skipping a baseline or a lookup.

---

## Still open

- Run arm A on this build (kwwhat `3e22382`, study `28bbc8e1`), then the remaining B cases (q019,
  q025, q027) so both arms cover the same set on the same ids.
- Rebuild Snowflake with `--full-refresh` and re-check every reference's `data_fingerprint`.
- The skill's step 1: check which chargers were commissioned where (q023, q024), and treat a named
  period with no activity as a valid baseline after checking supply (q024, q025). Decide after arm A.
- Give q023 a baseline ("compared to Oct 1–14").
- q025's reference wording, pending approval (from 2026-11-13).
- Size the noise before any A/B claim: `--repeats` of at least 5 and `--judge-repeats 3`.
