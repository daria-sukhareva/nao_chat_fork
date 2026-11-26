# Confirmatory scenario: a new seed for the confirmatory run

**Status:** reviewed 2026-11-25. Nothing generated yet.

The confirmatory cases come from a new synthetic network generated with `demo/logs-generator`.
The dev seed and its results stay as they are;
the new seed sits beside it and is swapped in only for the confirmatory run. This file is the
scenario: the network, the episodes planted in it, the controls, the lookups, and how each is
checked after dbt builds. It lives in the nao fork, which the agent never sees; nothing in it may
be copied into kwwhat, whose repo is synced into the agent's context.

## The case rule

Decided 2026-11-25 (`experiment_plan.md`, open decision 2):

- **Metrics:** visit success rate, first-attempt against troubled success, uptime, visits, active
  drivers, commissioned ports.
- **Comparisons:** adjacent periods (hours, days, weeks), location against location and charger
  against charger in the same period.
- **Size:** a root-cause case needs a relative change of at least 20% in its metric, in either
  direction, with at least 20 events in the baseline period.
- **Mix:** about 70% root-cause cases and 30% controls, split evenly into no-change,
  partial-period and false-premise. Of 32 cases: 22 root-cause, 3 no-change, 3 partial-period, 4
  false-premise.
- **Lookups:** 8 more, on topology and metrics, for the lookup guardrail. They are not part of the
  primary endpoint.
- **Questions:** one template per case, drawn at random (seed 20261125) from the set for its
  comparison type (below).
- **References and facts:** computed by SQL after the build, to the recipe below; short reference
  style (main claim, one number, the misleading reading and data limits as negations).

One episode per root-cause case, each on its own location or charger and period, so the cases are
independent. No two episodes share a location in overlapping baseline and episode periods.

## The network

All chargers speak OCPP 1.6, with 2 ports of 2 connectors each. IDs are new (LOC-101 to LOC-108,
CH-111 to CH-182) so nothing can be confused with the dev seed.

| Location | Chargers               | Drivers                          | Notes                                                          |
| -------- | ---------------------- | -------------------------------- | -------------------------------------------------------------- |
| LOC-101  | CH-111, CH-112, CH-113 | general pool                     | 8 arrivals per port per day; CH-113 decommissioned Feb 9 (E06) |
| LOC-102  | CH-121, CH-122         | general pool                     | demand rises from Jan 12 (E10) and stays                       |
| LOC-103  | CH-131, CH-132, CH-133 | fleet pool, 60 idTags, only here | CH-133 fails often throughout (E13)                            |
| LOC-104  | CH-141, CH-142         | general pool                     |                                                                |
| LOC-105  | CH-151, CH-152         | own pool, 120 new idTags         | commissioned Jan 26, 08:00 (E07)                               |
| LOC-106  | CH-161, CH-162         | general pool                     |                                                                |
| LOC-107  | CH-171, CH-172         | general pool                     |                                                                |
| LOC-108  | CH-181, CH-182         | general pool                     | no episodes: controls and lookups only                         |

- **Period:** Monday Jan 5, 2026, 00:00 to Wednesday Mar 4, 2026, 12:00 UTC. Eight full weeks
  (W1 Jan 5 to W8 Feb 23) and a partial ninth (W9, Mar 2 to Mar 4 12:00, 2.5 days).
- **General pool:** 400 idTags shared by LOC-101, 102, 104, 106, 107 and 108, so drivers move
  between sites.
- **Baseline behaviour, every charger, unless an episode says otherwise:** 5 arrivals per port per
  day, failed plug-in 0.05, fault 0.03, retry 0.3, online Authorize 0.3, heartbeat 300 s.
- **Generation:** one appended series per charger, one run per week (per day where an episode is
  day-level), with the week's flags. Offline windows are absolute and passed to every run of the
  charger. Seeds are fixed per charger and run, so the seed is reproducible.

## Root-cause episodes (22)

B is the baseline period, P the episode period. "Misleading reading" is what the reference states
as a negation.

