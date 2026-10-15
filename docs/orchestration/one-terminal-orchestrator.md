# One terminal, one orchestrator, many agents

Bottom line: don't build this, and don't install a third-party tmux manager. Claude Code now ships
everything you described. Your "NGISA" is **one Opus orchestrator session** that plans, then dispatches
**worktree-isolated Sonnet implementer subagents** in the background and an **Opus reviewer** on each result.
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
| `implementer.md`, `reviewer.md` | `~/.claude/agents/` | once, all repos |
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
description: Implements one task from an approved plan in its own worktree, TDD, then commits on its branch
model: sonnet
isolation: worktree
background: true
---
You get ONE task from an approved plan. Work only inside your worktree.
The task text gives the paths you may touch, the stack and the test command. Anything missing: use the repo contract below. The repo's CLAUDE.md has the stack conventions; follow them. The git, gate and scope rules below always win.
1. Setup: run `./tool/setup.sh`. No such file: run the setup commands in CLAUDE.md. Neither exists: stop and report, do not guess a stack.
2. TDD: write the failing test, show it red, make it green. Use the task's test command, else the one in CLAUDE.md or `tool/ci_local.sh`.
3. `./tool/ci_local.sh` must exit 0 before you stop. Never edit `tool/ci_local.sh` or `tool/setup.sh`. Never skip, delete or loosen tests, lint rules or analyzer config to get green. If setup or the gate cannot run, or fails for a reason outside your task, stop and report the exact error. A red gate in the report is fine; a faked green is not.
4. Commit on your branch. Never push, never merge, never touch main.
5. Final message, exactly: branch name, files changed, test command + result, anything you could NOT verify and why.
Do not edit files outside the task's listed paths. If you must, stop and say so.
```

`~/.claude/agents/reviewer.md`

```markdown
---
name: reviewer
description: Reviews one implementer branch against the plan task and the spec. Read-only.
model: opus
tools: Read, Grep, Glob, Bash
---
Diff the given branch against its base. Check: does it do the task as written, are tests real
(would they fail without the change), any edits outside the task's paths, logging or leaking of
sensitive data (PII, card data, tokens, secrets), anything irreversible.
Gate integrity: compare `tool/ci_local.sh` and `tool/setup.sh` in the branch's worktree with the copies in the
main checkout (`$(git rev-parse --path-format=absolute --git-common-dir)/..`). In a lab these files are untracked,
so the diff will not show them. Any difference is a BLOCK unless the task asked for it. Also BLOCK on weakened
checks: tests removed or skipped, assertions relaxed, lint or analyzer config loosened, new ignore/suppress comments.
Output: APPROVE or BLOCK, then a numbered list of findings with file:line.
Do not edit files.
```

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
1. Spec → plan with superpowers (brainstorming, writing-plans). STOP and wait for my approval of the plan.
2. Split the approved plan into tasks. Each task lists the exact paths it may touch, the stack (e.g. flutter, php)
   and the test command, and that text goes into the worker's prompt. A repo can mix stacks: name the stack per task.
   Two tasks that touch the same file are NOT parallel; chain them.
3. Dispatch parallel tasks to `implementer` (max 3 at once). Chain dependent ones.
4. For each finished task, dispatch `reviewer` on its branch. BLOCK → send findings back to a new implementer on that branch. Max 2 rounds, then escalate to me.
5. Only one agent runs integration tests / the emulator at a time.
6. Merge APPROVED task branches into the feature branch locally, run ./tool/ci_local.sh, push the feature branch, open a DRAFT PR.
7. Report to me: one table (task | branch | reviewer verdict | tests | unverified items), plus the PR link.
Quick task: if I say "quick" and it is one small edit in 1-2 named files, skip brainstorming and the plan.
  Spawn ONE implementer with exactly those paths, then run the reviewer as usual. Anything bigger: say it needs a plan.
Relay: when I ask for something extra from a worker (e.g. "have it carve", "fix the lint"), SendMessage it to
  that worker (same session, same branch). For carve: tell it to run /carve; I answer its prompts in its pane.
Style: talk in caveman ultra (a hook reminds you). Code, commits, PR text, security warnings: normal.
Never: merge to main, force-push, publish, touch store/remote-config/signing, delete branches with unmerged work.
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
repo-tab ~/code/my_app        # new tab: the repo's NGISA. Talk only to this.
> /superpowers:brainstorming  … → spec. You read the spec.          # HUMAN GATE 1: intent
> writing-plans …             → plan + paths per task. You approve. # HUMAN GATE 2: plan
> "execute the plan per Orchestrating rules"
   → implementers run in the background in worktrees, reviewer checks each one
   → you get one table + a draft PR link
# CI green + reviewer APPROVE on all tasks → you review the PR summary and golden diffs  # HUMAN GATE 3
# You merge.                                                         # HUMAN GATE 4: irreversible
```

Several repos at once: `repo-tab ~/code/<repo>` for each (section 3b). The overview tab
(`claude agents`) is your single screen for every agent in every repo. `Space` peeks,
`Enter` attaches, `←` detaches, yellow rows are the ones waiting on you, PR badges show CI status.
Set `/config defaultToAgentsView=true` if you want `claude` to open there by default.

Note: agent view deletes Claude-created worktrees when you delete the session. Implementers commit, so
work survives; still, don't `Ctrl+X` twice on a row with uncommitted work.

## 3b. WezTerm: one window, one tab per repo

Layout: **one WezTerm window**. Tab 1 = `overview` (`claude agents`, every agent in every repo;
`Ctrl+S` groups them by repo). Every other tab = **one repo**: its NGISA on the left, its agents
stacked on the right, max 3.

