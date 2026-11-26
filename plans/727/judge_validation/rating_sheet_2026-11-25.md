# Blind rating sheet, 2026-11-25

The second blind sheet: 20 answers from the dev pilot (2026-11-23, after the stop and recovery rules), none of them on the first sheet. Rate each answer before opening `rating_key_2026-11-25.json`. The sheet has no arm labels or tool traces. Order is shuffled (seed 20261125). Answers are verbatim except that citation tags are reduced to their numbers. References are the short references in the dataset as of 2026-11-25.

## Scales

Score both on **0 to 1, in steps of 0.1**.

**Correctness.** Judge the claims the answer makes. Penalize every claim that is false about the data, whether or not the reference mentions it, and details that are accurate but misleading in context. Do not penalize omissions or wording.

- 0–0.2: the main conclusion is wrong, or the answer makes no substantive claim about what the question asks.
- 0.3–0.5: the main conclusion is right, but a central value, entity or cause is wrong, or several claims are false.
- 0.6–0.8: the main conclusion and central claims are right; one or two minor claims are wrong or misleading.
- 0.9–1: no claim is false, and none is misleading.

**Completeness.** Does the answer address each part of the question and cover each element of the reference? Penalize omissions, partial answers and deflection heavily; do not penalize correct extra detail.

Rate the whole answer, not only its conclusion. Where the answer gives a count, check that it is the same quantity as the reference's before calling it wrong (successful visits against total visits, a daily figure against a period figure). For each item, fill in both scores and a one-line note naming the claim that set the score.

---

## S01

**Question:** Was CH-001 down on Oct 13, 2025?

**Reference:** No. CH-001 was in service all day on Oct 13, 2025, with 100% uptime. It simply had no visits: all 10 went to CH-002, which failed every one. The data doesn't show why drivers chose CH-002.

**Answer:**

> **CH-001 was not recorded as down on Oct 13, 2025** — but here's the full picture:
>
> **Charger status on Oct 13, 2025:**
>
> - CH-001 was **commissioned** on Oct 1, 2025 and **decommissioned** on Oct 15, 2025, so it was in the field on that date.
> - **No downtime records** exist in `fact_downtime_daily` for Oct 13 — meaning no OFFLINE (missed heartbeat) or FAULTED outages were logged.
> - **Zero charge attempts** were recorded that day either.
>
> The absence of both downtime events and charge attempts is worth noting — it could mean the charger was simply idle, or that there's a data gap. There's no evidence in the data of a formal outage on Oct 13.

| Correctness (0–1) | Completeness (0–1) | Note |
| ----------------- | ------------------ | ---- |
|                   |                    |      |

---

## S02

**Question:** Did visit success recover in the week of Nov 17, 2025?

**Reference:** No, the data can't show a recovery. The week is partial, since the data ends on Nov 19 at 12:00, and the cause of the drop continues: failed visits without an idTag are 22% of visits, the same share as in the week of Nov 10. The higher success rate, 76.1% against 68.9%, rests on 11 failed visits and isn't a trend.

**Answer:**

> Here is the full analysis:
>
> ---
>
> ## Metrics at a Glance
>
> | Metric       | Week of Nov 3 (baseline) | Week of Nov 10 (drop) | Week of Nov 17 (recovery?) | Change (Nov 10 → Nov 17) |
> | ------------ | ------------------------ | --------------------- | -------------------------- | ------------------------ |
> | Total Visits | 143                      | 148                   | 46                         | –102                     |
> | Success Rate | 91.6%                    | 68.9%                 | 76.1%                      | **+7.2 pp**              |
> | Failed Rate  | 8.4%                     | 31.1%                 | 23.9%                      | –7.2 pp                  |
>
> ---
>
> ## Conclusion: Partial recovery, not full
>
> The success rate rose 76.09% in the week of Nov 17, up +7.2 pp from the Nov 10 drop (68.9%), but it has **not returned to the baseline of 91.6%** — it remains 15.5 pp below pre-drop levels. The recovery is real but incomplete.
>
> ---
>
> ## Path Through the Breakdown
>
> ### 1. Data completeness flag
>
> The Nov 17 week only has data through Nov 19 (3 days vs a full 7-day week), giving just 46 visits vs 148 the week before. The rate is still meaningful, but the low count means more uncertainty.
>
> ### 2. What caused the Nov 10 drop
>
> The drop was driven by two things that appeared simultaneously:
>
> - **NO_TRANSACTION** failures surged: 10 → 33 (+23)
> - **AUTH_REJECTED** failures appeared from zero → 10 (new failure mode)
>
> Together those 36 extra failures pushed the rate from 8.4% to 31.1%.
>
> ### 3. What recovered and what didn't
>
> | Failure reason      | Nov 3 | Nov 10 | Nov 17 | Recovered?                |
> | ------------------- | ----- | ------ | ------ | ------------------------- |
> | NO_TRANSACTION      | 10    | 33     | 10     | ✅ Yes — back to baseline |
> | AUTH_REJECTED       | 0     | 10     | 1      | ✅ Mostly — nearly gone   |
> | INVALID_STOP_REASON | 2     | 3      | 0      | ✅ Yes                    |
>
> NO_TRANSACTION is back to its baseline count of 10, and AUTH_REJECTED nearly disappeared (10 → 1). **Both causes of the Nov 10 spike have largely resolved.**
>
> ### 4. Why the rate is still below baseline
>
> The remaining 23.9% failure rate is driven almost entirely by **NO_TRANSACTION at LOC-003** (9 of 11 total failures), which had 13 NO_TRANSACTION failures at Nov 10 and still had 9 at Nov 17. LOC-003's NO_TRANSACTION problem pre-existed the spike and **has not fully recovered**.
>
> Meanwhile, **LOC-002 did fully recover**: it had 27 failures (66.7% success) in the week of Nov 10 and only 1 failure (94.1% success) in the week of Nov 17 — essentially back to its baseline.
>
> ---
>
> **Summary:** The spike that caused the Nov 10 drop (AUTH_REJECTED + NO_TRANSACTION surge at both locations) has largely resolved. LOC-002 is fully recovered. The rate is still below the 91.6% baseline because LOC-003 continues to run a persistent NO_TRANSACTION failure rate that existed even before the drop.

| Correctness (0–1) | Completeness (0–1) | Note |
| ----------------- | ------------------ | ---- |
|                   |                    |      |

---

## S03

**Question:** Did CH-001's reliability change on Oct 6–7, 2025?

**Reference:** Yes. CH-001's reliability dropped on Oct 6–7, 2025: 3 of its 7 visits failed, against none on its other days, and it recovered on Oct 8. The failures came from a fault on the charger, a WeakSignal communication error. The counts are small, 3 and 4 visits a day.

**Answer:**

