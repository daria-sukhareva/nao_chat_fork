# Retrospective: a wider root-cause trigger

**Date:** 2026-11-23
**Scope:** the root-cause skill's trigger widened so it loads on comparisons such as q028; the plan
for rerunning q022–q028 on both arms.
**Status:** trigger changed, not yet committed. No eval runs yet on the new trigger.
The last B runs on q028 are `20261119_005130` (study `a7ae60ce`, before step 6 and #204).

This follows the [2026-11-21 retrospective](retrospective_2026-11-21.md).

---

## The trigger: why q028 never loaded the skill

q028 asks "Did charging demand recover in the week of Oct 20, 2025, compared to the week of
Oct 6?". The two weeks cover different sites: every visit in the week of Oct 20 was at LOC-002,
which opened that day. B's last three trials (`20261119_005130`) scored 0.1 / 0.0 each. None
loaded the root-cause skill, read the tree or queried `dim_chargers`; all three compared LOC-001's
week with LOC-002's as one site. A's latest run (`20261119_181714`) did the same.

The skill would have caught it. Its step 1 already checks network topology (`commissioned_ts` and
`decommissioned_ts` in `dim_chargers`) and step 4 says that when a location opens or closes inside
the comparison, "the periods then cover different sites". The failure is the trigger, not the
method.

The old triggers named change and cause: the skill description listed "why did X drop", "what
caused this change", "is this concentrated somewhere", and the shared RULES line said "whether,
why, or where a metric changed". q028 asks neither why nor where, and "recover" didn't read as
"whether a metric changed".

The new trigger is the shape of the question, a comparison, rather than its wording:

- **Skill description:** "Investigate whether, why, or where a metric changed, or what is driving
  it. Use whenever an answer compares a metric between two periods, locations, or chargers,
  including questions such as "why did X drop", "did X change", "what caused this change", or "is
  this concentrated somewhere". Do not use for looking up a single value."
- **Shared RULES line:** "For any question that compares a metric between periods, locations, or
  chargers, or asks whether, why, or where a metric changed, read
  `agent/skills/root-cause-analysis.md` before querying and follow its steps."
- **B's tree line:** "For questions that compare a metric between periods, locations, or chargers,
  or ask whether or why it changed or what drives it, read `docs/metrics_tree.md` and use it as
  the structure for your analysis."

"Did X recover" was left out on purpose: it would fit the description to q028's wording, and the
eval would then measure the prompt, not the method. The skill and the shared line change both
arms equally. B's tree line changes B's treatment: without it, B could load the skill on q028 and
still not read the tree.

## Next: rerun q022–q028

The topology cases, on both arms, after the commit: 5 trials per arm in the order A, B, B, A (3,
3, 2, 2 repeats), so drift over the day doesn't fall on one arm. Besides the scores, each trial is
checked for whether it loaded the skill and queried `dim_chargers`. That answers two questions:
whether the wider trigger fires on q028, and whether the topology regression (checks in 2 of 21
recent trials) was a trigger problem too.

## Querying topology isn't using it

The first B runs on the new build (`ac7f943e`, q022–q025, 3 trials each: `20261123_151949`,
`152411`, `152857`, `153302`) loaded the root-cause skill and queried `dim_chargers` in 12 of 12
trials. A recount of the earlier runs, matching the skill read as a file as well as through
`load_skill`, shows the same on q022–q027 on every build since Nov 18. Only q028 never loaded the
skill, in 0 of 11 trials across both arms. So "touched `dim_chargers`" isn't the topology check that
fails, and the "2 of 21" figure counted something narrower.

q025 trial 2 shows the real failure. It looked up commissioning, then said LOC-002's two chargers
and LOC-003's one "came online Oct 20" (LOC-003 has two, commissioned Nov 3), and compared Oct 1–14
with Oct 20 to Nov 19, a window that includes LOC-003. That gave 118 drivers and 53 anonymous ones,
against the reference's 20 drivers and none anonymous in the week of Oct 20. Correctness 0.4,
Completeness 0.4. The agent checks topology but doesn't use it to bound the comparison window.

The topology figure will measure that instead: whether the periods compared contain the same
locations and chargers, or the answer says they don't, rather than whether `dim_chargers` was
queried.

## q028 on B: the trigger fires, and two failures remain

On the new trigger (`20261123_154445`) B loaded the root-cause skill and read the tree in 3 of 3
q028 trials, against 0 of 11 trials on earlier builds across both arms. The mean rose from
0.1 / 0.0 to 0.50 / 0.53, but the trials split three ways:

| Trial | Correctness | Completeness | `dim_chargers` queries | Conclusion                                                                            |
| ----- | ----------: | -----------: | ---------------------: | ------------------------------------------------------------------------------------- |
| 1     |         0.1 |          0.1 |                      0 | "Yes, but with major caveats", the two weeks read as one site                         |
| 2     |         0.9 |          1.0 |                      1 | "entirely different sites, so the metrics don't directly measure recovery"            |
| 3     |         0.5 |          0.5 |                      1 | topology table right, then "volume did not recover, but the network that existed did" |

**Loading the skill is necessary but not sufficient: the step can still be skipped.** Trial 1
loaded the skill, but its step 1 checked data coverage and calendar only. It never looked up
commissioning, called Oct 15–19 "a 5-day gap in the record", and explained the driver mix by
authentication changes.

**It checks topology and doesn't let it limit the conclusion.** Trial 3 built a correct topology
table (CH-001 decommissioned, CH-002 offline, LOC-002 opened Oct 20) and still concluded that
"successful charging demand doubled", a comparison across two sites. That is the same failure as
q025 trial 2.

## q030 on B: a question that reads like a lookup

q030 asks "Did more drivers charge successfully on the network in the week of Nov 10, 2025 than in
the week of Nov 3?". On the new build (`20261123_155355`) B loaded the root-cause skill in 3 of 3
trials and read the driver skill, but not the tree, and ran 2–3 queries in 33–41 s. Every trial
gave the reference's headline (no: 57 drivers, then 41, and no anonymous successes) and stopped
there: none looked at the 6 drivers whose tokens expired, the anonymous failed visits rising from
10 to 33, or the flat visit volume. Completeness 0.3, 0.3, 0.2.

The skill loads, but the question reads like a lookup ("did more drivers…"), so B answers the count
and stops at steps 1–2. It is the same gap as q028 trial 1: a trigger that fires doesn't make the
later steps run.

## q027, A against B: where the tree shows its value

q027 asks why visits at LOC-002 dropped in the week of Oct 27; the answer is fewer drivers, not
reliability. Same study content on both arms (B `20261123_154002`, A `163306`, 3 trials each):

| Arm | Correctness | Completeness | Split visits into drivers × visits per driver |
| --- | ----------: | -----------: | --------------------------------------------: |
| A   |        0.70 |         0.60 |                                        1 of 3 |
| B   |        0.87 |         0.93 |                                        3 of 3 |

Every trial on both arms found the cause was demand, with 100% success and negligible downtime.
Two A trials stopped at the visit count; one split by charger (CH-003 and CH-004 each 19 to 6),
which is the skill's step 4, and never reached drivers. Every B trial split visits into drivers
(20 to 8) and visits per driver (1.9 to 1.5), and one got the reference's 80/20 share.

So this is where the tree shows its value: on a pure demand question, it tells the agent how to
split the visit count. The skill's step 2 ("split the metric into its parts") doesn't say what the
parts of a visit count are. A found them in 1 of 3 trials, B in 3 of 3. With 3 trials, that's
suggestive rather than conclusive.

## q030, A against B: A is better, and the driver skill is why

Same study content on both arms (B `20261123_155355`, A `164343`, 3 trials each):

| Arm | Correctness | Completeness | SQL queries |
| --- | ----------: | -----------: | ----------: |
| A   |        0.83 |         0.43 |         1–2 |
| B   |        0.33 |         0.27 |         2–3 |

A is better here, but not because it analyses more. Both arms gave the reference's headline (no:
57 drivers, then 41) and stopped, the lookup pattern above; neither looked at the expired tokens or
the anonymous visits. The difference is what each put next to the headline:

