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

## Lessons

- **Trigger on the shape of the question, not its words.** The skill had the right step for q028 and
  never loaded, because the question used none of the listed phrasings.

## Still open

- Rerun q022–q028 on the new trigger (above).
- q031: 0 of 18 trials avoid calling a recovery; a partial-period rule.
- q030: B's driver-skill misreadings.
- The judge check on hand-written answers; the hinted solvability run.
- The kwwhat array-sort PR and the #204 follow-ups listed on 2026-11-21.
