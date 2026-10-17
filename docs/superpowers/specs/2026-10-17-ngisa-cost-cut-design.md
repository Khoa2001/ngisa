# NGISA cost cut: design

Date: 2026-10-17. Branch: `feat/worker-reuse` (continues it) or a new branch from it; builder's call. Builds on PR #34 and the uncommitted worker-reuse work.

## Intent
The measure of 2026-10-17 (`docs/runs/2026-10-17-worker-reuse-measure.md`) showed the NGISA ties plain Claude on time for four small tasks but uses about 6x the cache-read tokens, 5x the cache writes and 1.4x to 1.7x the output; cost about 4x (estimate). The user finds all of these unacceptable.

## Bar (the user's, confirmed)
- Small or sequential work: NGISA within about 1.5x of plain Claude on tokens and cost, and not slower.
- Three or more independent tasks: clearly faster than plain Claude, with only a moderate cost increase.

## Where the tokens go (measured from transcripts)
- Base context at the first request: NGISA 54k, workers 52.7k, plain Claude 35.7k. Every request re-reads it.
- NGISA: 20 to 21 requests for 4 tasks (14 Bash, 4 SendMessage, 1 ToolSearch), about 1.25M cache read (about 40% of the total).
- Worker: 7 to 8 requests (5 to 6 Bash) for one test file, 0.4M to 0.5M cache read each.
- Unused warm worker: 2 requests, about 80k read + 33k write.
- Spike (`docs/runs/2026-10-17-trim-spike.md`): `claude --bg` honors trimming flags. A worker started with `--strict-mcp-config --disable-slash-commands --setting-sources project,local --tools "Bash,Edit,Write,Read,Glob,Grep"` has a 26.1k base instead of 52.5k, and Write, Edit, Read and Bash still work. `--tools` is variadic: the prompt must come before it.

## Goals
- Cut tokens per task by shrinking the base context and the request count; keep quality and the result format (`checks:`, `unverified:`, `asks:`).
- Meet the bar above, shown by a re-measure with tokens per role.

## Non-goals and anti-goals
- No change to the safety rules: NGISA never pushes or merges to main, guards and deny rules stay, workers never touch the main checkout.
- No third-party package; no new model for the NGISA (Haiku NGISA is out of scope: quality risk).
- Must not make plan-mode workers worse: they need the Skill and Agent tools and the user's plugins.

## Design (my calls unless marked)
### 1. Trimmed profiles
- **Lean worker profile** (`mode: quick` and `mode: direct`): started with the prompt first, then `--strict-mcp-config --disable-slash-commands --setting-sources project,local --tools "Bash,Edit,Write,Read,Glob,Grep"`. Applied in `agent-warm` (warm workers) and in the cold path of `agent-wall.sh`.
- **Full worker profile** (`mode: plan`): unchanged flags; plan-mode workers need superpowers skills and subagents. Plan-mode tasks therefore always take the cold path (a warm worker is lean by construction, and the mode is only known when the task arrives).
- **NGISA profile** (`repo-tab`): `--strict-mcp-config` and a `--tools` list that adds the tools it needs on top of the lean set minus Edit/Write: `Bash,Read,Glob,Grep,Skill,SendMessage,AskUserQuestion` (no ToolSearch hop for SendMessage). Keeps user plugins and skills (big tasks use brainstorming and writing-plans). The exact list and the base it yields are a spike item (below).
- **Shorter rules file:** `orchestrating.md` is read on every NGISA request (about 9 KB). Move rarely used rules (PR, relay, ask format details) into one-line pointers or trim wording; keep every behavior rule and the doc-copy tests.

### 2. Fewer NGISA requests (new scripts, `~/bin`, heredocs in the quickstart)
- `ngisa-start`: one call at the start of a request: `ngisa-report clear` (when it starts a new plan) and `mark - request`, prints the base sha (`git rev-parse HEAD`), the free warm workers (state done/idle, on `warm/N` or clean), and for finished reusable workers their `worker-ctx` and `worker-result ... HEAD` dirty flag.
- `ngisa-spawned <slug>=<session> ...`: one call after the SendMessages: `mark spawn`, `agent-wall.sh --attach`, and the refill (`agent-warm`) for all tasks of the batch.
- `ngisa-collect <slug> <session> <base> <branch>`: one call per idle notice: `worker-result`, `mark report`, `agent-wall.sh --close`, and `ngisa-report set` with an automatic state: `blocked` when `commits: 0`, no `checks:` line or `asks:` is not `none`; `fail` when the `checks:` line contains a red marker (fail, error, red; case-insensitive); else `ok`. It prints the result and the state; the NGISA may override with `ngisa-report set` when it reads something else.
- Both SendMessages of a batch go in one assistant message (parallel tool calls). Target: about 8 NGISA requests for 4 tasks in 2 batches, down from 20.