> **Yes — CH-001's reliability degraded materially on Oct 6–7.**
>
> ---
>
> ## Metrics at a Glance
>
> | Metric                     | Oct 4–5 (before) | Oct 6–7 (during) | Change       |
> | -------------------------- | ---------------- | ---------------- | ------------ |
> | Total visits               | 5                | 7                | —            |
> | First attempt success rate | 100.0%           | 42.9%            | **−57.1 pp** |
> | Troubled success rate      | 0.0%             | 14.3%            | +14.3 pp     |
> | Failed rate                | 0.0%             | 42.9%            | **+42.9 pp** |
>
> ---
>
> ## Root Cause Analysis
>
> ### 1. Change is real
>
> CH-001 was commissioned Oct 1 and decommissioned Oct 15 — it was fully in service on both comparison windows. Sample sizes are small (5 vs 7 visits) but the signal is clean: 0 failures before, 3 failures during.
>
> ### 2. Metric decomposition
>
> Success rate = first_attempt_success_rate + troubled_success_rate.
>
> - First attempt success rate fell from **100% → 42.9%** (−57.1 pp) — the dominant driver.
> - Troubled success rate rose +14.3 pp (one more driver retried and succeeded), partially offsetting.
> - Net: success rate dropped from **100% → 57.1%**, with failed rate climbing from **0% → 42.9%**.
>
> ### 3. Failure attribution
>
> All 3 failed visits share the **same failure signature**:
>
> - **Failure reason:** `INVALID_STOP_REASON` (transaction stopped for a reason other than Local/Remote/EVDisconnected — e.g. PowerLoss or EmergencyStop)
> - **Error code:** `WeakSignal` on every failed attempt
>
> ### 4. Concentration
>
> 100% of the Oct 6–7 failures occurred on **port CH-001-1** (the only port active). No other ports or chargers are involved — the issue is fully concentrated on this single port.
>
> ### 5. No FAULTED/OFFLINE downtime
>
> The `fact_downtime_daily` table returned no rows for CH-001 on Oct 4–8, confirming the port was not marked offline or faulted — consistent with the `uptime_ratio ↔ success_rate` decoupling described in the metrics tree: the port kept heartbeating, but charge attempts were stopping abnormally.
>
> ---
>
> ## Hypothesis
>
> A connectivity degradation (`WeakSignal`) on Oct 6 caused transactions on CH-001-1 to stop with an invalid stop reason (likely `PowerLoss` or a comms-initiated `Other`), rather than a driver-initiated stop. The charger stayed "up" from a heartbeat perspective, but was unable to complete sessions cleanly. By Oct 8, the failed rate returns to 0%, suggesting the issue was transient (2-day window).

| Correctness (0–1) | Completeness (0–1) | Note |
| ----------------- | ------------------ | ---- |
|                   |                    |      |

---

## S04

**Question:** Why was network uptime so low from Oct 15 to Oct 19, 2025?

**Reference:** Because CH-002 went offline (NoHeartbeat) on Oct 15 and stayed offline: network uptime was 12.38% from Oct 15 to Oct 19, against 98.64% from Oct 1 to Oct 14. From Oct 16, CH-002 and its 2 ports were all that was commissioned. CH-001's decommissioning on Oct 15 added no downtime; it removed CH-001's ports from the count.

**Answer:**

> Here is the full root-cause breakdown:
>
> ---
>
> ## Conclusion: CH-002 went completely offline on Oct 15 and stayed down
>
> The network uptime drop was caused by a **single charger — CH-002 at LOC-001 — going fully offline (no heartbeats) starting at 07:55 on Oct 15, 2025.** Both of its ports (CH-002-1 and CH-002-2) were taken down simultaneously, and the outage lasted until at least Nov 19, 2025 — a continuous OFFLINE event of **~844 hours**.
>
> ---
>
> ### Path through the breakdown
>
> | Finding              | Detail                                                                                           |
> | -------------------- | ------------------------------------------------------------------------------------------------ |
> | **Downtime type**    | 100% OFFLINE (`NoHeartbeat`) — the charger stopped sending heartbeats entirely, not a port fault |
> | **Charger affected** | CH-002, LOC-001                                                                                  |
> | **Ports affected**   | Both ports: CH-002-1 and CH-002-2                                                                |
> | **Other chargers**   | No other charger contributed any downtime Oct 15–19                                              |
> | **Outage start**     | Oct 15, 2025 at 07:55                                                                            |
> | **Outage end**       | Still ongoing as of Nov 19, 2025 (data cutoff) — 844 hours+                                      |
>
> ---
>
> ### Why it was so severe — the fleet context matters
>
> At 07:55 on Oct 15, two things happened simultaneously:
>
> - **CH-001** (the other LOC-001 charger) was **decommissioned** (its `decommissioned_ts` is 2025-10-15 07:55).
> - **CH-002** went **offline**.
>
> This meant that from Oct 15 onward, **CH-002's 2 ports were the only commissioned ports at LOC-001**, and CH-003/CH-004 (LOC-002) and CH-005/CH-006 (LOC-003) weren't yet commissioned until Oct 20 and Nov 3 respectively. So during Oct 15–19, **CH-002 was essentially the entire active fleet** — when it went down, **network uptime collapsed to 0%** on Oct 16–19 (both ports fully down all day, 2880 downtime minutes out of 2880 commissioned minutes each day).
>
> ---
>
> ### What is still unexplained
>
> The data shows **what** happened (charger stopped heartbeating) but not **why**:
>
> - Connectivity/network issue at the LOC-001 site?
> - Hardware failure on CH-002?
> - Deliberate shutdown coinciding with CH-001 decommissioning?
>
> The simultaneous timing with CH-001's decommissioning is suspicious — it may point to a site-level intervention (power cut, network reconfiguration). This would need operational/maintenance logs to confirm.

| Correctness (0–1) | Completeness (0–1) | Note |
| ----------------- | ------------------ | ---- |
|                   |                    |      |

---

## S05

**Question:** Was CH-001 down on Oct 13, 2025?

**Reference:** No. CH-001 was in service all day on Oct 13, 2025, with 100% uptime. It simply had no visits: all 10 went to CH-002, which failed every one. The data doesn't show why drivers chose CH-002.

**Answer:**

> **No, CH-001 was not down on Oct 13, 2025.** Here's the full picture:
>
> - **Commissioned:** Oct 1, 2025 → Decommissioned: Oct 15, 2025, so the charger was in service on Oct 13.
> - **No downtime records:** `fact_downtime_daily` has zero rows for CH-001 on that date — no OFFLINE (heartbeat loss) or FAULTED outages were logged.
> - **No charge activity:** there were also zero charge attempts recorded that day, which is worth noting — the charger was up but idle.
>
> In short, the charger was operational on Oct 13, 2025, just not in use.

| Correctness (0–1) | Completeness (0–1) | Note |
| ----------------- | ------------------ | ---- |
|                   |                    |      |

