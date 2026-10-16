# Context: hand-off research and ngisa

Everything decided so far in the "hand-off" project, as of 2026-10-14. Read this before changing the kit or the docs.

## The research question

Can an agent system take a spec and ship production-quality software end to end? Where does it break, and where must a human stay in the loop?

Objectives:
1. Map the lifecycle (spec, design, code, test, review, deploy, maintain) and rate each stage: manual, assisted, supervised or autonomous.
2. Build reference workflows: single agent, planner/executor, parallel multi-agent, reviewer/verifier loops.
3. Find the human floor: intent, taste, risk, irreversible actions. Define the minimum viable oversight.
4. Measure: success rate, human interventions per task, cost, wall-clock time, defect rate, regression rate.
5. Make it reusable: playbooks, prompts, skills and harness configs other teams can copy.

Success criteria:
- At least 3 real projects built with 90% or more agent-authored code.
- Intervention points logged and categorized per run.
- A baseline comparison against human-only or assisted development on the same task.
- A written playbook: "when to trust agents, when to gate".

Non-goals: benchmarking models for leaderboards, building a general agent framework. Use existing tools (Claude Code, obra/superpowers) and test workflows on top.

Hypotheses to test:
- Verification (tests, review agents, CI gates) matters more than generation quality.
- Spec clarity predicts success better than model choice.
- Parallel agents with isolated worktrees beat one long-context agent on large tasks.

## Starting point

- Workflow: obra/superpowers in Claude Code, moving to the Claude Max plan.
- Main stack: Flutter. Flutter is managed with fvm, so `flutter` is not on PATH; scripts must call `fvm flutter` / `fvm dart`.
- Repos in play: `vn_citizen_id_scan` (Flutter, ID-card scanning, handles PII), `owen-host-app` (private), a work app on GitLab. Terminal: WezTerm on macOS.

## Decisions so far

### Verification (docs/verification/cut-verification-time.md, 2026-10-02)
- Enforce with hooks, not prompts: PostToolUse runs `dart format` on edited files; a Stop hook runs `tool/ci_local.sh` (a local copy of CI) so an agent cannot say "done" while red.
- Definition of done is written as commands.
- Opus for plans and reviews, Sonnet for implementation, Haiku only for grunt work.
- Gate the plan, not the diff: a fresh Opus subagent checks the plan against the real code before execution.
- Make "needs a device" work testable: fake remote config, JUnit/XCTest for native helpers, emulator integration tests fed recorded frames, golden tests for UI.
- CI plus a Claude review is the second reviewer.

### Orchestrator (docs/orchestration/one-terminal-orchestrator.md, 2026-10-14)
- No custom framework and no tmux manager. Use Claude Code itself: background sessions (`claude --bg --name X`), subagents, worktrees, `claude agents` to see every agent in one list.
- Skip agent teams for code: experimental, shared checkout with no worktrees, about 7x the tokens, and their split mode does not support WezTerm.
- Layout went through three versions: (1) one pane, (2) two windows (NGISA window plus agent wall), then the final one, (3) **one WezTerm window, one tab per repo**. Each repo tab has its NGISA on the left and up to 3 agent panes on the right. `repo-tab <path>` opens one.
- **One NGISA per repo, not one global NGISA.** A global NGISA plans without the repo's CLAUDE.md, mixes repos in one context, and one stuck prompt stalls everything. Never run two NGISA sessions on the same repo.
- Roles: NGISA = Opus, plans and dispatches, never writes code. Implementer = Sonnet, in its own worktree, TDD, reports to `@ngisa-<repo>`. No reviewer agent (removed 2026-10-15): the user reviews the final diff. `gate-check` (a script) runs on each worker report; the NGISA records each report with `ngisa-report set`.
- Approved branches merge into a local feature branch, `ci_local.sh` runs, and a draft PR opens. Only the human merges to main (a hook enforces it).
- Never run in bypass-permissions mode: agent reports to the NGISA then get held for approval. Use auto mode.
- More tasks than slots: the NGISA starts 3 and queues the rest. `agent-wall.sh` refuses a 4th with "tab full".
- The NGISA tends to code itself when a fix looks tiny. `ngisa-settings.json` (passed by `repo-tab` with `--settings`, NGISA only) denies Edit (covers Write) on `lib/`, `test/`, `android/` and `ios/`. Known gap: shell edits such as `sed -i`. Log any NGISA edit as an intervention.
- Setup is once per machine (agents, rules, hooks, `~/bin` scripts). Per repo it is only 3 files, created by `agent-init`: `tool/ci_local.sh`, `.worktreeinclude`, and a `.gitignore` line.

