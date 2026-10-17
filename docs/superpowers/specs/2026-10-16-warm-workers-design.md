# Warm workers, no report loop, Sonnet NGISA

## Context
The speed parity baseline (`docs/runs/2026-10-16-baseline-run1.md`) showed NGISA's own steps are small (plan 5-8s, merge 0-2s) but every worker pays 30-60s plain Claude never pays: worktree create, `worktree-include`, `tool/setup.sh`, looking up `SendMessage`, writing a 7-line report. The warm worker spike (`docs/runs/2026-10-16-warm-worker-spike.md`) confirmed the mechanism: an NGISA session can `SendMessage` a finished `--bg --agent implementer` session, which keeps its worktree, takes the task, and wakes the NGISA with `notify_when_idle`. Branch: `feat/speed-parity`, never main.

## Agreed (user)
1. Warm workers: idle implementer sessions with worktree and setup done; the NGISA hands them the task.
2. Drop the report loop: no worker `SendMessage`, no 7-line report.
3. The NGISA always runs Sonnet (`repo-tab` pins it), including for big plans.
- Not chosen: an inline lane for tiny tasks, a reused lane worktree, a 4-minute parallel threshold.

## Goals and non-goals
- Goal: bring NGISA's parallel pair strictly below plain Claude's sequential total, and tiny/small close to plain Claude, at the same quality.
- Non-goals: an inline lane (NGISA still never edits code), changing the gate rules, new frameworks, touching `~/.claude`.
- Anti-goal: a faked green, or a worker that skips the repo's checks to save time.

## Design (my calls where marked)
- `agent-warm [n]` (new, my call: default 2, max 3): starts `n` warm workers named `<repo>-warm-N` with `claude --bg --agent implementer --model sonnet "<warm-up prompt>"`. The prompt makes the worker create `.claude/worktrees/warm-N` (branch `warm/N`) from HEAD, run `worktree-include` and `./tool/setup.sh`, and end its turn with `warm ready`. A running or already warm-ready worker with that name is skipped. `repo-tab` starts it in the background at tab open; the NGISA refills with `agent-warm 1` after it uses one.
- Assign: the NGISA sends one `SendMessage {to: <repo>-warm-N, message: <task text starting "Branch: <name>.">, notify_when_idle: true}`, stamps `spawn`, then runs `agent-wall.sh <slug> --attach <repo>-warm-N` to open the pane only. No free warm worker: the existing cold `agent-wall.sh <slug> implementer sonnet "<task>"` start, now without the report suffix.
- Worker on a message task: in its warm worktree `git checkout -B <branch> <base>` (base from the message, default `origin/HEAD`), skip setup unless the dependency manifest changed since warm-up, then the usual TDD and checks.
- Result without a report: the worker ends with a commit whose body has the lines `checks:`, `unverified:`, `asks:` (the spike showed the worker will not write them unless `implementer.md` says so), and one short final line. On the idle notice the NGISA reads `git log -1 --format=%B` and `git diff --stat`, then `ngisa-report set`.
- Cold workers drop the "send your final report to @ngisa-<repo>" suffix too; the NGISA subscribes with a pure `SendMessage {notify_when_idle: true}` after the spawn.
- `repo-tab` pins `--model sonnet` for the NGISA. Docs that say "NGISA = Opus" change.
- Kept: guards, per-worker worktrees, the minimal board, Stamps, no push/merge rules.

## Constraints
- Kit and docs change in the same commit; `.vi` copies where a doc has one; quickstart heredocs equal `~/bin`.
- Scripts call `fvm` only through the repo's `tool/setup.sh`; no stack rules in `implementer.md`.
- No em dash. Nothing committed until the user says so.

## Left to the builder
Exact wording of the warm-up prompt (start from the spike's), test fakes for `claude`/`wezterm`, how `agent-warm` detects a live warm worker (`claude agents --json --cwd`).