---

## S06

**Question:** Why did visits at LOC-002 drop in the week of Oct 27, 2025?

**Reference:** Because fewer drivers came, not because of a reliability problem. Visits at LOC-002 fell from 38 in the week of Oct 20 to 12 in the week of Oct 27, while every visit in both weeks succeeded and uptime stayed above 99.6%. Active drivers fell from 20 to 8, and the data doesn't show why.

**Answer:**

> Here is the full picture:
>
> ---
>
> ## Root Cause: Ports 2 (CH-003-2 and CH-004-2) Were Not Yet Online
>
> ### 1. The drop is real
>
> Visits at LOC-002 fell from 38 in the week of Oct 20 to 12 in the week of Oct 27 — a **–26 visit decline (–68%)**, then rebounded sharply to 63 the following week.
>
> ### 2. The cause: only 2 of 8 connectors were active during the drop week
>
> The location has two chargers (CH-003, CH-004), each with 2 ports and 2 connectors per port — **8 connectors total**. The data shows:
>
> | Week   | Active Connectors           | Visits |
> | ------ | --------------------------- | ------ |
> | Oct 20 | 2 (CH-003-1, CH-004-1 only) | 38     |
> | Oct 27 | 2 (CH-003-1, CH-004-1 only) | 12     |
> | Nov 3  | **8 (all connectors)**      | 63     |
>
> Connectors CH-003-2, CH-003-3, CH-003-4, CH-004-2, CH-004-3, and CH-004-4 had **zero activity until Nov 3** at the earliest — this is when Port 2 on each charger began serving drivers (connectors -3 and -4). The NACS connectors (-2) only came online on Nov 4.
>
> ### 3. So why was the Oct 27 week lower than Oct 20 even with the same 2 connectors?
>
> Both weeks had only 2 active connectors (one per charger). The Oct 20 week averaged **~5.4 visits/day** but Oct 27 averaged just **~1.9 visits/day** — using the same hardware. The daily pattern during Oct 27–Nov 2 shows a **rigid 2 visits/day** ceiling (always one visit on CH-003-1 and one on CH-004-1, happening at the exact same timestamp each day). This strongly suggests the two single-connector ports were operating at or near capacity with the available drivers, and the Oct 20 week — which was the **first week the chargers were commissioned** (commissioned_ts = Oct 20) — may have had a ramp-up burst of activity.
>
> ### 4. The recovery confirms it
>
> From Nov 3, all 8 connectors came online and visits jumped to 63 — a **5× increase** vs. the constrained Oct 27 week. The capacity expansion unlocked latent demand.
>
> ---
>
> **Conclusion:** The visit drop in the week of Oct 27 reflects the location operating with only 1 connector per charger (2 total) during its first two weeks — Port 2 and its connectors were not yet commissioned. The recovery on Nov 3 coincides exactly with Ports 2 (and additional connectors) going live. The Oct 27 week was not anomalous; it was simply the constrained baseline before the full hardware became available.

| Correctness (0–1) | Completeness (0–1) | Note |
| ----------------- | ------------------ | ---- |
|                   |                    |      |

---

## S07

**Question:** Did charging demand recover in the week of Oct 20, 2025, compared to the week of Oct 6?

**Reference:** The data can't show it, because the two weeks cover different sites. Every visit in the week of Oct 20 was at LOC-002, which opened that day, by drivers who were all new. LOC-001 had no working charger after Oct 14, so its demand left no record. So 38 visits against 69 is new demand at a new location, not LOC-001's demand recovering or falling.

**Answer:**

> ## Metrics at a Glance
>
> The comparison is **not apples-to-apples** — the two weeks cover entirely different locations. That is the most important finding.
>
> | Metric                     | Week of Oct 6 (LOC-001) | Week of Oct 20 (LOC-002) | Change       |
> | -------------------------- | ----------------------- | ------------------------ | ------------ |
> | Total visits               | 69                      | 38                       | −44.9%       |
> | Successful visits          | 19                      | 38                       | +100%        |
> | Failed visits              | 50                      | 0                        | −100%        |
> | Success rate               | 27.5%                   | 100.0%                   | **+72.5 pp** |
> | Failed rate                | 72.5%                   | 0.0%                     | −72.5 pp     |
> | First-attempt success rate | 24.6%                   | 100.0%                   | +75.4 pp     |
> | Troubled success rate      | 2.9%                    | 0.0%                     | −2.9 pp      |
>
> ---
>
> ## Why the Comparison Cannot Answer the Question Directly
>
> **Network topology changed between the two weeks:**
>
> - **LOC-001** had chargers CH-001 and CH-002. CH-001 was **decommissioned on Oct 15**, just before the Oct 20 window. LOC-001 had **zero visits** in the week of Oct 20.
> - **LOC-002** was a **brand-new site** — both its chargers (CH-003 and CH-004) were **commissioned on Oct 20**, the exact start of that week. All 38 visits in the Oct 20 week are from this new location's first week of operation.
>
> This means the two weeks are observing **different physical infrastructure**. The apparent "recovery" is actually the opening of a new site, not a rebound at the same location.
>
> ---
>
> ## What the Data Does Show
>
> **LOC-001 (the site active in the Oct 6 week):**
>
> - Struggled severely: 50 of 69 visits failed — a 72.5% fail rate. CH-001 was decommissioned on Oct 15, suggesting those reliability problems may have contributed to its removal.
> - Driver mix was dominated by anonymous visits (47 of ~57 active drivers), with only 6 returning authenticated drivers.
>
> **LOC-002 (the site active in the Oct 20 week):**
>
> - Perfect first-week reliability: 38 successful visits, 0 failures, 100% first-attempt success rate.
> - All 20 known drivers were new to the network — consistent with a site opening.
>
> **Conclusion:** Charging demand did **not recover** in the conventional sense. LOC-001's problems were still unresolved when it went quiet after Oct 15, and the Oct 20 week's healthy metrics reflect a new location, not a turnaround. To assess whether demand recovered, you would need to compare LOC-001 (or the whole network) in the Oct 20 week — but LOC-001 generated zero visits after decommissioning CH-001.

| Correctness (0–1) | Completeness (0–1) | Note |
| ----------------- | ------------------ | ---- |
|                   |                    |      |

---

## S08

**Question:** Did more drivers charge successfully on the network in the week of Nov 10, 2025 than in the week of Nov 3?

**Reference:** No, fewer drivers charged successfully: 57 identified drivers had a successful visit in the week of Nov 3, and 41 in the week of Nov 10. Drivers still came, but some had their charges refused because their tokens had expired. Anonymous visits rose from 10 to 33 and none succeeded. Counting each anonymous visit as a driver would show more drivers, but that is a shift from identified to anonymous visits, not more people.

**Answer:**

