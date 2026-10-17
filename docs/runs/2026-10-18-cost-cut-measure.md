# Run log: NGISA cost cut re-measure (2026-10-18, headless proxy)

Question: after the cost cut (lean worker profile, `ngisa-start`/`ngisa-spawned`/`ngisa-collect`, worker call pattern, warm pool on demand, one-task rule), how close is the NGISA to plain Claude? Real busy-bees, base `a18a9f3`, Sonnet everywhere. Same harness limits as `2026-10-17-worker-reuse-measure.md` (Claude drives the NGISA as a `claude --bg` session, no panes via the headless marker, no human wait, nothing pushed, `AskUserQuestion` forbidden). Harness changes: NGISA wall is read from the transcript (first to last message, ending when the merge exists), tokens are split by role (NGISA, workers, unused warm-ups), warm pool starts at 1 like `repo-tab`. One run per side; plain Claude is the earlier run for `small4` and a new one for `par3`.

## Scenarios
- `small4`: four test-writing tasks in two requests of two (as in the reuse measure). Plain Claude does the four in one session.
- `par3`: one request with three independent tasks (`session_model`, `syllabus_model`, `calendar_exam_model` tests).
- `one`: a single tiny task (checks the one-task rule only).

## Results
| Scenario | Side | Wall | Cache read | Cache write | Output | Requests | Est. cost vs plain |
|---|---|---|---|---|---|---|---|
| small4 | plain | 230s | 0.52M | 56k | 15.4k | 11 | 1.0x ($0.43 reported) |
| small4 | before the cut (reuse run) | 239s | 3.28M | 280k | 26k | 53 | about 4.2x |
| small4 | after, first run (buggy `ngisa-collect`) | 192s | 2.33M | 119k | 21.4k | 48 | 2.4x |
| small4 | **after, fixed** | **194s** | **1.89M** | **128k** | **19.4k** | **46** | **2.25x** |
| par3 | plain | 188s | 0.42M | 55k | 16.0k | 9 | 1.0x ($0.42 reported) |
| par3 | after, first run (buggy `ngisa-collect`) | 181s | 1.79M | 126k | 18.3k | 41 | 2.3x |
| par3 | **after, fixed** | **148s** | **1.31M** | **94k** | **16.5k** | **33** | **1.73x** |
| one | after | 13s | 27k (NGISA) | 26k | 0.2k | 1 (+2 warm-up) | about 1 request |

- Est. cost: weights read 0.1, write 2, output 5 (cache price ratios), applied to the token classes; `claude --bg` reports no dollar cost for the NGISA sides. It is an estimate, not a measured bill. Plain Claude's reported cost is real.
- Against plain Claude (fixed runs): small4 time 0.84x (16% faster), tokens read 3.6x, write 2.3x, output 1.26x; par3 time 0.79x (21% faster), read 3.1x, write 1.7x, output 1.03x.
- Role split, small4 fixed: NGISA 0.96M read in 16 requests, workers 0.88M in 28 requests (7 each), warm-ups 0.05M. par3 fixed: NGISA 0.64M in 11 requests, workers 0.67M in 22, warm-ups 0.05M.
- All sides wrote all test files and every test passes (51 to 70 tests); counts say nothing about test quality, blind review of the saved diffs is still not done.
- The one-task rule works: the NGISA answered `tiny: 1 new test file, 1 concern. one task: run it in plain Claude` in one request and started no worker.

## Problems found while running this
1. **`ngisa-collect` said `blocked` for every good worker** in the first runs: the `asks:` parser read the `Co-Authored-By:` trailer as a continuation of `asks: none`. The NGISA overrode it by hand (extra `ngisa-report set` and `agent-wall.sh --close` calls, about 3 requests per worker) so the first runs overstate the NGISA's request count. Fixed with two tests that include a trailer; the table's "fixed" rows are after the fix.
2. **Waiting for warm workers cost requests:** with a pool of 1, `ngisa-start; agent-warm 2 &` made the NGISA poll with 3 to 4 extra requests (about 30s). Fixed by `ngisa-start --need N`, which tops up and waits inside the script.
3. The NGISA still spends one request on `ToolSearch select:SendMessage`; the rules now tell it to run that in the same turn as `ngisa-start` (the effect is inside the "fixed" rows only for par3).

## Reading
- The cut worked where measured: against the reuse measure, small4 cache read went from 6.3x to 3.6x of plain Claude, cache write from 5x to 2.3x, estimated cost from about 4.2x to 2.25x, and wall time from a tie (239s against 230s) to 16% faster. par3 is 21% faster at an estimated 1.73x cost.
- **The bar is not met on cost:** the target was within about 1.5x of plain Claude for two or more tasks; the fixed runs are at 1.7x to 2.25x (estimate). Time passes the "not slower" part and is 16% to 21% faster; "clearly faster" for three parallel tasks is a moderate 21%.
- The NGISA is still about half of all cache reads (base context 54k, 11 to 16 requests); workers are the other half (26k base, 7 requests each).

## What would close the gap (not built; estimates)
1. NGISA base context 54k to about 40k with `--disable-slash-commands --setting-sources project,local --strict-mcp-config` (the spike measured 40.9k for that set), keeping the full profile as an option for big plans: about 25% of the NGISA's half.
2. Worker requests 7 to 5 (a stricter call pattern; the Read-after-checkout step and the retry of red checks are the likely extras): about 28% of the workers' half.
3. NGISA requests 16 to about 12 (one `ngisa-collect` per worker is already one request; the rest is the second `ngisa-start`, `ToolSearch`, merge and report).
