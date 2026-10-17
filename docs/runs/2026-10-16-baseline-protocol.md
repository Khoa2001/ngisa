# Speed parity: baseline protocol (2026-10-16)

Spec: `docs/superpowers/specs/2026-10-16-speed-parity-design.md`. Goal: NGISA not slower than plain Claude at the same quality. Measure first, then cut. This file is the protocol the baseline and the re-measure (phases 2 and 4) both reuse. Fill the tables in place, one section per run.

## The three tasks (repo: busy-bees)

Chosen by the user on 2026-10-16 (proposed by Claude after a read-only look at `~/Projects/dotb/busy-bees`). Frozen (T1 replaced on 2026-10-17: the original `FormDataEx.clone` task hid dead code and the two sides diverged, see `2026-10-16-baseline-run1.md`). Real repo, base commit `a18a9f3` (`main`) for all three.

| Id | Kind | Task | Paths it may touch |
|---|---|---|---|
| T1 | tiny | `StringEx.capitalize()` throws a `RangeError` on an empty string (it reads `this[0]`). Make it return the empty string unchanged for empty input and keep every other behavior (first letter upper, the rest lower). Add a `capitalize` test group: empty string, one letter, `hELLO` gives `Hello`, already capitalized. No "confirm it is a bug" step: the change is unconditional. | `lib/core/extensions/string_ex.dart`, `test/core/extensions/string_ex_test.dart` |
| T2 | small, parallel pair | Unit tests for `DateTimeEx`, no production change. | `test/core/extensions/datetime_ex_test.dart` |
| T3 | small, parallel pair | Unit tests for `ColorEx`, no production change. | `test/core/extensions/color_ex_test.dart` |

T2 and T3 touch independent files, so NGISA can run them as two workers at once. T2 and T3 are the same two tasks as Run 1 (in a lab clone); start from scratch, never reuse those results.

Give both sides the same task text (above). Verify only the task's own test file with `fvm flutter test <file>` and `fvm dart analyze <paths>`: `main` has about 12-14 old failing tests, so do not run the full suite. If T1 turns out not to be a bug, the side reports that and stops without a code change; record it as a result.

Before the NGISA side: run `real-init ~/Projects/dotb/busy-bees` again (the repo's `CLAUDE.local.md` is the old copy of `orchestrating.md` without the Stamps rules), restart the NGISA with `repo-tab`, and `ngisa-report clear` any stale row.

## Run order

1. Pick one base commit per task (T2 and T3 may share one). Both sides start from that same commit.
2. Plain Claude first, on a fresh branch off the base. Plain Claude means a normal `claude` session in the repo, no NGISA, no kit rules.
3. Then NGISA, on another fresh branch off the same base, in a clean session (a fresh NGISA session, new `repo-tab`; `ngisa-report clear` runs at the task message).
4. Never reuse a branch or a worktree between sides. Never let the second side see the first side's diff.
5. Pair (T2, T3): plain Claude does them one after the other in one session, NGISA does them as two parallel workers.
6. On both sides the user asks for the PR in the same message as the merge OK, so the merge stage is comparable.

## What to record, per task and side

| Field | NGISA | Plain Claude |
|---|---|---|
| Stage times | `ngisa-report timing`, pasted as is | stopwatch, same stage names |
| Interventions and why | every time the user had to step in (approvals, answers, corrections, NGISA editing code) | same |
| Cost | CLI total at the end of the run | CLI total at the end of the run |
| Checks | the worker's `gate:` line (checks the repo's `CLAUDE.md` names) | the checks Claude ran, as it reported them |

### Stage names

Same five columns on both sides so they compare:

| Column | NGISA (`ngisa-report timing`) | Plain Claude (stopwatch) |
|---|---|---|
| plan | request to worker spawn | task message to the first edit |
| worker | spawn to worker report | first edit to "done" message |
| report | worker report to my decision (`decided`) | "done" message to my OK |
| merge | decision to PR (`pr`) | OK to branch pushed or ready to merge |
| total | request to `pr` (else the last stamp) | task message to ready to merge |