| ID  | Unit, comparison                    | B, P                   | What is planted                                                                                                    | Metric              | Misleading reading                                              |
| --- | ----------------------------------- | ---------------------- | ------------------------------------------------------------------------------------------------------------------ | ------------------- | --------------------------------------------------------------- |
| E01 | CH-112, week                        | W2, W3                 | Fault 0.5 on CH-112 in W3                                                                                          | visit success       | the site rate, diluted by CH-111 and CH-113                     |
| E02 | CH-131 against CH-132, same week    | W2                     | Fault 0.45 on CH-131 in W2 only                                                                                    | visit success       | demand or driver differences                                    |
| E03 | LOC-104, week                       | W3, W4                 | Both chargers offline Tue Jan 27 00:00 to Fri Jan 30 00:00                                                         | visits              | a demand drop; drivers who came left no record                  |
| E04 | LOC-106, day                        | Feb 10, Feb 11         | CH-162 offline all of Feb 11                                                                                       | uptime              | a fault; it is a loss of connection                             |
| E05 | LOC-102, hours 17:00 to 21:00, week | W4, W5                 | Both chargers offline 17:00 to 21:00 every day of W5                                                               | evening visits      | evening demand fell                                             |
| E06 | LOC-101, week                       | W5, W6                 | CH-113 decommissioned Mon Feb 9, 08:00                                                                             | visits              | demand or reliability fell; 6 ports became 4                    |
| E07 | Network, week                       | W3, W4                 | LOC-105 opens Jan 26 with 120 new drivers, 10 arrivals per port per day                                            | active drivers      | returning demand; they are new drivers at a new site            |
| E08 | LOC-103, week                       | W6, W7                 | Half the fleet idTags Expired from Mon Feb 16 to the end                                                           | visit success       | the chargers; no error codes changed                            |
| E09 | LOC-106, week                       | W2, W3                 | Arrivals 5 to 2.5 per port per day in W3                                                                           | visits              | reliability; success and uptime unchanged                       |
| E10 | LOC-102, week                       | W1, W2                 | Arrivals 5 to 8 per port per day from W2                                                                           | visits              | new chargers; the topology didn't change                        |
| E11 | LOC-104, week                       | W6, W7                 | Failed plug-in 0.35 with retry 0.9 in W7                                                                           | first-attempt rate  | visit success fell; retries rescued most visits                 |
| E12 | CH-171, week                        | W2, W3                 | Failed plug-in 0.4, retry 0 in W3                                                                                  | visit success       | a fault; no error codes, failures are anonymous                 |
| E13 | LOC-103, week                       | W3, W4                 | CH-133 fault 0.8 throughout; arrivals at CH-131 and CH-132 fall to 1.5 in W4                                       | visit success       | a charger got worse; each charger's own rate held               |
| E14 | LOC-106, hours 06:00 to 10:00, week | W7, W8                 | Both chargers offline 06:00 to 10:00 every day of W8                                                               | morning visits      | morning demand fell                                             |
| E15 | LOC-102, day                        | Feb 18, Feb 19         | Fault 0.7 on CH-121 on Feb 19                                                                                      | visit success       | the token or driver side                                        |
| E16 | LOC-101, day                        | Fri Jan 30, Sat Jan 31 | Arrivals 3 per port per day on Jan 31 (base 8)                                                                     | visits              | an outage or reliability; the data doesn't show why demand fell |
| E17 | LOC-106 against LOC-101, week       | W5                     | CH-161 offline Mon Feb 2 00:00 to Thu Feb 5 00:00                                                                  | uptime              | faults; it is a loss of connection on one charger               |
| E18 | LOC-104 against LOC-102, week       | W1                     | Fault 0.4 on both LOC-104 chargers in W1                                                                           | visit success       | demand or drivers                                               |
| E19 | CH-151 against CH-152, week         | W6                     | Failed plug-in 0.5, retry 0 on CH-151 in W6                                                                        | successful visits   | fewer drivers chose CH-151                                      |
| E20 | LOC-107, week                       | W5, W6                 | Fault 0.3 with retry 0.95 on CH-172 in W6                                                                          | failed-attempt rate | visit success fell; retries kept visits successful              |
| E21 | LOC-105, week                       | W7, W8                 | 40% of LOC-105's idTags Blocked from Mon Feb 23 to the end                                                         | visit success       | the chargers; an equipment problem                              |
| E22 | CH-171, week                        | W7, W8                 | Fault 1.0 and 20 arrivals per port per day on CH-171 in W8, so both connectors of a port are often faulted at once | uptime              | a loss of connection; it is faulted downtime                    |

