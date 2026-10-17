# Run log: speed parity re-measure, run 2 (2026-10-17, headless proxy)

Same protocol and harness limits as `2026-10-16-baseline-run1.md` (headless, Claude drives the NGISA, no human wait, no PR, nothing pushed). Base `a18a9f3`, real busy-bees, kit re-installed with `real-init`. Changes under test: warm workers (`agent-warm`, `--attach`), no worker report (result read with `worker-result`), Sonnet NGISA. Pair only (DateTimeEx + ColorEx tests); the T1 tiny task was not re-run (still to be replaced).

## Setup
- Pool: `agent-warm 2` started `busy-bees-warm-2` and `-warm-3` (ready after 39s, deps installed, not counted in the run). It ignored the used spike worker `warm-1` ("free: 0").
- NGISA: `claude --bg`, Sonnet, headless, auto mode, told not to ask questions, merge into `baseline/ngisa-pair2` in `.claude/worktrees/integration-baseline`, no `agent-pr`.

## Results (pair)
| Side | plan | worker | report | merge | total (stamps) | wall (launch to idle) |
|---|---|---|---|---|---|---|
| plain Claude, T2 then T3 in one session | 0m39s / 0m22s | 0m36s / 1m05s | - | - | 1m16s + 1m27s = 2m43s | 2m43s |
| NGISA run 1 (cold workers, Opus NGISA, reports) | 6s / 8s | 1m44s / 2m38s | 0m00s | 0m00-2s | 2m46s | 3m02s |
| NGISA run 2 (warm workers, Sonnet NGISA, no report) | 21s / 21s | 1m05s / 1m53s | 1m00s / 0m13s | 2s / 1s | 2m28s | 2m46s |

Per task, run 2: `t2-datetime-ex` worker 1m05s, 17 tests; `t3-color-ex` worker 1m53s, 21 tests; both pass (re-run in the warm worktrees by the controller). Plain Claude wrote 13 and 10 tests, NGISA run 1 wrote 29 and 14.

## Reading
- Against run 1 the NGISA is faster: wall 3m02s to 2m46s (-9%), workers 1m44s to 1m05s and 2m38s to 1m53s.
- Against plain Claude it is a tie, not a win: wall 2m46s against 2m43s (+3s); by stamps 2m28s against 2m43s, but the stamps leave out about 18s of NGISA start-up and wrap-up. n = 1 per side, so treat the 3-second gap as noise. The rule asks for strictly below, so it is **not shown met**.
- The plan stage went up (6s to 21s): the Sonnet NGISA does more checks first (agent list, worker-result calls), or it is slower to start. Not investigated.
- `report` 1m00s on t2 is the NGISA waiting for t3 before merging both, which is inherent to the parallel pair, not overhead.
- What remains is worker time, not handoff time: the workers still write about twice the tests plain Claude writes (17 and 21 against 13 and 10) and the color worker took 1m53s against plain Claude's 1m27s for the same task. Going lower means either lighter workers (a quality choice) or running tiny/small work in the NGISA's own session (an option the user did not choose).

## Findings
1. **Duplicate warm worker.** Two `busy-bees-warm-4` sessions exist: the two refill calls (`agent-warm 1`, one per assignment) ran at the same time and each saw the same highest index. This is the known no-lock gap (deferred); it is real now and costs an extra idle session. A `mkdir` lock in `agent-warm` would fix it.
2. **Used workers keep the state `working`** in `claude agents` minutes after their last line (`done test/t2-datetime-ex`). The free test treats `working` as not free, so this is safe, but the state label cannot be used to tell a used worker from a busy one; use the branch check (`branch: warm/N`).
3. The warm path, the idle notice, `worker-result`, the commit-body result and the stamps all worked end to end in the headless proxy. Not exercised: the cold fallback, a blocked worker, a real `--attach` pane, a human reading the report.

## Left behind (local, nothing pushed)
Branches `baseline/plain`, `baseline/ngisa-pair`, `baseline/ngisa-pair2`, plus the spike branches `warm/1`, `test/color-ex-warm`; task branches `test/t2-datetime-ex`, `test/t3-color-ex`; worktrees `warm-1` to `warm-4`, `integration-baseline` and others under `busy-bees/.claude/worktrees/`, the plain-Claude worktree `~/Projects/dotb/busy-bees-baseline-plain`; sessions `busy-bees-warm-1..4` (two named `-warm-4`), the NGISA session, the older baseline sessions.