### NGISA (2026-10-14)
- The orchestrator is called **NGISA**, short for *NGƯỜI GIÁM SÁT* ("the supervisor" in Vietnamese). It was "gate", then briefly "Aegis". The repo is named `ngisa` too. "Gate" stays only for verification gates (human gates, the Stop gate, CI gates). Sessions are `ngisa-<repo>`, workers report to `@ngisa-<repo>`.
- Caveman ultra comes from a hook, not a prompt: `settings.local.json` runs `caveman-ultra-hook` on `SessionStart` and `UserPromptSubmit`, so the NGISA and implementers all get it, and worker final reports are terse. Code, commits and PR text stay normal. Checked: the hook fires and injects in a headless session; model compliance varies by model (Haiku ignored it on a plain question).
- The NGISA can relay extra requests to a worker (for example `/carve`) and has a quick-task path (one small edit in 1-2 named files, no plan, one implementer, gate-check still runs).
- PRs from a lab go through `agent-pr` only. `make-lab` adds the real remote as `upstream` (origin stays the local source with a `DISABLED` push URL). `git push` stays denied in `settings.local.json`; `agent-pr` is not in any allow list, so each call needs the user's approval. It refuses main, master, the base branch, `worktree-*` names and dirty trees, opens a DRAFT PR with `gh` for github.com and `tea` otherwise (busy-bees is on Gitea).

### Stack-agnostic workers (2026-10-15)
- The implementer prompt names no tool. It runs `tool/setup.sh` and gates on `tool/ci_local.sh`, both owned by the repo and written once by `agent-init` from the detected stack (Flutter via `pubspec.yaml`/`melos.yaml`, PHP via `composer.json`). A root manifest wins, else one level down, so a Flutter app plus a PHP backend get one gate. No manifest: nothing is written and `agent-init` says so.
- `agent-init` also writes `.worktreeinclude` (per stack secrets) and `.claude/ngisa-settings.json` (edit deny for the code dirs that exist). `repo-tab` prefers that file and falls back to the kit's Flutter `ngisa-settings.json`. `make-lab` copies the secrets listed in `.worktreeinclude`.
- Each task from the NGISA carries paths, stack and test command; the worker uses them first and the repo files as fallback. Non-command conventions go in the repo's `CLAUDE.md`.
- Gate integrity: `settings.local.json` denies Edit (covers Write) on `tool/setup.sh` and `tool/ci_local.sh`; `gate-check` fails a worktree whose copy of the gate files differs from the main checkout, or a branch that changed lint, analyzer, test or CI config. Known gap: it runs after the worker is done, so a shell edit is reported, not prevented. The implementer must report a failing or unrunnable gate, not fake green.
- Checked headless on 2026-10-15, see `docs/runs/2026-10-15-stack-agnostic-checks.md`. Pane layout, queueing and report delivery through `agent-wall.sh` were not exercised.
- The generated PHP gate is still a guess at pint, php-cs-fixer, phpstan and phpunit: review it against the repo's CI. `dotbedu_preschool_busybee` is a DotB monolith with no `composer.json`, so `agent-init` has a plain-PHP kind: a root `index.php` means no install step, `php -l` on changed `.php` files, and every `tests/*_test.php` must exit 0 (`./tool/ci_local.sh <paths>` runs chosen ones). Its code is vendored and PHP is 7.4. The generated gate passed on the lab, failed on a syntax error and on a failing test, and a worker finished a task through it and committed.
- Flutter gate on a repo that is not clean: busy-bees has 398 unformatted files, 158 analyzer warnings and 15 failing tests, so a repo-wide gate is red from the start. The generated gate therefore formats only changed files and fails warnings only in changed files. Failing tests: `./tool/ci_local.sh --record-baseline` (first argument only, run by a human once on a clean base) writes `tool/known_failures.txt`; the gate then fails only on failures not in it. busy-bees: 15 recorded, gate exits 0, a full run is about 11 minutes.
- `make-lab` copies a `CLAUDE.md` or `AGENTS.md` that git does not track (busy-bees gitignores it) and lists it in `.worktreeinclude`, so workers see it. Before this, labs of such repos had no `CLAUDE.md`.
- Worktree sessions do load the lab's `.claude/settings.local.json` (the deny on `tool/ci_local.sh` held inside a worktree), which closes that open item.

### Review stage removed (2026-10-15)
- Why: the user reviews every result anyway, so the Opus reviewer and its BLOCK loop (2 rounds) only added latency and quota use.
- What stays: `gate-check <branch> [base]` (a script in `~/bin`, no LLM) fails on a differing `tool/ci_local.sh`, `tool/setup.sh` or `tool/known_failures.txt`, or on changed lint, analyzer, test or CI config. The NGISA runs it on each report and stops on exit 1.
- What is lost: the reviewer's checks for secrets or PII in the diff, edits outside the task's paths, and tests that would pass without the change. The user covers them at the final diff.
- Old runs under `docs/runs/` still describe the reviewer; they are research data and were not rewritten.

