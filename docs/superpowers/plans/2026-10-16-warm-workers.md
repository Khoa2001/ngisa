# Warm workers, no report loop, Sonnet NGISA Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Cut the per-worker overhead the baseline found: warm workers, no report loop, a Sonnet NGISA.

**Architecture:** A new `agent-warm` script pre-starts idle implementer sessions with worktree and setup done. `agent-wall.sh` gains `--attach` (pane only) and loses the report suffix. The NGISA assigns tasks to warm workers by `SendMessage` with `notify_when_idle`, reads the result from the worker's commit body, and refills the pool. Scripts live as heredocs in `docs/orchestration/lab-quickstart.md` and are installed to `~/bin`.

**Tech Stack:** bash, Python 3 `unittest` (stdlib), markdown.

**Spec:** `docs/superpowers/specs/2026-10-16-warm-workers-design.md`

## Global Constraints
- Branch `feat/speed-parity`; never main; do not commit, add or push (the user commits).
- Kit and docs change together; `~/bin/<script>` equals its quickstart heredoc byte for byte; `orchestrating.md` equals its quickstart copy.
- Vietnamese copies: `docs/orchestration/one-terminal-orchestrator.vi.md` mirrors the English doc; code and commands stay English.
- No em dash. Do not touch `~/.claude`. Scripts use no bare `flutter`/`dart` (the repo's `tool/setup.sh` owns that).
- Existing `agent-wall.sh <slug> <agent> <model> "<prompt>"` behavior (cold start, pane layout, tab-full check) stays identical except for the removed report suffix.
- Tests run with `python3 -m unittest discover -s tests -p '<file>' -v` (no `-I`).

## Review Focus
- `agent-warm` twice in a row starts no duplicate; `n` above 3 is capped; `n` 0 or non-numeric exits 2.
- `agent-wall.sh --attach` with a name that has no session still exits 1 with a clear message, never opens an empty pane.
- A cold start still works when no warm worker is free (fallback), and no longer tells the worker to message the NGISA.
- A worker message that omits `Branch:` must not make the worker guess a branch name (it asks via `asks:`/stops).
- Idle notice for a blocked worker: the rule says read the pane/commit and treat "no new commit" as blocked, not as done.

---

### Task 1: `agent-warm`

**Files:**
- Create: `tests/test_agent_warm.py`
- Create: `~/bin/agent-warm`
- Modify: `docs/orchestration/lab-quickstart.md` (new heredoc `cat > ~/bin/agent-warm <<'EOF'` placed after the `agent-wall.sh` block; add `agent-warm` to the install list and the "all must print a path" check line)

**Interfaces:**
- Produces CLI `agent-warm [n]`, run from inside the repo. `n` defaults to 2, integer 1..3 (above 3 is capped to 3; 0, negative or non-integer: stderr `agent-warm: n must be 1..3`, exit 2). Repo name = basename of `git rev-parse --show-toplevel`. Worker names `<repo>-warm-1`..`<repo>-warm-n`. For each N whose name is not already a live or done warm session (`claude agents --json --all --cwd "$PWD"` filtered by `.name`): run `claude --bg --name <name> --agent implementer --model sonnet "<WARM_PROMPT>"` with N substituted; print `warm <name> started` per start and `warm <name> exists` per skip. Exit 0.
- `WARM_PROMPT` (constant in the script): the spike's warm-up text with `warm-N`/`warm/N` filled in: create `.claude/worktrees/warm-N` on branch `warm/N` from HEAD, run `worktree-include` then `./tool/setup.sh`, end the turn with the single line `warm ready`; later a task arrives as a message that begins `Branch: <name>.`; on it run `git checkout -B <name> <base>` in that worktree, skip setup, follow the usual rules, end with a commit whose body has `checks:`, `unverified:`, `asks:` lines and one short final line; never send a report with SendMessage.

- [ ] **Step 1: Write failing tests** in `tests/test_agent_warm.py`. Each test builds a temp git repo and a temp `bin/` holding a fake `claude` (shell script: for `agents` prints the JSON array from `$FAKE_AGENTS`, else appends its args as one line to `$FAKE_LOG`) put first on `PATH`; run `~/bin/agent-warm` (path from env `AGENT_WARM_BIN`, default `~/bin/agent-warm`) with cwd the repo. Tests: `test_default_starts_two` (log has two `--bg` lines named `<repo>-warm-1` and `-warm-2`, each with `--agent implementer --model sonnet` and `warm/1`/`warm/2` in the prompt); `test_cap_at_three` (`9` starts three); `test_bad_n_exit_2` (`0`, `x`, `-1` each exit 2, nothing started); `test_existing_is_skipped` (`$FAKE_AGENTS` lists `<repo>-warm-1`; output has `exists`, no second start for it); `test_outside_repo_fails` (cwd a non-git dir exits 1).
- [ ] **Step 2: Run to confirm failure.** `python3 -m unittest discover -s tests -p 'test_agent_warm.py' -v` expects all FAIL (no such file).
- [ ] **Step 3: Implement `~/bin/agent-warm`** (bash, `set -euo pipefail`, executable) per the Interfaces block. Reuse the repo-name idiom from `agent-wall.sh`.
- [ ] **Step 4: Run tests.** Expect 5 passed.
- [ ] **Step 5: Sync the quickstart heredoc** and verify `cmp ~/bin/agent-warm <(heredoc body)` prints nothing; update the install/check lines.

### Task 2: `agent-wall.sh --attach` and no report suffix

**Files:**
- Create: `tests/test_agent_wall_attach.py`
- Modify: `~/bin/agent-wall.sh`
- Modify: `docs/orchestration/lab-quickstart.md` (the `agent-wall.sh` heredoc)

**Interfaces:**
- Produces: `agent-wall.sh <slug> --attach <session-name>`: skips `claude --bg`, uses `<session-name>` as the pane/session name for the state file and viewer, otherwise identical pane logic (3-pane limit, split percent, `equalize_column`). If `claude agents --json --all` has no session with that name: stderr `agent-wall.sh: no session <name>`, exit 1, no pane.
- Changes the cold path: the `claude --bg` prompt no longer appends "When finished, send your final report to @ngisa-$repo with SendMessage."

- [ ] **Step 1: Write failing tests.** Fakes: `claude` (as in Task 1; `agents` prints `$FAKE_AGENTS`), `wezterm` (`cli list --format json` prints `$FAKE_PANES`; `cli split-pane` prints a new id and appends args to `$FAKE_LOG`; other `cli` calls succeed). Env `WEZTERM_PANE=1`. Tests: `test_attach_opens_pane_only` (no `--bg` call logged, one `split-pane` whose command is `claude attach <name>`); `test_attach_missing_session_exits_1` (empty `$FAKE_AGENTS`: exit 1, no split-pane); `test_cold_start_has_no_report_suffix` (`agent-wall.sh s implementer sonnet "do x"` logs a `--bg` call whose prompt contains `do x` and does not contain `SendMessage`); `test_tab_full_still_refuses` (three other panes in the tab: exit 1 with `tab full`).
- [ ] **Step 2: Run to confirm failure.** Expect the attach and no-suffix tests FAIL.
- [ ] **Step 3: Implement** in `~/bin/agent-wall.sh`: parse `$2 == --attach` before the positional assignment (`slug=$1`, `name=$3`), run the existence check, branch around the `claude --bg` call, remove the suffix from the cold prompt. Keep `set -euo pipefail` and every other line.
- [ ] **Step 4: Run tests.** Expect 4 passed; also `bash -n ~/bin/agent-wall.sh`.
- [ ] **Step 5: Sync the heredoc;** `cmp` prints nothing.

### Task 3: `repo-tab` Sonnet and warm start

**Files:**
- Create: `tests/test_repo_tab.py`
- Modify: `~/bin/repo-tab`, `docs/orchestration/lab-quickstart.md` (the `repo-tab` heredoc)

**Interfaces:**
- Changes: the `args=(...)` line uses `--model sonnet`; before the `exec claude`/`wezterm cli spawn` step, `repo-tab` runs `agent-warm "${NGISA_WARM:-2}" >/dev/null 2>&1 &` from `$dir` when `command -v agent-warm` finds it and `NGISA_WARM` is not `0`.

- [ ] **Step 1: Write failing tests.** Static: the script text contains `--model sonnet`, not `--model opus`; contains `agent-warm` and `NGISA_WARM`; `bash -n` passes. Behavioral: with fake `agent-warm`, `claude`, `wezterm` on PATH and `WEZTERM_PANE` unset, running `repo-tab <tmp git repo>` logs one `agent-warm 2` call (cwd the repo) and the `claude` args contain `--model sonnet`; with `NGISA_WARM=0` no `agent-warm` call. (`exec claude` ends the script, so assert from the fake's log.)
- [ ] **Step 2: Run to confirm failure.**
- [ ] **Step 3: Implement** the two changes. Keep everything else.
- [ ] **Step 4: Run tests;** expect pass. **Step 5:** sync heredoc, `cmp`.

### Task 4: `implementer.md`: warm tasks, commit-body result, short final

**Files:**
- Modify: `agents/implementer.md`
- Create: `tests/test_kit_text.py` (static assertions on kit text; reused by Task 5)

**Interfaces:**
- Produces in `agents/implementer.md`: (a) a "Warm start" paragraph: if the task arrives as a message that begins `Branch: <name>.` and your worktree is `.claude/worktrees/warm-*`, run `git checkout -B <name> <base>` there (base = the task text's base, else `origin/HEAD`), skip step 1 setup unless `git diff --name-only <warm-up commit> HEAD` touches the dependency manifest, then continue at step 2; a message without `Branch:` is a stop: put it in the commit-less final line and wait. (b) Step 4 and 5 change: the commit body ends with lines `checks: <commands and result>`, `unverified: <what or none>`, `asks: <deferred decisions with your recommendation, `;`-separated, or none>`; the final message is ONE short line (`done <branch>` or the blocking reason); no `SendMessage` to the NGISA. The seven-line report and the `ledger:` line are removed; plan mode keeps its ledger file and names its path in the commit body as `ledger: <path>`.

- [ ] **Step 1: Write failing tests** in `tests/test_kit_text.py`: `implementer.md` contains `Branch:`, `checks:`, `unverified:`, `asks:` and `git checkout -B`; does not contain `exactly these seven lines` or `SendMessage`; front matter still has `isolation: worktree`.
- [ ] **Step 2: Run to confirm failure. Step 3: Edit** the file. **Step 4:** run; expect pass. Keep caveman ultra wording and the rule that `implementer.md` names no stack tool.

### Task 5: `orchestrating.md`: assign, subscribe, read git, refill

**Files:**
- Modify: `orchestrating.md`, `docs/orchestration/lab-quickstart.md` (its copy), `tests/test_kit_text.py`

**Interfaces:**
- Produces rules in `orchestrating.md`: item 3 spawn: prefer a free warm worker (`claude agents --json --cwd .` lists `<repo>-warm-N` with state done and not yet assigned this run): `SendMessage {to: <repo>-warm-N, notify_when_idle: true, message: "Branch: <name>. <task text>"}`, then `ngisa-report mark <slug> spawn`, then `agent-wall.sh <slug> --attach <repo>-warm-N`, then `agent-warm 1 >/dev/null 2>&1 &` to refill. No free warm worker: cold `agent-wall.sh <slug> implementer sonnet "<task>"` then a pure subscription `SendMessage {to: <repo>-<slug>, notify_when_idle: true}`. Item 4: on the idle notice (not a report) run `git -C <worker worktree> log -1 --format=%B` and `git diff --stat <base> HEAD`, map `checks:` to the state glyph (red check = `fail`), `asks:` to the board `?`; no new commit since the assignment means blocked: say so in one line and open the pane. The `report` stamp is at the notice. The stale-board and Stamps rules stay.

- [ ] **Step 1: Write failing tests** (append to `tests/test_kit_text.py`): `orchestrating.md` contains `notify_when_idle`, `--attach`, `agent-warm 1`, `Branch:` and no longer contains `When a worker's report arrives` or `send your final report`; the quickstart copy region equals the root file's text (compare the Stamps-bearing numbered list). **Step 2:** run, expect FAIL. **Step 3:** edit both copies identically. **Step 4:** run, expect pass.

### Task 6: Docs: Sonnet NGISA and the new flow (EN + VI)

**Files:**
- Modify: `CONTEXT.md`, `docs/orchestration/one-terminal-orchestrator.md`, `docs/orchestration/one-terminal-orchestrator.vi.md`, `docs/orchestration/lab-quickstart.md` (prose), `README.md`/`README.vi.md` and `docs/README.md` only if they say "Opus" for the NGISA or describe the report

**Interfaces:**
- Produces: `CONTEXT.md` "Warm workers (2026-10-16)" bullet (decisions, spike link, expected saving, the Sonnet bet) and updated role lines ("NGISA = Sonnet", Max plan line "Sonnet everywhere, Opus only if asked"); the two orchestrator docs describe warm workers, `--attach`, the idle notice and the commit-body result in their NGISA/worker sections, and replace "one Opus orchestrator session" and the `--model opus` snippet; the `.vi.md` mirrors every change with commands in English.

- [ ] **Step 1:** `rg -n -i "opus" CONTEXT.md README*.md docs/orchestration docs/README.md` and update only statements about the NGISA's model (not the verification doc's Opus-for-reviews history). **Step 2:** add the new bullet and doc sections. **Step 3:** `rg -n "—"` on touched files finds nothing new. **Step 4:** `rg -n "NGISA.*Opus|opus" docs/orchestration/one-terminal-orchestrator.md docs/orchestration/one-terminal-orchestrator.vi.md` shows only historical/other-role mentions.

### Task 7: `worker-result` (added after the Task 5 review)

**Why:** the NGISA must read a worker's commit without `Bash(git -C:*)`; that allow lets `git -C <path> push` through because the deny `Bash(git push:*)` does not match it.

**Files:**
- Create: `tests/test_worker_result.py`, `~/bin/worker-result`
- Modify: `docs/orchestration/lab-quickstart.md` (new heredoc `cat > ~/bin/worker-result <<'EOF'` after the `agent-warm` block; install/check lines: `chmod`, `which`, count)

**Interfaces:**
- Produces CLI `worker-result <worktree-path> <base>`: read-only. Exit 2 with stderr `usage: worker-result <worktree-path> <base>` when an argument is missing; exit 1 with `worker-result: not a git worktree: <path>` when the path is not a git worktree or `<base>` is not a commit there. Output: line `commits: N` (`git rev-list --count <base>..HEAD`), line `branch: <git branch --show-current>`; when N > 0 also `--- body` then `git log -1 --format=%B`, then `--- stat` then `git diff --stat <base> HEAD`. N = 0: only the first two lines. Never writes, never runs anything but git reads.

- [ ] Tests (temp git repo; a base commit, then a worker commit whose body has the lines `checks:`, `unverified:`, `asks:`): `test_prints_commit_body_and_stat`, `test_zero_commits`, `test_missing_args_exit_2`, `test_not_a_worktree_exit_1`, `test_bad_base_exit_1`, `test_does_not_modify_repo` (HEAD and status unchanged). RED, implement, GREEN, sync the heredoc (`cmp` prints nothing).

## Self-review notes
- Spec coverage: warm pool (T1), attach and report suffix (T2), Sonnet and warm start (T3), worker side (T4), NGISA rules (T5), docs (T6). Phase 2 re-measure is a separate run, not in this plan.
- Every Review Focus line has a test (T1 dedupe/cap/bad n, T2 missing session/fallback, T4 `Branch:` rule; the blocked-notice rule is a T5 text assertion).
