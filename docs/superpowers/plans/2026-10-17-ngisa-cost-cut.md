# NGISA cost cut Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Cut the NGISA's tokens and cost toward plain Claude: trimmed worker and NGISA profiles, fewer NGISA and worker requests, warm pool on demand, single small tasks answered in one line.

**Architecture:** Trim flags in `agent-warm` and `agent-wall.sh` (lean worker profile; plan mode keeps the full one); a fixed 4 to 5 request call pattern in `implementer.md`; three new scripts (`ngisa-start`, `ngisa-spawned`, `ngisa-collect`) that each replace a chain of NGISA Bash calls; a shorter `orchestrating.md` with the single-task rule. Scripts live as heredocs in `docs/orchestration/lab-quickstart.md` and are installed to `~/bin`.

**Tech Stack:** bash, jq, Python 3 `unittest` (stdlib), markdown.

**Spec:** `docs/superpowers/specs/2026-10-17-ngisa-cost-cut-design.md` (binding, incl. "Calls settled" and "Lever 5 decided").

## Global Constraints
- Branch `feat/worker-reuse` (continues the uncommitted reuse work) unless the user names another; never main; do not commit, add or push (the user commits).
- Kit and docs change together; `~/bin/<script>` equals its quickstart heredoc byte for byte (tests extract and compare); `orchestrating.md` and `agents/implementer.md` equal their copies in `lab-quickstart.md` and both one-terminal docs (`tests/test_kit_text.py` checks the lines).
- Vietnamese copy: `docs/orchestration/one-terminal-orchestrator.vi.md` mirrors the English doc; `lab-quickstart.md`, specs and plans have none. Code and commands stay English.
- No em dash. Do not touch `~/.claude`. No bare `flutter`/`dart` in scripts.
- Tests: `python3 -m unittest discover -s tests -p '<file>' -v`; fake `claude`/`wezterm`/`agent-wall.sh`/`ngisa-report` on PATH as in `tests/test_agent_warm.py` and `tests/test_worker_retire.py`; script path via env var with `~/bin/<name>` default.
- `claude --bg` flags: the prompt must come BEFORE `--tools` (variadic). Lean flags exactly: `--strict-mcp-config --disable-slash-commands --setting-sources project,local --tools "Bash,Edit,Write,Read,Glob,Grep"`.
- Existing behavior of `agent-warm`, `agent-wall.sh` (attach, close, headless marker, layout), `worker-*` stays unless a task says otherwise.

## Review Focus
- A `mode: plan` task never gets the lean flags (it needs Skill and Agent tools and user plugins), warm or cold.
- `ngisa-collect` never reports `ok` for a `checks:` line with a failure, and treats "0 failures" / "no errors" as clean; ambiguous means `fail`.
- `ngisa-collect` closes the pane only on `ok`; `blocked` and `fail` keep it.
- A worker whose log tail hides a failure: the check chain prints the exit status and the first failing lines.
- A single `tiny`/`small` worker task produces the one-line reply and no `ngisa-report` stamp, no worker, no warm top-up.

---

### Task 0: Spikes (run first; each can change the plan)

**Files:** Create `docs/runs/2026-10-18-cost-cut-spikes.md`.

- [ ] **Step 1 (NGISA profile):** start a `claude --bg` session in busy-bees with `--strict-mcp-config --tools "Bash,Read,Glob,Grep,Skill,SendMessage,AskUserQuestion"` (prompt first) and a prompt asking it to `SendMessage` a warm worker and reply; read its first-request context. Pass: tool names accepted, `SendMessage` works, base under 40k. Fail: keep the full NGISA profile (Task 6 skips the `repo-tab` flag change); record why.
- [ ] **Step 2 (lean worker, real task):** with the lean flags and `--agent implementer`, run one real quick task in busy-bees (a one-file test) and check: no permission prompt blocks, `fvm flutter test`/`fvm dart analyze`/`git commit` run, the chained form `cmd > "$log" 2>&1; echo "exit=$?"; tail -n 40 "$log"` is allowed. If a prompt appears, note the exact command; Task 6 adds that allow entry.
- [ ] **Step 3:** write the results and clean up spike sessions, worktrees and branches (`claude stop` + `claude rm`, `git worktree remove`), nothing left in busy-bees.

### Task 1: Lean flags in `agent-warm` and `agent-wall.sh`

**Files:** Modify `~/bin/agent-warm`, `~/bin/agent-wall.sh` and both heredocs. Test: `tests/test_agent_warm.py`, `tests/test_agent_wall_attach.py` (add cases).

