# Run log: warm worker spike (2026-10-16)

Phase 0 of the speed parity phase 3 plan. Headless harness (see `2026-10-16-baseline-run1.md` for its limits), real busy-bees checkout, base `a18a9f3`, kit re-installed with `real-init`. One warm worker, one task (the ColorEx tests, same text as the baseline T3).

## What was run
- Warm-up: `claude --bg --name busy-bees-warm-1 --agent implementer --model sonnet "<warm-up prompt>"` in the repo root. The worker created `.claude/worktrees/warm-1` (branch `warm/1`), ran `worktree-include` and `./tool/setup.sh`, and ended its turn with `warm ready`. State `done`, resumable.
- Assign: a Sonnet NGISA session (`NGISA_MODEL=sonnet`, headless, auto mode) sent one `SendMessage` to `busy-bees-warm-1` with `notify_when_idle: true`, stamped `spawn`, waited for the notice, then stamped `report` and read the result with git.

## Results
| Question | Result |
|---|---|
| (a) Does an NGISA-class `SendMessage` reach an idle `--bg` worker without the approval hold? | Yes. Delivered, no hold, no delivery notice. (My own interactive session's messages were held; the NGISA session's were not.) |
| (b) Does a finished `--bg --agent implementer` keep its worktree and accept a task by message? | Yes. It resumed, checked out the new branch, wrote the test file, committed (`1bc190b`, 1 file, +77 lines, 11 tests, analyze clean). |
| (c) Does `notify_when_idle` fire when the worker finishes? | Yes, about 1m47s after the send. Not tested: the blocked case. |
| (d) Time saved by a warm worker | Warm-up took 35s, off the critical path. Send to idle: 1m47s for ColorEx (11 tests). The cold worker in the baseline took 2m38s for the same task (14 tests, one red-then-fix cycle). About 50s saved, but the outputs differ in size, so treat it as an estimate. |

NGISA stamps for the spike: `plan 0m06s  worker 1m47s  total 1m53s` (no `decided`/`pr`, no merge). Plain Claude's T3 total was 1m27s.

## Findings
1. The plan holds: a warm worker works as designed on all three spikes that could have failed it.
2. The worker did not write the `checks:`, `unverified:`, `asks:` trailers; it only left the attribution trailer. That instruction was only in the warm-up prompt, not in `implementer.md`. The build must put the commit-body convention in `implementer.md` and test it, or the NGISA has nothing to read instead of a report.
3. The NGISA read the result from git (`git log -1`, `git diff --stat`) and answered correctly without a worker report.

## Left behind (local)
Branches `warm/1`, `test/color-ex-warm`; worktree `.claude/worktrees/warm-1` in busy-bees; sessions `busy-bees-warm-1` and `ngisa-busy-bees` (done).
