# Worker reuse and cleanup Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Close a worker's pane when it reports, let the NGISA reuse a finished warm worker when that is cheaper or retire it, with no user step in the normal path.

**Architecture:** Two new scripts (`worker-ctx` reads a worker's context size, idle time and task count from its transcript; `worker-retire` safely ends a finished worker), `agent-wall.sh --close` (kills the recorded pane only), and new NGISA rules in `orchestrating.md`. Scripts live as heredocs in `docs/orchestration/lab-quickstart.md` and are installed to `~/bin`.

**Tech Stack:** bash, jq, Python 3 `unittest` (stdlib), markdown.

**Spec:** `docs/superpowers/specs/2026-10-17-worker-reuse-design.md` (read it; the "Calls settled" section binds).

## Global Constraints
- Branch `feat/worker-reuse`; never main; do not commit, add or push (the user commits).
- Kit and docs change together; `~/bin/<script>` equals its quickstart heredoc byte for byte; `orchestrating.md` and `agents/implementer.md` equal their quickstart copies (`tests/test_kit_text.py` checks the copies).
- Vietnamese copy: `docs/orchestration/one-terminal-orchestrator.vi.md` mirrors the English doc; code and commands stay English. Specs and plans have no Vietnamese copy.
- No em dash. Do not touch `~/.claude`. No bare `flutter`/`dart` in scripts.
- Tests: `python3 -m unittest discover -s tests -p '<file>' -v`; fakes for `claude` and `wezterm` on PATH as in `tests/test_agent_wall_attach.py` and `tests/test_agent_warm.py`; script path via env var with `~/bin/<name>` default.
- No raw `claude stop`, `claude rm` or `git worktree remove` in `settings.local.json`; only `worker-ctx` and `worker-retire`.
- Existing `agent-wall.sh` behavior (cold start, `--attach`, layout, tab-full check) stays identical.

## Review Focus
- `worker-retire` on a busy, wrongly named or dirty worker changes nothing and exits non-zero; on a clean `done` worker the task branch and its commits survive.
- `agent-wall.sh --close` for a missing pane file or an already dead pane exits 0 and leaves other panes alone.
- `worker-ctx` on a transcript with no assistant message, or with a compaction (context drops), reports the latest value without crashing.
- The orchestrating text never tells the NGISA to run raw `claude stop`/`claude rm`/`git worktree remove`.
- A reused worker starts the new task from the Base ref, not from its old task branch.

---

### Task 1: `worker-ctx`

**Files:**
- Create: `~/bin/worker-ctx`, heredoc in `docs/orchestration/lab-quickstart.md` after `worker-result`
- Test: `tests/test_worker_ctx.py`

**Interfaces:**
- Produces: `worker-ctx <session-name>` prints exactly three lines `ctx: <n>k`, `idle: <n>m`, `tasks: <n>`; exit 0. Exit 1 with `worker-ctx: <reason>` on stderr when the session (from `claude agents --json --all --cwd .`, matched on `.name`) or its transcript (`~/.claude/projects/*/<sessionId>.jsonl`, projects root overridable by env `CLAUDE_PROJECTS_DIR`) is missing.
- Consumes: agent JSON rows have `name`, `sessionId`.

- [ ] **Step 1: Write failing tests** in `tests/test_worker_ctx.py` (class `WorkerCtxTest`, fake `claude` printing `$FAKE_AGENTS`, temp projects dir). Test names and assertions:
  - `test_sums_last_assistant_usage`: two assistant lines with usage `{input_tokens:10, cache_read_input_tokens:20000, cache_creation_input_tokens:5000}` then `{2, 49000, 1000}`; stdout has `ctx: 50k` (integer division of 50002 by 1000).
  - `test_context_drop_after_compaction`: usages 184000 then 12000 total; stdout `ctx: 12k`.
  - `test_idle_minutes_from_last_assistant`: last assistant `timestamp` 12 min before a fixed `now` (env `WORKER_CTX_NOW` ISO8601 override for tests); a later user line must not change it; stdout `idle: 12m`.
  - `test_tasks_counts_branch_messages`: three user messages whose text starts `Branch:` plus one that does not; stdout `tasks: 3`. User message text may be a string or a list of `{type:"text", text}` parts.
  - `test_no_assistant_message`: only a user line; `ctx: 0k`, `idle: 0m`... if no assistant timestamp use the file mtime for idle; exit 0.
  - `test_unknown_session`: exit 1, stderr contains `worker-ctx: no session`.
  - `test_missing_transcript`: exit 1, stderr contains `worker-ctx: no transcript`.
- [ ] **Step 2: Run** `python3 -m unittest discover -s tests -p 'test_worker_ctx.py' -v`; expect FAIL (script missing).
- [ ] **Step 3: Implement** `~/bin/worker-ctx` (bash + inline `python3 -I -c` or `jq`; the builder chooses, keep one file, `set -euo pipefail`). Sum is `input_tokens + cache_read_input_tokens + cache_creation_input_tokens` of the LAST `type=="assistant"` line with `message.usage`.
- [ ] **Step 4: Run tests;** expect PASS.
- [ ] **Step 5:** copy the script into the quickstart heredoc (`cat > ~/bin/worker-ctx <<'EOF' ... EOF` plus a `chmod +x` line like its neighbours) and confirm `diff` against `~/bin/worker-ctx` is empty.

### Task 2: `agent-wall.sh --close`

**Files:**
- Modify: `~/bin/agent-wall.sh` and its quickstart heredoc
- Test: `tests/test_agent_wall_close.py`

**Interfaces:**
- Produces: `agent-wall.sh --close <session-name>` (first argument `--close`): reads `${XDG_CACHE_HOME:-$HOME/.cache}/ngisa/panes/<session-name>`, runs `wezterm cli kill-pane --pane-id <id>`, removes the file; prints nothing; always exit 0 (missing file, dead pane, wezterm error). It must run before the `me=${WEZTERM_PANE:?...}` check so it also works outside WezTerm.

- [ ] **Step 1: Write failing tests** (reuse the fake `wezterm` pattern; the fake logs `kill-pane` lines): `test_close_kills_recorded_pane_and_removes_file` (file with `99` -> log has `kill-pane --pane-id 99`, file gone), `test_close_missing_file_is_silent_ok` (exit 0, no kill-pane logged), `test_close_survives_wezterm_failure` (fake exits 1 for kill-pane; exit 0, file removed), `test_close_leaves_other_pane_files` (second file untouched), `test_attach_and_cold_start_unchanged` (run the three existing attach/cold assertions' essence: `--attach` still logs one split-pane).
- [ ] **Step 2: Run;** expect FAIL.
- [ ] **Step 3: Implement** the early `--close` branch in `agent-wall.sh`.
- [ ] **Step 4: Run** the new test and `tests/test_agent_wall_attach.py`; expect PASS.
- [ ] **Step 5:** update the quickstart heredoc; diff against `~/bin/agent-wall.sh` empty.

### Task 3: `worker-retire`

**Files:**
- Create: `~/bin/worker-retire`, quickstart heredoc after `worker-ctx`
- Test: `tests/test_worker_retire.py`

**Interfaces:**
- Produces: `worker-retire <session-name>`, run from the repo root (or any subdirectory). Steps in order: (1) name must match `<repo>-warm-<N>` with `<repo>` = basename of `git rev-parse --show-toplevel`, else exit 2 `worker-retire: not a warm worker: <name>`; (2) agent row for that name must exist and have `state` `done` or `idle`, else exit 1 `worker-retire: <name> is <state>`; (3) `git status --porcelain` in `.claude/worktrees/warm-N` must be empty, else exit 1 `worker-retire: dirty worktree`; (4) `claude stop <id>`; (5) `claude rm <id>`; (6) `git worktree remove .claude/worktrees/warm-N` (no `--force`); (7) `git branch -d warm/N` (failure ignored); (8) `agent-wall.sh --close <name>` (failure ignored). Prints one line `retired <name>`. Never touches the worktree's current (task) branch.
- Consumes: agent JSON rows `name`, `state`, `id`; `agent-wall.sh --close` from Task 2 (found on PATH; tests put a fake on PATH).

- [ ] **Step 1: Write failing tests** with a real temp git repo (as `test_agent_warm.py`), a real linked worktree `.claude/worktrees/warm-1` on branch `warm/1`, and fake `claude`/`agent-wall.sh` logging calls: `test_refuses_non_warm_name` (exit 2, nothing logged), `test_refuses_busy_worker` (state `working` -> exit 1, no stop/rm, worktree still exists), `test_refuses_dirty_worktree` (untracked file in worktree -> exit 1, no stop), `test_happy_path_order` (log order: stop, rm, close; worktree dir gone; `warm/1` branch gone; stdout `retired demo-warm-1`), `test_task_branch_and_commits_survive` (worktree is on `feat/x` with one commit made before retire; after retire `git branch --list feat/x` still lists it and `git log feat/x` has the commit), `test_unknown_session` (no row -> exit 1).
- [ ] **Step 2: Run;** expect FAIL.
- [ ] **Step 3: Implement** `~/bin/worker-retire` exactly in the step order above.
- [ ] **Step 4: Run tests;** expect PASS.
- [ ] **Step 5:** quickstart heredoc; diff empty.

### Task 4: Kit rules, settings, docs

**Files:**
- Modify: `orchestrating.md`, `agents/implementer.md`, `settings.local.json`, the matching copies in `docs/orchestration/lab-quickstart.md`, `docs/orchestration/one-terminal-orchestrator.md` and `.vi.md`, `CONTEXT.md`, `docs/README.md`
- Test: `tests/test_kit_text.py` (extend)

**Interfaces:**
- Consumes: scripts from Tasks 1-3 and the "Calls settled" section of the spec.

- [ ] **Step 1: Extend `tests/test_kit_text.py` with failing assertions:** `orchestrating.md` contains `worker-ctx`, `worker-retire`, `agent-wall.sh --close`, `# Compact instructions`, the thresholds `100k`, `55 min`, `3 tasks`, and the sentence that a dependent task on a retired worker uses `Base:` = the earlier task branch tip; it does NOT contain `claude stop` or `claude rm` outside the `Never` line; the `Never` line says `worker-retire` only on a finished worker. `implementer.md` contains a sentence that a reused worker starts from the Base ref and applies only this task's paths. `settings.local.json` allow list contains `Bash(worker-ctx:*)` and `Bash(worker-retire:*)` and no entry starting `Bash(claude stop`, `Bash(claude rm`, or `Bash(git worktree remove`. The quickstart copies of `orchestrating.md`/`implementer.md`/`settings.local.json` equal the kit files (extend the existing copy tests), and both `one-terminal-orchestrator` docs contain the new kit lines verbatim.
- [ ] **Step 2: Run;** expect FAIL.
- [ ] **Step 3: Edit the kit.** In `orchestrating.md` add, near step 3 and step 4, the rules from the spec "Orchestrating rules" section and "Calls settled" items 2, 4, 5 (close the pane after `worker-result`; reuse test with all four conditions; retire otherwise; unknown paths means retire; reuse via the unchanged SendMessage and `agent-wall.sh <slug> --attach`; optional one-time `AskUserQuestion` to `/compact` only when the worker holds over 100k of clearly useful context, default retire without asking), amend the `Never` line, and append a `# Compact instructions` block (keep slug -> worker map with task counts, base refs, the board, decisions made, open asks; rebuild the list from `claude agents --json`, `git worktree list --porcelain` and `worker-ctx` if context was lost). Keep the file in caveman-ultra style and under the length of neighbouring rules. Add the `implementer.md` sentence. Add the two allow entries.
- [ ] **Step 4: Sync docs:** update the quickstart copies and the verbatim kit blocks in both one-terminal docs (EN, VI text around them), add a short "Worker reuse" section to both, update `CONTEXT.md` (decision: reuse/retire, NGISA cannot compact workers, spike 3 result, open: measure run, interactive NGISA compaction unverified) and the `docs/README.md` index.
- [ ] **Step 5: Run** `python3 -m unittest discover -s tests -v`; expect all PASS (67 old + new).

### Task 5: Install and verify

**Files:** `~/bin/worker-ctx`, `~/bin/worker-retire`, `~/bin/agent-wall.sh` (already written in Tasks 1-3).

- [ ] **Step 1:** for each of the three scripts, extract the quickstart heredoc and `diff` it against `~/bin/<name>`; empty diffs.
- [ ] **Step 2:** `chmod +x`, then a dry smoke test with real `claude`: `worker-ctx <an existing session name>` prints three lines; `worker-retire` on a non-warm name exits 2.
- [ ] **Step 3:** `real-init` is NOT run here; tell the user it must be re-run per repo (busy-bees) after merge.
- [ ] **Step 4:** report to the user: files changed, test counts, what is unverified (interactive NGISA compaction, thresholds).

### Task 6: Measure run (needs the user's go; it uses quota)

**Files:** Create `docs/runs/2026-10-17-worker-reuse-measure.md`.

- [ ] **Step 1:** ask the user before running. Setup: busy-bees base `a18a9f3`, four medium tasks in two batches (two tasks each), three ways: reuse, fresh warm each time, plain Claude; one run per side; capture wall time and cost this time (`/usage` or transcript usage sums).
- [ ] **Step 2:** log results, `worker-ctx` at the second batch, any compaction seen on the NGISA, and interventions in the run log; update `docs/README.md`.
- [ ] **Step 3:** pass if reuse is not slower than fresh warm and cheaper from the second batch; otherwise record the finding and tune thresholds in the spec.