**Interfaces:** Produces: `agent-warm` starts workers as `claude --bg --name <n> --agent implementer --model sonnet "<prompt>" <lean flags>`. `agent-wall.sh` cold start: prompt contains `mode: plan` or env `AGENT_PROFILE=full` means the full profile (no lean flags); otherwise lean flags after the prompt. Warm start (`--attach`) starts nothing.

- [ ] **Step 1: Failing tests:** `test_warm_start_has_lean_flags_after_prompt` (logged `--bg` line ends with the four lean flags and the prompt precedes `--tools`), `test_cold_start_quick_is_lean`, `test_cold_start_plan_mode_is_full` (prompt `Branch: x. Base: y. mode: plan /p`, no `--tools`, no `--setting-sources`), `test_cold_env_full_profile`.
- [ ] **Step 2:** run; expect FAIL.
- [ ] **Step 3: Implement** a `lean=(...)` array in each script and the plan-mode test in `agent-wall.sh`.
- [ ] **Step 4:** run both test files; expect PASS. **Step 5:** sync heredocs, `diff` empty.

### Task 2: `implementer.md` call pattern and output trimming

**Files:** Modify `agents/implementer.md` and its copies in the quickstart and both one-terminal docs. Test: `tests/test_kit_text.py`.

- [ ] **Step 1: Failing assertions:** `implementer.md` contains the quick-mode call pattern (parallel `git checkout -B` plus Write/Edit in one turn; ONE chained check call; ONE commit call; one-line final), the exact check form `cmd > "$log" 2>&1; echo "exit=$?"; tail -n 40 "$log"`, the red-case rule `grep -n -m 20 -E 'FAIL|Error|error:' "$log"`, and the sentence that plan mode keeps its own procedure; existing assertions still hold.
- [ ] **Step 2:** run; expect FAIL. **Step 3:** edit `implementer.md` in the existing terse style, quick and direct modes only. **Step 4:** sync copies; run `test_kit_text.py`; expect PASS.

### Task 3: `ngisa-start`

**Files:** Create `~/bin/ngisa-start` + heredoc. Test: `tests/test_ngisa_start.py`.

**Interfaces:** Produces `ngisa-start [--new-plan]`: runs `ngisa-report clear` only with `--new-plan`, then `ngisa-report mark - request`; prints `base: <git rev-parse HEAD>`, then one line per `<repo>-warm-N` session in `claude agents --json --cwd .` with state `done`/`idle`: `warm-N branch=<branch> dirty=<yes|no> ctx=<n>k idle=<n>m tasks=<n>` (from `worker-result .claude/worktrees/warm-N HEAD` and `worker-ctx`; `-` for an unreadable field), then `free: <count of those on branch warm/N>`. Exit 0 even when a worker line cannot be read.

- [ ] **Step 1: Failing tests** (real temp git repo with worktrees `warm-1` on `warm/1` and `warm-2` on `feat/x` with a dirty file; fake `claude agents`, fake `worker-ctx`, fake `ngisa-report` logging): `test_new_plan_clears_then_marks`, `test_without_flag_only_marks`, `test_prints_base_and_free_count`, `test_dirty_and_branch_per_worker`, `test_unreadable_worker_prints_dash`, `test_busy_worker_not_listed`.
- [ ] **Steps 2-5:** run (FAIL), implement, run (PASS), sync heredoc.

### Task 4: `ngisa-spawned`

**Files:** Create `~/bin/ngisa-spawned` + heredoc. Test: `tests/test_ngisa_spawned.py`.

**Interfaces:** Produces `ngisa-spawned <slug>=<session> ...`: for each pair `ngisa-report mark <slug> spawn` then `agent-wall.sh <slug> --attach <session>`; after all pairs `agent-warm "${NGISA_WARM:-1}"` in the background, output discarded. One output line per step (`ok`/`FAIL <step>`); exit status = number of failed steps; a failed step does not stop the rest. Bad argument (no `=`) exits 2.

- [ ] **Step 1: Failing tests** (fake `ngisa-report`, `agent-wall.sh`, `agent-warm` logging): `test_two_pairs_in_order`, `test_failed_attach_continues_and_exit_count`, `test_refill_uses_ngisa_warm_default_1`, `test_refill_env_override`, `test_bad_argument_exit_2`.
- [ ] **Steps 2-5** as Task 3.

### Task 5: `ngisa-collect`

**Files:** Create `~/bin/ngisa-collect` + heredoc. Test: `tests/test_ngisa_collect.py`.

