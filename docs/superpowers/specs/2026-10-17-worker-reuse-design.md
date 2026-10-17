# Worker reuse and cleanup: design

Date: 2026-10-17. Branch: `feat/worker-reuse`. Builds on PR #34 (warm workers, single-use).

## Intent
A finished worker leaves its pane on screen and, being single-use, its context is thrown away. The user wants the pane gone when a new task comes in, the NGISA and workers to stay light, and an existing worker's context (repo knowledge, prior result, warm prompt cache) reused when that saves time and money.

## What research found (decides the design)
1. The NGISA cannot send `/compact` or `/clear` to a worker. A slash command in a cross-session message arrives as plain text and is never run (Claude Code cross-session messaging docs). Only `claude attach <name>` and typing it works, which is the user.
2. A background (`--bg`) worker does not compact itself at a lower window. Spike 3 (2026-10-17, Haiku, one `Read` per request): with `autoCompactWindow: 100000` in `--settings`, and separately with `--autocompact 100000`, context grew 49k, 73k, 96k, 118k, 140k, 162k, 184k over several requests past 100k and no compaction happened. Neither lever works for `--bg` sessions. Spikes 1 and 2 were inconclusive for lack of requests after the threshold; spike 3 settled it.
3. A worker's real context size can be read from its transcript: for the last assistant message, `input_tokens + cache_read_input_tokens + cache_creation_input_tokens` in `~/.claude/projects/*/<sessionId>.jsonl`.
4. The main-conversation prompt cache lives 1 hour on a subscription. A background session unattached for about an hour has its process stopped by Claude Code; a message wakes it from the saved conversation.
5. Closing a pane (detach or `wezterm cli kill-pane`) never stops the session. `claude stop`, `claude rm` end and remove it; the transcript stays.
6. No public third-party package fits: orchestrators (Composio agent-orchestrator, ccmanager, dmux, Claude Squad) only manage worktrees and panes; prompt compressors (LLMLingua, mem0, Intel Adaptive Token Compressor) work at the API-client level and Claude Code has no hook to rewrite history. Add none.

## Goals
- When a worker reports, its pane closes; the session stays alive in the background.
- The next task goes to a finished worker when that is cheaper (reuse), otherwise to a fresh warm worker; heavy or old workers are retired.
- No user action needed in the normal path.
- Measured: reuse is not slower than a fresh warm worker and costs fewer tokens after the first task.

## Non-goals and anti-goals
- No NGISA-driven `/compact`; no third-party package; no change to `quick`/`direct`/`plan` modes or the result format.
- Must not delete a worker's work: retire only a finished worker whose result was read and whose worktree is clean; branches are never deleted unless merged (`git branch -d`).
- Must not weaken permissions: no blanket `claude stop` / `claude rm` / `git worktree remove` in the allow list.

## Decisions (user's)
Pane closes, session stays. NGISA chooses reuse or retire per worker. Criteria: same code area, dependent task, worker context size, session age (cache). The NGISA shrinks its own context automatically at each new batch. A user manual compact is allowed as an option, not required.

