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