Coverage: weeks (14), days (3), hours (2), location against location (2), charger against charger
(2). Metrics: visit success (9), visits (7), uptime (3), active drivers, first-attempt rate and
failed attempts (1 each).

Not covered, by design: a change in a single connector, which the generator can't target, and a
change at a single hour, too few events to pass the 20-event floor.

## Controls (10)

| ID  | Kind           | Question gist                                                | Why it is a control                                                                 |
| --- | -------------- | ------------------------------------------------------------ | ----------------------------------------------------------------------------------- |
| N1  | No change      | Did visit success at LOC-108 change in W4 against W3?        | No episode; must change by less than 10%                                            |
| N2  | No change      | Did visits at LOC-101 change on Jan 15 against Jan 14?       | The first adjacent day pair in W2 within 10%; the process didn't change             |
| N3  | No change      | Did uptime at LOC-106 change in W2 against W1?               | No outage in either week                                                            |
| P1  | Partial period | Did visits at LOC-108 drop in the week of Mar 2?             | W9 has 2.5 days; the raw drop is coverage, not demand                               |
| P2  | Partial period | Did visit success at LOC-103 recover in the week of Mar 2?   | Partial week, and the fleet tokens are still expired: the cause continues (as q031) |
| P3  | Partial period | Why were there fewer visits on Mar 4 than on Mar 3?          | The data ends at 12:00 on Mar 4                                                     |
| F1  | False premise  | Why did visit success at LOC-108 drop in the week of Feb 9?  | It didn't                                                                           |
| F2  | False premise  | Why did CH-111 go offline in the week of Jan 19?             | It had no outage                                                                    |
| F3  | False premise  | Why were LOC-104's chargers decommissioned in February?      | They weren't                                                                        |
| F4  | False premise  | Why did active drivers at LOC-108 fall in the week of Feb 9? | They rose                                                                           |

## Lookups (8)

| ID  | Kind     | Question                                                                       |
| --- | -------- | ------------------------------------------------------------------------------ |
| L1  | Topology | How many ports were commissioned at LOC-101 on Feb 10, 2026?                   |
| L2  | Topology | When was LOC-105 commissioned, and with which chargers?                        |
| L3  | Topology | How many chargers were in commission on the network on Mar 1, 2026?            |
| L4  | Topology | Which chargers are at LOC-103, and how many ports does each have?              |
| L5  | Metric   | What was LOC-102's visit success rate in the week of Jan 12, 2026?             |
| L6  | Metric   | What was network uptime in January 2026?                                       |
| L7  | Metric   | How many active drivers did LOC-106 have in the week of Feb 16, 2026?          |
| L8  | Metric   | What share of LOC-104's successful visits were troubled in the week of Jan 12? |

## Question templates

One is drawn per case. Dates are written out, with the year.

- **Period change:** "Why did {metric} at {unit} {drop or rise} in {P} compared to {B}?",
  "What caused the change in {metric} at {unit} between {B} and {P}?", "Did {metric} at {unit}
  change in {P} compared to {B}, and why?"
- **Unit against unit:** "Why was {metric} at {unit A} lower than at {unit B} in {P}?", "What
  explains the difference in {metric} between {unit A} and {unit B} in {P}?"
- **Hours:** "Why did {metric} between {h1} and {h2} at {unit} {drop or rise} in {P} compared to
  {B}?"
- **Recovery:** "Did {metric} at {unit} recover in {P}?"
- **No change and false premise:** the period-change templates, with the direction the premise
  states.

## References and facts

Computed by SQL from the built marts, to one recipe per case type, after the checks below pass.

- **Short reference:** the verdict and cause; the metric in B and P; the misleading reading as a
  negation; the data limits that apply (partial period, anonymous visits can't be tied to drivers,
  drivers who came while a charger was offline left no record).
- **Facts:** the topology of the case's locations over B and P (chargers, ports, commissioning,
  outages); the metric at period and daily grain, and per charger; the data range; how anonymous
  visits are recorded; error codes and `failure_reason` labels together wherever failures are
  counted.

## Checks after the build

The generator writes what was intended; dbt must show it. Each check is a SQL query against the
marts, and the seed is accepted only when every check passes.

