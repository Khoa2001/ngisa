# Run log: speed parity baseline, run 1 (2026-10-16, headless proxy)

Protocol: `2026-10-16-baseline-protocol.md`. Base commit `a18a9f3` (`main` of busy-bees, real repo). Quality bar: NGISA no lower than plain Claude on correctness, scope, tests (user's decision).

## How this run differs from the protocol (read before trusting any number)
- **Headless, Claude drove both sides, not the user.** Plain Claude: `claude -p` (default model sonnet, `--permission-mode auto`) in a separate worktree `~/Projects/dotb/busy-bees-baseline-plain`, branch `baseline/plain`. NGISA: Opus `claude --bg` session in the real busy-bees checkout with the kit (`real-init` re-run), a headless `agent-wall.sh` stand-in (no WezTerm panes), Sonnet implementer workers, merge into `baseline/ngisa-pair` in `.claude/worktrees/integration-baseline`. No PR (`agent-pr` not run, nothing pushed).
- **Not measured:** pane layout, real approval delays, how long a human takes to read a report. `report` and `merge` columns here are model speed, not human speed. Cost: not captured (no cost field in the NGISA/worker transcripts); plain Claude cost is in the table.
- **Questions could not be answered.** A message to a background session is held for approval (different permission class), so `AskUserQuestion` could not be answered. The pair run told the NGISA not to ask. The T1 NGISA run blocked on a real ask.
- **Plain Claude commits on its experiment branch** (task text authorizes it); the user's "never commit" rule applies to this repo, not these throwaway branches.
- **Stage mapping:** plain "plan" = start to first file-writing command; "work" = first write to end. NGISA stages come from `ngisa-report timing` stamps.
- A first NGISA T1 attempt in a linked worktree was discarded: the worker did not get its own worktree and committed on the NGISA checkout's branch. The T1 rerun used the real checkout.

## Results
| Task | Side | plan | worker/work | report | merge | total | Cost | Notes |
|---|---|---|---|---|---|---|---|---|
| T1 tiny | plain | 0m28s | 1m54s | - | - | 2m22s | $0.16 | fixed `FormDataEx.clone`, 1 test, committed; did not notice the extension is shadowed by dio's `clone()` |
| T1 tiny | NGISA | 0m05s | 3m01s | - | - | blocked | - | worker found the extension is dead code (dio's `FormData.clone()` shadows it; the only caller uses dio's); NGISA asked the user (delete / fix / leave). No merge, no result |
| T2 DateTimeEx tests | plain | 0m39s | 0m36s | - | - | 1m16s | $0.14 | 13 tests, pass |
| T3 ColorEx tests | plain | 0m22s | 1m05s | - | - | 1m27s | $0.19 | 10 tests, pass; same session as T2 |
| T2 | NGISA | 0m06s | 1m44s | 0m00s | 0m02s | 1m52s | - | 29 tests |
| T3 | NGISA | 0m08s | 2m38s | 0m00s | 0m00s | 2m46s | - | 14 tests |

Pair totals: plain Claude sequential 2m43s (T2 + T3); NGISA 2m46s by stamps (largest per-slug total), 3m02s wall from launch to final message.

## Verdict against the "equal" rule (provisional)
- **Pair:** NGISA is not strictly below plain Claude (2m46s to 3m02s against 2m43s). The rule asks for strictly below, so it is not met. The two NGISA workers ran in parallel but the slower worker (color, 2m38s) already took about as long as plain Claude did for both tasks.
- **Tiny (T1):** no valid comparison. The sides did different things (see Notes).
- **Quality:** pending the user's blind review. Test counts: NGISA 29 + 14, plain 13 + 10; NGISA wrote about twice the tests. More tests are not the same as better ones, hence the blind review.

## Findings
1. The NGISA's own overhead is small here: plan 5-8 s, merge 0-2 s. The time is in the worker (Sonnet with TDD and setup) and the thoroughness of what it writes, not in the handoffs. This contradicts the guess that handoff stages dominate; the human-wait part is not measured.
2. T1 was a poor baseline task: the premise ("confirm it is a real bug") hides dead code, and the two sides diverged. Replace it.
3. `real-init` leaves the real `CLAUDE.local.md` updated (backup `CLAUDE.local.md.bak-real-init`).

## Left behind (local, nothing pushed)
Branches `baseline/plain`, `baseline/ngisa-pair`; worktrees `~/Projects/dotb/busy-bees-baseline-plain` and `.claude/worktrees/integration-baseline` in busy-bees; stopped sessions; scratch data in the session scratchpad (`baseline/`, includes the sealed A/B key for the blind review).