> **No — fewer drivers charged successfully in the week of Nov 10 than in the week of Nov 3.**
>
> | Metric                      | Week of Nov 3 | Week of Nov 10 | Change             |
> | --------------------------- | ------------- | -------------- | ------------------ |
> | Unique drivers (successful) | 57            | 41             | −16 drivers (−28%) |
> | Successful visits           | 131           | 102            | −29 visits (−22%)  |
> | Total visits                | 143           | 148            | +5 visits          |
> | Success rate                | 91.6%         | 68.9%          | **−22.7 pp**       |
>
> The drop is notable: total visits were actually slightly _higher_ in the week of Nov 10 (+5), but successful visits fell sharply. Failed visits jumped from 12 to 46 — a near 4× increase — which drove the success rate down by 22.7 pp. This warrants investigation into what caused the spike in failures.

| Correctness (0–1) | Completeness (0–1) | Note |
| ----------------- | ------------------ | ---- |
|                   |                    |      |

---

## S09

**Question:** Did CH-001's reliability change on Oct 6–7, 2025?

**Reference:** Yes. CH-001's reliability dropped on Oct 6–7, 2025: 3 of its 7 visits failed, against none on its other days, and it recovered on Oct 8. The failures came from a fault on the charger, a WeakSignal communication error. The counts are small, 3 and 4 visits a day.

**Answer:**

> **Yes — CH-001's reliability degraded significantly on Oct 6–7, 2025, then recovered.**
>
> ---
>
> ## Metrics at a Glance
>
> | Metric                     | Oct 1–5 (baseline) | Oct 6–7 (event) | Oct 8–14 (recovery) |
> | -------------------------- | ------------------ | --------------- | ------------------- |
> | Total visits               | 12                 | 7               | 19                  |
> | First-attempt success rate | 100%               | 42.9%           | 94.7%               |
> | Failed rate                | 0%                 | 42.9%           | 0%                  |
> | Change vs baseline         | —                  | **−57.1 pp**    | +51.8 pp vs event   |
>
> ---
>
> ## Breakdown
>
> **Step 1 — Change is real.**
> CH-001 was commissioned on **2025-10-01** and decommissioned on **2025-10-15**, so both periods are fully within its operational window. The drop covers 7 visits, which is small but all cleanly resolved (no nulls / in-progress).
>
> **Step 2 — What drove the failures?**
>
> On Oct 6–7, there were **3 failed attempts** (out of 7 total):
>
> | Date  | Failure reason        | Error code   | Count |
> | ----- | --------------------- | ------------ | ----- |
> | Oct 6 | `INVALID_STOP_REASON` | `WeakSignal` | 1     |
> | Oct 6 | `FAULTED_AFTER`       | `WeakSignal` | 1     |
> | Oct 7 | `INVALID_STOP_REASON` | `WeakSignal` | 2     |
>
> All 3 failures are associated with a **`WeakSignal`** error code. The connector faulted or stopped with an invalid reason every time a `WeakSignal` error was present — none of the 4 successful attempts on those days had any error code.
>
> **Step 3 — Downtime.**
> No `FAULTED` downtime was recorded on Oct 6–7. The brief offline events on Oct 1–2 and Oct 11 (10–20 min each, `NoHeartbeat`) are unrelated.
>
> **Step 4 — Recovery.**
> From Oct 8 onward, the failed rate returned to 0% and no `WeakSignal` errors appear. The `WeakSignal` condition appears to have been transient.
>
> ---
>
> **Conclusion:** The Oct 6–7 degradation (−57.1 pp in first-attempt success rate) is concentrated in `WeakSignal` connectivity errors causing `FAULTED_AFTER` and `INVALID_STOP_REASON` failures. The root cause is a 2-day connectivity issue on CH-001 that resolved on its own by Oct 8. Sample size is small (7 visits), so the rates are directionally strong but not statistically certain.

| Correctness (0–1) | Completeness (0–1) | Note |
| ----------------- | ------------------ | ---- |
|                   |                    |      |

---

## S10

**Question:** Did more drivers charge successfully on the network in the week of Nov 10, 2025 than in the week of Nov 3?

**Reference:** No, fewer drivers charged successfully: 57 identified drivers had a successful visit in the week of Nov 3, and 41 in the week of Nov 10. Drivers still came, but some had their charges refused because their tokens had expired. Anonymous visits rose from 10 to 33 and none succeeded. Counting each anonymous visit as a driver would show more drivers, but that is a shift from identified to anonymous visits, not more people.

**Answer:**

> **No — fewer drivers charged successfully in the week of Nov 10 than in the week of Nov 3.**
>
> ## Metrics at a glance
>
> | Metric                           | Week of Nov 3 | Week of Nov 10 | Change         |
> | -------------------------------- | ------------- | -------------- | -------------- |
> | Drivers who charged successfully | 57            | 41             | **−16 (−28%)** |
> | — New drivers                    | 40            | 3              | −37            |
> | — Returning drivers              | 17            | 38             | +21            |
> | — Anonymous drivers              | 0             | 0              | —              |
> | Successful visits                | 131           | 102            | −29 (−22%)     |
>
> **Active drivers dropped from 57 to 41** — a fall of 16 drivers (−28%).
>
> ### Key pattern: a dramatic shift in driver mix
>
> The headline drop is almost entirely explained by a **collapse in new drivers** (40 → 3), while **returning drivers nearly doubled** (17 → 38). This is a striking composition shift:
>
> - In the week of Nov 3, new drivers made up **70% of all successful drivers** — unusually high. This may reflect a promotion, an event, or simply the early period in the data (history starts Oct 1, so drivers who look "new" in Nov 3 may have charged before data collection began — treat new counts in these early weeks with some caution).
> - In the week of Nov 10, returning drivers dominated at **93%**, which is a more typical pattern.
>
> The **net result** is fewer total drivers and fewer successful visits in the Nov 10 week, but the returning base is growing, which is a healthy sign.

| Correctness (0–1) | Completeness (0–1) | Note |
| ----------------- | ------------------ | ---- |
|                   |                    |      |

---

## S11

**Question:** Why did the number of successful visits go up after Oct 19, 2025, compared to Oct 15–19?

**Reference:** Because supply came back: LOC-002 opened on Oct 20 with CH-003 and CH-004, while LOC-001 still had no working charger. There were no successful visits from Oct 15 to Oct 19, and 38 in the week of Oct 20, all at LOC-002. This is new supply, not LOC-001 recovering.

**Answer:**

