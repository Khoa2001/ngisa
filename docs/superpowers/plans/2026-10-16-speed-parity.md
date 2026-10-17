# Speed parity, phase 1 (instrument) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Let the NGISA stamp stage events per run and print time per stage, and define the baseline protocol, so phases 2 to 4 are measured.

**Architecture:** `ngisa-report` gets two commands, `mark` and `timing`, backed by a top-level `marks` dict in the existing per-repo JSON. `set` already replaces only task rows, so marks survive it. The NGISA calls `mark` at fixed events (rule in `orchestrating.md`). The script source lives as a heredoc in `docs/orchestration/lab-quickstart.md` and is installed to `~/bin/ngisa-report`; both change together.

**Tech Stack:** Python 3 standard library, `unittest`, bash.

**Spec:** `docs/superpowers/specs/2026-10-16-speed-parity-design.md`

## Global Constraints
- Branch `feat/speed-parity`; never main; commit only when the user says so.
- Kit and docs change in the same commit. `~/bin/ngisa-report` equals the quickstart heredoc byte for byte.
- Python 3 standard library only. Existing `set`, `show`, `clear` behavior and output do not change.
- Plain dash, no em dash. Code and commands in English.
- Do not touch `~/.claude`. `~/bin` is allowed (the kit installs there).

## Review Focus
- `mark` on a slug with no task row: still stored, not an error.
- `timing` with a missing event: print `-` for that stage, never crash.
- `set` after `mark`: marks survive.
- Corrupt or wrong-shape JSON: `mark` starts fresh like `set` does, no traceback.
- Events out of order (report stamped before spawn): print the negative gap as `-`, not a negative duration.

---

### Task 1: `mark` and `timing` in ngisa-report

**Files:**
- Create: `tests/test_ngisa_report_timing.py`
- Modify: `~/bin/ngisa-report`
- Modify: `docs/orchestration/lab-quickstart.md` (the `cat > ~/bin/ngisa-report` heredoc, about line 1161)

**Interfaces:**
- Produces CLI `ngisa-report mark <slug> <event> [--at EPOCH]`. `event` in `request, spawn, report, decided, pr`. Slug `-` means batch level (used for `request`). Stores `data["marks"][slug][event] = epoch int` (default `int(time.time())`). Exit 2 on unknown event, nothing saved. Prints nothing on success.
- Produces CLI `ngisa-report timing [slug]`. One line per slug that has marks (all, or the named one), format
  `<slug>  plan <d>  worker <d>  report <d>  merge <d>  total <d>` where:
  plan = spawn - request (batch `-` request), worker = report - spawn, report = decided - report, merge = pr - decided, total = pr - request (or last mark if no pr). `<d>` is `NmSSs` (e.g. `4m31s`) or `-` when an event is missing or the gap is negative. Exit 1 with stderr `ngisa-report: no marks` when none.
- Helper `fmt_dur(seconds: int | None) -> str` in the script.

- [ ] **Step 1: Write failing tests** in `tests/test_ngisa_report_timing.py`. Each test runs the script as a subprocess (path from env `NGISA_REPORT_BIN`, default `~/bin/ngisa-report`) with `XDG_CACHE_HOME` set to a temp dir and `NGISA_REPO=demo`. Names and assertions:
  - `test_mark_then_timing`: marks `- request --at 1000`, `a spawn --at 1060`, `a report --at 1360`, `a decided --at 1420`, `a pr --at 1480`; `timing a` stdout equals `a  plan 1m00s  worker 5m00s  report 1m00s  merge 1m00s  total 8m00s\n`.
  - `test_missing_event_prints_dash`: only `spawn` and `report`; output contains `plan -` and `merge -`.
  - `test_unknown_event_rejected`: `mark a nope` exits 2, stderr contains `unknown event`, `timing` afterwards exits 1.
  - `test_set_keeps_marks`: `mark a spawn --at 1`, then `set a --state ok`, then `timing a` still shows the stamp.
  - `test_negative_gap_is_dash`: `report --at 10`, `spawn --at 20` gives `worker -`.
  - `test_corrupt_json_mark_starts_fresh`: write `{"x": 1}` to the report path, `mark a spawn`, exit 0.
  - `test_no_marks_exit_1`: `timing` on a fresh cache exits 1 with `no marks`.
