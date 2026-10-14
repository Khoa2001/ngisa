# Context: hand-off research and agent-orchestration-kit

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
- No custom framework and no tmux manager. Use Claude Code itself: background sessions (`claude --bg --name X`), subagents, worktrees, `claude agents` for the overview.
- Skip agent teams for code: experimental, shared checkout with no worktrees, about 7x the tokens, and their split mode does not support WezTerm.
- Layout went through three versions: (1) one pane, (2) two windows (gate window plus agent wall), then the final one, (3) **one WezTerm window, one tab per repo**. The first tab runs `claude agents` as the overview. Each repo tab has its gate on the left and up to 3 agent panes on the right. `repo-tab <path>` opens one.
- **One gate per repo, not one global gate.** A global gate plans without the repo's CLAUDE.md, mixes repos in one context, and one stuck prompt stalls everything. Never run two gates on the same repo.
- Roles: gate = Opus, plans and dispatches, never writes code. Implementer = Sonnet, in its own worktree, TDD, reports to `@gate-<repo>`. Reviewer = Opus, answers APPROVE or BLOCK. A BLOCK goes back to the same implementer, for 2 rounds at most, and after that the human decides.
- Approved branches merge into a local feature branch, `ci_local.sh` runs, and a draft PR opens. Only the human merges to main (a hook enforces it).
- Never run in bypass-permissions mode: agent reports to the gate then get held for approval. Use auto mode.
- More tasks than slots: the gate starts 3 and queues the rest. `agent-wall.sh` refuses a 4th with "tab full".
- The gate tends to code itself when a fix looks tiny. `gate-settings.json` (passed by `repo-tab` with `--settings`, gate only) denies Edit/Write on `lib/`, `test/`, `android/` and `ios/`. Known gap: shell edits such as `sed -i`. Log any gate edit as an intervention.
- Setup is once per machine (agents, rules, hooks, `~/bin` scripts). Per repo it is only 3 files, created by `agent-init`: `tool/ci_local.sh`, `.worktreeinclude`, and a `.gitignore` line.

### Max plan limits
- Every agent draws on the same 5-hour and weekly quota. Keep it to 3 agents per tab and about 4 or 5 running across all repos.
- Implementers on Sonnet; Opus only for the gate and the reviewer.

### Lab (docs/orchestration/lab-setup.md, lab-quickstart.md)
- The orchestrator is still experimental, so the global `~/.claude/CLAUDE.md` stays untouched. Test it in throwaway clones under `~/lab/<repo>`.
- This kit lives at `/Users/khoamai/Projects/my_proj/agent-orchestration-kit` (override with `LAB_KIT=...`).
- `make-lab <repo>` clones to `~/lab/<repo>`, disables push, copies gitignored secrets, copies the kit in as project-level files (`.claude/agents/`, `.claude/settings.local.json`, `CLAUDE.local.md`), hides them from git status, and runs `agent-init`.
- Project-level files load on top of the global config; nothing global is replaced. The quota is the one thing a lab cannot isolate.
- Full isolation is possible with `CLAUDE_CONFIG_DIR=~/.claude-lab`, but it means reinstalling superpowers, so it was skipped.
- Cleanup: `rm -rf ~/lab/<repo>`.

## Kit map

| Kit file | Source in the docs |
|---|---|
| `agents/implementer.md`, `agents/reviewer.md` | one-terminal-orchestrator.md section 2a |
| `orchestrating.md` (becomes `CLAUDE.local.md` in a lab) | section 2c, plus the queue rule |
| `settings.local.json` (block hook + permissions) | section 2d |
| `gate-settings.json` (gate-only edit deny) | lab-quickstart.md step 2 |
| `~/bin/agent-init`, `make-lab`, `repo-tab`, `agent-wall.sh` | lab-quickstart.md step 3 |

If the kit and the docs disagree, the newest doc wins. lab-quickstart.md had the latest changes: fvm detection in `agent-init`, `gate-settings.json`, and the queue rule.

## Runs so far

### Run 1: busy-bees (2026-10-14, in progress)
- Lab: `~/lab/busy-bees`. Gate on Opus, two Sonnet workers (`busy-bees-datetime-ex`, `busy-bees-color-ex`) adding tests for the DateTimeEx and ColorEx extensions. A third task was dropped. Screenshot: `docs/assets/gate-run-busy-bees.png`.
- Seen so far: the layout works as designed. The worktree branch `worktree-test-datetime-ex` did not match the plan's `test/datetime-ex`, so check that the reviewer reads the branch actually used. `flutter` was not on PATH (fixed in `agent-init` via fvm). The weekly quota was at 72%.
- Still to log: wall-clock time, interventions and why, BLOCK count, and a comparison against one agent doing the same tasks.

## Open items
- Pick the 3 real projects and a human-only or assisted baseline task.
- Decide where run logs and metrics live (this repo is the natural place: add `runs/`).
- Close the gate's shell-edit gap.
- Fix the worktree branch naming mismatch.
- Move the kit into `~/.claude` once lab runs are trusted.

## Working preferences
- Khoa wants short answers with diagrams over walls of text.
- Every doc has a Vietnamese copy (`.vi.md`). Code, commands and config stay in English in both.