> Here is the complete root-cause analysis.
>
> ---
>
> ## Root Cause: Equipment Swap — Faulty CH-002 Retired, Two New Chargers Commissioned
>
> ### Metrics at a Glance
>
> | Metric                        | Oct 1–14 (before)     | Oct 20+ (after) | Change       |
> | ----------------------------- | --------------------- | --------------- | ------------ |
> | Total visits / day (avg)      | ~10                   | ~6.4            | −3.6         |
> | Successful visits / day (avg) | ~2.5                  | 6.4             | +3.9         |
> | Success rate                  | 25.2%                 | **100%**        | **+74.8 pp** |
> | Dominant failure reason       | FAULTED_AFTER (72.7%) | None            | Eliminated   |
>
> ---
>
> ### Step 1 — The change is real, but the periods cover different equipment
>
> The data has **no visits from Oct 15–19** at all. This aligns exactly with the inventory:
>
> - **CH-001** (LOC-001): commissioned Oct 1, **decommissioned Oct 15** — explains the data gap
> - **CH-002** (LOC-001): commissioned Sep 15, still active through Oct 14
> - **CH-003 & CH-004** (LOC-002): both **commissioned Oct 20** — start of the "after" period
>
> This is **not a gap in data** — it is a real gap in activity. The fleet at this point had no commissioned chargers between Oct 15 and Oct 20.
>
> ---
>
> ### Step 2 — Decomposing the success rate change
>
> The improvement is 100% explained by a **charger swap**, not by any organic improvement in an existing charger:
>
> **Before (Oct 1–14):**
>
> - 101 visits started on **CH-002**, of which **0 succeeded** — a 0% success rate
> - 101 failures on CH-002 all had `failure_reason = FAULTED_AFTER` and `error_code = ConnectorLockFailure`
> - 38 visits on CH-001, with 35 succeeding (92%)
> - CH-002 dragged the blended rate down to **25.2%**
>
> **After (Oct 20+):**
>
> - CH-002 and CH-001 are gone; **CH-003 and CH-004** (new, LOC-002) take all traffic
> - 24 / 24 visits on CH-003 succeeded; 24 / 24 on CH-004 — both at **100%**
> - Zero `FAULTED_AFTER` failures anywhere
>
> ---
>
> ### Conclusion
>
> The rise in successful visits after Oct 19 is entirely a **fleet composition change**, not an improvement in charger reliability:
>
> 1. **CH-002 was a broken charger** — it generated 101 visits and 101 failures, all due to `ConnectorLockFailure` causing a `FAULTED_AFTER` outcome. It failed every single visit from Oct 1–14.
> 2. CH-002 (and CH-001) were **decommissioned on Oct 15**, removing all activity from the network for 5 days.
> 3. On **Oct 20, two new healthy chargers (CH-003, CH-004) at a new location (LOC-002) were commissioned** — and they have had a 100% success rate since launch.
>
> The network didn't get better — it shed a broken charger and replaced it with working ones. The underlying `ConnectorLockFailure` issue on CH-002 was never resolved; it was simply retired.

| Correctness (0–1) | Completeness (0–1) | Note |
| ----------------- | ------------------ | ---- |
|                   |                    |      |

---

## S12

**Question:** Why were there no charging visits from Oct 15 to Oct 19, 2025?

**Reference:** Because no charger was available. On Oct 15, CH-001 was decommissioned and CH-002, the only charger left, went offline (NoHeartbeat) for the rest of the period, so uptime was 0% from Oct 16 to Oct 19. Drivers who came while it was offline leave no record, so demand in those days can't be measured.

**Answer:**

> The gap in visits from Oct 15–19 is fully explained by two simultaneous events that left **zero operational chargers** on the network:
>
> ### Root Cause: Complete Network Blackout
>
> **Two things happened at 07:55 on October 15:**
>
> | Event           | Charger          | Detail                                                                                                    |
> | --------------- | ---------------- | --------------------------------------------------------------------------------------------------------- |
> | Decommissioning | CH-001 (LOC-001) | `decommissioned_ts = 2025-10-15 07:55` — taken permanently out of service                                 |
> | OFFLINE outage  | CH-002 (LOC-001) | Lost heartbeat at 07:55 on Oct 15 — both ports (CH-002-1, CH-002-2) went offline (1,440 min/day × 5 days) |
>
> CH-002 was the **only remaining commissioned charger** after CH-001 was decommissioned — and it went offline at the exact same moment. This left the network with no chargers capable of serving drivers until Oct 20, when CH-003 and CH-004 were commissioned at LOC-002.
>
> **Key timestamps:**
>
> - CH-001 decommissioned: `2025-10-15 07:55`
> - CH-002 offline outage start: `2025-10-15 07:55` → still offline as of the data's latest update (`2025-11-19`)
> - CH-003 & CH-004 commissioned: `2025-10-20 08:00` → visits resume
>
> The simultaneous decommission of CH-001 and offline drop of CH-002 (same timestamp, same location LOC-001) suggests a **planned site intervention** — possibly a power cut, infrastructure work, or a migration — that took the entire LOC-001 site down.

| Correctness (0–1) | Completeness (0–1) | Note |
| ----------------- | ------------------ | ---- |
|                   |                    |      |

---

## S13

**Question:** Why were there more chargers after Oct 19, 2025?

**Reference:** Because LOC-002 was commissioned on Oct 20, 2025, with two chargers, CH-003 and CH-004, of 2 ports each. That took the network from one commissioned charger, CH-002, which counts although it was offline, to three. The data records the commissioning, not the reason for it.

**Answer:**

> The answer is straightforward from the inventory data. Here's the full picture:
>
> ---
>
> ## Why there were more chargers after Oct 19, 2025
>
> This is a **network expansion event**, not a data anomaly. The step-change is explained entirely by new charger commissionings.
>
> ### What happened
>
> | Event                            | Date       | Chargers active               | Change            |
> | -------------------------------- | ---------- | ----------------------------- | ----------------- |
> | Baseline                         | Oct 1–14   | 2 (CH-001, CH-002 at LOC-001) | —                 |
> | CH-001 decommissioned            | Oct 15     | 1                             | −1                |
> | **CH-003 & CH-004 commissioned** | **Oct 20** | **3**                         | **+2 at LOC-002** |
> | CH-005 & CH-006 commissioned     | Nov 3      | 5                             | +2 at LOC-003     |
>
> The count jumped from **1 charger** (Oct 15–19) to **3 chargers** on Oct 20 because two brand-new chargers — **CH-003** and **CH-004** — were commissioned at a new location (**LOC-002**) on Oct 20, 2025 at 08:00. CH-001 at LOC-001 had already been decommissioned on Oct 15, which explains the brief dip before the jump.
>
> So "more chargers after Oct 19" reflects:
>
> 1. CH-001 going offline on Oct 15 (−1)
> 2. Two new chargers (CH-003, CH-004) coming online at LOC-002 on Oct 20 (+2), resulting in a **net +2** vs the Oct 1–14 baseline.
>
> A further expansion to 5 chargers occurred on Nov 3, when CH-005 and CH-006 were commissioned at a third location (LOC-003).

