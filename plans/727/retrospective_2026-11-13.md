# Retrospective: a second arm B run on a stale build

**Date:** 2026-11-13 (covers a run started on the evening of 2026-11-12)
**Scope:** a re-run of arm B on q019 and q022–q027, meant to test the changes made after the first
exploratory A/B run; it ran on the old build instead.
**Status:** No study files changed except this retrospective. The changes from 2026-11-12 are
committed (`7ec0c6fa` in the study, `172273e` in kwwhat) but not yet built into either arm.

This follows the [2026-11-12 retrospective](retrospective_2026-11-12.md).

---

## The re-run used the old build

Arm B ran q019 and q022–q027 twice each, 14 trials, all completed without errors. Agent $2.79,
judge $4.04, $6.83 in total.

The results' arm manifest is identical to the first B run's: `sha256` `bda7ac74…`, `study_commit`
`fc4bcd63`, and the same hashes for `RULES.md`, both skills, the tree and the dataset. The dataset
has no q028. `demo/chat-bi/arm.json` dates from 14:34 on 2026-11-12; the study commit with the
changes, `7ec0c6fa`, came at 16:26. `build-arm.sh` wasn't re-run, and the container served the old
arm. So this run had:

- no `RULES.md` line pointing to the root-cause skill;
- no location step in the skill;
- neither new sentence in the tree;
- the old q024 and q025 questions, without "compared to Oct 15–19";
- no q028.

One change did reach the agent: the removal of `drivers_count`. The kwwhat files are synced from
the mounted repo at container start, outside the manifest (an open item from 2026-11-12), and
`172273e` was in place when this container started.

The run doesn't test the changes. It is a second run of the same arm B, with one difference in the
synced context, and that makes it a measure of run-to-run noise.

## Two runs of the same arm

Correctness, two trials per case:

| Case     | B, run 1 (2026-11-12) | B, run 2 (this run) |
| -------- | --------------------- | ------------------- |
| q019     | 0.7, 0.7              | 0.7, 0.4            |
| q022     | 0.7, 0.5              | 0.5, 0.9            |
| q023     | 0.4, 0.4              | 0.6, 0.9            |
| q024     | 0.4, 0.3              | 0.4, 0.4            |
| q025     | 0.4, 0.4              | 0.4, 0.4            |
| q026     | 0.9, 0.8              | 0.7, 0.6            |
| q027     | 0.7, 0.7              | 0.8, 0.9            |
| **Mean** | **0.57**              | **0.61**            |

The root-cause skill was read in every trial except q019's, as in run 1.

### Findings

- **Two runs of one arm differ more than the two arms did.** Arm B's mean moved by 0.04 between
  runs; A and B differed by 0.03 in the first run. Within one case, the same arm ranged from 0.4 to
  0.9 (q023) and from 0.5 to 0.9 (q022). The first run's A/B gap is inside this noise and says
  nothing about the tree. This is two trials per case, scored once each, so it also mixes agent and
  judge variance; `--judge-repeats 3` would separate them.
- **q023's commissioning error didn't recur, on the same tree.** The 2026-11-12 retrospective said
  "the tree caused q023's error": both run-1 B trials read CH-001's 475 minutes as a mid-period
  commissioning. In run 2, trial 2 says CH-001 was decommissioned partway through Oct 15 and that
  CH-003 and CH-004 came in on Oct 20, and scores 0.9; trial 1 doesn't say why CH-001 drops out. The
  tree's wording may have caused the error; with two trials per run, the data can't show that it
  did. The tree fix stays, as a clarification, not a proven repair. Trial 1 again gives the outage
  an end of Nov 3, the end-of-data artifact.
- **Without `drivers_count`, arm B counts drivers by the skill.** In q025 both trials counted each
  anonymous visit as a driver: about 82 drivers over Oct 5–14 against 20 after Oct 19 (trial 1), and
  44 against 20 over Oct 10–14 (trial 2). Trial 1 concluded "there weren't more drivers". Both
  found the cause, LOC-002 opening on Oct 20 with 20 new drivers and no anonymous visits, but chose
  their own baselines, since the question they got had none. The reworded question names one.
- **The judge misreads the q025 reference.** The reference says "10 on CH-003 and 10 on CH-004",
  meaning drivers. The judge read it as visits and marked trial 2's 50 visits at LOC-002 wrong
  ("should be 20"). The agent's own figure was inconsistent: 50 in the text, 48 in its table.
  Writing "10 drivers on CH-003 and 10 on CH-004" removes the ambiguity; not yet done.

---

## Lessons

- **Check the manifest before reading results.** `study_commit` and the dataset's row list show in
  a minute whether the run used the intended build. Here they showed it hadn't, before any answer
  was read.
- **A replicate is worth having.** The run tested nothing it was meant to, but it measured the
  noise that the first comparison needed and lacked.
- **Two trials can't attribute an error.** An error both trials share may still be chance; a
  cause needs the error to persist across runs, or a change that removes it.
- **References must name their units.** A bare number next to a charger reads as visits to the
  judge.

---

## Still open

- Rebuild both arms from `7ec0c6fa` and check the results' manifest (`study_commit`, q028 in the
  dataset) before reading them. `build-arm.sh` refuses an existing output directory or manifest,
  so move the old ones aside first.
- Then re-run q019, q022–q025 and q028 on both arms, as planned on 2026-11-12.
- Make `build-arm.sh` or `nao evals` warn when `study_commit` differs from the study repo's `HEAD`.
- In q025's reference, write "10 drivers on CH-003 and 10 on CH-004", pending the author's approval.
- Size the noise before any A/B claim: more repeats per case and `--judge-repeats 3`.
- Carried over from 2026-11-12: hash the synced context in the arm manifest; the thinning rule in
  the generation rule; `--metrics correctness --metrics completeness`; the kwwhat issues; a fixed
  `as_of`; the remaining seed types; the pilot and sizing; threshold calibration; arm D; the A/B
  pairing files; `persist_docs`.