### 3. Fewer worker requests (`agents/implementer.md`, quick and direct modes)
- Fixed call pattern, target 4 to 5 requests: (1) in one turn, in parallel: `git checkout -B <name> <ref>` and the Write/Edit of the files; (2) one Bash chain with all listed checks, output piped through `tail -n 40` so context does not grow with logs (failing lines must stay visible); (3) one Bash commit with the body lines; (4) the one-line final message. A red check is fixed and re-run as before.
- Cold start and plan mode keep their longer procedure.

### 4. Warm pool on demand
- `repo-tab` default `NGISA_WARM=1` (was 2). `ngisa-start` reports the free count; the NGISA tops up to the number of independent tasks right after sizing (`agent-warm N` in the background; about 25 s to ready), so the pool is not paid for when the request is a single task.

### 5. Single small tasks (the user chose (b))
With levers 1 to 4 a single tiny task still costs a worker session plus the NGISA's requests, about 2x plain Claude by my estimate, over the 1.5x bar. Options: (a) inline lane: the NGISA edits in its own lane worktree for `tiny` tasks only (needs root-anchored `Edit(/lib/**)`-style deny patterns, an `ngisa-guard` exception and a lane worktree; breaks "NGISA never writes code" for tiny tasks; ties plain on time in the earlier test); (b) the NGISA tells the user to run a tiny or single small task in plain Claude and spends nothing; (c) accept about 2x for single tiny tasks.

## Constraints
Kit and docs change together (EN + `.vi` for the one-terminal doc); `~/bin` equals the quickstart heredocs; tests in `tests/` with fake `claude`/`wezterm`; scripts call no bare flutter/dart; never commit or push unless the user says so.

## Measure (after build)
Same harness (`measure.py`, end detection fixed) with tokens per role (NGISA, workers, warm-ups) and these scenarios: 4 small tasks in 2 batches (as before), 3 independent medium tasks in parallel, and a single tiny task (only to confirm the NGISA answers in one request and starts no worker). One run per side first; repeat only if a result is within noise. Pass: the bar above.

## Spike items for the builder (cheap, before building)
1. NGISA tool list: does a `--bg` session with `--tools "Bash,Read,Glob,Grep,Skill,SendMessage,AskUserQuestion"` still send messages to peers and ask questions? What base does it show?
2. Does the lean worker (without user-level settings) still obey the project's permission allow list for `fvm flutter test`, `fvm dart analyze`, `git commit` in a real busy-bees warm worker?

## Calls settled after the builder check (mine, flagged)
1. **Lean profile with `--agent implementer`:** the trim spike already ran with `--agent implementer` in busy-bees (the log showed `@implementer`), with `--setting-sources project,local`, so the project-level agent file loads and `implementer.md` has no `tools:` frontmatter; `--tools` set the list. No fallback needed; spike item 2 re-checks it in a real warm worker.
2. **Plan-mode tasks:** the NGISA classifies the mode at sizing (already its first step) before topping up warm workers; the top-up counts only `quick`/`direct` tasks. Plan-mode tasks always take the cold path with the full profile, never reuse a finished worker, and their workers are retired when done.
3. **Reuse verdict:** `ngisa-start` prints facts per finished worker (`ctx`, `idle`, `tasks`, `dirty`), as `worker-ctx`/`worker-result` do; the NGISA decides with the existing thresholds because "paths overlap" needs judgment.
4. **Partial failure:** `ngisa-spawned` and `ngisa-collect` continue past a failed step, print one line per step, and exit non-zero with the count of failed steps.
5. **Red markers in `ngisa-collect`:** match whole words (`fail`, `failed`, `failure(s)`, `error(s)`, `red`) after removing negations (`0 failures`, `no errors`, `no failures`, `without errors`). A false `ok` is worse than a false `fail`, so anything ambiguous is `fail`.
6. **Pane close:** `ngisa-collect` closes the pane only for `ok`. A `blocked` or `fail` worker keeps its pane (its question or failure is there); this also settles the deferred minor from the reuse review.
7. **NGISA profile fallback:** if the spike shows a `--tools` name is invalid (for example `SendMessage`) or the NGISA base stays above 40k, ship levers 2 to 4 with the full NGISA profile. `--strict-mcp-config` is acceptable: no NGISA flow uses MCP tools.
8. **Output trimming without hiding failures:** the check chain writes to a log file, prints the exit status, then the last 40 lines (`cmd > "$log" 2>&1; echo "exit=$?"; tail -n 40 "$log"`), and a red check prints the first failing lines too (`grep -n -m 20 -E 'FAIL|Error|error:' "$log"`). This avoids the pipe hiding the exit code.
9. **Permissions:** the lean worker keeps the project allow list from `real-init`; the builder adds `Bash(tail:*)` and `Bash(grep:*)` only if the spike shows a prompt, and the kit, docs and tests change together. Spike item 2 covers compound commands (`;`, redirects) against the prefix rules in a real Flutter repo; PHP is covered by the same mechanism and checked once.
10. **Sources of truth:** the heredocs in `lab-quickstart.md` are the source, `~/bin` holds installed copies that must equal them (tests extract and compare, as for `worker-ctx`); `lab-quickstart.md` has no Vietnamese copy (as `docs/README.md` says).

