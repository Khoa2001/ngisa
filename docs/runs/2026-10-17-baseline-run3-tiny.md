# Run log: speed parity, replacement tiny task (T1), 2026-10-17, headless proxy

Same harness limits as `2026-10-16-baseline-run1.md` and `2026-10-17-baseline-run2.md` (headless, Claude drives the NGISA, no human wait, no PR, nothing pushed). Base `a18a9f3`, real busy-bees. NGISA side: warm pool (`agent-warm 2`, ready after 35s, not counted), Sonnet NGISA, no worker report, kit as of run 2 plus the `agent-warm` lock.

Task T1 (replaces the FormDataEx task): `StringEx.capitalize()` throws a `RangeError` on an empty string; return it unchanged for empty input, keep the rest, add a `capitalize` test group. Unconditional change; two real call sites, nothing shadows it.

## Results
| Side | plan | worker/work | report | merge | total (stamps) | wall | Cost |
|---|---|---|---|---|---|---|---|
| plain Claude (`claude -p`, sonnet) | 0m34s | 0m34s | - | - | 1m08s | 1m09s | $0.14 |
| NGISA (warm worker, Sonnet NGISA) | 0m11s | 1m25s | 0m11s | 0m00s | 1m47s | 2m07s | not captured |

## Reading
- **Quality is the same.** Both sides made the identical one-line fix (`if (isEmpty) return this;`) and added 4 tests; the test file passes on both (16 tests). The blind diffs `T1b_A.diff` and `T1b_B.diff` are in the scratchpad folder (the code part is identical; the test text differs).
- **Speed: NGISA is slower on the tiny task.** 2m07s against 1m09s wall (+58s, about 1.8x), 1m47s against 1m08s by stamps (+39s). This is the worst case for the design: one short task, one handoff.
- **Where the extra time is.** The worker alone (1m25s) is already longer than plain Claude's whole run (1m08s) for the same one-line change. Plus plan 11s, report 11s and about 20s of start-up and wrap-up that the stamps leave out. So even with the pool warm and no report, a single handoff costs about 40-60s on a task that takes about 1 minute.
- **Rule status** ("tiny and small: NGISA total at or below plain Claude's"): **not met**, and it cannot be met by shaving the handoff alone, because the worker's own time exceeds plain Claude's whole run.
- **Pair vs tiny summary:** pair is a tie (run 2: 2m46s against 2m43s), tiny is 1.8x slower. Parallel work amortizes the handoff; short single tasks cannot.

## Implication for the design
To reach plain-Claude speed on tiny/small work the NGISA has to skip the worker for those tasks (an inline lane in the user's own session, or the user running plain Claude directly). The user did not choose the inline lane earlier. The remaining options are to accept the gap on tiny tasks, or reopen that choice with this data.

## Left behind
Cleaned up after this run (see the cleanup note in the session): this run's branches, worktrees and sessions.