| Correctness (0–1) | Completeness (0–1) | Note |
| ----------------- | ------------------ | ---- |
|                   |                    |      |

---

## S14

**Question:** Did charging demand recover in the week of Oct 20, 2025, compared to the week of Oct 6?

**Reference:** The data can't show it, because the two weeks cover different sites. Every visit in the week of Oct 20 was at LOC-002, which opened that day, by drivers who were all new. LOC-001 had no working charger after Oct 14, so its demand left no record. So 38 visits against 69 is new demand at a new location, not LOC-001's demand recovering or falling.

**Answer:**

> ## Metrics at a Glance
>
> | Metric                     | Week of Oct 6 (LOC-001) | Week of Oct 20 (LOC-002) | Change   |
> | -------------------------- | ----------------------- | ------------------------ | -------- |
> | Total visits               | 69                      | 38                       | -45%     |
> | Successful visits          | 19                      | 38                       | +100%    |
> | Failed visits              | 50                      | 0                        | -100%    |
> | First-attempt success rate | 24.6%                   | 100.0%                   | +75.4 pp |
> | Total energy (kWh)         | 36.8                    | 60.8                     | +65%     |
> | Avg energy / visit (kWh)   | 0.53                    | 1.60                     | +202%    |
>
> ---
>
> ## The comparison is not apples-to-apples — different locations, different fleets
>
> The two weeks cover **entirely different sites**, which fundamentally changes what the comparison means:
>
> - **Week of Oct 6** was served exclusively by **LOC-001** (chargers CH-001 and CH-002). CH-001 was decommissioned on **Oct 15**, so the fleet for this period was partially intact.
> - **Week of Oct 20** is served exclusively by **LOC-002** (chargers CH-003 and CH-004), which were **commissioned on Oct 20, 2025** — the very first day of this period. LOC-001 had no visits in this week (CH-001 was gone, CH-002 still present but idle).
>
> **There is no overlap in location or charger fleet between the two weeks.**
>
> ---
>
> ## What the numbers do show
>
> **Reliability recovered dramatically — but that's partly structural.** LOC-001 in week 1 had a catastrophic 72% failure rate, with 48 of 51 failed attempts due to `FAULTED_AFTER` (connectors faulting after Preparing) and 3 from `INVALID_STOP_REASON`. LOC-002 in week 2 had a **100% success rate** with zero failures across 38 visits — consistent with brand-new equipment in its first week.
>
> **Visit volume dropped by 45%** (69 → 38), but LOC-002 is a new site and likely not at full utilization yet. It's also only been live for 7 days at the point of this comparison.
>
> **Energy per visit tripled** (0.53 → 1.60 kWh), reflecting that LOC-002 visits are all successful charges, while LOC-001's visits were mostly failed attempts delivering near-zero energy.
>
> ---
>
> ## Conclusion
>
> **You cannot directly conclude LOC-001's demand "recovered"** — LOC-001 was essentially idle during the week of Oct 20 (CH-001 decommissioned, CH-002 unused). What happened instead is that **a new location (LOC-002) opened**, with fresh hardware and no faults. The improvement in success rate and energy reflects new, reliable equipment rather than resolution of the Oct 6 problems at LOC-001.

| Correctness (0–1) | Completeness (0–1) | Note |
| ----------------- | ------------------ | ---- |
|                   |                    |      |

---

## S15

**Question:** Why were there no charging visits from Oct 15 to Oct 19, 2025?

**Reference:** Because no charger was available. On Oct 15, CH-001 was decommissioned and CH-002, the only charger left, went offline (NoHeartbeat) for the rest of the period, so uptime was 0% from Oct 16 to Oct 19. Drivers who came while it was offline leave no record, so demand in those days can't be measured.

**Answer:**

> Here is what the data shows, following the investigation:
>
> ---
>
> ## Why there were no visits Oct 15–19, 2025
>
> **The gap is real and fully explained by a network topology change — not missing data.**
>
> ### What happened
>
> Two events coincided on **Oct 15 at 07:55**:
>
> | Event                         | Detail                                                                                                                                  |
> | ----------------------------- | --------------------------------------------------------------------------------------------------------------------------------------- |
> | **CH-001 decommissioned**     | `decommissioned_ts = 2025-10-15 07:55` — the only charger that had been active throughout Oct 1–14                                      |
> | **CH-002 went fully offline** | An OFFLINE outage (`NoHeartbeat`) started at exactly the same timestamp (`outage_from_ts = 2025-10-15 07:55`) and lasted through Nov 19 |
>
> This left **zero operational chargers** on the network between Oct 15 and Oct 19, which is why no visits or charge attempts were recorded during that window.
>
> ### Why visits resumed on Oct 20
>
> - **CH-003** and **CH-004** were both commissioned on `2025-10-20 08:00` at LOC-002, and visits resumed that same day (8 visits on Oct 20).
> - CH-002's OFFLINE outage continued well past Oct 20 — it did not contribute.
>
> ### Network state summary
>
> | Period         | Active Chargers                              | Visits  |
> | -------------- | -------------------------------------------- | ------- |
> | Oct 1 – 14     | CH-001 (LOC-001), CH-002 (LOC-001)           | ~10/day |
> | Oct 15 – 19    | None (CH-001 decommissioned, CH-002 offline) | **0**   |
> | Oct 20 onwards | CH-003, CH-004 (LOC-002)                     | Resumed |
>
> **Confidence: High.** The decommissioning timestamp of CH-001 and the outage start of CH-002 both pin to the exact minute the gap begins, and new chargers commissioned on Oct 20 align exactly with when visits resumed. There is nothing unexplained.

| Correctness (0–1) | Completeness (0–1) | Note |
| ----------------- | ------------------ | ---- |
|                   |                    |      |

---

## S16

**Question:** Did visit success recover in the week of Nov 17, 2025?

**Reference:** No, the data can't show a recovery. The week is partial, since the data ends on Nov 19 at 12:00, and the cause of the drop continues: failed visits without an idTag are 22% of visits, the same share as in the week of Nov 10. The higher success rate, 76.1% against 68.9%, rests on 11 failed visits and isn't a trend.

**Answer:**

