# Retrospective: a stale build, a rebuilt arm B, and the network's layout

**Date:** 2026-11-13 (covers a run started on the evening of 2026-11-12)
**Scope:** a re-run of arm B on q019 and q022–q027, meant to test the changes made after the first
exploratory A/B run, that ran on the old build instead; the first cases of arm B on the rebuilt arm;
why q022 keeps failing (the agent can't see the network's layout, and `port_id` isn't unique); and
two kwwhat issues that came out of it.
**Status:** No study files changed except this retrospective. Arm B is running on the rebuilt arm
(study commit `55bdd743`, whose `study/` folder matches `7ec0c6fa`); q019, q022 and q023 are in,
q024, q025 and q028 and all of arm A are still to run. kwwhat issues
[#195](https://github.com/appspace/kwwhat/issues/195) and
[#196](https://github.com/appspace/kwwhat/issues/196) are filed; nothing in kwwhat has changed.

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

## Arm B on the rebuilt arm, first three cases

The arm was rebuilt and its manifest checked before the run: `study_commit` `55bdd743` (the only
change since `7ec0c6fa` is this retrospective), the new hashes for `RULES.md`, the skill and the
tree, and q028 in the dataset. The `--metrics` flags were left out, so all five metrics ran again
($0.89–1.24 per case).

| Case | B, run 1 | B, run 2 (stale build) | B, rebuilt arm |
| ---- | -------- | ---------------------- | -------------- |
| q019 | 0.7, 0.7 | 0.7, 0.4               | 0.8, 0.9       |
| q022 | 0.7, 0.5 | 0.5, 0.9               | 0.4, 0.5       |
| q023 | 0.4, 0.4 | 0.6, 0.9               | 0.3, 0.8       |

- **The `RULES.md` line works.** All six trials read the root-cause skill, including both q019
  trials; q019 had never read it before. Both q019 trials found WeakSignal, the drop on Oct 6–7 and
  the recovery on Oct 8, with Completeness 0.9 against 0.4–0.6 before.
- **The `dim_chargers` pointer works where it sits.** Both q023 trials queried `dim_chargers`,
  which no B trial on the old tree did, and both said CH-001 was decommissioned at 07:55 on Oct 15.
  Trial 1 quoted the new sentence. Its 0.3 came from giving daily uptime against Oct 8–14 rather
  than the period's 12.38% against Oct 1–14: q023's question names no baseline either.
- **q022 didn't improve.** Neither trial queried `dim_chargers`. Trial 1 said CH-001 "also went
  offline"; trial 2 read Oct 20's visits at LOC-002 as "CH-002 came back online", the mistake the
  new tree sentence about sites was meant to prevent.

Two trials per case, against a spread of 0.4 to 0.9 within one arm, make none of these score
changes a result; what the answers did is the evidence.

## q022: the agent can't see the network's layout

The author's reading: q022 fails because the network's layout isn't clear to the agent, not
because of the tree. All eight q022 trials so far support it:

| Run            | Correctness | Queried `dim_chargers` | Counted ports with `COUNT(DISTINCT port_id)` |
| -------------- | ----------- | ---------------------- | -------------------------------------------- |
| A, run 1       | 0.8, 0.2    | trial 1 only           | no                                           |
| B, run 1       | 0.7, 0.5    | no                     | both                                         |
| B, run 2       | 0.5, 0.9    | no                     | both                                         |
| B, rebuilt arm | 0.4, 0.5    | no                     | trial 2 (trial 1 used `port_key`)            |

- **One trial in eight looked at the charger dimension**, and it was among the better answers.
- **`port_id` isn't unique across the network.** It is the port number within a charger, "1" or
  "2", from the raw `ports` source. `COUNT(DISTINCT port_id)` returned 2 ports on Oct 14 for a
  network of 4. From that, the rebuilt arm's trial 2 concluded "no other chargers were
  commissioned", and then explained Oct 20's visits at LOC-002 by CH-002 coming back.
- **The rest of the layout is inferred, not looked up.** Trial 1 read CH-001's 475 commissioned
  minutes on Oct 15 as an outage. `fact_downtime_daily` gives only a hashed `location_key`, so one
  trial joined `dim_locations` to learn where the outage was.
- **Descriptions wouldn't have reached it.** The trial that counted 2 ports read only the semantic
  model, not any `columns.md`. A column's name and values reach every query; its description
  reaches only the agents that read it.
- **`connector_id` has the same trap, less often.** It runs 1–4 within a charger, as OCPP's
  `connectorId` does (the staging description, "within the port", is wrong). The agents used it in
  2 of 395 queries.

So q022 has mostly tested whether the agent reconstructs the layout, not the tree's
supply–demand reasoning, which explains both its spread and why the tree's sentence about sites
had no effect. The layout is a fact about the data, not part of the treatment: a fix belongs in the
context both arms share, or arm B would get credit for data documentation. A written description
of this particular network was rejected: it would give away q022's answer and go stale with every
new scenario. The agent should be pointed to where the layout is, not told what it is.

### Unique ids instead of better names

Options considered, for `port_id`:

- **Better descriptions only.** Cheapest, but they don't reach the agents that fail.
- **A rename: `port_number`, `port_index`, `port_local_id`.** `port_number` reads as a number
  within something; a bare `port` would collide with the semantic model's `port` entity. Names
  ending in `_id` were rejected: models treat `_id` as safe to count and join on.
- **Change the values (chosen).** `port_id = 'CH-002-1'`, unique across the network, with the raw
  number kept in `port_number`. `COUNT(DISTINCT port_id)` then gives the right answer, results
  read "CH-002-1 offline", and the agent keeps the most natural name. Connectors follow the
  charger, since that's where their numbers are unique: `connector_id = 'CH-002-3'`,
  `connector_number = 3`.

Filed as kwwhat [#195](https://github.com/appspace/kwwhat/issues/195), written by the
analytics-product-manager agent. Reading the code added: the OCPP log join on the raw connector
number must move to `connector_number`; seven incremental models key on these columns and need a
`--full-refresh`; `port_key` values change; row counts and metric totals must match the build
before the change. Adding `location_id` to `fact_downtime_daily` is in the issue as optional.

When it lands, the references' facts still hold, but every fingerprint has to be re-checked, and
it is a change to the common context: comparisons of q022 across that change measure the ids as
well as the tree. It waits until arm A has run on the current build, so this round is the before.
Unique ids don't make the agent look at `dim_chargers`; a line in the root-cause skill's step 1
("check which chargers and ports were commissioned at each location in each period") is still
proposed for that.

## Generating scenarios from a narrative

Describing the current scenario in plain language for the author (two sites, four chargers, three
acts: a charger that fails every attempt while online, the site going dark on Oct 15, a new site
with new drivers from Oct 20 and a demand drop in the week of Oct 27) suggested the generation
rule's form: a narrative in, logs out. Filed as kwwhat
[#196](https://github.com/appspace/kwwhat/issues/196): an LLM skill over the synthetic OCPP
generator in kwwhat PR #85 that turns a narrative into seeds and generator calls, writes a
`scenario_facts` file of the intended truths, and checks after `dbt build` that the marts reproduce
them. The current scenario is its acceptance example.

Reading #85 showed what it can't yet produce, filed as requirements G1–G5: a charger online that
fails every attempt with one code (the scenario's central event), faults on chosen dates, named or
anonymous drivers kept to a location, exact counts, and short offline blips. The ±20% tolerance for
"about" figures is the agent's proposal. #85's seeds put CH-003 at LOC-001 from Oct 1, against
LOC-002 from Oct 20 in the demo data, so they shouldn't be merged into the demo as they are. dbt
has never run on #85's output.

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
- **A pointer works only where the agent passes.** The `dim_chargers` pointer sat under commissioned
  minutes: q023 went through it, q022 didn't.
- **Fix the data before documenting it.** An identifier that isn't unique misleads every query;
  a description helps only the agents that read it.
- **Ask what a case tests before reading its scores.** q022 was written for the tree's
  supply–demand branch, and mostly tested whether the agent can count ports.

---

## Still open

- Finish arm B on the rebuilt arm (q024, q025, q028), then run arm A on the same build, checking
  each results file's manifest first.
- After arm A: implement kwwhat #195, rebuild both warehouses, re-check every fingerprint, and
  record it as a change to the common context.
- Decide on the root-cause skill's step 1 line about which chargers were commissioned where.
- Give q023 a baseline ("compared to Oct 1–14"), as q024 and q025 got.
- kwwhat #196 (scenario generator) depends on PR #85; decide the tolerance and #85's CH-003 seed.
- Make `build-arm.sh` or `nao evals` warn when `study_commit` differs from the study repo's `HEAD`.
- In q025's reference, write "10 drivers on CH-003 and 10 on CH-004", pending the author's approval.
- Size the noise before any A/B claim: more repeats per case and `--judge-repeats 3`.
- Carried over from 2026-11-12: hash the synced context in the arm manifest; the thinning rule in
  the generation rule; `--metrics correctness --metrics completeness`; the kwwhat issues; a fixed
  `as_of`; the remaining seed types; the pilot and sizing; threshold calibration; arm D; the A/B
  pairing files; `persist_docs`.