- **Every episode:** its metric changes in the planted direction by at least 20%, with at least 20
  events in B; and the misleading reading is false (for example, E09's success and uptime change
  by less than 5%, E13's per-charger rates by less than 5%).
- **Outages:** each offline window appears in `fact_downtime_daily` as OFFLINE for its charger,
  within one heartbeat interval of the planted times, and nowhere else.
- **Topology:** commissioning and decommissioning in `dim_chargers` match `chargers.csv`.
- **Tokens:** E08 and E21 rejections appear as `AUTH_REJECTED` with the planted statuses, and
  nowhere else.
- **Retries:** E11 and E20 raise troubled visits as planted, and visit success changes by less
  than 5%.
- **Controls:** N1 to N3 change by less than 10%; F1 to F4's premises are false; P1 to P3's
  periods are partial as stated.
- **Independence:** no episode's metric moves by more than 10% in another episode's unit and
  periods.

A failed check means the scenario's parameters change and the seed is regenerated, before anyone
sees an agent answer.

## The seed beside the dev seed

- The new seed goes to `demo/seeds_confirmatory/` in kwwhat (logs, `chargers.csv`,
  `connectors.csv`, `ports.csv`), beside `demo/seeds/`. The log file is about 100 MB, so it is
  gitignored and rebuilt by the script, which is deterministic; its sha256 and the generator commit
  are recorded in `work/seed_manifest.json`. Driver pools and the auth list stay in `work/`,
  outside kwwhat, because they reveal the token episodes.
- `docker-compose.yml` mounts `demo/${SEED_DIR:-seeds}`, so the public demo keeps the dev seed and
  the confirmatory run sets `SEED_DIR=seeds_confirmatory`. dbt rebuilds with `--full-refresh` on
  every start, so the swap needs no other change.
- The generation script and its schedule live in the nao fork (`plans/727/confirmatory/generate_seed.py`, outside `study/` so arm builds stay clean),
  not in kwwhat, so the agent can't read the scenario.

## Size and cost

32 primary cases plus 8 lookups, 3 trials, 4 arms: 480 trials, about $100 at $0.21 a trial. With
about $110 spent of $300, that leaves about $90 for the judge validation round, any regeneration,
and contingency.

## Generation and tuning (2026-11-25)

The seed was generated, built and checked three times; parameters changed between rounds, all
before any agent answer existed. Final seed: sha256 `60e2d349…`, 808,718 log rows, generator at kwwhat `622e28b`. dbt builds with all 31 models, 370 data tests and 110
unit tests passing, and all 78 scenario checks pass (`check_seed.py`).

- **Round 1 (39 of 78):** a fresh build processed nothing, because dbt reads one
  `incremental_window` (3 months) from `start_processing_date` (2025-10-01); the dbt service now
  takes `START_PROCESSING_DATE` (2026-01-01 here), and unit tests run without it since their
  fixtures assume the default. Then: E07 rose only 15% (pool 80 to 120); E16's baseline had 17
  visits (LOC-101 base 5 to 8); E20's failed-attempt count had 4 baseline events (metric changed
  to the failed-attempt rate, 117 baseline attempts); E22 moved uptime 1%; F4's premise was
  true by chance (W7 to W6). Two check bugs: outages are at port grain, and "held" was a fixed
  5%, which a charger failing 80% of the time can't meet on ~55 visits (now a two-proportion
  z-test, |z| < 2).
- **Round 2 (75 of 78):** E16's one-day rise saturated, because a port serves one driver at a
  time and arrivals while it's busy are lost (LOC-101 tops out near 40 visits a day); E16 became
  a one-day drop. E22 reached only 7% at site level (now CH-171, fault 1.0, 20 arrivals). N2's
  day pair moved 16%, daily noise; N2 is now the first adjacent day pair in W2 within 10%.
- **Round 3:** all 78 pass.

Noise is large enough to matter: LOC-108, which has no episodes, moved 24% in visits from W7 to
W8 by chance. Controls are therefore checked against the built data, not assumed.

## Review decisions (2026-11-25)

- The 22 episodes stay as they are.
- 8 lookups are enough for the guardrail.
- Partial-period controls use W9 only.
- Commissioned ports added to the metrics.
- Facts are optional: a case without them is judged against its reference alone, and confirmatory
  mode doesn't require them.
