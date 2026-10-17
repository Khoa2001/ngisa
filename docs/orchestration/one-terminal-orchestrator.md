# One terminal, one orchestrator, many agents

Bottom line: don't build this, and don't install a third-party tmux manager. Claude Code now ships
everything you described. Your "NGISA" is **one Sonnet orchestrator session** (Opus was the first choice; Sonnet is faster and the NGISA only plans and dispatches, see "Warm workers") that plans, then dispatches
**worktree-isolated Sonnet implementer subagents** in the background and a result row per worker, read from its commit (you review the diff yourself).
When you have several *independent* features going, **agent view** (`claude agents`) is the one screen
that shows all of them. Agent teams look like exactly what you asked for, but they don't isolate agents in
worktrees and they're experimental. Don't use them for code yet.

And the hard truth from the last playbook still applies: parallel agents without hooks + CI gates just
multiply what you have to check. If `gate.sh` / `ci_local.sh` from
[cut-verification-time.md](../verification/cut-verification-time.md) aren't in your repos yet, do that first.

Checked against the current Claude Code docs (Oct 2026):
[agents](https://code.claude.com/docs/en/agents), [agent view](https://code.claude.com/docs/en/agent-view),
[agent teams](https://code.claude.com/docs/en/agent-teams), [worktrees](https://code.claude.com/docs/en/worktrees),
[workflows](https://code.claude.com/docs/en/workflows), [costs](https://code.claude.com/docs/en/costs).
Feature names and flags move fast; run `claude update` before you start.

---

## 1. What exists, and what to use it for

| Option | Who orchestrates | Isolation | Verdict for you |
|---|---|---|---|
| **Subagents** (`.claude/agents/*.md`, `isolation: worktree`, `background: true`) | Your orchestrator session, turn by turn | Each subagent gets its own worktree | **Use this.** It *is* the NGISA you described. Results return to one conversation. |
| **Agent view** (`claude agents`, `claude --bg "…"`) | You | Each dispatched session moves into its own worktree before editing | **Use this as your one screen** when you run 2–3 independent orchestrators (one per feature). Research preview. |
| **Agent teams** (`CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS=1`) | A lead session, with a shared task list and messaging | **None.** Teammates share one checkout; you must partition files by hand | Use for **research, review, competing-hypothesis debugging** only. Not for parallel coding. Experimental, ~7× tokens in plan mode, no resume. |
| **Dynamic workflows** (`ultracode: …`, `/workflows`) | A script Claude writes | Can isolate per item | Use for **wide mechanical jobs**: "migrate every widget to X", "audit every repository class". Not for feature work. |
| **`/batch`** | Claude | 5–30 worktree subagents | Shortcut for one big mechanical change. Same bucket as workflows. |
| claude-squad, ccmanager, Conductor, tmux scripts | You | Worktrees | **Skip.** They predate agent view and now duplicate it. Conductor is a Mac GUI, not one terminal. Extra tool, extra failure mode, no gain. |
| Agent SDK custom orchestrator | Your code | Whatever you build | **Skip.** Building a framework is a stated non-goal of this project, and the built-ins already do routing, isolation and collection. |

## 2. The setup

### Once per machine vs once per repo

Most of this lives in your home folder and applies to every repo. Only three small files are per repo.

| Piece | Where | Scope |
|---|---|---|
| `implementer.md` | `~/.claude/agents/` | once, all repos |
| Orchestrating rules | `~/.claude/CLAUDE.md` (or a user skill `~/.claude/skills/orchestrate/`) | once |
| Format hook, Stop gate, irreversible-command block, permission allowlist | `~/.claude/settings.json` | once |
| `agent-wall.sh` | `~/bin/` (on PATH) | once |
| WezTerm | nothing to configure; the script uses `wezterm cli` | once |
| `tool/ci_local.sh` | repo | **per repo** (its exact format/analyze/test commands; CI calls it too) |
| `.worktreeinclude` | repo root | **per repo** (which gitignored files each worktree needs) |
| `.claude/worktrees/` line in `.gitignore` | repo | **per repo** |

For this to work at user level, the hooks must not assume a repo layout. The Stop gate becomes
"run `./tool/ci_local.sh` if it exists, else do nothing", and the format hook formats only `*.dart`
(skip generated files). Then a repo without `ci_local.sh` just isn't gated yet; nothing breaks.

Per-repo step, one command. `~/bin/agent-init`:

```bash
#!/usr/bin/env bash
# run once in a repo root: adds the three per-repo files if missing
set -euo pipefail
mkdir -p tool
grep -qxF '.claude/worktrees/' .gitignore 2>/dev/null || echo '.claude/worktrees/' >> .gitignore
[[ -f .worktreeinclude ]] || printf '.env\n.env.local\nandroid/key.properties\n' > .worktreeinclude
[[ -f tool/ci_local.sh ]] || { cat > tool/ci_local.sh <<'S'
#!/usr/bin/env bash
set -euo pipefail
if [[ -f melos.yaml ]]; then
  melos exec -- dart format . --set-exit-if-changed && melos analyze && melos test
else
  dart format . --set-exit-if-changed && flutter analyze && flutter test
fi
S
chmod +x tool/ci_local.sh; }
echo "done: check .worktreeinclude matches your gitignored secrets, then commit"
```

This block is the original Flutter-only version. The current `agent-init` detects the stack (Flutter, PHP), writes `tool/setup.sh` and `tool/ci_local.sh` from it, and adds a per-repo `.claude/ngisa-settings.json`. The agents run those two files instead of naming a tool. The current script is in [`lab-quickstart.md`](lab-quickstart.md) step 3, and it wins over this block.


Where a repo already has project-level `.claude/agents/` or `.claude/settings.json`, those win over
the user ones for that repo. Use that only when a repo genuinely differs (e.g. the GitLab work app).

The snippets below are written as files; put them in the location the table says.


### 2a. Agent definitions

`~/.claude/agents/implementer.md`

```markdown
---
name: implementer
description: Implements one task (quick or direct mode) or a whole plan (plan mode, subagent-driven) in its own worktree, then commits on its branch
model: sonnet
isolation: worktree
background: true
---
You get ONE task or one plan group from NGISA. Work only inside your worktree.
Never change the branch, index or files of the main checkout; if you find yourself there, stop touching it and create your worktree first.
The task text starts with `mode: quick`, `mode: direct` (default when missing) or `mode: plan <absolute path of the plan file>`. Direct mode is the numbered steps below. Quick mode is under "Quick mode" and plan mode under "Plan mode", both after them.
The task text gives the paths you may touch, the stack and what to verify. Anything missing: use the repo's CLAUDE.md, which has the stack conventions and the commands to format, analyze and test; follow it. The git and scope rules below always win.
Task text format: `Branch: <name>. Base: <ref>. <task text>` (<ref> = full sha of NGISA's HEAD). Cold start: the task is given in the prompt. First decide whether you are isolated: `git rev-parse --show-toplevel` equal to the first path printed by `git worktree list --porcelain` (the main checkout) means you are NOT isolated. Not isolated: create your own worktree `git worktree add .claude/worktrees/<last path segment of Branch> -b <name> <ref>`, `cd` into it, run `worktree-include`, and work ONLY there; NEVER run `git checkout`, `git switch`, `git reset` or commit in the main checkout. Already in a linked worktree (path under `.claude/worktrees/`): run `git checkout -B <name> <ref>` there. Then steps 1-5 as written. A task given in the prompt (cold start) is not a message: the no-branch stop below never applies to it.
Warm start: task message begins `Branch: <name>. Base: <ref>.` and your worktree path matches `.claude/worktrees/warm-*`: run `git checkout -B <name> <ref>` there (use the Base ref, never origin/HEAD). Skip step 1. A test or analyze run then fails on missing packages: run `./tool/setup.sh` once, continue at step 2. In a `warm-*` worktree, a task message with no `Branch:` line: stop, edit nothing, final line `no branch given`.
1. Before you touch any file, run `./tool/setup.sh`. No such file: your worktree was probably made with a plain `git worktree add`, which skips `.worktreeinclude`. Run `worktree-include` once (it copies the files `.worktreeinclude` lists from the main checkout), then run `./tool/setup.sh` again. Still no such file: run the setup commands in CLAUDE.md. Neither exists: stop, edit nothing, final line = the exact error, do not guess a stack.
2. TDD: write the failing test, show it red, make it green. Use the test command in CLAUDE.md (or the task text).
3. Before you stop, run the checks CLAUDE.md names (format, analyze, tests) on what you changed, and the whole test suite if CLAUDE.md says so. Do not reformat code you did not change: if a formatter rewrites other lines, undo those hunks before committing. Never skip, delete or loosen tests, lint rules or analyzer config to get green. A test that was already red before your change: leave it and name it in `unverified:`. CLAUDE.md names no checks, or they cannot run: stop and report the exact error. A red result in `checks:` is fine; a faked green is not.
4. Commit on your branch. Never push, never merge, never touch main. Commit body (after subject, before any attribution trailer) has three lines (the LAST commit on your branch carries them; if the last commit is not yours, e.g. made by a subagent, add a `git commit --allow-empty` with the lines), caveman ultra (no articles or filler, fragments OK); commands and errors exact:
   checks: <commands run and their result, or the exact error>
   unverified: <what you could NOT verify and why, or none>
   asks: <decisions you deferred, each with your recommendation, separated by ";", or none>
5. Final message: ONE short line. `done <branch>` or the blocking reason. Nothing else.
Do not edit files outside the task's listed paths. If you must, stop and say so.

Quick mode (`mode: quick`): lean worker for tiny and small tasks. Start (warm or cold), steps 1, 3, 4 and 5 and the scope rule apply as written; step 2 is replaced:
- Make only the change the task text lists and write only the tests it lists: no extra test cases, no refactors, no failing-test-first demonstration. Do not reformat code you did not change: if a formatter rewrites other lines, undo those hunks before committing. Write the change and its tests, then run.
- Run each listed check once. A failing check: fix, re-run until green or report it red; that is not an extra run.
- Never loosen tests, lint rules or analyzer config. Commit body lines `checks:`, `unverified:`, `asks:` on the LAST commit, and ONE short final line.
- Task text may hold several numbered steps: do them in order in this worktree, one commit per step, the LAST commit carries the `checks:`/`unverified:`/`asks:` lines for all steps.
Direct mode is unchanged: full TDD, red first. Task text may hold several numbered steps: do them in order in this worktree, one commit per step, the LAST commit carries the `checks:`/`unverified:`/`asks:` lines for all steps.

Plan mode (`mode: plan <path>`): read the plan file (never edit it), then do step 1 (warm start: as the Warm start line says) and run `superpowers:subagent-driven-development` on the task numbers the task text names. It dispatches a fresh implementer subagent per task, a task review after each and a final review of your branch; let it. Differences from the skill:
- Autonomous: decide conflicts and ambiguities yourself, as the skill says, and write each as `Ruling: <what> - <why> - <cost if wrong>` in its ledger. Do not ask about rulings.
- Stop and put it in `asks:` (commit body) only for the skill's four cases: an irreversible or destructive operation, a security-sensitive action, a side effect outside this worktree (merge, push, publish), a plan so broken every path is a guess.
- Do not run `finishing-a-development-branch`: no merge, no PR, no push. Leave the work committed on your branch.
- Steps 3 and 4 still apply: run the repo's checks (a red result is reported in `checks:`, never faked).
- Commit body adds `ledger: <path of the ledger file>` (also on the last commit). Direct mode: no `ledger:` line.
```

There is no reviewer agent. You read the diff.

### 2b. Worktree hygiene for Flutter

- `.gitignore`: add `.claude/worktrees/`.
- `.worktreeinclude`: list gitignored files every worktree needs, e.g. `.env`, `android/key.properties`,
  `android/app/google-services.json`, `ios/Runner/GoogleService-Info.plist` (only the ones that are actually gitignored).
- Every worktree is a fresh checkout: `pub get` + `build_runner` per worktree. That's disk and minutes.
  It's the price of isolation. Pay it.
- **One emulator/simulator, shared.** Only one agent may run `integration_test` at a time. Put that rule
  in the orchestrator instructions below. Unit/widget tests run in parallel fine.
- Settings: `"worktree": { "baseRef": "head" }` if implementers must branch from the feature branch the
  orchestrator is on (usually what you want). Default `"fresh"` branches from `main`.

### 2c. Orchestrator rules (put in `~/.claude/CLAUDE.md` or a user skill)

```md
## Orchestrating
You are the orchestrator (NGISA) for this repo. You do not write feature code yourself.
1. Size the task first (see Size below). Big tasks: spec → plan with superpowers (brainstorming, writing-plans). STOP and wait for my approval of the plan.
2. Split the approved plan into tasks. Each task lists the exact paths it may touch, the stack (e.g. flutter, php)
   and the test command, and that text goes into the worker's prompt. Task text starts `mode: quick|direct|plan <path>`. A repo can mix stacks: name the stack per task.
   Say what to verify, not how: "verify as the repo's CLAUDE.md says". Never write a raw runner (`flutter test`, `phpunit`, ...) in a task text.
   Tasks that depend on each other (one needs a file or change the other makes) or that touch the same file go to ONE worker as a single task text, tasks in order. Only independent tasks get separate workers.
   Combined task text: numbered steps in order, each with its own paths and checks, ONE `mode:` prefix for the whole text, one Branch/Base.
3. Spawn each parallel task. First look for a free warm worker: `claude agents --json --cwd .` lists sessions named `<repo>-warm-N`; free = state `done` or `idle` and not yet assigned in this run, and `worker-result .claude/worktrees/warm-N HEAD` prints `branch: warm/N` (a used worker is on its task branch, not free).
   Base ref: `git rev-parse HEAD` (full sha), the same ref goes to `worker-result` later.
   Free one: ONE `SendMessage {to: "<repo>-warm-N", notify_when_idle: true, message: "Branch: <name>. Base: <ref>. <task text>"}` (branch = clean name like `feat/<slug>`, never `worktree-*`; task text incl. `mode:`),
   then `ngisa-report mark <slug> spawn`, then `agent-wall.sh <slug> --attach <repo>-warm-N`, then refill: `agent-warm 1 >/dev/null 2>&1 &`.
   No free warm worker: cold path `agent-wall.sh <slug> implementer sonnet "Branch: <name>. Base: <ref>. <task text>"`, then a pure subscription `SendMessage {to: "<repo>-<slug>", notify_when_idle: true}`.
   Keep a list `slug -> warm-N` in your reply; never reuse a name on it this run (a finished worker shows `done` again); an idle notice maps to its slug through this list.
   Max 3 at once. Never open WezTerm windows, tabs or panes any other way.
   If you create a worker's worktree yourself with `git worktree add`, git skips `.worktreeinclude`: tell the worker in its task text
   to run `worktree-include` before anything else, so it gets `tool/setup.sh`.
   More tasks than free slots: keep a queue in your reply, start the next one each time a worker's idle notice arrives.
   You may not edit code yourself (your settings deny the code dirs), even for a one-line fix. Every code change goes to a worker.
   A bug report is a task too: repro, root cause and fix all go to a worker (say "repro first" in the task text). You never run tests, write repro files or edit code with shell commands (`ngisa-guard` blocks them).
   Stamps (silent, no chat line): once, at the message that gives the task (never on my OK, answers or follow-ups), before sizing, run `ngisa-report clear` (only when it starts a new plan, not for an extra request to a running worker), then `ngisa-report mark - request`.
   Chain a stamp onto the command it follows with `&&` when there is one (e.g. `agent-wall.sh ... && ngisa-report mark <slug> spawn`).
   `ngisa-report mark <slug> spawn` right after the send (warm) or the `agent-wall.sh` call (cold).
   `ngisa-report mark <slug> report` at the worker's idle notice.
   `ngisa-report mark <slug> decided` when I answer the ask, say merge, or when you start merging an ok branch with no ask (skip only if none of these happen).
   `ngisa-report mark <slug> pr` for every slug in that PR, after `agent-pr`. Do not print timing; I run `ngisa-report timing` myself.
4. When a worker's idle notice arrives (not a report), read the result (worker worktree: warm = `.claude/worktrees/warm-N`, N from its name; cold = the worktree whose `branch refs/heads/<name>` shows in `git worktree list --porcelain`): ONE call `worker-result <worker worktree> <ref>` (prints `commits: N`, `branch:`, then `--- body` and `--- stat` when N>0). I read the diff myself, so do not add your own review.
   Then record the row: `ngisa-report set <slug> --base <ref> --branch <branch> --state ok|fail|blocked`.
   `fail` when `checks:` shows a red result. `blocked` when `asks:` is not `none`, or when there is NO new commit since you assigned the task (`commits: 0`), or when the last commit has no `checks:` line (never `ok`) (worker waits on a decision: say so in one line; its pane has the question). Else `ok`. A worker still running is `--state working`.
   Findings and unverified items stay in the commit body and pane, not on the board. Ignore `ledger:`: do not show it; give its path only when I ask. An ask from `asks:` goes to me through `AskUserQuestion` as before.
5. Only one agent runs integration tests / the emulator at a time.
6. Merge task branches that finished ok (or that I allowed) into a local feature branch. Never push on your own.
   Do the merge in its own worktree (`git worktree add .claude/worktrees/integration -b <feature branch>`). Never check out or merge in the main checkout: it may hold my uncommitted work.
7. Report to me: paste the output of the last `ngisa-report set` unchanged (the board), then the PR link if any. Never retype or reword it.
   When a worker is `fail` or holds an ask: after the board add ONE line saying why (12 words at most), then ask me with the `AskUserQuestion` tool (see Ask). Never print the question again as text.
Quiet: my screen is for decisions, not a log. While workers run, say ONE line per event (spawn: `<slug> spawned.`).
  No board until a worker's idle notice arrives, no session ids or `claude attach` hints (the worker pane shows its work), and never mention
  hook blocks, retries or workarounds: fix them silently. Only asks, the board after an idle notice, and the PR link get more than one line.
Ask: when you need a decision, use the `AskUserQuestion` tool, never prose or a pasted card, then wait. It draws at the right width in my terminal.
  One question per decision (several in one call are fine). `header` = the task slug cut to 12 characters. The first option is the worker's recommendation, labelled `<answer> (Recommended)`; its description is the worker's `why`, or one short line of yours. Add one or two real alternatives (usually the opposite). Plain words, no abbreviations like y/n/rec. A red check with no worker ask: ask `Merge anyway?` with `No (Recommended)` first.
Size: judge every task and say it in one line (`tiny`, `small` or `big`, and why). "quick" from me means tiny.
  tiny = clear, 1-2 named files or one obvious bug: no brainstorming, no plan. One worker, `mode: quick`, exactly those paths.
  small = a few files, one concern: a 3-5 line plan in chat, wait for my OK, then `mode: quick` worker(s).
  big or unclear: brainstorming, writing-plans, plan file at `<repo>/.claude/plans/<slug>.md` (excluded from git), wait for my approval.
    Split the plan into independent groups (max 3 workers). Each task text starts `mode: plan <absolute plan path>` and names its task numbers.
    Tasks that depend on each other stay in one worker, in order. The worker runs subagent-driven-development (reviews inside); you add none.
  borderline (cannot tell): ask me `tiny, small or big?` with `AskUserQuestion` before anything else.
  `mode: direct` (full TDD) only when I ask for thorough or TDD. A tiny or small task never gets reviewers.
Relay: when I ask for something extra from a worker (e.g. "have it carve", "fix the lint"), SendMessage it to
  that worker (same session, same branch); a relay to a running or blocked worker carries `notify_when_idle: true`. For carve: tell it to run /carve; I answer its prompts with `claude attach <name>` (worker panes are read-only).
Pull request: only when I ask, from the local feature branch. Run
  `agent-pr "<title>" "<body>"` (draft PR; it pushes to the `upstream` remote). I approve each call.
  Never use `git push` or `gh`/`tea` directly. Branch name must not start with `worktree-`.
Style: caveman ultra in EVERY message to me (status, spawn notices, summaries, questions, report tables): drop articles, filler,
  pleasantries, hedging; fragments OK; abbreviate (DB, auth, config, req, res, fn); arrows for causality. Paths, branches, commands,
  session ids, quoted errors: exact. Code, commits, PR text, security warnings: normal.
  Not: "I have started the implementer worker. It is still running." Yes: "fix-x spawned."
  Long text too (findings, decisions): numbered fragments, never prose paragraphs.
  Not: "Because every birthdate is the 1st, the age step never runs." Yes: "1. All birthdates 1st -> dart:45-47 never runs. Add test? Rec yes."
  Boards are templates: paste them, do not rewrite them.
Never: merge to main, push or open a PR without my ask, publish, touch store/remote-config/signing,
  delete branches with unmerged work, or run `git worktree prune`, `git worktree remove` or `claude rm` on a worker's worktree or session while it runs (a worker lost its green fix that way).
```

### 2d. Hooks that make it a gate, not a suggestion

In `~/.claude/settings.json`, on top of the format + `Stop` gate from the verification playbook:

- **`PreToolUse` on `Bash`** blocking `git push.*(main|master)`, `git push --force`, `flutter pub publish`,
  `fastlane`, `firebase deploy`, anything touching remote config. Exit 2 with a reason. This is what
  actually keeps irreversible actions with you; the orchestrator prompt alone isn't enough.
- **`Notification`** hook (`agent_needs_input`, `agent_completed`) → desktop or phone notification, so you
  stop watching the screen.
- Pre-approve the boring commands (`fvm flutter test`, `melos *`, `dart format`, `git add/commit/diff/log`)
  in `permissions.allow`. Otherwise every background agent parks on "Needs input" and the parallelism is fake.

## 3. Daily flow

```bash
repo-tab ~/code/my_app        # this tab becomes the repo's NGISA (new tab if this one has panes). Talk only to this.
> /superpowers:brainstorming  … → spec. You read the spec.          # HUMAN GATE 1: intent
> writing-plans …             → plan + paths per task. You approve. # HUMAN GATE 2: plan
> "execute the plan per Orchestrating rules"
   → implementers run in the background in worktrees, gate-check runs on each one
   → you get one table + a draft PR link
# CI green + gate-check clean on all tasks → you review the PR summary and golden diffs  # HUMAN GATE 3
# You merge.                                                         # HUMAN GATE 4: irreversible
```

Several repos at once: `repo-tab ~/code/<repo>` for each (section 3b). There is no dedicated overview tab.
When you want one screen for every agent in every repo, run `claude agents` in any spare tab. `Space` peeks,
`Enter` attaches, `←` detaches, yellow rows are the ones waiting on you, PR badges show CI status.
Set `/config defaultToAgentsView=true` if you want `claude` to open there by default.

Note: agent view deletes Claude-created worktrees when you delete the session. Implementers commit, so
work survives; still, don't `Ctrl+X` twice on a row with uncommitted work.

## 3b. WezTerm: one window, one tab per repo

Layout: **one WezTerm window**. Every tab = **one repo**: its NGISA on the left, its agents
stacked on the right, max 3. (`claude agents` in a spare tab shows every agent in every repo;
`Ctrl+S` groups them by repo.)

```
┌ scanner ┬ owen-host-app ┬ work-app ┐
│ ngisa-scanner (Sonnet) │ scanner-cache   [Done]     │
│ you type ideas here    ├────────────────────────────┤
│                        │ scanner-sync    [Working]  │
│                        ├────────────────────────────┤
│                        │ scanner-ui      [Needs you]│
└────────────────────────┴────────────────────────────┘
```

### Why an NGISA per repo, not one global NGISA

One global NGISA across all repos can be made to work (start it in `~/code`, pass the repo to the
spawn script), but don't:
- **It plans blind.** A session loads `CLAUDE.md`, project settings and skills from the folder it starts
  in. An NGISA in `~/code` doesn't load the scanner's `CLAUDE.md` or Definition of done while it writes
  the plan, and the plan is the step that matters most.
- **One context for everything.** Specs, plans and findings for three repos pile into one
  conversation, it compacts sooner, and compaction drops plan details first.
- **One failure stops all repos.** A stuck permission prompt or a usage-limit wait in the NGISA
  stalls every repo's work.

An NGISA per repo tab fixes all three, and "global" is still true where it counts: the agents,
rules, hooks and scripts are user-level (section 2), and `claude agents` shows everything at once.

### Usage limits are global, not per repo

All repos draw on the same Max allowance. So the cap is **3 agents per repo tab, and about 4–5 running
in total**. Two repos at full speed already burns ~6× a single session. Run heavy work in one repo at a
time; keep the others on planning or review.

### Scripts (both in `~/bin`, both user-level)

`repo-tab`: turn the current tab into the repo's NGISA (a new tab if the current one has several panes). The version in `lab-quickstart.md` step 3 is the current one.

```bash
#!/usr/bin/env bash
# usage: repo-tab ~/code/scanner
set -euo pipefail
dir=$(cd "$1" && pwd); name=$(basename "$dir")
[[ -x "$dir/tool/ci_local.sh" ]] || echo "warning: $name has no tool/ci_local.sh, run agent-init there first" >&2
pane=$(wezterm cli spawn --cwd "$dir" -- claude --name "ngisa-$name" --model sonnet)
wezterm cli set-tab-title --pane-id "$pane" "$name"
```

`agent-wall.sh`: the only thing an NGISA calls to spawn an agent. It splits *the NGISA's own tab*,
so agents always land next to the NGISA that owns them.

```bash
#!/usr/bin/env bash
# usage: agent-wall.sh <task> <agent-type> <model> "<prompt>"   (called by an NGISA, from its repo)
set -euo pipefail
task=$1 agent=$2 model=$3 prompt=$4
repo=$(basename "$(git rev-parse --show-toplevel)")
name="$repo-$task"
me=${WEZTERM_PANE:?run from inside WezTerm}           # the NGISA's pane, inherited by its shell
json=$(wezterm cli list --format json)
tab=$(jq --argjson p "$me" '.[] | select(.pane_id==$p) | .tab_id' <<<"$json")
mapfile -t others < <(jq --argjson t "$tab" --argjson p "$me" \
  '.[] | select(.tab_id==$t and .pane_id!=$p) | .pane_id' <<<"$json")
(( ${#others[@]} < 3 )) || { echo "tab full: 3 agents already shown for $repo; wait for one to finish" >&2; exit 1; }

claude --bg --name "$name" --agent "$agent" --model "$model" \
  "$prompt"

if (( ${#others[@]} == 0 )); then
  wezterm cli split-pane --pane-id "$me" --right --percent 55 -- agent-view "$name"
else
  # equal heights: the last pane holds 1/n of the column, the new one takes n/(n+1) of it
  n=${#others[@]}
  wezterm cli split-pane --pane-id "${others[-1]}" --bottom --percent $(( 100 * n / (n + 1) )) -- agent-view "$name"
fi
```

Notes:
- Agent names are `<repo>-<task>`, so two repos can both have a `cache` task without colliding, and
  each agent reports to its own repo's NGISA (`@ngisa-scanner`).
- Each agent is a background session started from the repo, so its worktree is in that repo's
  `.claude/worktrees/`. Repos never share worktrees.
- Panes are read-only views (`agent-view` shows status only: the name, `working` / `needs you` / `done` with the time, one dim line (the branch) and one result line (the commit); a `quiet for Nm` line after 2 minutes without a move, and a red line if the NGISA never got the result; no input box; `AGENT_VIEW_DETAIL=1` brings back the full view). The NGISA's status line shows a `workers` roster (`ngisa-statusline`, wired in by `repo-tab`). To answer a worker that shows `needs you`, `claude attach <name>` in a spare pane. Closing a pane never stops the agent; `wezterm cli kill-pane` when done.
- The "tab full" check counts panes, not running agents. If you closed a pane early, the agent still
  runs and still counts against your quota; check `claude agents`.
- Check `wezterm cli list --format json` on your version prints `tab_id`; it should.

### NGISA rules (replace steps 3 and 4 in the Orchestrating block)

```md
3. Spawn each parallel task. First look for a free warm worker: `claude agents --json --cwd .` lists sessions named `<repo>-warm-N`; free = state `done` or `idle` and not yet assigned in this run, and `worker-result .claude/worktrees/warm-N HEAD` prints `branch: warm/N` (a used worker is on its task branch, not free).
   Base ref: `git rev-parse HEAD` (full sha), the same ref goes to `worker-result` later.
   Free one: ONE `SendMessage {to: "<repo>-warm-N", notify_when_idle: true, message: "Branch: <name>. Base: <ref>. <task text>"}` (branch = clean name like `feat/<slug>`, never `worktree-*`; task text incl. `mode:`),
   then `ngisa-report mark <slug> spawn`, then `agent-wall.sh <slug> --attach <repo>-warm-N`, then refill: `agent-warm 1 >/dev/null 2>&1 &`.
   No free warm worker: cold path `agent-wall.sh <slug> implementer sonnet "Branch: <name>. Base: <ref>. <task text>"`, then a pure subscription `SendMessage {to: "<repo>-<slug>", notify_when_idle: true}`.
   Keep a list `slug -> warm-N` in your reply; never reuse a name on it this run (a finished worker shows `done` again); an idle notice maps to its slug through this list.
   Max 3 at once. Never open WezTerm windows, tabs or panes any other way.
   If you create a worker's worktree yourself with `git worktree add`, git skips `.worktreeinclude`: tell the worker in its task text
   to run `worktree-include` before anything else, so it gets `tool/setup.sh`.
   More tasks than free slots: keep a queue in your reply, start the next one each time a worker's idle notice arrives.
   You may not edit code yourself (your settings deny the code dirs), even for a one-line fix. Every code change goes to a worker.
   A bug report is a task too: repro, root cause and fix all go to a worker (say "repro first" in the task text). You never run tests, write repro files or edit code with shell commands (`ngisa-guard` blocks them).
   Stamps (silent, no chat line): once, at the message that gives the task (never on my OK, answers or follow-ups), before sizing, run `ngisa-report clear` (only when it starts a new plan, not for an extra request to a running worker), then `ngisa-report mark - request`.
   Chain a stamp onto the command it follows with `&&` when there is one (e.g. `agent-wall.sh ... && ngisa-report mark <slug> spawn`).
   `ngisa-report mark <slug> spawn` right after the send (warm) or the `agent-wall.sh` call (cold).
   `ngisa-report mark <slug> report` at the worker's idle notice.
   `ngisa-report mark <slug> decided` when I answer the ask, say merge, or when you start merging an ok branch with no ask (skip only if none of these happen).
   `ngisa-report mark <slug> pr` for every slug in that PR, after `agent-pr`. Do not print timing; I run `ngisa-report timing` myself.
4. When a worker's idle notice arrives (not a report), read the result (worker worktree: warm = `.claude/worktrees/warm-N`, N from its name; cold = the worktree whose `branch refs/heads/<name>` shows in `git worktree list --porcelain`): ONE call `worker-result <worker worktree> <ref>` (prints `commits: N`, `branch:`, then `--- body` and `--- stat` when N>0). I read the diff myself, so do not add your own review.
   Then record the row: `ngisa-report set <slug> --base <ref> --branch <branch> --state ok|fail|blocked`.
   `fail` when `checks:` shows a red result. `blocked` when `asks:` is not `none`, or when there is NO new commit since you assigned the task (`commits: 0`), or when the last commit has no `checks:` line (never `ok`) (worker waits on a decision: say so in one line; its pane has the question). Else `ok`. A worker still running is `--state working`.
   Findings and unverified items stay in the commit body and pane, not on the board. Ignore `ledger:`: do not show it; give its path only when I ask. An ask from `asks:` goes to me through `AskUserQuestion` as before.
```

Allow exactly `"Bash(agent-wall.sh:*)"` in `~/.claude/settings.json`. Don't allow `Bash(wezterm cli:*)`.

Caveman ultra for the NGISA and the workers' reports comes from a `SessionStart` + `UserPromptSubmit` hook that runs `caveman-ultra-hook` (it adds context; nothing is blocked), plus the same rule in the NGISA's system prompt (`repo-tab` passes `--append-system-prompt`), because a one-line reminder alone was not enough for Opus. Code, commits and PR text stay normal. The lab version of these rules, which routes PRs through `agent-pr`, is in `lab-quickstart.md`.

The board is a fixed template, not free prose. The NGISA records each worker result (read from its last commit by `worker-result`) with `ngisa-report set` (script block in `lab-quickstart.md`) and pastes its output as the final report: one line per task with a state symbol, findings (`!`) and asks (`?`, with a recommendation) inline under their row, unverified items and a legend (`✓ ok  ✗ fail  ▶ working  ? asks you  ! finding`). There is no extra pane for it: the board lives in the chat, next to the `workers` roster in the status line. A decision comes through the native `AskUserQuestion` tool, not a pasted card. The worker's report is its commit body: the `checks:`, `unverified:` and `asks:` lines (plus `ledger:` in plan mode) and one short final line, so the NGISA can map them to the flags and a missing `checks:` line shows at once (it is never `ok`).

Don't run NGISA sessions or agents in `bypassPermissions`: in that mode incoming reports from other sessions
are held for approval instead of delivered.

Agent teams' split-pane mode only drives tmux or iTerm2, not WezTerm, so it can't produce this layout.

## 4. Where you stay in the loop (non-negotiable)

1. **Spec / acceptance criteria.** Intent. Agents can't know it.
2. **Plan approval, including the task split.** A bad split = merge conflicts × N agents.
3. **A failed `gate-check`.** You decide: keep the change (the task asked for it) or send the worker back.
4. **Merge to main, releases, pub.dev, store, remote config, signing, secrets.** Hook-blocked, so only you can.
5. **Anything handling card/PII data.** Read it yourself every time.
6. **Device feel** (camera, scan UX). Once per feature at the end.

Everything else (format, analyze, tests, routing, per-task `gate-check`) is the machine's job.

## 5. Max plan: the limits will bite

- Every background agent, subagent and workflow agent draws on the **same** 5-hour and weekly allowance.
  The docs are blunt: 10 parallel agents burn quota ~10× as fast. Agent teams ~7× a single session.
- Sonnet for the NGISA and for implementers, Opus only if you ask for it. Haiku for mechanical sweeps. `repo-tab` pins `--model sonnet` for the NGISA (Sonnet is faster and the NGISA only plans and dispatches; whether it is enough for big plans is still unproven). Pin `model: sonnet` in the agent file too.
- **Cap parallelism at 3** to start. Raise it only if `/usage` shows headroom at the end of a week.
- Turn on `autoContinueAtUsageLimit` so a run waits for reset instead of failing mid-task.
- Use `/usage` (attribution view) weekly to see which agents eat the quota.
- Expect to hit the weekly limit if you run 3 agents all day, every day. That's the real ceiling on
  "many agents", not the tooling.

## 6. When parallel is the wrong call

- Tasks touching the same files (shared models, `pubspec.yaml`, routing tables, generated code). Chain them.
- Small features (< ~3 tasks). One session with superpowers' `subagent-driven-development` is faster.
- When your NGISA sessions aren't in place yet. You'll drown in review.

## 7. Measure it (ties to the project hypothesis)

The project bets that parallel worktree agents beat one long-context agent on big tasks. Test it:
run the next two comparable features one each way and log per feature:
`wall-clock | your minutes | interventions (intent / plan-wrong / merge-conflict / test-gap / taste / irreversible / agent-error) | gate-check FAILs | CI red after merge | % of 5h window used`.
If "merge-conflict" and "plan-wrong" dominate on the parallel run, the task split is the problem, not the agents.

## Roll-out order

1. Verification hooks + `ci_local.sh` (from the previous playbook) if not done.
2. `implementer.md` + `.worktreeinclude` + `.gitignore`.
3. Orchestrator rules + `PreToolUse` block hook + permission allowlist.
4. One feature through the flow with max 2 parallel implementers. Fix what breaks.
5. Then 3 parallel, then open a second repo tab.
6. Agent teams: only for a review or debugging session, to see if it's worth it. Not for code.

### Sizes and plan mode (2026-10-16)
- Why: the user wants one input (the NGISA) and only to watch, and the review cost should match the task. The NGISA now sizes every task in one line: tiny (no brainstorming, no plan, one worker), small (short plan in chat), big or unclear (brainstorming, writing-plans, approved plan file). A borderline task is asked to the user first.
- A worker runs `mode: direct` (TDD, checks, no reviewers) or `mode: plan <path>`: `superpowers:subagent-driven-development` on the plan, with a task review after each task and a final branch review. It follows the skill's rulings rule: it decides conflicts itself and writes each as a ruling in its ledger, and stops only for the skill's four cases (destructive, security-sensitive, a side effect outside the worktree, a plan too broken to follow). No merge, push or PR from the worker.
- The ledger is not on the board; the commit body has a `ledger:` line, and the NGISA gives the path only on request.
- Checked 2026-10-16: a background `--agent implementer` session can dispatch subagents with the Agent tool.

### Gate removed (2026-10-16)
- `gate-check`, `tool/ci_local.sh` and `tool/known_failures.txt` are gone from the kit. Reason: on a real repo with old red tests the full gate was red for every worker (about 11 minutes per run), so good work was marked `fail` and the NGISA spawned an unrequested worker to fix `main`. The user reads the diff anyway.
- Workers now run the checks the repo's `CLAUDE.md` names (format, analyze, tests) and report what they ran in the `gate:` line. `agent-init` still writes `tool/setup.sh` (dependency install for a fresh worktree) and `.worktreeinclude`. Task text says "verify as the repo's CLAUDE.md says", never a raw runner.
- Sections above that mention `gate-check`, `ci_local.sh`, a Stop gate or a CI-green merge describe the earlier design; the implementer and orchestrating blocks in 2a and 2c are current.

### Native asks (2026-10-16)
- Decisions no longer come as a pasted `ngisa-report ask` card: the NGISA uses the `AskUserQuestion` tool (drawn by the terminal at any width). The first option is the worker's recommendation labelled `(Recommended)`, with its `why` as the description. `ngisa-report ask` is removed; `--ask` stays so the board shows the `?` line. Older blocks in this doc that mention `ngisa-report ask` describe the previous design.

### Speed parity (2026-10-16)
- The NGISA stamps stages silently with `ngisa-report mark <slug> request|spawn|report|decided|pr`; `ngisa-report clear` moved to the task message, before the `request` stamp. The user runs `ngisa-report timing` to read the stage times.
- Baseline protocol (NGISA vs plain Claude): `docs/runs/2026-10-16-baseline-protocol.md`.

### Warm workers (2026-10-16)
- Why: the baseline run showed each worker paid 30-60s plain Claude never pays (worktree, `worktree-include`, `tool/setup.sh`, looking up `SendMessage`, writing the 7-line report). Spec `docs/superpowers/specs/2026-10-16-warm-workers-design.md`, spike `docs/runs/2026-10-16-warm-worker-spike.md` (about 50s saved on one task).
- Pool: `agent-warm [n]` (default 2, max 3) starts idle `<repo>-warm-N` implementer sessions (`--bg --agent implementer --model sonnet`) that create `.claude/worktrees/warm-N` (branch `warm/N`) from HEAD, run `worktree-include` and `./tool/setup.sh`, and stop at `warm ready`. `repo-tab` starts the pool in the background when the tab opens; `NGISA_WARM=0` turns it off, another number sets the size. The NGISA refills with `agent-warm 1` after it uses one.
- Assign: one `SendMessage {to: <repo>-warm-N, notify_when_idle: true, message: "Branch: <name>. Base: <sha>. <task text>"}` (`<sha>` = `git rev-parse HEAD`), then `agent-wall.sh <slug> --attach <repo>-warm-N`, which only opens the pane for the running session. A warm worker is single-use: free = session `done` or `idle` AND its worktree still on branch `warm/N` (`worker-result .claude/worktrees/warm-N HEAD` prints `branch: warm/N`); `agent-warm` tops the pool up to n free workers with a monotonic index. The worker runs `git checkout -B <name> <base>` in its warm worktree, skips setup, and runs `./tool/setup.sh` once only if a test or analyze run fails on missing packages. No free warm worker: cold start `agent-wall.sh <slug> implementer sonnet "Branch: <name>. Base: <sha>. <task text>"` (the task carries Branch/Base too), then a pure `notify_when_idle` subscription; the NGISA finds the cold worker's worktree with `git worktree list --porcelain`.
- No worker report: the worker sends no message back. It ends with a commit whose body has `checks:`, `unverified:`, `asks:` lines (plus `ledger:` in plan mode) and one short final line. When the idle notice arrives the NGISA runs `worker-result <worktree> <base>` (commit count, branch, commit body, diff stat) and records the row with `ngisa-report set`. No new commit, `asks:` not `none`, or no `checks:` line in the last commit means `blocked`; a red `checks:` means `fail`.
- `Bash(git -C:*)` is deliberately not allowed: it would bypass the `git push` deny. `worker-result` wraps the `git -C` reads instead.
- Caveat on the evidence: the ~50s saving is one sample on different-sized tasks (11 vs 14 tests), and plain Claude's T3 total (1m27s) was still lower than the warm NGISA's 1m53s in the spike.
- This replaces the 'send your final report to @ngisa-<repo>' flow and the seven-line final message described in sections above.

### Lean mode (2026-10-17)
- Tiny and small tasks now go to a worker with `mode: quick`: only the change and tests the task text lists, no extra test cases, no red-first demonstration, each listed check run once. `mode: direct` (full TDD) only when the user asks for thorough or TDD; big stays `mode: plan <path>`.
- Evidence: `docs/runs/2026-10-17-options-abc-tiny.md`, a lean instruction cut the worker from 1m25s to 47s on a tiny task with identical code and tests. Expected result: about 20% over plain Claude on a tiny task (one run). Quality on harder tasks is unproven.
