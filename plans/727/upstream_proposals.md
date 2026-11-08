# Proposals for getnao/nao#1092

What this study has learned that should go back to
[getnao/nao#1092](https://github.com/getnao/nao/pull/1092), "Plans: propose chat context eval
designs". That PR is plans only (`plans/727/correctness_plan.md` and
`plans/727/rag_triad_plan.MD`, at `4b02276f`). It's open, and it asks for a decision on
measurement strategy and judge ownership.

These are proposals for those plans. The study's code still stays in this fork (see the
[experiment plan's settled decisions](experiment_plan.md#settled-decisions-2026-11-05)).

| #   | Proposal                                           | Status    | Changes                                                     |
| --- | -------------------------------------------------- | --------- | ----------------------------------------------------------- |
| 1   | Pin the judge at temperature 0                     | Agreed    | `correctness_plan.md` §8 "Judge Model"; `rag_triad_plan.MD` |
| 2   | Exclude the `story` tool from eval runs            | Agreed    | Both plans' backend sections                                |
| 3   | Decouple Correctness from Completeness             | Agreed    | `correctness_plan.md` §2, §8, and "rubric profiles"         |
| 4   | Build the judge's context with a denylist of tools | Agreed    | `rag_triad_plan.MD` "Tool result serialization"             |
| 5   | Give the judge the project's rules                 | Candidate | Both plans' problem statement and context capture           |
| 6   | State Faithfulness's limits                        | Candidate | `rag_triad_plan.MD` "DeepEval Metric Configuration"         |

---

## Agreed

### 1. Pin the judge at temperature 0

**The PR now:** `correctness_plan.md` §8 "Judge Model" covers which model judges, but not its
settings. The prototype sent no temperature, so the Claude judge ran at the provider's
default, and results didn't record it.

**Found:** the judge is the measuring instrument, so its noise should be as low as possible
([2026-11-05 retrospective](retrospective_2026-11-05.md), §8). With the judge pinned at 0,
rejudging the same answers gave the same Correctness score, or one 0.1 step off, across four
judgments ([2026-11-07 retrospective](retrospective_2026-11-07.md#the-rejudge-result)).

**Propose:**

- Pin the judge's temperature at 0, and record the judge settings in every result.
- Leave the agent at its default. It's the system under test.

**Caveat to state with it:** temperature 0 makes the judge reproducible, not right. A bias the
judge has every time still scores the same every time. The multi-step metrics, Faithfulness and
ContextualRelevancy, still varied by up to 0.13 at temperature 0.

### 2. Exclude the `story` tool from eval runs

**The PR now:** the eval endpoint runs the agent with its full tool set.

**Found:** an eval run uses a temporary chat that is never saved, so the `story` tool fails
whenever the agent calls it. That adds errors unrelated to the question, and changes what the
agent does next. Fixed in this fork by `31366b66`, "Exclude the story tool from eval runs".

**Propose:** the eval endpoint excludes tools that need a saved chat, starting with `story`.
Record the tool set each run had, so the exclusion is visible in results.

### 3. Decouple Correctness from Completeness

**The PR now:**

- §2 says Correctness checks that the answer "contains the required facts" and "uses the
  required terminology and framing".
- The §8 steps implement that: "Verify that every required fact … is present" and "Verify that
  the required naming, terminology, and framing are used".
- The "rubric profiles" extension adds "preserves the expected intent, terminology, and
  framing".

**Found:** with those steps, Correctness partly measures coverage and wording.

- An answer that stated nothing false, but left out one fact and didn't use the reference's
  phrase "mix shift", scored Correctness 0.7 and Completeness 0.9. The two judge reasons were
  nearly the same text.
- Rejudging gave 0.7 four times out of four. So this wasn't noise: the judge was following the
  rubric.
- Step 4's "unsupported additions" also penalizes correct extra detail.

**Propose:**

- Correctness scores only what the answer claims. Penalize claims that contradict the
  reference, and misleading details.
- State outright what not to penalize: omissions, wording, and claims the reference neither
  supports nor contradicts.
- Completeness scores coverage.
- Add GEval score bands, so a 7 has a defined meaning.
- Write references as a list of required claims, including the facts that rule out the
  likely wrong diagnoses.

**Evidence:** the fork's rubric `0015f7a322a7` does this (since refined to `fbda3f9f0f46`). On five saved answers, three judge
repetitions each
([details](retrospective_2026-11-07.md#checking-the-new-rubric-against-the-judge)):

- A wrong diagnosis still scored 0.2 every time.
- The incomplete-but-correct answer rose from 0.7 to 0.9.
- Wording stopped costing points.

Still open: a borderline answer was unstable (0.5 to 0.8), because the judge read its true
"the situation worsened" as a claim that the charger got worse. Omissions still nudge scores
within the top band.

### 4. Build the judge's context with a denylist of tools

**The PR now:** `rag_triad_plan.MD` includes `execute_sql`, `read` and `grep` in the curated
context. Every other tool is left out, and the nao team decides case by case whether a new tool
should be added.

**Found:** with an allowlist, results from `execute_semantic_query`, `load_skill`,
`read_query_result` and `task` never reached the judge. Faithfulness then scored answers
against less evidence than the agent had. SQL results were also cut to 20 rows, while the agent
sees 40.

Fixed in this fork by `NON_EVIDENCE_TOOLS` and `AGENT_VISIBLE_QUERY_ROWS` in
`cli/nao_core/commands/evals/tool_calls.py` (instrumentation plan, step 4).

**Propose:**

- Exclude a short list of tools that carry no evidence, such as `list`, `search`,
  `display_chart` and `suggest_follow_ups`. Then new tools reach the judge by default.
- Give the judge the same rows the agent saw.
- Save every tool call in the results, whether or not the judge sees it.

---

## Candidates (not yet agreed)

### 5. Give the judge the project's rules

**The PR now:** the problem statement promises to show "when a change to my `rules.md` … makes
the chat agent … use wrong terminology, or ignore my configuration". Neither plan gives the
judge the rules.

**Found:** an answer with every "visit" replaced by "session", breaking the rule
`Never use the term "session"`, scored the same as the original under the PR's Correctness
rubric, under the decoupled one, and under Completeness
([details](retrospective_2026-11-07.md#rule-compliance-tested-then-left-out-of-scope)). The
cause is where the rules travel. `rules.md` reaches the agent through the system prompt, not
through a tool, so it is never in the captured tool output the RAG triad judges against. The
Correctness judge sees only the answer and the reference. So no judge ever sees a rule the
answer could break.

**Propose:**

- Capture the project's rules for each run, as their own field, next to the captured tool
  output.
- Judge answers against them with a rule criterion of their own, rather than folding them into
  Correctness, which compares against the reference.
- Use deterministic checks where a rule allows it, such as a word match for banned terms.

Faithfulness without the rules didn't catch it either, in default or strict mode. Adding the
rules to Faithfulness's context is untested, and probably isn't enough on its own: Faithfulness
checks the answer's claims against facts, and a rule like "never say session" isn't a fact a
claim can contradict.

### 6. State Faithfulness's limits

**The PR now:** Plan A assumes that an answer grounded in relevant context is likely correct.

**Found:**

- Faithfulness scored 1.0 on wrong diagnoses, because every number in them was real.
- In long contexts with repeated values, the judge also matched numbers to the wrong dates,
  and marked a correct answer down.
- DeepEval's default counts only contradictions. Strict mode (`penalize_ambiguous_claims`)
  also counts claims the context doesn't support. On the best answer so far it scored 0.57 to
  0.70, below the 0.7 threshold. It caught real overgeneralizations ("all week" when only two
  days were queried), but two of three reasons also called the correct conclusion a
  contradiction.

**Propose:** present Faithfulness as a grounding check, not a correctness check. Don't adopt
strict mode without validating it against human labels, and don't gate on either mode until
then.
