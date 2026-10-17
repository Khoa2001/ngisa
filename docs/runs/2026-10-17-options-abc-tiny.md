# Run log: three ways to speed up a tiny task (2026-10-17, headless proxy)

Task T1 (`StringEx.capitalize()` empty-string fix), base `a18a9f3`, real busy-bees. Same harness limits as the earlier logs (headless, Claude drives the NGISA, no human wait, nothing pushed). One run per option, so network jitter (roughly 10-20s) can move any single number; compare with that in mind.

## Options
- **A** plain Claude directly (`claude -p`, sonnet). Measured in `2026-10-17-baseline-run3-tiny.md`.
- **B** inline lane: the Sonnet NGISA does the task itself in a prepared worktree (`.claude/worktrees/lane`), no worker.
- **C** lean worker: normal warm worker path, but the task text starts with a LEAN MODE paragraph (only the listed change and tests, no red-first ritual, one run of each check, one-line final message).
- Reference: the standard warm-worker NGISA from run 3.

## Results
| Option | plan | work | report | stamps total | wall | cost |
|---|---|---|---|---|---|---|
| A plain Claude | 0m34s | 0m34s | - | 1m08s | 1m09s | $0.14 |
| B inline lane (NGISA Sonnet) | 0m06s | 0m39s | 0m00s | 0m45s | 1m12s | n/a |
| C lean warm worker | 0m11s | 0m47s | 0m06s | 1m04s | 1m24s | n/a |
| reference: standard warm worker | 0m11s | 1m25s | 0m11s | 1m47s | 2m07s | n/a |

All four produced the identical one-line fix and a 4-test `capitalize` group (18 added test lines in A, B and C); tests pass (16 in the file). Saved diffs: `blind/T1_optionB_inline.diff`, `blind/T1_optionC_lean.diff` (scratchpad).

## Reading
- **B reaches parity** (1m12s against 1m09s, +3s) and is the only option that removes the handoff. The stamps (45s) leave out about 27s of NGISA session start-up and wrap-up.
- **C gets close** (1m24s, +15s or +22%) without changing who edits code; it cut the worker from 1m25s to 47s, so the worker's thoroughness (red-first, extra cases, repeated checks) was most of the old gap.
- Quality did not differ on this task: same code, same number of test lines. One small task cannot show whether lean mode loses quality on harder ones.
- **Neither is "strictly below" plain Claude** on a tiny task; B ties, C is within about a fifth.

## What B needed (harness-only, not built in the kit)
The spike found three blocks the kit would have to change:
1. `ngisa-settings.json` deny patterns `Edit(lib/**)` also match files under `.claude/worktrees/lane/lib/`; with root-anchored patterns (`Edit(/lib/**)`) the Edit tool worked in the lane. Not verified: that the anchored patterns still block edits in the main checkout.
2. `ngisa-guard` blocks `fvm flutter test` ("runs tests directly"); the spike run used a guard wrapper that allows commands starting with `cd <repo>/.claude/worktrees/lane`.
3. A lane worktree has to exist with setup done (7s here); `dart analyze`, `git add` and `git commit` were allowed already.
B also breaks "NGISA never writes code" for tiny tasks, which was the earlier objection.

## Cleanup
This round's sessions, worktrees (`lane`, `warm-1`, `warm-2`, `integration-baseline`) and branches were removed afterwards. Nothing pushed.