- **A** listed total visits (143 to 148), successful visits, successful drivers and the success
  rate. Every figure is right, and side by side they already show visits flat while successes
  fell.
- **B** followed the driver skill and split successful drivers into new and returning (40 to 3
  new), with "≈0 anonymous". That split doesn't answer the question, and one trial built a wrong
  explanation on it (early-October drivers "still counted as new" in the week of Nov 3). Without
  total visits alongside, the judge read B's "131 to 102 successful visits" as contradicting "143
  to 148 visits", and "≈0 anonymous" drivers as contradicting "10 to 33 anonymous visits", in all
  three trials.

So on q030 B's driver skill hurts B: it adds a breakdown the question didn't ask for, the
breakdown invites a wrong explanation, and the judge's misread of two different counts as one
penalises it. Correctness is held down partly by that misread; Completeness is low on both arms for
the same reason, the stop after the headline.

## First block: A against B on q022–q031

Same study content on both arms (B runs `20261123_151949` to `155716`, A runs `161355` to
`164715`), 3 trials per case:

| Case     | Correctness A | Correctness B | Completeness A | Completeness B |
| -------- | ------------: | ------------: | -------------: | -------------: |
| q022     |          0.87 |          0.67 |           0.67 |           0.70 |
| q023     |          0.47 |          0.53 |           0.50 |           0.63 |
| q024     |          0.63 |          0.63 |           0.60 |           0.47 |
| q025     |          0.47 |          0.50 |           0.47 |           0.57 |
| q026     |          0.73 |          0.70 |           0.43 |           0.47 |
| q027     |          0.70 |      **0.87** |           0.60 |       **0.93** |
| q028     |          0.47 |          0.50 |           0.33 |           0.53 |
| q029     |          0.53 |          0.60 |           0.53 |           0.60 |
| q030     |      **0.83** |          0.33 |           0.43 |           0.27 |
| q031     |          0.17 |          0.20 |           0.20 |           0.20 |
| **Mean** |      **0.59** |      **0.55** |       **0.48** |       **0.54** |