A dash means the stage did not happen or was not stamped (for example no ask, so no `decided`).

### Reading `ngisa-report timing`

Stamps (`mark - request`, then `mark <slug> spawn|report|decided|pr`) are silent; the NGISA runs them. Output is one line per task:

```
tiny-fix  plan 2m00s  worker 10m00s  report 2m00s  merge 1m00s  total 15m00s
```

The user runs `ngisa-report timing` from the target repo checkout (the report is keyed by repo name, here busy-bees) and pastes the output into this repo's `docs/runs` log and the run table at run end. For the pair, run it once (it prints one line per worker slug).

Per-stage columns compare NGISA baseline vs NGISA re-measure. Across sides only the totals compare (plain Claude research lands in plan, NGISA worker research lands in worker).

Small bias in NGISA's favour: `request` is stamped a few seconds after the user's message. The user also stopwatches the NGISA total from the message.

### Run table (copy per task and side)

| Task | Side | Base commit | Branch | plan | worker | report | merge | total | Interventions (count, why) | Cost | Checks |
|---|---|---|---|---|---|---|---|---|---|---|---|
| T1 | plain | | | | | | | | | | |
| T1 | NGISA | | | | | | | | | | |
| T2 | plain | | | | | | | | | | |
| T2 | NGISA | | | | | | | | | | |
| T3 | plain | | | | | | | | | | |
| T3 | NGISA | | | | | | | | | | |
| T2+T3 | plain (sum) | | | | | | | | | | |
| T2+T3 | NGISA (pair) | | | | | | | | | | |

Pair totals: plain Claude's pair total is the sum of its T2 total and its T3 total (sequential, one after the other). NGISA's pair total is the wall-clock time from the first request to the last PR, with both workers running at once; in the timing output that is the largest per-slug total.

## Blind diff review

Quality is judged by the user on the two diffs, without knowing which is which.

1. For each task, flip a coin to assign the labels: heads = NGISA is A, tails = NGISA is B. Write the assignment in the sealed line below and do not look at it.
2. Show the user both diffs labelled A and B only (no branch names, no commit messages that name the tool).
3. The user scores each diff 1 to 5 on correctness, scope (only what the task asked) and tests (adequate and meaningful), before the reveal.
4. Then reveal which side was which and copy the scores into the table.

| Task | Coin | NGISA is | Side | Correctness (1-5) | Scope (1-5) | Tests (1-5) | Note |
|---|---|---|---|---|---|---|---|
| T1 | | (sealed) | A | | | | |
| T1 | | (sealed) | B | | | | |
| T2 | | (sealed) | A | | | | |
| T2 | | (sealed) | B | | | | |
| T3 | | (sealed) | A | | | | |
| T3 | | (sealed) | B | | | | |

After the reveal, quality is equal when the NGISA side scores no lower than plain Claude on each of the three criteria (decided by the user, 2026-10-16). Pair quality = T2 and T3 both equal.

## The "equal" rule

- T1 (tiny) and any small task alone: NGISA total at or below plain Claude's total.
- Pair (T2 + T3): NGISA pair total strictly below plain Claude's sequential total (T2 total plus T3 total).
- Quality equal as above (the 1-point allowance is only a proposal until the user decides). Faster at lower quality does not count.

Verdict per task (fill in): T1 ___  pair ___.

## Notes

- Vietnamese copy check (plan Task 4): `rg -n "ngisa-report"` over `docs/orchestration/one-terminal-orchestrator.md` and `.vi.md` shows the same mentions in both, and the plan does not change the English orchestrator doc, so no `.vi` change needed. `lab-quickstart.md` and `orchestrating.md` have no `.vi` copy today; left as is.
- This is run data, per the project rule: log time, interventions and why, check results and cost for every run under `docs/runs/`.
