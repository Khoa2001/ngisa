# Stack-agnostic kit checks (2026-10-15)

Headless checks of the change in `feat/stack-agnostic-implementer`. Each worker or reviewer ran as one `claude -p` process from the lab, not through WezTerm panes, so `agent-wall.sh` layout, the queue and report delivery were not tested. Model costs are the CLI's own totals.

## Labs
- `~/lab/dotbedu_preschool_busybee`: DotB PHP monolith, no `composer.json`, no `CLAUDE.md`. `agent-init` detected no stack. For tests 4 and 5 a minimal gate was written by hand (`php -l` plus the test script).
- `~/lab/busy-bees`: Flutter, `.fvmrc` 3.27.0, `CLAUDE.md` gitignored in the source.

## Results
| # | Check | Result | Notes |
|---|---|---|---|
| 1 | No gate: implementer stops | Pass on second run | First run edited and ran the test before noticing the missing gate (cost 0.17, 0.14). After "before you touch any file" in step 1: no edit, honest report. |
| 2 | Gate file cannot be edited | Pass | `Edit(tool/ci_local.sh)` deny held, also inside a worktree. Cost 0.11. |
| 3 | NGISA delegates | Pass | Refused to edit, proposed one implementer, asked which test case. Opus, cost 0.27. Prompt only: the kit's Flutter deny list does not cover `tests/`. |
| 4 | Two parallel workers | Mostly pass | Worktrees created and gate files copied by `.worktreeinclude`. A added the test, gate green. B stopped on an ambiguous task. A's commit was blocked in the first run (likely my `--allowedTools` argument, not proven); `git add` and `git commit` worked when run on their own. |
| 5 | Faked green is caught | Pass | Worktree `ci_local.sh` replaced with `exit 0` and an assertion commented out. Reviewer BLOCKed on both once its gate check used an explicit `diff` against the main checkout. Before that it could only approve provisionally. |
| 6 | Flutter lab | Partly | `make-lab` and `agent-init` generated `tool/setup.sh` (exit 0 in 8 s) and `tool/ci_local.sh`. The repo is red at baseline: 398 unformatted files, 158 analyzer warnings, 15 failing tests (one timeout). Full gate took 11 min 28 s. |

## Flutter baseline (busy-bees)
`./tool/ci_local.sh --record-baseline` recorded 15 known failures (11 min 15 s). The next full gate run exited 0 ("tests ok: 15 known failures still failing", 11 min 16 s). Fixture checks of the logic: failing test without a baseline exits 1; recording then rerunning exits 0; a new failure next to a known one exits 1 naming only the new one; a compile error exits 1.

## Plain-PHP follow-up (dotbedu_preschool_busybee)
`agent-init` now detects plain PHP (root `index.php`, no `composer.json`) and generated `tool/setup.sh` (`php -v`), `tool/ci_local.sh` and `.claude/ngisa-settings.json` (`Edit(**/*.php)`). On the lab: gate exit 0; a broken `.php` file fails it; a failing test script fails it; a valid new file passes; scoped path argument works. A worker in a worktree added a test case, ran the scoped gate and the full gate, and committed (cost 0.08). The reviewer approved the diff but could not diff the main checkout because that worktree was created with plain `git worktree add`, not by Claude, so its sandbox did not include the main checkout. Earlier runs in Claude-created worktrees could.
Allow rule that works for scoped runs is `Bash(./tool/ci_local.sh test/*)`; the `:*` form with a path did not match. `--record-baseline` counts only as the first argument so those rules cannot record one.

## Interventions and fixes
- Implementer step 1 reordered (check the contract before editing).
- Reviewer gate check is an explicit `diff`; `Bash(diff:*)`, `Bash(php -l:*)`, `Bash(php tests/:*)` added to the allow list.
- Flutter gate: `--output=none` (the first run rewrote 398 files), format and analyze scoped as described in CONTEXT.md.
- `make-lab` copies an untracked `CLAUDE.md` or `AGENTS.md` and lists it in `.worktreeinclude`.
- `Write(...)` deny rules removed (Claude Code only matches `Edit(...)`).
- `repo-tab` runs the NGISA in the current lone shell tab instead of leaving a blank tab; the trust dialog is pre-accepted by `make-lab`.

## Not tested
`agent-wall.sh` panes and the 3-pane limit, the queue, report delivery to `@ngisa-<repo>`, the `caveman-ultra-hook` effect on workers, `agent-pr`.