- [ ] **Step 2: Run to confirm failure.** Run: `python3 -m unittest discover -s tests -p 'test_ngisa_report_timing.py' -v`. Expected: all FAIL (argparse "invalid choice: 'mark'").
- [ ] **Step 3: Implement** `cmd_mark`, `cmd_timing`, `fmt_dur` and the two subparsers in `~/bin/ngisa-report`. Reuse `load`, `save`, `report_path`, `repo_name`; `cmd_mark` loads with the same `load(path) or {"repo": repo, "tasks": []}` fallback and writes through `save`. Update the module docstring usage block.
- [ ] **Step 4: Run tests.** Same command. Expected: 7 passed.
- [ ] **Step 5: Regression check** by hand: `ngisa-report set demo-x --state working` then `show` prints the same board as before this change.
- [ ] **Step 6: Sync the heredoc.** Replace the quickstart heredoc body with the new script; verify `diff <(sed -n '/^cat > ~\/bin\/ngisa-report <<.EOF.$/,/^EOF$/p' docs/orchestration/lab-quickstart.md | sed '1d;$d') ~/bin/ngisa-report` prints nothing.

### Task 2: NGISA stamps the events

**Files:**
- Modify: `orchestrating.md`
- Modify: `docs/orchestration/lab-quickstart.md` (the matching `orchestrating.md` text; grep `ngisa-report clear` near line 65)

**Interfaces:**
- Consumes: `ngisa-report mark <slug> <event>` from Task 1.
- Produces: a rule block, "Stamps", in `orchestrating.md`: `mark - request` at the user's task message (before sizing); `mark <slug> spawn` right after each `agent-wall.sh`; `mark <slug> report` when a worker report arrives; `mark <slug> decided` when the user answers the ask or says merge; `mark <slug> pr` after `agent-pr`. At the end of a run, `ngisa-report timing` output goes to the run log, not the chat. Stamps print nothing and add no chat line (keeps the quiet-tab rule).

- [ ] **Step 1:** Add the "Stamps" block to `orchestrating.md`, five lines, after the spawn rules. `Bash(ngisa-report:*)` is already allowed, so no settings change.
- [ ] **Step 2:** Copy the same text into the quickstart copy of `orchestrating.md`; confirm the two match with `diff`.
- [ ] **Step 3:** Dry run: `ngisa-report clear`, run the five marks by hand for slug `demo`, `ngisa-report timing demo` prints one line with five durations; `ngisa-report clear`.

### Task 3: Baseline protocol

**Files:**
- Create: `docs/runs/2026-10-16-baseline-protocol.md`
- Modify: `CONTEXT.md` (add a "Speed parity (2026-10-16)" bullet under Decisions, one open item under Open items)

**Interfaces:**
- Produces: the protocol the three phases reuse. Contents: the three busy-bees tasks (tiny fix, test task A, test task B; exact tasks "to be named by the user"), the run order (plain Claude first, then NGISA, fresh branch each, same base commit), what to record per task and side (stage times from `ngisa-report timing` for NGISA, stopwatch for plain Claude; interventions and why; cost from the CLI total; gate or check results), the blind diff review sheet (side labelled A/B by coin flip, user scores correctness, scope, tests; reveals sides after), and the "equal" rule (tiny and small: NGISA total at or below plain Claude; parallel pair: NGISA total strictly below).

- [ ] **Step 1:** Write the protocol file with the headings above, as a fill-in table template.
- [ ] **Step 2:** Add the `CONTEXT.md` bullet (decision, goal, link to spec and protocol) and one open item "name the three busy-bees baseline tasks".
- [ ] **Step 3:** `rg -n "—" docs/runs/2026-10-16-baseline-protocol.md CONTEXT.md` finds nothing new (no em dash).

### Task 4: Vietnamese copy check

**Files:**
- Modify only if touched: `docs/orchestration/one-terminal-orchestrator.vi.md`

- [ ] **Step 1:** `rg -n "ngisa-report" docs/orchestration/one-terminal-orchestrator.md docs/orchestration/one-terminal-orchestrator.vi.md`. If the English doc is unchanged by this plan, record "no `.vi` change needed" in the Task 3 protocol file's notes. `lab-quickstart.md` and `orchestrating.md` have no `.vi` copy today; leave as is.

## Self-review notes
- Spec coverage: Phase 1 (instrument, protocol) is Tasks 1 to 3. Phases 2 to 4 are runs and need user picks, so they are not in this plan.
- Every Review Focus line has a test in Task 1.
- Open for the user: exact three busy-bees tasks (Task 3).