### Report output (2026-10-16)
- Why: the NGISA's final report was free text, hard to scan and decide on, and its caveman style slipped on long text (findings, decisions) twice, see `docs/runs/2026-10-15-pane-view-and-caveman.md`. Prose rules did not hold, so structure replaces them.
- Final report is the glyph board (one line per task, findings `!` and asks `?` inline, unverified items, legend). It is produced by `ngisa-report set` and pasted unchanged, so chat and the coloured report pane (`ngisa-report view`, a strip under the NGISA pane opened by `agent-wall.sh`, outside the 3 worker slots) share one source: `~/.cache/ngisa/report/ngisa-<repo>.json`.
- Asks come as `ngisa-report ask <slug>`: finding, why, `y · n · d diff`, rec. One ask per message.
- Implementer final message is six fixed lines: `branch / files / gate / scope / unverified / asks`. The NGISA maps them to the `ngisa-report set` flags.
- Not chosen: a post-check hook that rewrites drifting NGISA text (latency, misfires on code and quoted errors); a pane that parses the NGISA transcript (internal format).

### Max plan limits
- Every agent draws on the same 5-hour and weekly quota. Keep it to 3 agents per tab and about 4 or 5 running across all repos.
- Implementers on Sonnet; Opus only for the NGISA.

### Lab (docs/orchestration/lab-setup.md, lab-quickstart.md)
- The orchestrator is still experimental, so the global `~/.claude/CLAUDE.md` stays untouched. Test it in throwaway clones under `~/lab/<repo>`.
- This kit lives at `/Users/khoamai/Projects/my_proj/ngisa` (override with `LAB_KIT=...`).
- `make-lab <repo>` clones to `~/lab/<repo>`, disables push, copies gitignored secrets, copies the kit in as project-level files (`.claude/agents/`, `.claude/settings.local.json`, `CLAUDE.local.md`), hides them from git status, and runs `agent-init`.
- Project-level files load on top of the global config; nothing global is replaced. The quota is the one thing a lab cannot isolate.
- Full isolation is possible with `CLAUDE_CONFIG_DIR=~/.claude-lab`, but it means reinstalling superpowers, so it was skipped.
- Cleanup: `rm -rf ~/lab/<repo>`.

## Kit map

| Kit file | Source in the docs |
|---|---|
| `agents/implementer.md` | one-terminal-orchestrator.md section 2a |
| `orchestrating.md` (becomes `CLAUDE.local.md` in a lab) | section 2c, plus the queue, quick-task, relay and PR rules from lab-quickstart.md |
| `settings.local.json` (permissions + caveman hook) | section 2d, plus lab-quickstart.md step 2 |
| `ngisa-settings.json` (NGISA-only edit deny, Flutter fallback; per-repo copy comes from `agent-init`) | lab-quickstart.md step 2 |
| `~/bin/agent-init`, `make-lab`, `repo-tab`, `agent-wall.sh`, `agent-pr`, `caveman-ultra-hook`, `gate-check`, `ngisa-report` | lab-quickstart.md step 3 |

If the kit and the docs disagree, the newest doc wins. lab-quickstart.md has the latest changes: fvm detection in `agent-init`, `ngisa-settings.json`, the queue rule, and the NGISA rules below. The kit files and `~/bin` scripts are regenerated from its heredocs.

## Runs so far

### Run 1: busy-bees (2026-10-14, in progress)
- Lab: `~/lab/busy-bees`. NGISA on Opus, two Sonnet workers (`busy-bees-datetime-ex`, `busy-bees-color-ex`) adding tests for the DateTimeEx and ColorEx extensions. A third task was dropped. Screenshot: `docs/assets/gate-run-busy-bees.png`.
- Seen so far: the layout works as designed. The worktree branch `worktree-test-datetime-ex` did not match the plan's `test/datetime-ex`, so check that the reviewer reads the branch actually used. `flutter` was not on PATH (fixed in `agent-init` via fvm). The weekly quota was at 72%.
- Still to log: wall-clock time, interventions and why, BLOCK count, and a comparison against one agent doing the same tasks.

## Open items
- Run the stack-aware `agent-init` and an implementer on a real Composer PHP repo; add Node or Go when a repo needs it.
- Full Flutter gate on busy-bees takes about 11 minutes. Workers can use `./tool/ci_local.sh test/<path>` while working; consider whether the full gate should run once per task or only at merge.
- Plain-PHP gate has no baseline file for failing tests (only Flutter does) and does not run `config.php`-dependent tests: the repo's one test is standalone. Add `config.php` to `.worktreeinclude` if a task needs it.
- Exercise the real flow in WezTerm once: `agent-wall.sh` panes, the queue, report delivery.
- Pick the 3 real projects and a human-only or assisted baseline task.
- Decide where run logs and metrics live (this repo is the natural place: add `runs/`).
- Close the NGISA's shell-edit gap. Same for workers: a shell edit of `tool/ci_local.sh` is only caught by `gate-check`, after the fact.
- Run `agent-pr` for real against a throwaway repo on GitHub and on Gitea. Only the dry run and the guards were tested.
- Check that Opus and Sonnet follow the caveman hook, and that worktree sessions load the hook (they use the project settings of the main clone).
- Fix the worktree branch naming mismatch.
- Exercise the report pane in a real WezTerm tab: placement under the NGISA pane, live refresh, reopening after all workers closed.
- Move the kit into `~/.claude` once lab runs are trusted.

## Working preferences
- Khoa wants short answers with diagrams over walls of text.
- Every doc has a Vietnamese copy (`.vi.md`). Code, commands and config stay in English in both.
