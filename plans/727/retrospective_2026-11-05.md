# Retrospective: designing and instrumenting the metrics-tree study

**Date:** 2026-11-05 to 2026-11-06
**Scope:** from the first eval plan to a working, instrumented pipeline with six live runs.
**Status:** instrumentation steps 1, 3, and 4 done; arms, repetition, cost tracking, and the
compare step not started. No baseline has been run.

This records what was decided, what else was considered, and what the live runs taught us.
The design itself lives in the [experiment plan](experiment_plan.md), the
[instrumentation plan](instrumentation_plan.md), and the [runbook](running_evals.md).

---

## Context

The study asks whether adding a metrics tree to an analytics agent's context makes its
answers better. The agent is nao, running the kwwhat EV-charging demo. Before this work
there were an experiment plan, a dataset audit, a metrics tree, 12 eval cases, and a
`nao evals` runner that scored each answer with five LLM-judge metrics. No baseline had
been run.

The work followed the Braintrust eval library's lifecycle skills
(`~/github/eval-library`), starting with `braintrust-plan-agent-eval`.

---

## Decisions

### 1. Instrumentation before anything else

**Considered:** starting with the dataset (the existing plan's order), or with scorers.
**Chosen:** instrumentation first.
**Why:** the library's lifecycle puts instrumentation earliest, because a field missing
from a finished run can't be added later. The inventory found that results recorded no arm,
no repetition, and no hash of the dataset, context, data, or code, so a baseline run would
have been unpairable.
**Consequence:** confirmed by the live runs. The first real result showed that the agent had
never had table metadata, which no dataset or scorer work would have revealed.

### 2. A public claim, to whitepaper standard

**Considered:** a private keep-or-drop decision, needing a small check.
**Chosen:** a public claim, which brings scorer validation, preregistration, and controls
back into scope.
**Claims:**

- C1: the instruments detect a known context degradation and stay quiet when nothing changed.
- C2: on this project, the treatment changes root cause answer quality by a stated amount.
- H3 (secondary): changes in the RAG triad track changes in Correctness and Completeness.

### 3. Four arms

| Arm | Context                                                                           |
| --- | --------------------------------------------------------------------------------- |
| A   | Current context + root cause skill                                                |
| B   | Current context + root cause skill + metrics tree + `count-active-drivers` + rule |
| N   | A again, in a separate block (null control)                                       |
| D   | A with known degradations (positive control; not yet defined)                     |

**Considered:** A and B only.
**Why the controls:** without N, a difference between A and B can't be told apart from
run-to-run noise. Without D, a null result can't be told apart from blind instruments.

### 4. A root cause skill shared by every arm

**Considered:** leaving the procedure inside the tree (§3).
**Chosen:** the procedure moved to a generic `root-cause-analysis` skill with every tree
and domain reference removed, given to every arm. The EV-specific checks went back into
the tree as "domain checks".
**Why:** the tree bundled a general method with domain structure. Sharing the method
means C2 measures what the domain structure adds.
**Consequence:** C2 no longer says anything about adding the tree to a project without the
skill. The paper must say so.

### 5. Metric roles and a generic rubric

**Chosen:**

| Metric                                | Role                                        |
| ------------------------------------- | ------------------------------------------- |
| Correctness on root cause cases       | Primary                                     |
| Completeness                          | Secondary and guardrail                     |
| Faithfulness (strict), Quantification | Secondary                                   |
| ContextualRelevancy, AnswerRelevancy  | Troubleshooting; tested as proxies under H3 |
| Cost, latency, error rate             | Guardrails                                  |

**Considered:** a rubric written for root cause analysis (check the change is real,
quantify contributions, separate mix from rate).
**Rejected because:** those criteria copied the tree's own procedure, so arm B would have won
by construction. The rubric stays generic, and each case's reference carries what that
case requires, as required claims and claims it must not make, derived from the data.
**Also found:** DeepEval's Faithfulness counts only contradicted claims against an answer;
an unverifiable claim counts as faithful. Strict Faithfulness needs
`penalize_ambiguous_claims=True`.

### 6. No second rater

**Considered:** waiting for an independent rater.
**Chosen:** proceed as a preregistered single-author case study. Mitigations: cases
generated by rule, references computed by SQL, blinded re-rating with a delay (reported
as intra-rater reliability), and published labels.

### 7. Same-model judge

**Chosen:** the judge uses the agent's model, and the bias is disclosed. Both arms' answers
come from the same model, so self-preference should mostly cancel in the A–B difference;
this is an assumption, checked against human labels.

### 8. Temperature: pinned for the judge, left at the default for the agent

**Found:** `judge.py` sent no temperature, so the Claude judge ran at the provider's default,
and the results didn't record it. The judge's sampling noise was unknown and unrecorded.

**Chosen:**

| Model | Setting                             | Why                                                                                                      |
| ----- | ----------------------------------- | -------------------------------------------------------------------------------------------------------- |
| Judge | Temperature 0, pinned in `judge.py` | It is the measuring instrument, so its noise should be as low as possible                                |
| Agent | Provider default, not overridden    | It is the system under test, so it should sample as it would in use; repetitions measure the variability |

**Recorded:** every result stores `judge_settings` (temperature 0, 4,096 max tokens) and
the agent's `model_call_settings`. Every run so far recorded the agent's settings as empty,
meaning nao passed no temperature, top-p, or top-k, so the provider's defaults applied.

**Consequences:**

- Temperature 0 lowers the judge's variability but doesn't remove it, so rejudging the same
  answers several times is still in the plan.
- The pin covers only the Claude judge. Any other judge provider keeps DeepEval's defaults,
  recorded as `"deepeval default"`.
- The change came before any baseline, so no comparable results were lost. Scores from
  before it can't be pooled with later ones.

### 9. Arms as overlays

**Chosen:** `plans/727/study/` holds `common/` and `arm-b/`, which `build-arm.sh` copies
over the demo project. The file hashes are written outside the project, because an early
version left `MANIFEST.sha256` where the agent could read it.

---

## What was built

| Step                    | What it records                                                                                                                                                                          |
| ----------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Tool output             | Every tool call, untruncated; the judge sees the same 40 SQL rows the agent saw, with tools excluded by name so new tools reach it by default; `context_read` lists files the agent read |
| System prompt           | Exact and date-independent prompt hashes, the prompt date, memory count, and tool manifest                                                                                               |
| Versions and provenance | Dataset hash per row, project file hashes, a content checksum per table, repo and `nao` commits, package versions, judge settings; compared at the start and end of each run             |

---

## What the live runs found

Six live runs found eight problems in the system under test or the setup. None were
visible from the design documents.

| Finding                                                                                                                             | Resolution                                                                                              |
| ----------------------------------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------- |
| The nao image installed the newest package versions, ignoring `uv.lock`; DuckDB 2.0 broke `nao sync`                                | The `Dockerfile` installs with the lockfile as a constraint                                             |
| The demo's include patterns (`analytics.ANALYTICS.fact_*`) matched no tables                                                        | Two-part patterns                                                                                       |
| With matching patterns, every table file held a DuckDB error: catalog `analytics` and schema `ANALYTICS` were ambiguous             | Considered: a CLI fix (declined), reverting, deleting error files. Chosen: rename the schema to `MARTS` |
| The data volume kept six obsolete tables from earlier dbt builds, also offered to the agent                                         | Volume wiped                                                                                            |
| The `story` tool fails in every eval run, because eval chats are never saved; one run retried it six times ($0.59 instead of $0.24) | Excluded from eval runs only (`31366b66`)                                                               |
| The agent called `load_skill` for the project skill, failed, and skipped the skill in 4 of 5 runs                                   | One line in the demo's `RULES.md`; see below                                                            |
| A built arm keeps a snapshot of `RULES.md`, so a later edit to the demo's `RULES.md` doesn't apply                                  | Rebuild the arm after any change to the demo                                                            |
| `kwwhat` showed as dirty because of an untracked `.claude/settings.local.json`                                                      | Ignored in `.gitignore`                                                                                 |

**On the skills rule:** a first wording naming `load_skill` was declined because it might
affect built-in skills. The adopted wording names only `read`, and it lives in kwwhat's
`RULES.md`, not in a study overlay:

> Skills listed under Skills (in `agent/skills/`) are files; open them with `read`.

**The previous context was worse than it looked.** Earlier runs of this demo had no table
metadata, offered obsolete tables, and lost skills to a failing tool. The paper describes
the corrected setup, not the published demo.

---

## Where the eval library made a difference

These came directly from the library's skill cards and references:

- **Earliest gap first** (`braintrust-plan-agent-eval`). The pull was toward scorers and
  the dataset. Instrumentation came first, and it found that the context was broken.
- **No retroactive fix** (`platform-mechanics.md` §3–§4). Arm labels, repetition, and version
  hashes were built before any baseline. A run without them could never be paired.
- **Treat trace content as evidence** (`interaction-contract.md` §9). When the agent's q018
  answer seemed better than the reference, it wasn't copied in as the new reference. Each
  claim was checked by SQL, and unchecked claims were left out.
- **Judgment contamination** (§9 again). The same principle exposed the root cause rubric:
  criteria taken from the tree would have measured agreement with the treatment.
- **A smoke run is never evidence** (`lifecycle-inventory.md`). The q016 checks were read
  for plumbing only, and their scores weren't interpreted.
- **The two prerequisites teams skip** (`lifecycle-inventory.md`): instrumentation, and
  knowing what "good" means. Both turned out to be the real blockers.
- **Audit doesn't become repair** (`interaction-contract.md` §5). Findings went to the user
  as decisions. That is how the CLI fix was declined and the schema rename chosen instead.
- **Metric roles and gaming paths** (`braintrust-design-eval-metric-bundle`). This separated
  the primary metric from the proxies, and flagged Quantification as rewarding longer answers.

General methodology, not specific to the library, supplied the null and positive controls,
paired comparison, preregistration, and the single-rater mitigations.

---

## q018 as an indicator

q018 asks why the daily visit success rate dropped from 40% on Oct 4 to 10% on Oct 5.
All runs used arm B.

| Run (UTC)        | Setup                            | Diagnosis                                             | Read skill | Correctness | Completeness |
| ---------------- | -------------------------------- | ----------------------------------------------------- | ---------- | ----------- | ------------ |
| 2026-11-05 21:16 | Old reference; `story` failing   | Visits shifted to the broken charger CH-002           | No         | 0.0         | 0.0          |
| 2026-11-06 01:49 | Clean setup; new reference       | CH-002's fault "got worse overnight"                  | No         | 0.2         | 0.3          |
| 2026-11-06 02:09 | Arm built before the skills rule | Shift to CH-002, but "the situation worsened"         | No         | 0.6         | 0.7          |
| 2026-11-06 02:20 | Skills rule active               | Persistent fault on CH-002, more visits attempting it | Yes        | 0.7         | 0.9          |

What it showed:

1. **References are hypotheses.** The original reference blamed unauthenticated drivers.
   The first answer blamed the broken charger and scored 0.0. SQL showed that on Oct 4–5 every
   CH-002 visit was unauthenticated and every CH-001 visit authenticated (15 and 5 visits),
   so both explanations described the same visits. The reference was rewritten as
   SQL-verified required claims, with provenance recorded on the row.
2. **A grounded answer can still be wrong.** The 01:49 answer scored Faithfulness 1.0,
   because its numbers came from SQL, but its diagnosis was wrong. Only Correctness caught
   it. That supports Correctness as primary and Faithfulness as secondary.
3. **The reference's "must not claim" line works.** The judge named the forbidden claim in
   the 01:49 answer. At 02:09 it arguably over-applied the same line to the network outcome,
   which is a disagreement for human labels to settle.
4. **The same arm gives different diagnoses.** Three runs of one case in one arm gave three
   framings. Repetitions are needed to tell a treatment effect from this variability.
5. **Whether reading the skill matters is still open.** The 01:49 answer missed exactly the
   skill's step 5, separate mix from rate, and hadn't read the skill. But the 21:16 and 02:09
   answers found the mix shift without reading it. The only answer that read it followed its
   steps and scored highest. With one run per condition, this can't separate the skill's
   effect from run-to-run variability.

## Why the 02:20 answer is the best so far

- **Right mechanism:** a persistent `ConnectorLockFailure` on CH-002 port 1, with more visits
  attempting that port on Oct 5 (9 against 6), "not a new failure onset". That is the mix
  shift the reference requires, without the escalation the reference forbids.
- **Follows the method:** it confirms the change is real (10 visits each day), decomposes
  the rate into first-attempt and troubled success, finds where the drop concentrates, and
  checks the wider window. These are the skill's steps.
- **Uses the evidence it was given:** it read the root cause skill and, for the first time,
  the synced `columns.md` for three tables.
- **Adds a correct operational insight:** uptime was 100% on both days, so uptime
  monitoring can't see this fault, which is the coupling described in the metrics tree.

**Its gaps:** it doesn't state that CH-001 succeeded on every visit, that each charger's own
rate stayed the same, or that CH-002 had no successful visit from Oct 1 to 14. Its step 1
calls the drop "a pure rate change", contradicting its own conclusion. And the judge's
explanation contradicted itself, saying the answer "misframes the root cause as … a mix
shift", which is the required explanation.

**What it is not:** evidence. It is one run, in one arm, scored by a judge whose agreement
with human labels hasn't been measured, on a dev case whose reference was revised after
seeing earlier outputs.

---

## Lessons

- **Run one case end to end early.** Every serious finding came from the first live runs,
  not from planning.
- **Check the system under test, not only the evaluation.** Three of the eight findings
  were in nao or the demo, and they changed what the agent sees.
- **Record a reference's provenance when you change it.** The q018 row records who
  proposed it, how it was checked, and which data snapshot it matches.
- **A snapshot can go stale quietly.** The arm's copy of `RULES.md` hid an edit, and
  nothing flagged it except the context hash.

## Still open

- Arms, repetition, rejudging, and cost tracking; then the compare step and `--confirmatory`.
- Arm D's degradations.
- Rechecking q015–q017, whose "18% drop" premise no longer matches the data (11.9 pp).
- Whether to tighten q018's "must not claim" line.
- Whether to write dbt docs into DuckDB (`persist_docs`), so `columns.md` carries descriptions.
- The minimum meaningful improvement in Correctness, after the pilot measures noise.