The arms are close: A is slightly ahead on Correctness (0.59 against 0.55), B on Completeness
(0.54 against 0.48). Two questions define the result, and they pull in opposite directions:

- **q027, where B wins:** the tree tells B how to split a visit count into drivers × visits per
  driver. B made that split in 3 of 3 trials and A in 1 of 3.
- **q030, where A wins:** B's driver skill adds a new and returning split the question didn't ask
  for. One trial built a wrong explanation on it, and the judge misread its counts as
  contradicting the reference. A gave the plain count next to total visits.

Without these two cases Correctness is the same on both arms (0.54), and B keeps a smaller lead on
Completeness (0.52 against 0.47), from q023, q025 and q028. The same B artefacts, the tree and the
driver skill, help on one demand question and hurt on the other. With 3 trials per case none of the
gaps is conclusive; the second block (2 more trials per arm) completes 5.

## The ceiling: q031, and the check the conclusion ignores

**The ceiling.** All 10 dev cases are pilot data: q019–q031 are dev only, and the plan rules out
q001–q018 for confirmation. The first block showed failures that both arms share: on q031 every
trial on both arms called a recovery, and on q023, q025 and q028 the agent checked topology and
answered as if it hadn't. These put a ceiling on both arms, which shrinks the room the tree has to
show a difference. The plan allows changing the shared skill on dev, since both arms get it, but
only before the freeze.