```
┌ overview ┬ scanner ┬ owen-host-app ┬ work-app ┐
│ ngisa-scanner (Opus)   │ scanner-cache   [Done]     │
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
- **One context for everything.** Specs, plans and reviewer verdicts for three repos pile into one
  conversation, it compacts sooner, and compaction drops plan details first.
- **One failure stops all repos.** A stuck permission prompt or a usage-limit wait in the NGISA
  stalls every repo's work.

An NGISA per repo tab fixes all three, and "global" is still true where it counts: the agents,
rules, hooks and scripts are user-level (section 2), and the overview tab shows everything at once.

### Usage limits are global, not per repo

All repos draw on the same Max allowance. So the cap is **3 agents per repo tab, and about 4–5 running
in total**. Two repos at full speed already burns ~6× a single session. Run heavy work in one repo at a
time; keep the others on planning or review.

### Scripts (both in `~/bin`, both user-level)

`repo-tab`: open a repo as a new tab in the current window with its NGISA.

```bash
#!/usr/bin/env bash
# usage: repo-tab ~/code/scanner
set -euo pipefail
dir=$(cd "$1" && pwd); name=$(basename "$dir")
[[ -x "$dir/tool/ci_local.sh" ]] || echo "warning: $name has no tool/ci_local.sh, run agent-init there first" >&2
pane=$(wezterm cli spawn --cwd "$dir" -- claude --name "ngisa-$name" --model opus)
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
  "$prompt  When finished, send your final report to @ngisa-$repo with SendMessage."

if (( ${#others[@]} == 0 )); then
  wezterm cli split-pane --pane-id "$me" --right --percent 55 -- claude attach "$name"
else
  wezterm cli split-pane --pane-id "${others[-1]}" --bottom -- claude attach "$name"
fi
```

Notes:
- Agent names are `<repo>-<task>`, so two repos can both have a `cache` task without colliding, and
  each agent reports to its own repo's NGISA (`@ngisa-scanner`).
- Each agent is a background session started from the repo, so its worktree is in that repo's
  `.claude/worktrees/`. Repos never share worktrees.
- Panes are viewers (`claude attach`). Closing one never stops the agent; `wezterm cli kill-pane` when done.
- The "tab full" check counts panes, not running agents. If you closed a pane early, the agent still
  runs and still counts against your quota; check the overview tab.
- Check `wezterm cli list --format json` on your version prints `tab_id`; it should.

### NGISA rules (replace steps 3 and 4 in the Orchestrating block)

```md
3. Spawn each parallel task with `agent-wall.sh <task-slug> implementer sonnet "<task text>"`.
   Max 3 at once. Never open WezTerm windows, tabs or panes any other way.
4. When a worker's report arrives, run the `reviewer` subagent (in-process) on its branch.
   BLOCK -> message that worker with the findings (same session, same branch). Max 2 rounds, then ask me.
```

Allow exactly `"Bash(agent-wall.sh:*)"` in `~/.claude/settings.json`. Don't allow `Bash(wezterm cli:*)`.

Caveman ultra for the NGISA and the workers' reports comes from a `SessionStart` + `UserPromptSubmit` hook that runs `caveman-ultra-hook` (it adds context; nothing is blocked). Code, commits and PR text stay normal. The lab version of these rules, which routes PRs through `agent-pr`, is in `lab-quickstart.md`.

Don't run NGISA sessions or agents in `bypassPermissions`: in that mode incoming reports from other sessions
are held for approval instead of delivered.

Agent teams' split-pane mode only drives tmux or iTerm2, not WezTerm, so it can't produce this layout.

## 4. Where you stay in the loop (non-negotiable)

1. **Spec / acceptance criteria.** Intent. Agents can't know it.
2. **Plan approval, including the task split.** A bad split = merge conflicts × N agents.
3. **Reviewer vs implementer disagreement after 2 rounds.** You decide.
4. **Merge to main, releases, pub.dev, store, remote config, signing, secrets.** Hook-blocked, so only you can.
5. **Anything handling card/PII data.** Read it yourself every time.
6. **Device feel** (camera, scan UX). Once per feature at the end.

Everything else (format, analyze, tests, routing, per-task review) is the machine's job.

## 5. Max plan: the limits will bite

- Every background agent, subagent and workflow agent draws on the **same** 5-hour and weekly allowance.
  The docs are blunt: 10 parallel agents burn quota ~10× as fast. Agent teams ~7× a single session.
- Opus only for orchestrator + reviewer. Sonnet for implementers. Haiku for mechanical sweeps.
  Never let implementers inherit an Opus orchestrator's model; pin `model: sonnet` in the agent file.
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
`wall-clock | your minutes | interventions (intent / plan-wrong / merge-conflict / test-gap / taste / irreversible / agent-error) | reviewer BLOCKs | CI red after merge | % of 5h window used`.
If "merge-conflict" and "plan-wrong" dominate on the parallel run, the task split is the problem, not the agents.

## Roll-out order

1. Verification hooks + `ci_local.sh` (from the previous playbook) if not done.
2. `implementer.md` + `reviewer.md` + `.worktreeinclude` + `.gitignore`.
3. Orchestrator rules + `PreToolUse` block hook + permission allowlist.
4. One feature through the flow with max 2 parallel implementers. Fix what breaks.
5. Then 3 parallel, then open a second repo tab.
6. Agent teams: only for a review or debugging session, to see if it's worth it. Not for code.
