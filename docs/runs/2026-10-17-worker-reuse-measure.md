# Run log: worker reuse measure (2026-10-17, headless proxy, one run per side)

Question: does reusing a finished warm worker beat giving each task a fresh warm worker, and how do both compare with plain Claude? Real busy-bees, base `a18a9f3`, Sonnet everywhere, kit with `worker-ctx`, `worker-retire`, `agent-wall.sh --close`. Same harness limits as the earlier logs: Claude drives the NGISA as a `claude --bg` session, no WezTerm panes (new headless marker file `~/.cache/ngisa/headless` makes `agent-wall.sh` skip pane handling), no human wait, nothing pushed, `AskUserQuestion` forbidden in the prompt.

## Tasks
Four test-writing tasks (no production change), all in `lib/features/schedule/models/`: `session_model`, `syllabus_model` (request 1) and `holiday_model`, `calendar_exam_model` (request 2). The NGISA got both requests in one prompt and was told to treat request 2 as a new request after request 1 was recorded. Plain Claude did the four one after another in one `claude -p` session in a pre-set-up worktree (setup untimed, like the warm pool). Both NGISA sides started with 2 warm workers ready (untimed).
- reuse: "apply your Reuse rule for request 2".
- fresh: "do NOT reuse or retire finished workers; fresh warm worker per task" (the PR #34 behavior).

## Results
| Side | Wall | Tests (4 files) | Commits | Tokens (cache read / cache write / output) | Cost |
|---|---|---|---|---|---|
| plain Claude | 230s | 70 | 4 | 0.52M / 0.056M / 15k | $0.43 (reported) |
| NGISA, reuse | 239s | 73 | 5 | 3.28M / 0.28M / 26k | not reported |
| NGISA, fresh warm | 206s | 63 | 5 | 3.14M / 0.27M / 21k | not reported |

- Wall times for the NGISA sides are read from the NGISA transcript (first to last message): reuse 22:52:45 to 22:56:36 local time (the harness only saw `done` at 239s but then waited to its 25 minute cap; see problems), fresh 16:19:27 to 16:22:53 UTC (the same clock as the transcript) (the session then stayed `working` for 13 minutes inside a Stop hook).
- What the reuse NGISA did: request 1 to `warm-1` and `warm-2`; for request 2 it ran `worker-ctx` on both, reused `warm-1` for `holiday-model` ("same dir, ctx 76k, tasks 1") and used the fresh `warm-3` for `calendar-exam-model` because `warm-2` was still `working` (its refill had not finished). It closed every pane with `agent-wall.sh --close`.
- The fresh NGISA's refills (`agent-warm 2` after each batch) were ready in time, so request 2 started on warm workers with no wait.

## Reading
1. **No speed win from reuse here.** 239s against 206s for fresh warm workers (n = 1, a 33s gap is inside the noise); the refill pool is already hiding the start-up that reuse would save.
2. **No token saving from reuse.** The reused worker carried 76k of old context into its second task; totals are within about 5% of the fresh run.
3. **NGISA against plain Claude:** a tie on wall time (206s to 239s against 230s) for four small tasks in two batches, at roughly 6x the cache-read tokens, 5x the cache writes and 1.4 to 1.7x the output of plain Claude. The extra tokens are the NGISA's own context re-read on every turn plus one worker session per task. Plain Claude's dollar cost was $0.43; the NGISA sides' cost was not reported by `claude --bg`, so no dollar figure is claimed.
4. The earlier "three medium tasks in parallel: about 40% faster" result does not repeat here because these tasks are smaller (`mode: quick`, 1 to 1.5 minutes each) and arrive in two serial batches of two.
5. Quality: all sides wrote the four test files and every test passes; test counts (63 to 73) say nothing about test quality; blind review of the saved diffs has not been done.

## Problems found while running this
1. **Harness end detection** waited for every `busy-bees-*` session to stop working; old sessions of the user's own (blocked or working) never do, so the first run ran to its cap although the NGISA finished at 239s. Fixed to end when the NGISA is done.
2. **Stop hook hang:** in the second run the NGISA session stayed `working` for 13 minutes after its last message ("running Stop hook… 0/2"). Not investigated; it delays `notify_when_idle` for anything waiting on the NGISA, so it is worth a look.
3. The token sums include the initial warm-up sessions of each side (about the same for both) and the background refill sessions.

## Decision
Keep pane close (`--close`) and `worker-retire` (tidier screen, bounded pile of sessions). The reuse rule did not earn a speed or cost advantage on this setup; keep it as written (it costs nothing when no worker qualifies) but do not expect a gain, and re-test on larger tasks or a repo with a slow setup, where a warm refill takes longer than a batch.