## Design (my calls where marked)
### New scripts (source = heredocs in `docs/orchestration/lab-quickstart.md`, copies in `~/bin`)
- `worker-ctx <session-name>`: prints `ctx: <n>k`, `idle: <n>m` and `tasks: <n>` (see the settled calls below). Finds the sessionId through `claude agents --json --all --cwd .`, the transcript through `~/.claude/projects/*/<sessionId>.jsonl`, `ctx` from the last assistant `usage` as above, `idle` from the last line's timestamp. Exit 1 with a message if the session or transcript is not found.
- `worker-retire <session-name>`: refuses unless the name is `<repo>-warm-N`, its state is `done`/`idle`, and `git status --porcelain` is empty in `.claude/worktrees/warm-N`. Then `claude stop`, `claude rm`, `git worktree remove` of that worktree, `git branch -d warm/N` (fails harmlessly if the branch has commits not merged) and closes its pane. Prints one line. The NGISA never runs raw `claude stop`/`claude rm`/`git worktree remove`; only `worker-retire` is allowed in settings.
- `agent-wall.sh <slug> --close`: reads `~/.cache/ngisa/panes/<repo>-<slug or warm name>`, runs `wezterm cli kill-pane --pane-id <id>`, removes the file. Missing file or dead pane: exit 0 silently. The pane file is keyed by session name today (`$state/$name`); for a warm worker the name is the warm name, so `--close` takes the session name (`--close <session-name>` after the slug-less form `agent-wall.sh --close <session-name>`; exact CLI is the builder's call, tests fix it).

### Orchestrating rules (`orchestrating.md`)
- At a worker's idle notice, after `worker-result`: `agent-wall.sh --close <session-name>`.
- On a new task, for each warm worker whose state is `done`/`idle`, whose result was already read and not in use this run, and whose `worker-result <wt> HEAD` shows a clean worktree: run `worker-ctx`. Reuse it when ALL hold: new task's paths overlap the last task's paths or its directory, or the task depends on it (dependent tasks already go to one worker, so the dependent case is the same worker); `ctx` under 100k tokens [my call]; `idle` under 55 min [my call, cache]; the worker has done fewer than 3 tasks this run [my call]. Otherwise `worker-retire` it and use a fresh warm worker (refill with `agent-warm 1`).
- Reuse uses the unchanged SendMessage and `agent-wall.sh <slug> --attach` (a new pane). The "free" test for fresh workers stays "on `warm/N`"; reused workers are tracked by the NGISA's `slug -> warm-N (tasks)` list.
- Optional (user's choice): if a worker holds more than 100k tokens of clearly useful context, the NGISA may ask once with `AskUserQuestion` whether to `claude attach` and `/compact` it or retire it. Default is retire, no question.
- The `Never` line is amended: no raw `claude rm` / `worktree remove`; `worker-retire` only on a finished worker.
- Add a `# Compact instructions` block at the end of the NGISA rules: keep the slug -> worker map with task counts, base refs, the board, decisions made, open asks. Best-effort: `--autocompact`/window is unverified for the interactive NGISA (spike 3 covered `--bg` only).

### `implementer.md`
Warm start already runs `git checkout -B <name> <ref>` in a `warm-*` worktree; it works on a worktree left on an old task branch. Add one sentence: a reused worker may remember earlier tasks; it still starts from the Base ref, ignores earlier tasks' scope, and applies this task's path list only.

### `settings.local.json`
Add `Bash(worker-ctx:*)`, `Bash(worker-retire:*)`. `agent-wall.sh:*` already covers `--close`.

### Tests (stdlib unittest, fake `claude`/`wezterm`/`git` as in `tests/test_agent_warm.py`)
`test_worker_ctx.py` (token sum, idle minutes, missing transcript), `test_worker_retire.py` (refuses wrong name / busy / dirty; happy path calls stop, rm, worktree remove in order; unmerged branch kept), `test_agent_wall_close.py` (kills the recorded pane, removes the file, tolerates missing), `test_kit_text.py` additions (new rules present in kit and in the docs copies, allow-list entries, no raw `claude rm` in allow list).

### Docs
`CONTEXT.md` (decisions, open items), `docs/orchestration/one-terminal-orchestrator.md` and `.vi.md` (kit blocks verbatim, new section), quickstart heredocs, `docs/README.md` runs index. Specs in this repo have no Vietnamese copy; follow that.

## Constraints
Kit and docs change in the same commit. `~/bin` equals the heredocs. Scripts call `fvm` where Flutter is involved (none here). Never commit or push unless the user says so. Feature branch only.

## Measure (after build)
Four medium tasks in two batches, three ways: reuse, fresh warm each time, plain Claude. Record wall time and cost (capture cost this time) in `docs/runs/`. Pass: reuse not slower than fresh warm; context of a reused worker at its second task visible via `worker-ctx` and its prompt cache hit visible. Also check whether the interactive NGISA compacts at a low window (`/usage` Prompt cache line, expected rebuilds).

## Calls settled after the builder check (all mine, flagged)
1. **Retire never deletes work.** A finished worker sits on its task branch, not `warm/N`. `worker-retire` removes the worktree only; the task branch and its commits stay for merge. `git branch -d warm/N` removes the leftover warm branch (it only holds the base commit, so `-d` succeeds). No "unmerged" refusal needed; the refusals are: wrong name, state not `done`/`idle`, dirty worktree.
2. **Dependency does not override the thresholds.** A dependent task goes to the same worker when it is under the thresholds. Over a threshold, the worker is retired and the dependent task runs on a fresh warm worker with `Base:` = the earlier task branch's name (a valid ref, so it sees that work; ruling during the build: the NGISA has no allowed command that prints a branch's sha). Merge order is unchanged.
3. **NGISA shrink needs no state file.** The NGISA's worker list is rebuildable from git and the agent list: warm names from `claude agents --json`, each worktree's branch from `git worktree list --porcelain`, `tasks:` from `worker-ctx`. The `# Compact instructions` block is therefore enough for the "shrink automatically" goal; it is best-effort until the measure run checks it.
4. **"Last task's paths"** come from the NGISA's own list in its reply. If the list is lost (compaction, restart), paths are unknown and the safe default applies: retire and use a fresh warm worker.
5. **"Result already read" and "not in use this run"** are procedural, from the NGISA's own list. They are not safety conditions: a result lives in git (the branch is kept), so retiring an unread worker loses nothing.
6. **`worker-ctx` fields:** `ctx: <n>k`, `idle: <n>m`, `tasks: <n>`. `idle` is minutes since the last assistant message (that is what refreshes the cache). `tasks` is the count of user messages in the transcript that start with `Branch:`.

## Left to the builder
Exact CLI of `agent-wall.sh --close`; `worker-ctx` output format beyond the two fields; whether `worker-retire` closes the pane itself or the NGISA does both; test fixtures.

## Open
- Whether `--autocompact` works for the interactive NGISA (unverified).
- 100k / 55 min / 3-task thresholds are my calls; tune from the measure run.

## Fixes from the final review (2026-10-17)
- `worker-ctx`: `tasks` also counts a task wrapped in `Another Claude session sent a message: <cross-session-message ...>` (the real SendMessage format); synthetic and sidechain assistant entries are ignored for `ctx` and `idle`.
- `agent-wall.sh --close` rejects session names outside `[A-Za-z0-9._-]` or containing `..` (exit 2).
- `worker-retire` refuses a detached HEAD (commits could be lost).
- `worker-result` prints `dirty: yes|no` after `branch:`; the reuse rule uses `dirty: no`.
- `agent-warm` keeps the highest index ever used in `<git common dir>/agent-warm.last`, so a retired worker's index is never reused.
- `orchestrating.md`: no new assignment gets a name already on the list (a finished worker only gets a task through the reuse rule); a task that depends on a worker's earlier task gets `Base:` = that branch name, reused or fresh; `implementer.md` widens `<ref>` to a branch name.
- Deferred minors: pane closes also for `blocked` workers (their question is in the pane); `--close` does not check the pane id still belongs to this tab after a WezTerm restart; `worker-retire` stops the session before `git worktree remove` can fail; non-worktree `warm-N` directory and leading-zero names; duplicate session names; paths with spaces in `worker-retire`; cold sessions and `failed` sessions are never retired; naive timestamps crash `worker-ctx`.
