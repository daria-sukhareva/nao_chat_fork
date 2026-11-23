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

## Lessons

- **Trigger on the shape of the question, not its words.** The skill had the right step for q028 and
  never loaded, because the question used none of the listed phrasings.
- **Loading the skill is necessary but not sufficient.** A loaded skill's step can still be skipped,
  as q028 trial 1 skipped the topology check, and a question that reads like a lookup gets
  answered at steps 1–2, as on q030.
- **Measure whether a check changed the answer, not whether it ran.** Every trial queried
  `dim_chargers`; one still compared windows with different sites.

## Still open

- Rerun q022–q028 on the new trigger (above).
- q031: 0 of 18 trials avoid calling a recovery; a partial-period rule.
- q030: B's driver-skill misreadings.
- The judge check on hand-written answers; the hinted solvability run.
- The kwwhat array-sort PR and the #204 follow-ups listed on 2026-11-21.
