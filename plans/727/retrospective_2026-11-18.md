# Retrospective: unique ids, and getting the agent to check what was commissioned

**Date:** 2026-11-18
**Scope:** kwwhat #195 landed (network-unique `port_id` and `connector_id`); a check that the demo
serves the new ids; arm B re-run on q022, q023, q024 and q026, the cases where the agent had
misread the network's layout; what each answer said. In the afternoon: why the agent kept
misreading CH-001's missing rows in q023, and four attempts to fix it (a corrected grain, table
docs, a `RULES.md` rule, a Network Topology bullet in the skill).
**Status:** kwwhat is at `ad83493` on `exp/metric_tree`: #195 (`c13c68b`), the uptime grain
description (#201, `b7e54d7`), `persist_docs` (`0043e94`) and the `marts.yml` rule (`ad83493`). The
skill's Network Topology bullet is uncommitted, so the last runs' manifest reads
`815cadd0-dirty`. Arm A has not run on any of this. Snowflake hasn't been rebuilt, so the
references' `data_fingerprint` values are unchecked against the new ids.

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

## Afternoon: what a missing row means

### The worry

Two q023 answers explained CH-001's missing rows wrongly: "may not have been commissioned or
tracked" (a guess) and "CH-001 was unaffected throughout" (true numbers, 950 commissioned minutes
and 0 downtime on Oct 15, around a wrong claim). Both come from reading the absence of rows in
`fact_uptime_daily` without checking `dim_chargers`, which states `decommissioned_ts = 2025-10-15
07:55`. The q024 and q025 baseline errors are the same reading: an empty period taken for missing
data.

What the agent's context said:

- Every `columns.md` under `databases/` said "_No description available._": kwwhat didn't set
  `persist_docs`.
- `marts.yml` described `fact_uptime_daily` as "One row per Port per day", but rows exist only
  while a port is commissioned (the model builds them from `int_charger_commissioned_daily`, which
  keeps days with `commissioned_minutes > 0`).
- The demo's `RULES.md` pointed to `marts.yml` in the second half of the SQL rule. Across all 64
  trials from Nov 12 to 18, `marts.yml` was read in 18, against 50 for `semantic_models.yml`.
- `dim_chargers/preview.md` already showed CH-001's `decommissioned_ts`. Neither trial opened it.

"Unaffected throughout" is worth naming in the write-up: a true number wrapped around a wrong
claim reads as a finding, and the judge took off only part of the score.

### Changes, in order