**What we did, on q031.** The skill told the agent to notice a partial period ("If a period is
partial, flag it") and small counts ("the counts are large enough for the change to mean
something"), but not what either does to the answer. Every trial flagged the partial week and
answered "Yes". Two changes went in:

- **The stop rule** (`84b93f82`, by the author): "If the change does not survive this step, the
  conclusion is that the data can't show it. Lead with that, then give what is known."
- **A recovery rule in step 6** (`7936f876`): "When asked whether a metric recovered, check whether
  the cause of the earlier drop is still present: compare the share of each failure mode with the
  period before the drop. A rate can rise while the cause continues."

Two other proposals were not adopted. Comparing only the same days and hours of each period was
rejected by the author: the agent should not change the reference periods. A noise test (the new
period's daily values against the earlier period's daily spread) is held for now.

**How it changed the outcomes** (3 trials each; A `20261123_173539` on a dirty manifest, B
`174401` on `7936f876`; both with the same skill content):

| Arm | Correctness before | Correctness after | Completeness before | Completeness after | Verdicts after                                          |
| --- | -----------------: | ----------------: | ------------------: | -----------------: | ------------------------------------------------------- |
| A   |               0.17 |              0.37 |                0.20 |               0.33 | "partial recovery" ×3                                   |
| B   |               0.20 |              0.43 |                0.20 |               0.43 | "No, did not recover" ×1, "partial recovery" ×2; 1 pass |

No trial said "Yes" outright any more, and every trial queried failure reasons by week, against 3 of
6 before. B's trial 1 was the first q031 pass on either arm, and the first to measure the week's
coverage as 2.5 days. B's trial 2 computed each failure mode as a share of visits in all three weeks
and labelled `NO_TRANSACTION` (7.0%, 22.3%, 21.7%) "Not recovered", which is the reference's
evidence. It still concluded "Partial recovery". A's trial 3 found the change "real but small… the
signal is weak" and still called a partial recovery. The new rule made some trials split by location
on small segments (LOC-002 at 94.1% from 17 visits), and none flagged the counts.

**The failure mode: the check runs and the conclusion ignores it.** The same pattern shows up in
three places today:

| Where                            | The check ran                                                | The conclusion ignored it             |
| -------------------------------- | ------------------------------------------------------------ | ------------------------------------- |
| q025 B trial 2                   | looked up commissioning                                      | compared windows that include LOC-003 |
| q028 A trials 1 and 3, B trial 3 | built a correct topology table                               | "Yes, recovered", across two sites    |
| q031, both arms                  | flagged the partial week; labelled the cause "Not recovered" | "partial recovery"                    |

The rules say what to check, and the agent checks it. None says what a result does to the answer:
the stop rule depends on step 1 deciding that the change didn't survive, and without a test step 1
never decides that. The recovery rule says to check whether the cause is still present, not what
follows if it is. The candidate next change keeps to the author's constraint on periods and links
the finding to the verdict: "If the cause is still present, the metric hasn't recovered, whatever
the rate did."

## Dev pilot on the new skill, and rough sizing

**The runs.** Both arms on all 13 dev cases (q019–q031), 3 trials each, with the stop and recovery
rules in the skill (same skill hash `f3e408a7` on both arms): B `20261123_180613` to `185117` on
`7936f876`, A `190652` to `194856` on `ccc161aa` (retro-only change on top). Clean manifests, no
errors; the skill loaded in 78 of 78 trials.

| Case     | Correctness A | Correctness B | Completeness A | Completeness B |
| -------- | ------------: | ------------: | -------------: | -------------: |
| q019     |          0.87 |          0.87 |           0.93 |           0.93 |
| q020     |          0.50 |          0.33 |           0.30 |           0.20 |
| q021     |          0.47 |          0.30 |           0.30 |           0.20 |
| q022     |          0.83 |          0.87 |           0.67 |           0.70 |
| q023     |          0.40 |      **0.63** |           0.37 |           0.63 |
| q024     |          0.67 |          0.60 |           0.53 |           0.47 |
| q025     |      **0.70** |          0.40 |           0.63 |           0.37 |
| q026     |          0.83 |          0.57 |           0.37 |           0.50 |
| q027     |          0.30 |      **0.63** |           0.30 |           0.53 |
| q028     |          0.77 |          0.57 |           0.57 |           0.53 |
| q029     |          0.73 |          0.53 |           0.53 |           0.53 |
| q030     |          0.60 |          0.33 |           0.33 |           0.33 |
| q031     |          0.47 |          0.43 |           0.37 |           0.43 |
| **Mean** |      **0.63** |      **0.54** |       **0.48** |       **0.49** |

**What the pilot shows:**

- **The skill change did no harm where the answer is "yes", and helped q031.** q019, the guard case
  (CH-001's real drop on small counts), still scored 0.87 on both arms. q031 rose from 0.17 to 0.47
  on A and from 0.20 to 0.43 on B; each arm had one trial open with "No, … not fully recovered".
- **q023 is the clearest sign of a tree benefit.** Across both blocks, 3 of A's 6 q023 trials
  computed uptime against the 12 ports the network has today (about 83–88% instead of 12.38%); none
  of B's 6 did. Every trial queried `commissioned_minutes`, so the difference is in how the
  numbers were read, and B reads the tree, which frames uptime per period through commissioned
  minutes. Six trials per arm: suggestive.
- **q027's tree advantage didn't repeat.** In the first block every B trial split visits into
  drivers × visits per driver; this time none computed visits per driver, and two split drivers
  into new and returning (the driver skill's breakdown, as on q030). B still led, 0.63 to 0.30,
  because two A trials invented a port-level cause ("Ports 2 … were not yet online") from ports
  with no visits. The section above on q027 overstated the finding; it was one block.
- **No rows read as no equipment, or no data.** A's q027 ports, B's q020 trial 1 ("CH-001 was
  down" because there were no visits and no downtime rows) and B's q025 trials 2 and 3 ("a data
  gap") are the same failure as kwwhat#206.

**The noise.**

- **Judge:** 42 saved answers rescored 3 times each (`rejudge_results_20261123_175146` to
  `180244`, about $1): 109 of 126 judgments matched the original exactly, with a mean change of
  0.02 on Correctness and 0.01 on Completeness. The judge at temperature 0 is consistent,
  including when it is wrong: the q030 counting misread came back on every repeat. One judgment
  per answer is enough; the plan's call for several judge repeats predates temperature 0.
- **Agent:** within a case, Correctness varies with a standard deviation of 0.23 on A and 0.20 on
  B (26 degrees of freedom each). Case means moved by 0.2–0.4 between the two blocks of 3 (A's
  q030 0.83 to 0.60, A's q027 0.70 to 0.30, B's q027 0.87 to 0.63), so per-case wins from one block
  mostly don't repeat.
- **Where the noise sits:** about 80% of the spread in per-case A − B differences is trial noise.
  The real variation of the effect between cases is small, a standard deviation of about 0.09.

**Rough sizing**, for a comparison paired by case, from these estimates:

| Cases × trials per arm | Standard error of A − B | Smallest effect detectable (80% power) |
| ---------------------- | ----------------------: | -------------------------------------: |
| 13 × 3 (this pilot)    |                   0.053 |                                  ~0.15 |
| 13 × 5                 |                   0.044 |                                  ~0.12 |
| 30 × 5                 |                   0.029 |                                  ~0.08 |

The lever is more confirmatory cases, not more trials on dev. The second dev blocks (2 more
trials per arm) were skipped: they would tighten the dev table, which can't support a claim, and
change the noise estimates little.

### The sizing math

All figures are Correctness on the new-skill pilot: 13 cases, 3 trials per arm per case.

**Degrees of freedom.** The spread of 3 scores has 2 degrees of freedom: their deviations from the
mean sum to zero, so two fix the third, and the sample variance divides by k − 1. For A on q023
(0.2, 0.3, 0.7; mean 0.4), s² = (0.04 + 0.01 + 0.09) / 2 = 0.07. Averaging the 13 per-case
variances pools them: s²_A = 0.0528 (s_A = 0.23) and s²_B = 0.0379 (s_B = 0.195), each on
13 × (3 − 1) = 26 degrees of freedom. With 26, the true s_A is roughly 0.18–0.31 (95%).

**Model.** score(case, arm, trial) = overall level + case effect + arm effect + case × arm + trial
noise. Pairing by case removes the case effect. The case × arm term, with variance τ², is how much
the effect itself differs between cases; trial noise has variances σ²_A and σ²_B. The per-case
difference dᶜ = mean of A's k trials − mean of B's k trials has

Var(dᶜ) = τ² + σ²_A / k + σ²_B / k.

**Estimates.** Over the 13 cases, the mean of dᶜ is 0.082 (A ahead) and Var(dᶜ) = 0.0377 (SD
0.194). Trial noise at k = 3 is (0.0528 + 0.0379) / 3 = 0.0303, which is 0.0303 / 0.0377 = 80% of
it. The rest is τ² = 0.0377 − 0.0303 = 0.0075, τ = 0.086.

**Standard error** of the mean difference over n cases: SE = √([τ² + (σ²_A + σ²_B) / k] / n).

| n   | k   | τ²     | (σ²_A + σ²_B) / k | Total  |    SE |
| --- | --- | ------ | ----------------- | ------ | ----: |
| 13  | 3   | 0.0075 | 0.0303            | 0.0377 | 0.054 |
| 13  | 5   | 0.0075 | 0.0182            | 0.0256 | 0.044 |
| 30  | 5   | 0.0075 | 0.0182            | 0.0256 | 0.029 |

More trials shrink only the noise term; more cases divide everything, including τ², which trials
can't remove.

**Smallest detectable effect,** two-sided α = 0.05, 80% power: MDE = (z₀.₉₇₅ + z₀.₈₀) × SE =
(1.960 + 0.842) × SE = 2.80 × SE, giving 0.151, 0.124 and 0.082 for the three rows. With few cases
the t distribution is more honest: the multiplier is 2.179 + 0.873 = 3.05 at 12 degrees of freedom
and 2.045 + 0.854 = 2.90 at 29, giving 0.16, 0.14 and 0.085. As a check, the pilot's own A lead is
0.082 / 0.054 = 1.52 standard errors, below the 2.18 needed at 12 degrees of freedom: consistent
with noise, as a pilot this size should be.

**The target: an effect of 0.10** on the 0–1 Correctness scale (the author's minimum effect of
interest). The SE has to reach 0.10 / 2.80 = 0.036, so n = per-case variance / 0.036²:

| Trials per arm per case | Per-case variance | Cases (z) | Cases (t) | Trials per arm |
| ----------------------: | ----------------: | --------: | --------: | -------------: |
|                       3 |            0.0377 |        30 |        32 |             96 |
|                       5 |            0.0256 |        21 |        23 |            115 |
|                      10 |            0.0166 |        14 |        16 |            160 |

Fewer trials on more cases is the cheaper route: 32 cases × 3 trials needs fewer agent calls than
23 × 5. The case count is sensitive to τ²: at k = 5, τ² = 0 would need 15 cases, and τ² two to three
times the estimate (0.015 to 0.0225) would need 27 to 32.

**Why it's rough.**

- **Scores aren't normal.** They are bounded at 0 and 1 and come in steps of 0.1; the formulas
  assume roughly normal means, which is approximate at 13 or more cases.
- **τ² is very uncertain.** It's the difference of two noisy numbers (0.0377 − 0.0303); with 13
  cases its true value could be 0 or two to three times larger, and the case count above moves with
  it.
- **The noise isn't the same everywhere.** Per-case variances run from 0.003 (q019, q026) to 0.19
  (B on q025), and pooling assumes one σ. Confirmatory cases may be noisier or calmer than dev.
- **One endpoint is assumed.** Correctness on all cases with no multiplicity correction; restricting
  the claim to root cause cases, or testing several metrics, needs its own sizing.
- **Consistent judge errors aren't in the model.** Judge noise is included, since each trial was
  judged once, but a misread that repeats every time (q030) is bias, not noise, and no sample size
  fixes it. The blind rating (step 3) is what checks it.

### The budget

The study has $200 for agent and judge calls, pilot included (`experiment_plan.md`). The cost
ledger (`tests/outputs/cost_ledger.jsonl`) records $101.89 since Nov 8; runs from Nov 5–7 predate
it, so at most about $98 is left. Today's 144 trials averaged $0.21 each ($0.20 on A, $0.22 on B);
the judge is about $0.016 of that.

**Decided:** every confirmatory block is the size the 0.10 target needs at 3 trials, 32 cases × 3
trials. N and D are compared against A just as B is, so a smaller N or D would be a less sensitive
test than C2.

| Block            | Cases × trials | Trials |     Cost |
| ---------------- | -------------: | -----: | -------: |
| A                |         32 × 3 |     96 |     ~$20 |
| B                |         32 × 3 |     96 |     ~$20 |
| N (null control) |         32 × 3 |     96 |     ~$20 |
| D (degraded)     |         32 × 3 |     96 |     ~$20 |
| **Total**        |                |    384 | **~$81** |

That leaves about $17, less whatever the runs before Nov 8 cost. Two risks: D's cost per trial is
unknown (a degraded agent may take more queries), so a D smoke run on 2–3 dev cases (about $1–2)
comes before the budget is fixed; and every confirmatory block runs with `--max-cost`, around $25
per block, so one runaway run can't spend the margin. Further dev runs come out of the same margin
(a full 13 × 3 dev rerun on both arms costs about $16).

## Arm D, the positive control

**Decided:** D is the demo as it was before the experiment: the demo's `RULES.md` unchanged, with no
root cause skill and no rule pointing to it. It carries only the eval dataset, which the harness
reads and the agent doesn't. D therefore differs from A in exactly one thing, the skill and its
trigger, so D against A measures what the shared skill adds.

Two choices behind it:

- **The current `RULES.md`, not the one from before the experiment.** The demo's rules gained two
  lines during the study: "Skills listed under Skills … are files; open them with `read`" (kwwhat
  #198, Nov 13) and "Before querying a table, read its entry in `marts.yml`" (`54bcb3d`, Nov 18).
  Both stay in D, as in A and B, so the skill is the only difference. The data and the semantic
  model couldn't be reverted per arm in any case: `repos/` and `databases/` are synced from the
  kwwhat checkout at start-up and shared by every arm.
- **No corrupted definitions.** A first draft degraded `RULES.md` instead (grounding rules removed,
  two wrong definitions added); it was dropped in favour of the pre-experiment context.

`build-arm.sh` now copies the dataset for every arm and gives D no overlay. Rebuilt with it, A is
byte-for-byte the running A arm.

**What it means for C1.** A positive control needs an effect that is known to exist. D's effect is
the skill's, which the dev runs suggest is real (q028 scored 0.1 on both arms while the skill never
loaded, and 0.47 to 0.77 per arm and block once it did) but haven't measured across cases. If the
skill's effect turned out small, D against A would fail C1 without the instruments being at fault.
The smoke run gives a first estimate.

**The smoke run** (about $2): what a D trial costs, and whether D scores measurably below A. Four
dev cases, 2 trials each: q028 and q031, where the skill visibly changed answers on dev; q029, a
root cause case where it mattered less; and q019, a guard where A and B both scored 0.87. Set
before running: D passes if it runs without errors, costs no more than about $0.30 a trial, and
scores below A's pilot on q028 and q031.

**Smoke result** (`20261123_213057` to `213728`): passed on all three. No errors in 8 trials; $0.16
a trial ($1.31 in all); and D scored 0.10 on q028 and 0.20 on q031, against A's 0.77 and 0.47.
Without the skill D behaves like the demo before the experiment: no trial queried `dim_chargers`,
most ran 1–3 queries, and both q028 trials answered "Yes, charging demand recovered", the answer
and the 0.1 that A and B gave before the trigger fix.

**All 13 dev cases on D** (2 trials each; `20261123_213057` to `215541`, built from `5dda7a2c`
before `build-arm.sh` was committed, so the manifests say dirty; the served files are the same):

| Case     | Correctness A | Correctness B | Correctness D | D trials |
| -------- | ------------: | ------------: | ------------: | -------- |
| q019     |          0.87 |          0.87 |          0.55 | 0.8, 0.3 |
| q020     |          0.50 |          0.33 |      **0.90** | 0.9, 0.9 |
| q021     |          0.47 |          0.30 |          0.20 | 0.2, 0.2 |
| q022     |          0.83 |          0.87 |          0.45 | 0.5, 0.4 |
| q023     |          0.40 |          0.63 |          0.20 | 0.2, 0.2 |
| q024     |          0.67 |          0.60 |          0.45 | 0.5, 0.4 |
| q025     |          0.70 |          0.40 |          0.25 | 0.4, 0.1 |
| q026     |          0.83 |          0.57 |          0.40 | 0.4, 0.4 |
| q027     |          0.30 |          0.63 |      **0.65** | 0.8, 0.5 |
| q028     |          0.77 |          0.57 |          0.10 | 0.1, 0.1 |
| q029     |          0.73 |          0.53 |          0.55 | 0.6, 0.5 |
| q030     |          0.60 |          0.33 |          0.60 | 0.4, 0.8 |
| q031     |          0.47 |          0.43 |          0.20 | 0.2, 0.2 |
| **Mean** |      **0.63** |          0.54 |      **0.42** |          |

Completeness means are 0.48 on A, 0.49 on B and 0.29 on D.

- **D − A is −0.20 on Correctness** (per-case SD 0.30, so a standard error of 0.084 over 13 cases,
  about 2.4 standard errors) and −0.19 on Completeness. The smoke subset (−0.36) overstated it:
  its four cases were the ones where the skill matters most.
- **D beats A on two cases, neither because the skill hurts.** On q020 ("Was CH-001 down on Oct
  13?") D answers in one to four queries that CH-001 was not down and scores 0.9; A adds claims
  ("no visits is unusual") that contradict the reference. D's Completeness there is 0.25: it leaves
  out that CH-001 simply had no visits while CH-002 took all ten. On q027 D's trial 2 makes A's
  invention (ports 2 inactive) and scores 0.5; A's 0.30 came from two such trials of three.
- **q019's D trial 2 (0.3) is a reference and judge mismatch, not a degradation.** It attributed
  CH-001's failures to `INVALID_STOP_REASON` and `FAULTED_AFTER`, the `failure_reason` labels from
  kwwhat #204; the reference names only the error code, WeakSignal, and the judge treated the two as
  contradictory. Both are true of the same attempts (stop reason Other after a WeakSignal fault).
  The reference now names both (stop reason Other, `INVALID_STOP_REASON`, after WeakSignal) and says
  the one `FAULTED_AFTER` attempt was in a visit that succeeded on retry, so a trial that blames it
  for a failed visit is still wrong. It is also a candidate item for the blind rating.

**Stated limitation.** D's effect is about −0.2, twice the 0.10 target, so the D half of C1 shows
the instruments detect a drop of that size, not one of 0.10. A milder second control would be
needed to show sensitivity near 0.10, and the budget doesn't cover it. The paper states this. D
stays as designed because it is a meaningful control: the context before the experiment.

**A note on the metrics, from q020:** a terse answer can score high on Correctness and low on
Completeness, so a degraded arm can look better on Correctness alone in lookup cases. Both metrics
are reported.

## Lessons

- **Trigger on the shape of the question, not its words.** The skill had the right step for q028 and
  never loaded, because the question used none of the listed phrasings.
- **Loading the skill is necessary but not sufficient.** A loaded skill's step can still be skipped,
  as q028 trial 1 skipped the topology check, and a question that reads like a lookup gets
  answered at steps 1–2, as on q030.
- **A rule that says what to check must also say what the result does to the answer.** Otherwise
  the check runs and the conclusion ignores it, as on q025, q028 and q031.
- **The skill costs time and money where it does work, and only there.** On the 9 cases arm D has
  run (2 trials each, against A's and B's 3-trial pilot blocks), D averaged $0.159 and 45 s a
  trial, A $0.180 and 58 s, B $0.214 and 68 s. D was cheaper and faster on the root cause
  comparisons (q023, q024, q028, q029, q031; on q028 and q031 about half A's time), where A reads
  the skill and runs its checks and D answers after a few queries, which is also where D scores
  lowest. On cases with a direct answer (q019, q020, q022) D was slightly dearer. Paired by case,
  D is about $0.02 cheaper and 13 s faster than A. Lower cost on a case is a sign the method didn't
  run, not a saving; D's block cost depends on how many confirmatory cases are comparisons.
- **One block of 3 trials can't carry a per-case finding.** q027's tree advantage was 3 of 3
  trials in one block and didn't repeat in the next.
- **Measure whether a check changed the answer, not whether it ran.** Every trial queried
  `dim_chargers`; one still compared windows with different sites.

## Still open

- Rerun q022–q028 on the new trigger (above).
- q031: the stop and recovery rules are in; the verdict still ignores the evidence. Next: tie the recovery finding to the verdict, and rerun q031 with q019, q027 and q029 as guards.
- q030: B's driver-skill misreadings.
- The judge check on hand-written answers; the hinted solvability run.
- The kwwhat array-sort PR and the #204 follow-ups listed on 2026-11-21.
- Rebuild D from a clean commit before any confirmatory D block; the dev D runs were built from
  `5dda7a2c-dirty`.
- Blind rating of `judge_validation/rating_sheet_2026-11-23.md` (step 3).