## Lever 5 decided (user)
The user chose (b): a request that sizes to exactly one worker task of size `tiny` or `small` (this includes dependent tasks that would go to ONE worker) gets one line from the NGISA, `one task: run it in plain Claude`, and no worker, no stamps, no board. Requests with two or more independent tasks, and every `big` request, run as before. Consequences: the "1 tiny task" measure scenario is dropped from the pass criteria (the check becomes: the NGISA's reply costs about one request); "within 1.5x of plain Claude" applies to requests with 2+ tasks. The inline lane (a) and accepting 2x (c) are out of scope.

## Left to the builder
Exact flag order helper (one function used by `agent-warm` and `agent-wall.sh`), output format of `ngisa-start`, the red-marker list in `ngisa-collect`, test fixtures, how far to trim `orchestrating.md`.

## Open
- Thresholds from earlier work (100k, 55 min, 3 tasks) stay until the re-measure.

## Fixes from the final review (2026-10-18)
- The check chain uses `{ <check 1> || rc=1; <check 2> || rc=1; } > "$log" 2>&1; echo "exit=$rc"` (a `( a; b )` subshell returned only the last exit code).
- `ngisa-collect` needs positive evidence for `ok` (pass, green, clean, ok, success, `exit=0`); an exit code, a `n/m` ratio with n different from m, `not green`, timeout, broke, cannot run, an empty line or no evidence means `fail`; continuation lines of `checks:` and `asks:` are read; a missing `asks:` line, `dirty: yes` or a branch other than the expected one means `blocked`.
- Quick-mode call pattern: `git checkout -B` first (alone), reads only after it, then parallel Write/Edit; direct mode keeps red first; multi-step tasks run the pattern once per step. Target 5 to 6 requests.
- Top-up is `agent-warm N` with N = number of quick/direct tasks (max 3); `agent-warm` counts workers still warming (state `working`, no worktree yet or still on `warm/N`) as pending so a top-up plus a refill does not over-start; the NGISA waits up to 60 s for them instead of starting cold.
- `agent-warm`, `ngisa-start`, `ngisa-spawned` work from the main checkout even when called from a linked worktree (`claude agents --json --all --cwd <main checkout>`).
- `agent-wall.sh --attach` twice for the same session opens no second pane; the rules close panes left open after an answered ask, an override to `ok` or a merge.
- The single-task rule is checked at sizing (one line, no tool call) before `ngisa-start`, and does not apply to a relay or follow-up to a running worker. Lean workers have no skills, so carve is run by the user.
- Ruling: the "80% of the old size" target for `orchestrating.md` was dropped (the file is about 1% of the tokens); the test only forbids growing past the old 10.7 KB.
- Deferred minors: paths with spaces in `worker-retire`; false `fail` for odd wording; no check of the last commit's author on a relay round; `worker-result` errors replaced by "no readable worktree"; `ngisa-spawned` prints `ok` after a stamp failure and does not check the session is warm; plan workers and cold sessions are not retired (`worker-retire` accepts warm names only); `--new-plan` for a tiny/small multi-task request; no stop when a lean warm worker gets a plan-mode task; stale "single-use" wording in the docs (`one-terminal-orchestrator*`, `agent-warm` comment, `CONTEXT.md:120`) and the VI doc lacks "(default 1)".
- Unverified: the braces form of the check chain and `mktemp` against the permission rules in a real Flutter repo (the earlier spike ran the subshell form); `notify_when_idle` for a lean warm worker; whether `--disable-slash-commands` removes the built-in `/compact`; whether `claude agents --json` hides finished sessions without `--all` (the scripts now pass `--all`).

## Re-measure fixes (2026-10-18)
- `ngisa-collect` read a `Co-Authored-By:` trailer as part of `asks:` and said `blocked` for every good worker; a field now ends at a blank line, a key line or `---` (tests include a trailer).
- `ngisa-start --need N`: tops up with `agent-warm N` and waits inside the script (up to `NGISA_START_WAIT`, default 60 s) until N warm workers are free; the NGISA no longer polls. The rules also say: run `ToolSearch select:SendMessage` in the same turn as `ngisa-start`; do not re-run `ngisa-report set` or `agent-wall.sh --close` after `ngisa-collect`.
- Result: `docs/runs/2026-10-18-cost-cut-measure.md`. The bar (about 1.5x of plain Claude for 2+ tasks) is not met (1.7x to 2.25x estimated); next levers are listed there.