1. **The grain (kwwhat #201).** `fact_uptime_daily` in `marts.yml`: "One row per Port per day while
   the port is commissioned … No row means the port was not commissioned that day: before its
   charger's commissioned_ts or after its decommissioned_ts (see dim_chargers). It is not missing
   data, and it is not downtime."
2. **`persist_docs`** (`relation: true, columns: true`) in `dbt_project.yml`. Tested in a separate
   compose project: 100 of 100 models and tests passed, 24 of 26 mart tables got a comment, and
   fact and dim columns got theirs. **Gap:** nao's DuckDB sync reads table descriptions only from
   `duckdb_tables()`, and `fact_uptime_daily` is a view (`materialized='view'`, from #177), so its
   `columns.md` still says "_No description available._" Column descriptions do sync.
3. **A `RULES.md` rule**, its own line after the semantic-model rule: "Before querying a table, read
   its entry in `repos/kwwhat/models/marts/marts.yml`. It states the table's grain and what a
   missing row means." Kept: the author finds it sensible.
4. **A Network Topology bullet in the skill's step 1**, written by the author:

    > **Network Topology:** which locations, chargers and ports were in commission in each period.
    > Look up `commissioned_ts` and `decommissioned_ts` in `dim_chargers` before hypothesising what
    > happened. A charger counts only between its commissioning and decommissioning, so a charger
    > with no rows outside that window isn't missing data. Understand what equipment was in the
    > field before interpreting signals or missing data.

    "For every charger" was proposed and declined: a real network can be very large.

### q023 under each context

All arm B, 3 trials per run except the first.

| Context                             | File              | Trials | Queried `dim_chargers` | Named CH-001's decommissioning | Correctness/Completeness  |
| ----------------------------------- | ----------------- | ------ | ---------------------- | ------------------------------ | ------------------------- |
| Unique ids only                     | `20261118_165707` | 2      | 0                      | 0                              | 0.5/0.5, 0.5/0.4          |
| + table docs                        | `181332`          | 3      | 1                      | 0                              | 0.5/0.5, 0.4/0.5, 0.4/0.5 |
| + table docs (stale arm, see below) | `184838`          | 3      | 1                      | 1                              | 0.4/0.4, 0.4/0.5, 0.7/0.7 |
| + `marts.yml` rule                  | `185909`          | 3      | 0                      | 0                              | 0.6/0.5, 0.4/0.4, 0.5/0.5 |
| + rule + Network Topology bullet    | `192413`          | 3      | 3                      | 2                              | 0.4/0.5, 0.7/0.6, 0.7/0.8 |

What each run's answers said about CH-001:

- **Table docs (`181332`).**
    - Trial 1: "CH-001 remained at 100% throughout … CH-001's ports dropped out of the commissioned window (partial day on Oct 15)".
    - Trial 2: read `dim_chargers/columns.md` and queried the table, but only `WHERE charger_id = 'CH-002'`; said nothing about CH-001.
    - Trial 3: "CH-002 stopped appearing in the commissioned set once it went dark", which pins CH-001's disappearance on the wrong charger.
    - Two of three reported 12.38% for the period, against a baseline they chose (Oct 8–14, 99.95%).
- **Table docs, replicate (`184838`).**
    - Trial 1: "CH-001 … was not yet fully commissioned on those days" and "appears to have been commissioned around Oct 20", which is CH-003 and CH-004's date.
    - Trial 2: "CH-001 was absent from the uptime fact on those days (possibly explained by how commissioned minutes roll up when a charger has an active outage spanning the full day)", an invented mechanism.
    - Trial 3 read `dim_chargers/columns.md`, queried it, and wrote "CH-001 (the other 2-port charger at LOC-001) was decommissioned at 07:55 on Oct 15 — the exact same timestamp CH-002 went offline", labeling the shared timestamp as a hypothesis (a site-level event). It was the first q023 trial to get this.
- **`marts.yml` rule (`185909`).**
    - All 3 trials read `marts.yml` before their first SQL query, so the corrected grain was in context each time. None queried `dim_chargers`.
    - Trial 1: "CH-001 had no commissioned minutes (it appears to have been decommissioned or not yet re-registered after Oct 15)", hedged and unchecked.
    - Trial 2: "the other 2 ports, belonging to CH-001, stay at 100%".
    - Trial 3: "2 ports fully down, 2 ports up … the other 2 ports' uptime is simply zero".
    - Agent cost $0.75 against $0.59 for the docs-only run, about 25% more.
- **Rule + Network Topology bullet (`192413`).**
    - Trial 1 queried `dim_chargers` for CH-002 only and said nothing about CH-001.
    - Trial 2 queried CH-002, then CH-001: "The drop in commissioned minutes on Oct 15 is explained by CH-001 being decommissioned at 07:55 on Oct 15 (intentional, not an outage) … CH-002 was the only remaining commissioned charger".
    - Trial 3 queried all chargers: "CH-001 was decommissioned at 07:55 (its `decommissioned_ts = 2025-10-15T07:55:00`)", with the Oct 15 split (475 minutes each, 49.6%) and the shared timestamp as a hypothesis.
    - No trial invented a reason for the missing rows.

### q024 with the rule and the bullet

File `20261118_192854`, 3 trials, $0.64. Earlier today, on unique ids only: 0.6/0.5, 0.6/0.6.

- **Trial 1 (0.7/0.4).**
    - Gave a table of all four chargers with commissioning and decommissioning dates: CH-001 decommissioned Oct 15, CH-002 "still up, but offline", CH-003 and CH-004 from Oct 20.
    - Still set the named baseline aside: "There are zero visits on Oct 15–19 in the data. The correct comparison is" Oct 1–14.
- **Trial 2 (0.9/0.6).**
    - "CH-001 was decommissioned on Oct 15 at 07:55, which explains the data gap Oct 15–19"; LOC-002's CH-003 and CH-004 came online "on Oct 20 at 08:00", with 19 and 19 successful visits.
    - Also compared against Oct 1–14.
    - Wrong: "CH-002 was also fully OFFLINE … from Oct 1 onward" (from Oct 15).
- **Trial 3 (0.6/0.5).**
    - An event table: CH-001 decommissioned Oct 15 07:55, CH-002 OFFLINE from Oct 15, CH-003 and CH-004 commissioned Oct 20 08:00.
    - Kept Oct 15–19 as a row with 0 visits: "This is not a data quality issue — it is explained by the topology".
    - Wrong: CH-001 is "the charger that was causing most failures" (CH-002 was).

All three queried `dim_chargers` and named both events. Completeness still misses the reference's
4 ports at 99.69%, 38 successful visits in the week of Oct 20 (only trial 2 found them) and the
20 new drivers.

### A stale arm, again

`184838` was meant to test the rule but ran without it: `arm/RULES.md` and `arm.json` were from
11:45, before the rule, and the manifest check passed because both were stale together. The same
trap as 2026-11-13. The run is kept as a replicate of the table-docs condition. A proposed fix:
`build-arm.sh` records the kwwhat commit and a hash of the demo's `RULES.md`, and `nao evals
--arm-manifest` fails when either differs from what is served.

### Findings

- **Putting the fact in front of the agent wasn't enough.** With the corrected grain read in 3 of
  3 trials, or `dim_chargers`'s docs available in 6, the agent named CH-001's decommissioning in 1
  of 9 trials, and every trial that skipped the lookup invented a reason.
- **A step that asks for the lookup was.** With the bullet, every trial queried `dim_chargers`, and
  5 of 6 across q023 and q024 named the decommissioning, against 2 of 13 before it. No trial
  invented a reason. With 3 trials per case and noise of about 0.07 this is behavior, not yet a
  score claim.
- **What remains is a lookup's scope and the baseline.** One q023 trial looked up only the charger
  it suspected. Two of three q024 trials still replaced the empty Oct 15–19 baseline with Oct 1–14:
  the bullet explains why a period is empty, but not that it is still a valid baseline.
- **The rule and the bullet are confounded** in the last two runs. The rule alone gave 0 of 3.
- **None of this is about the tree.** Every change is in the context both arms share; arm A hasn't
  run on it.

## Lessons

- **Read the queries before the scores.** The scores moved by a noise-sized amount on three of four
  cases; the queries showed exactly which error disappeared and which remained.
- **A data fix removes a class of error; it doesn't teach the method.** Unique ids stopped the
  agent from miscounting, but not from skipping a baseline or a lookup.
- **Knowing a definition isn't checking a fact.** The agent read that a missing row means "not
  commissioned" and still didn't ask which ports were missing or why. A step that names the lookup
  changed the behavior; documentation of what it would find didn't.
- **Check the served file, not the manifest.** A stale arm with a stale `arm.json` passes the check.
  `grep` the arm and the container for the change before running.

---

## Still open

- Commit the skill's Network Topology bullet, so the manifest isn't `-dirty`.
- Decide on a baseline clause for the bullet ("A period with no activity is still a valid baseline
  when the question names it"); test on q024 and q025.
- Run arm A on this build, then the remaining B cases (q019, q022, q025, q026, q027) so both arms
  cover the same set on the same context.
- `fact_uptime_daily` is a view, so its description doesn't sync: materialize it as a table (check
  why #177 made it a view) or rely on the rule.
- Make `build-arm.sh` and `nao evals --arm-manifest` catch a stale arm (kwwhat commit and
  `RULES.md` hash).
- Count `marts.yml` reads and `dim_chargers` lookups per trial in the analysis, separately from the
  scores.
- Rebuild Snowflake with `--full-refresh` and re-check every reference's `data_fingerprint`.
- Give q023 a baseline ("compared to Oct 1–14").
- q025's reference wording, pending approval (from 2026-11-13).
- Size the noise before any A/B claim: `--repeats` of at least 5 and `--judge-repeats 3`.
