# Run log: medium parallel bench (three model test files), 2026-10-17, headless proxy

Same harness limits as the earlier logs (headless, Claude drives the NGISA, no human wait, no PR, nothing pushed). Base `a18a9f3`, real busy-bees, kit with warm workers, `mode: quick`, Sonnet NGISA, cold-start isolation check. Task: write unit tests (no production change) for `session_model.dart`, `syllabus_model.dart` and `notification_model.dart`, each its own test file. Plain Claude does them one after another in one session; the NGISA gets three workers in parallel from a warm pool of 3.

## Valid runs
| Run | Side | Wall | Notes |
|---|---|---|---|
| rep 1 | plain | 4m59s | 3 commits, 51 tests, $0.96 |
| rep 1 | NGISA | 2m27s | 3 files, 83 tests |
| rep 2 | plain | 4m07s | 3 commits, 69 tests, $0.97 |
| rep 2 | NGISA | 2m44s, **incomplete** | 2 of 3 files (53 tests); see below |
| rep 3 | plain | 4m40s | 3 commits, 59 tests, $1.09 |
| rep 3 | NGISA | 3m00s | 3 files, 76 tests |
| rep 2b | NGISA | not run | usage limit hit (HTTP 429, session limit, reset 1:40pm Asia/Saigon) |

- **Plain Claude:** median 4m40s (4m07s to 4m59s). Per task 1m02s to 2m09s.
- **NGISA, complete runs (2):** 2m27s and 3m00s, mean 2m43s. About 40% faster than the plain median. n = 2 complete runs plus one partial, so this is an indication, not a statistic.
- **Rep 2 incomplete:** the syllabus worker stopped (blocked) because a branch named `test/syllabus-model` already existed with someone else's commit; it refused to reset it. That is the worker doing the safe thing; the cause was leftover branches from earlier runs, because the driver's cleanup did not remove them (worker worktrees were still registered, so `git branch -D` failed). Fixed in the driver afterwards.
- **Quality:** NGISA wrote more tests per file (83 and 76 across three files against 51 to 69 for plain Claude); test counts say nothing about test quality. Blind review of these diffs has not been done.
- **Cost:** plain Claude $0.96 to $1.09 per run; the NGISA side's cost was not captured, and it uses at least three worker sessions plus the NGISA, so it spends more tokens per run even though it finishes sooner.

## What this says
On three independent medium tasks the warm-pool NGISA beats plain Claude's sequential time by roughly 40%, the first time the speed-parity target is met in these tests. The earlier results were a tie on the pair of small tasks and a loss on a tiny task, so the gain appears once there are about three tasks of 1 to 2 minutes each to run in parallel.

## Problems found while running this
1. **Two copies of the stage ran at once** (my mistake, a background `&` inside a background task). Their results were discarded and the whole stage rerun as one process with a lock.
2. **Cold workers could start in the user's main checkout** and run `git checkout -B` there (a regression from my own cold-start wording). The main checkout ended up on a worker branch with three stacked commits; I restored `main` and rewrote the cold-start rule to check isolation first and create its own worktree.
3. **`git worktree prune`** (run by my cleanup) removed four stale worktree entries in busy-bees whose directories were already gone (`fix-main-red-tests`, `notification-unread-count`, `shorebird-auto-update`, `student-detail-checkup-tab`). Their branches are intact.
4. **Usage limit.** The stage consumed the session limit; the dependent-task bench stopped on HTTP 429 after its first plain run failed to start. Nothing from that stage is valid.

## Dependent tasks (D), one run per side
Two tasks where the second needs a test helper file the first creates: D1 creates `health_test_fixtures.dart` and basic tests for `health_display_utils.dart`; D2 uses that helper for the statistics tests. The NGISA must run them in order. Both sides wrote tests only.

| Side | Wall | Notes |
|---|---|---|
| Plain Claude | 2m20s | D1 1m25s, D2 0m54s, 35 tests, $0.41 |
| NGISA (warm worker) | 3m20s (stamps 3m00s) | D1 worker 1m14s, then D2 started 1m34s after the request and took 1m16s; 33 tests |

- **NGISA is about 43% slower** (3m20s against 2m20s; n = 1 per side). With a dependency there is no parallelism to win back the handoff, so the NGISA pays plan, report and start-up costs twice. The NGISA's own report stage on D1 (1m35s) mostly overlaps the wait before it released D2.
- Output was the same size (two commits each, 33 against 35 tests).
- The driver left three warm branches and one benchmark branch behind (a quoting bug in its branch listing, so cleanup never ran for branches); removed by hand and fixed.

## Dependent tasks after the one-worker rule (D rerun)
Rule added to `orchestrating.md`: tasks that depend on each other, or touch the same file, go to ONE worker as one task text with numbered steps in order. Same two tasks, one NGISA run (plain Claude's 2m20s is the reference).

| Side | Wall | Notes |
|---|---|---|
| NGISA, two workers (before) | 3m20s | D2 in a fresh worker: 1m16s and a second handoff |
| NGISA, one worker (after) | 2m19s (stamps 2m06s) | one worker `test-health-utils`: plan 10s, worker 1m48s, report 7s; 43 tests, 3 files |
| Plain Claude | 2m20s | 35 tests |

The one-worker rule closes the gap: 2m19s against 2m20s, a tie (n = 1 per side; the NGISA wrote 43 tests against 35).

## Large bench (L): six model test files in three groups, plan mode, one run per side
The plan file was pre-written by me and marked approved, so planning time is on neither side. Plain Claude did the six tasks one after another in one session; the NGISA ran three `mode: plan` workers in parallel (two files each, per-task and final reviews inside each worker).

| Side | Wall | Tests | Notes |
|---|---|---|---|
| Plain Claude | 9m05s | 156 | 6 commits, 6 files, 2,167 lines, $3.91 |
| NGISA (3 plan-mode workers) | 5m37s (stamps 5m12s) | 127 | 5 commits, 6 files, 1,816 lines; workers 3m33s to 4m17s, report+merge wait 0m42s to 1m26s; cost not captured |

The NGISA was about 38% faster (n = 1 per side). The NGISA spends more tokens per run (three worker sessions with internal reviews plus the NGISA itself); its cost was not measured.

## Left to do
Nothing planned. Repetitions are low (one run per side for D and L, two complete NGISA runs for the medium bench) because the first stage hit the usage limit. The human-wait stages are still not measured, and output quality (not just test counts) has not been reviewed.