**Interfaces:** Produces `ngisa-collect <slug> <session> <base> <branch>`: worktree = `.claude/worktrees/warm-N` when `<session>` is `<repo>-warm-N`, else the worktree whose `branch refs/heads/<branch>` shows in `git worktree list --porcelain`. Runs `worker-result <wt> <base>` (prints it), `ngisa-report mark <slug> report`, derives `state` per spec call 5: `blocked` when `commits: 0`, no `checks:` line, or `asks:` value other than `none` (case-insensitive); else `fail` when the `checks:` line has a whole-word `fail`, `failed`, `failure(s)`, `error(s)` or `red` after removing negations (`0 fail...`, `no fail...`, `no error...`, `without error...`); else `ok`. Then `ngisa-report set <slug> --base <base> --branch <branch> --state <state>` (prints the board), and `agent-wall.sh --close <session>` only when `ok`. Prints `state: <state>` before the board. Exit = number of failed steps.

- [ ] **Step 1: Failing tests** (real temp repo with a worker commit whose body varies; fakes for `ngisa-report`, `agent-wall.sh`): `test_ok_closes_pane`, `test_zero_failures_is_ok`, `test_no_errors_is_ok`, `test_two_errors_is_fail_keeps_pane`, `test_tests_failed_is_fail`, `test_red_word_is_fail`, `test_no_checks_line_is_blocked`, `test_zero_commits_is_blocked`, `test_asks_not_none_is_blocked_keeps_pane`, `test_cold_worker_found_by_branch`, `test_step_failure_counted`.
- [ ] **Steps 2-5** as Task 3.

### Task 6: Rules, settings, profile, docs

**Files:** Modify `orchestrating.md`, `settings.local.json`, `~/bin/repo-tab` (+ heredocs), the one-terminal docs EN/VI, `CONTEXT.md`, `docs/README.md`. Test: `tests/test_kit_text.py`, `tests/test_repo_tab.py`.

- [ ] **Step 1: Failing assertions:** `orchestrating.md` names `ngisa-start`, `ngisa-spawned`, `ngisa-collect`; has the single-task rule text `one task: run it in plain Claude`; says to top up warm workers with `agent-warm N` for `quick`/`direct` tasks only after sizing; says plan-mode tasks take the cold path and never reuse; no longer lists the multi-call chains that the scripts replace; its length is at most 80% of the current 9.0 KB; `settings.local.json` allows `Bash(ngisa-start:*)`, `Bash(ngisa-spawned:*)`, `Bash(ngisa-collect:*)` (plus any entry Task 0 step 2 found); `repo-tab` default `NGISA_WARM` is 1, and, if Task 0 step 1 passed, `repo-tab` passes `--strict-mcp-config` and `--tools "Bash,Read,Glob,Grep,Skill,SendMessage,AskUserQuestion"` with the prompt-before-flag rule respected.
- [ ] **Step 2:** run; expect FAIL. **Step 3:** edit the kit (keep every behavior rule: guards, merge worktree, no push, asks via `AskUserQuestion`, stamps, reuse/retire, compact instructions); trim wording only. **Step 4:** sync heredocs and docs (EN + VI sections: "Cost cut" with the trim spike numbers); update `CONTEXT.md` decisions and open items, `docs/README.md` index. **Step 5:** `python3 -m unittest discover -s tests -v`; expect all PASS.

### Task 7: Install and verify

- [ ] **Step 1:** for each changed or new script, extract its quickstart heredoc and `diff` against `~/bin/<name>`; empty. **Step 2:** smoke tests with the real `claude`: `ngisa-start` in busy-bees prints a base and free count; `ngisa-collect` on a missing worktree exits non-zero without damage. **Step 3:** remind the user to re-run `real-init` on busy-bees.

### Task 8: Re-measure (needs the user's go; uses quota)

**Files:** `docs/runs/2026-10-18-cost-cut-measure.md`; the harness stays in the session scratchpad.

- [ ] **Step 1:** update `measure.py` to report tokens per role (NGISA, workers, warm-ups) and add the scenario "3 independent medium tasks in parallel" and "1 tiny task" (confirms the one-line reply and no worker). **Step 2:** ask the user, then run: 4 small tasks in 2 batches (as before), 3 parallel medium tasks, plain Claude for each, one run per side. **Step 3:** log results against the bar (2+ tasks: within about 1.5x of plain on tokens and cost and not slower; 3 parallel: clearly faster, moderate cost); if missed, name the biggest remaining token source from the per-role split.