> ## Metrics at a Glance
>
> | Metric               | Week of Nov 3 (baseline) | Week of Nov 10 (drop) | Week of Nov 17 |
> | -------------------- | ------------------------ | --------------------- | -------------- |
> | Total Visits         | 143                      | 148                   | 46 ⚠️          |
> | Success Rate         | 91.6%                    | 68.9%                 | 76.1%          |
> | Failed Rate          | 8.4%                     | 31.1%                 | 23.9%          |
> | Change vs prior week | —                        | **−22.7 pp**          | **+7.2 pp**    |
>
> ---
>
> ## Conclusion: Partial recovery, not a full one — and the week is incomplete
>
> **Success rate rose +7.2 pp** (68.9% → 76.1%), which is a step in the right direction, but the rate is still **−15.5 pp below the Nov 3 baseline** of 91.6%. The data only covers **3 of 7 days** (Nov 17–19), so the final weekly rate may differ.
>
> ---
>
> ## Path through the breakdown
>
> ### 1. Data completeness
>
> The Nov 17 week has only 46 visits ending between **Nov 17 and Nov 19** — no data exists beyond Nov 19. Volume is also sharply lower (46 vs 148 the prior week), which raises the possibility that either the data is incomplete or demand genuinely dropped. Treat the week as **partial**.
>
> ### 2. Failure modes — the root cause is still present
>
> | Failure Reason      | Nov 10 week (46 failures) | Nov 17 week (11 failures) |
> | ------------------- | ------------------------- | ------------------------- |
> | NO_TRANSACTION      | 33 (71.7%)                | 10 (90.9%)                |
> | AUTH_REJECTED       | 10 (21.7%)                | 1 (9.1%)                  |
> | INVALID_STOP_REASON | 3 (6.5%)                  | 0                         |
>
> `NO_TRANSACTION` — the dominant failure during the Nov 10 drop — **is still the leading failure mode** in Nov 17, now making up an even larger share (90.9% vs 71.7% of failures). The absolute count fell (33 → 10) but that is partly driven by the lower total volume.
>
> ### 3. Where the partial recovery is concentrated
>
> | Location    | Nov 10 success rate | Nov 17 success rate   | Change          |
> | ----------- | ------------------- | --------------------- | --------------- |
> | **LOC-002** | 66.7% (81 visits)   | **94.1%** (17 visits) | **+27.5 pp** ✅ |
> | **LOC-003** | 71.6% (67 visits)   | **65.5%** (29 visits) | **−6.1 pp** ❌  |
>
> The aggregate improvement is **entirely explained by LOC-002 recovering**. LOC-003 actually got slightly worse. The root cause at LOC-003 (predominantly `NO_TRANSACTION` failures) has not resolved.
>
> ---
>
> **Summary:** Success rate is recovering but only partially and unevenly. LOC-002 has largely recovered; LOC-003 has not, and the `NO_TRANSACTION` failure mode that drove the Nov 10 drop is still dominant there. The week is also cut short at Nov 19, so a full picture requires waiting for the complete week's data.

| Correctness (0–1) | Completeness (0–1) | Note |
| ----------------- | ------------------ | ---- |
|                   |                    |      |

---

## S17

**Question:** Why were there more chargers after Oct 19, 2025?

**Reference:** Because LOC-002 was commissioned on Oct 20, 2025, with two chargers, CH-003 and CH-004, of 2 ports each. That took the network from one commissioned charger, CH-002, which counts although it was offline, to three. The data records the commissioning, not the reason for it.

**Answer:**

> The answer is straightforward: **two new chargers were commissioned on Oct 20, 2025** — one day after Oct 19.
>
> Here's the full commissioning timeline:
>
> | Date             | Event                                      | Active Chargers |
> | ---------------- | ------------------------------------------ | --------------- |
> | Sep 15, 2025     | CH-002 commissioned (LOC-001)              | 1               |
> | Oct 1, 2025      | CH-001 commissioned (LOC-001)              | 2               |
> | Oct 15, 2025     | CH-001 **decommissioned** (LOC-001)        | 1               |
> | **Oct 20, 2025** | **CH-003 & CH-004 commissioned (LOC-002)** | **3**           |
> | Nov 3, 2025      | CH-005 & CH-006 commissioned (LOC-003)     | 5               |
>
> The jump you observed after Oct 19 is entirely explained by the commissioning of **CH-003 and CH-004 at LOC-002** on Oct 20, 2025 — a brand-new location coming online with 2 chargers simultaneously.

| Correctness (0–1) | Completeness (0–1) | Note |
| ----------------- | ------------------ | ---- |
|                   |                    |      |

---

## S18

**Question:** Why did visits at LOC-002 drop in the week of Oct 27, 2025?

**Reference:** Because fewer drivers came, not because of a reliability problem. Visits at LOC-002 fell from 38 in the week of Oct 20 to 12 in the week of Oct 27, while every visit in both weeks succeeded and uptime stayed above 99.6%. Active drivers fell from 20 to 8, and the data doesn't show why.

**Answer:**

> Here's the full picture:
>
> ---
>
> ## LOC-002 Visit Drop — Week of Oct 27, 2025
>
> ### Conclusion
>
> The drop from 38 to 12 visits (−68%) was driven entirely by a **demand-side effect**: the site opened the previous week (Oct 20), which attracted a burst of 20 first-time drivers. Once that opening surge subsided, only the subset of those drivers who returned continued charging — just 8 returning drivers in the drop week.
>
> ---
>
> ### Path through the breakdown
>
> | Level                   | Metric | Oct 20–26 | Oct 27–Nov 2 | Change     |
> | ----------------------- | ------ | --------- | ------------ | ---------- |
> | **Total Visits**        |        | 38        | 12           | −26 (−68%) |
> | **Success Rate**        |        | 100%      | 100%         | 0 pp       |
> | **Known Drivers**       |        | 20        | 8            | −12        |
> | **— New Drivers**       |        | 20        | 0            | −20        |
> | **— Returning Drivers** |        | 0         | 8            | +8         |
> | **Anonymous Drivers**   |        | 0         | 0            | 0          |
>
> ---
>
> ### Key findings
>
> 1. **Opening week effect.** LOC-002 was commissioned on **Oct 20, 2025** (the same day as CH-003 and CH-004). The first week attracted 20 entirely new drivers — people visiting for the first time ever. The Oct 27 week had **zero new drivers** because the novelty effect exhausted itself.
> 2. **Low return rate.** Of the 20 new drivers from opening week, only **8 (40%)** came back the following week. This is the primary explanation for the low visit count.
> 3. **Supply is not the cause.** Uptime was healthy — the only downtime was brief OFFLINE (NoHeartbeat) blips of 10 minutes each. Both chargers split the drop equally (19 → 6 visits each), ruling out a single-charger failure.
> 4. **Success rate was 100% in both weeks.** No quality degradation; every visit that happened was successful.
> 5. **The site then recovered.** Visits surged to 63 in the week of Nov 3 and 81 in Nov 10 as the driver base grew with new signups and returning drivers, confirming this was a typical **opening-week spike followed by a demand normalization**, not a structural problem.
>
> ---
>
> ### Hypothesis (not yet confirmed by data)
>
> The 8 drivers who returned were likely the most highly motivated, frequent EV users, while the other 12 new drivers from opening week either: (a) are infrequent chargers who returned later, or (b) had a one-time need. The ramp-up visible from Nov 3 onward is consistent with organic word-of-mouth adoption rather than any operational issue.

| Correctness (0–1) | Completeness (0–1) | Note |
| ----------------- | ------------------ | ---- |
|                   |                    |      |

---

## S19

**Question:** Why did the number of successful visits go up after Oct 19, 2025, compared to Oct 15–19?

**Reference:** Because supply came back: LOC-002 opened on Oct 20 with CH-003 and CH-004, while LOC-001 still had no working charger. There were no successful visits from Oct 15 to Oct 19, and 38 in the week of Oct 20, all at LOC-002. This is new supply, not LOC-001 recovering.

**Answer:**

> Here's the full root-cause breakdown:
>
> ---
>
> ## Conclusion
>
> The jump from ~25% to 100% success rate after Oct 19 was caused entirely by a **fleet swap** — the broken charger (CH-002) was removed from service and replaced by two new, fully functional chargers (CH-003 and CH-004) at a new location.
>
> ---
>
> ## Step-by-step breakdown
>
> ### 1. The gap in data (Oct 15–19) is real
>
> There are **zero visits** recorded between Oct 15 and Oct 19. This aligns perfectly with the hardware transition — no charger was generating activity during that window.
>
> ### 2. What changed in the fleet
>
> | Charger | Commissioned     | Decommissioned    | Location |
> | ------- | ---------------- | ----------------- | -------- |
> | CH-001  | Oct 1            | **Oct 15 07:55**  | LOC-001  |
> | CH-002  | Sep 15           | _(still active?)_ | LOC-001  |
> | CH-003  | **Oct 20 08:00** | —                 | LOC-002  |
> | CH-004  | **Oct 20 08:00** | —                 | LOC-002  |
>
> - **CH-001** was decommissioned on Oct 15 — it had a 92% success rate but only 38 visits.
> - **CH-002** was responsible for **101 out of 104 failed visits** (Oct 1–14), with a **0% success rate** across all 101 of its visits. Every single one failed with `FAULTED_AFTER` + `ConnectorLockFailure` — a persistent hardware fault (the connector lock mechanism never worked).
> - **CH-003 and CH-004** came online Oct 20 at a new location (LOC-002) and immediately hit **100% success across 38 visits**.
>
> ### 3. Attribution of the "before" failures
>
> Of the 104 failed visits in the before period:
>
> - **101** (97%) came from CH-002 → all `FAULTED_AFTER`, all caused by `ConnectorLockFailure`
> - **3** came from CH-001 → `INVALID_STOP_REASON`
>
> ### 4. Why successful visits "went up"
>
> It's not that the same visits became more successful — the population changed:
>
> - CH-002, which failed **100% of its visits**, stopped appearing in the data (last activity Oct 14)
> - Two brand-new chargers at a different location (LOC-002) replaced it, with zero faults
>
> This is a **mix change**, not a rate improvement on existing equipment: a 0%-success charger exited and 100%-success chargers entered.
>
> ---
>
> **Confidence: High.** The commissioning timestamps, failure codes, and visit counts all tell a consistent story with no unexplained residual.

| Correctness (0–1) | Completeness (0–1) | Note |
| ----------------- | ------------------ | ---- |
|                   |                    |      |

---

## S20

**Question:** Why was network uptime so low from Oct 15 to Oct 19, 2025?

**Reference:** Because CH-002 went offline (NoHeartbeat) on Oct 15 and stayed offline: network uptime was 12.38% from Oct 15 to Oct 19, against 98.64% from Oct 1 to Oct 14. From Oct 16, CH-002 and its 2 ports were all that was commissioned. CH-001's decommissioning on Oct 15 added no downtime; it removed CH-001's ports from the count.

**Answer:**

> Here is the full root-cause analysis.
>
> ---
>
> ## Metrics at a Glance
>
> | Metric             | Pre-incident (Oct 8–14)    | Incident (Oct 15–19)    | Change                |
> | ------------------ | -------------------------- | ----------------------- | --------------------- |
> | Network uptime     | ~100%                      | **0–33%**               | **−67 to −100 pp**    |
> | Commissioned ports | 4 (CH-001 × 2, CH-002 × 2) | 2 (CH-002 × 2 only)     | CH-001 decommissioned |
> | Downtime type      | None material              | OFFLINE (NoHeartbeat)   | —                     |
> | Affected charger   | —                          | **CH-002 (both ports)** | —                     |
>
> ---
>
> ## Root Cause: Two Compounding Events
>
> ### 1. CH-001 was decommissioned on Oct 15 at 07:55
>
> **CH-001** (2 ports at LOC-001) was permanently decommissioned on **Oct 15 at 07:55**. This cut the commissioned port count from 4 to 2, halving the network's capacity denominator for the uptime ratio. It is not downtime — decommissioning shrinks the denominator — but it left the network with only CH-002 going into the incident.
>
> ### 2. CH-002 went fully OFFLINE starting Oct 15 at 07:55 — and never came back
>
> Simultaneously (literally the same timestamp), **CH-002** stopped sending heartbeats — classified as `OFFLINE / NoHeartbeat`. Both of its ports (CH-002-1 and CH-002-2) were affected. This was **not a brief dropout**: the outage started on Oct 15 and the `outage_to_ts` shows it was still open as of **Nov 19**, indicating the charger never recovered during this period.
>
> The downtime breakdown:
>
> | Day       | Downtime minutes (CH-002) | % of Commissioned |
> | --------- | ------------------------- | ----------------- |
> | Oct 15    | 1,930 (965 × 2 ports)     | 67%               |
> | Oct 16–19 | 1,440 × 2 = 2,880 / day   | **100%**          |
>
> Because CH-002 was the **only remaining commissioned charger** after CH-001's decommissioning, its complete OFFLINE outage drove network uptime to **0%** from Oct 16 through Oct 19 (and beyond).
>
> ### Why uptime looks even worse: the double hit
>
> The simultaneous decommissioning of CH-001 and the OFFLINE outage on CH-002 happened at the **exact same timestamp (Oct 15, 07:55)**. This suggests a coordinated network event — possibly a site migration, a power or connectivity outage at the shared location (both CH-001 and CH-002 are at **LOC-001**), or a maintenance window that took CH-001 offline permanently while CH-002 lost connectivity unexpectedly.
>
> ---
>
> ## What's Still Unexplained
>
> - **Why** CH-002 lost its heartbeat connection is not visible in the data (no FAULTED error code — purely OFFLINE). It could be a network/connectivity failure, a power cut, or a physical failure at the site.
> - The timing alignment (same minute) between CH-001's decommissioning and CH-002's OFFLINE start is a strong hypothesis that a **site-level event** (power outage, ISP cut, etc.) at LOC-001 caused both simultaneously.
> - CH-002's outage ran through at least Nov 19, suggesting it was not a transient issue.

| Correctness (0–1) | Completeness (0–1) | Note |
| ----------------- | ------------------ | ---- |
|                   |                    |      |

---
