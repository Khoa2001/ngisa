# Lab quickstart (copy-paste)

Run every block in WezTerm, in order. Replace `~/Projects/vn_citizen_id_scan` in step 4 with the repo you
want to test on. Nothing here touches `~/.claude` or your real repo.

## Step 1. Tools

```bash
brew install jq            # the scripts read WezTerm's pane list with jq
mkdir -p ~/bin ~/lab
grep -q 'HOME/bin' ~/.zshrc || echo 'export PATH="$HOME/bin:$PATH"' >> ~/.zshrc
source ~/.zshrc
```

## Step 2. Fill the kit

```bash
KIT=/Users/khoamai/Projects/my_proj/ngisa
mkdir -p $KIT/agents

cat > $KIT/agents/implementer.md <<'EOF'
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
EOF

cat > $KIT/agents/reviewer.md <<'EOF'
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
EOF

cat > $KIT/orchestrating.md <<'EOF'
## Orchestrating
You are the orchestrator (NGISA) for this repo. You do not write feature code yourself.
1. Spec → plan with superpowers (brainstorming, writing-plans). STOP and wait for my approval of the plan.
2. Split the approved plan into tasks. Each task lists the exact paths it may touch, the stack (e.g. flutter, php)
   and the test command, and that text goes into the worker's prompt. A repo can mix stacks: name the stack per task.
   Two tasks that touch the same file are NOT parallel; chain them.
3. Spawn each parallel task with `agent-wall.sh <task-slug> implementer sonnet "<task text>"`.
   Max 3 at once. Never open WezTerm windows, tabs or panes any other way.
   More tasks than free slots: keep a queue in your reply, start the next one each time a worker's report arrives.
   You may not edit code yourself (your settings deny the code dirs), even for a one-line fix. Every code change goes to a worker.
4. When a worker's report arrives, run the `reviewer` subagent (in-process) on its branch.
   BLOCK -> message that worker with the findings (same session, same branch). Max 2 rounds, then ask me.
5. Only one agent runs integration tests / the emulator at a time.
6. Merge APPROVED task branches into a local feature branch and run ./tool/ci_local.sh. This is a lab: never push on your own.
7. Report to me: one table (task | branch | reviewer verdict | tests | unverified items).
Quick task: if I say "quick" and it is one small edit in 1-2 named files, skip brainstorming and the plan.
  Spawn ONE implementer with exactly those paths, then run the reviewer as usual. Anything bigger: say it needs a plan.
Relay: when I ask for something extra from a worker (e.g. "have it carve", "fix the lint"), SendMessage it to
  that worker (same session, same branch). For carve: tell it to run /carve; I answer its prompts in its pane.
Pull request: only when I ask, from the local feature branch, after ci_local.sh is green. Run
  `agent-pr "<title>" "<body>"` (draft PR; it pushes to the `upstream` remote). I approve each call.
  Never use `git push` or `gh`/`tea` directly. Branch name must not start with `worktree-`.
Style: talk in caveman ultra (a hook reminds you). Code, commits, PR text, security warnings: normal.
Never: merge to main, push or open a PR without my ask, publish, touch store/remote-config/signing,
  delete branches with unmerged work.
EOF

cat > $KIT/settings.local.json <<'EOF'
{
  "permissions": {
    "allow": [
      "Bash(fvm flutter test:*)", "Bash(flutter test:*)", "Bash(fvm flutter pub get)", "Bash(flutter pub get)",
      "Bash(melos:*)", "Bash(dart format:*)", "Bash(dart run build_runner:*)", "Bash(fvm dart run build_runner:*)",
      "Bash(composer install:*)", "Bash(composer run-script:*)", "Bash(vendor/bin/phpunit:*)",
      "Bash(vendor/bin/pint:*)", "Bash(vendor/bin/phpstan:*)",
      "Bash(./tool/setup.sh)", "Bash(./tool/ci_local.sh)",
      "Bash(git status)", "Bash(git diff:*)", "Bash(git log:*)", "Bash(git add:*)", "Bash(git commit:*)",
      "Bash(git merge:*)", "Bash(git checkout:*)", "Bash(agent-wall.sh:*)"
    ],
    "deny": [
      "Bash(git push:*)", "Bash(flutter pub publish:*)", "Bash(dart pub publish:*)",
      "Bash(fastlane:*)", "Bash(firebase deploy:*)",
      "Edit(tool/ci_local.sh)", "Edit(tool/setup.sh)"
    ]
  },
  "hooks": {
    "SessionStart": [{ "hooks": [{ "type": "command", "command": "caveman-ultra-hook" }] }],
    "UserPromptSubmit": [{ "hooks": [{ "type": "command", "command": "caveman-ultra-hook" }] }]
  }
}
EOF

# NGISA-only settings: the NGISA can write plans/docs but not code (workers don't load this file).
# This is the Flutter default. agent-init writes a per-repo .claude/ngisa-settings.json from the detected stack,
# and repo-tab prefers that one.
cat > $KIT/ngisa-settings.json <<'EOF'
{
  "permissions": {
    "deny": [
      "Edit(lib/**)", "Edit(test/**)", "Edit(integration_test/**)",
      "Edit(android/**)", "Edit(ios/**)"
    ]
  }
}
EOF

ls -R $KIT     # expect: agents/implementer.md agents/reviewer.md orchestrating.md settings.local.json ngisa-settings.json
```

## Step 3. Install the scripts

```bash
cat > ~/bin/agent-init <<'EOF'
#!/usr/bin/env bash
# run once in a repo root: detects the stack(s) and adds the per-repo files if missing
# (tool/setup.sh, tool/ci_local.sh, .worktreeinclude, .claude/ngisa-settings.json, a .gitignore line)
set -euo pipefail
mkdir -p tool .claude
grep -qxF '.claude/worktrees/' .gitignore 2>/dev/null || echo '.claude/worktrees/' >> .gitignore

# one "kind:dir" per line. A manifest at the repo root wins; otherwise look one level down.
stacks=""
detect() {  # kind manifest...
  local kind=$1 m d; shift
  for m in "$@"; do [[ -f $m ]] && { stacks="$stacks$kind:.
"; return; }; done
  for d in */; do
    d=${d%/}
    case $d in vendor|node_modules|build) continue;; esac
    for m in "$@"; do [[ -f $d/$m ]] && { stacks="$stacks$kind:$d
"; break; }; done
  done
  return 0
}
detect flutter pubspec.yaml melos.yaml
detect php composer.json

setup_block() {  # kind dir
  case $1 in
    flutter) sed "s|__DIR__|$2|g" <<'B'
( cd "__DIR__"
  if command -v fvm >/dev/null; then F="fvm flutter"; D="fvm dart"; else F=flutter; D=dart; fi
  if [[ -f melos.yaml ]]; then melos bootstrap; else $F pub get; fi
  if grep -q build_runner pubspec.yaml 2>/dev/null; then $D run build_runner build -d; fi )
B
    ;;
    php) sed "s|__DIR__|$2|g" <<'B'
( cd "__DIR__" && composer install --no-interaction --prefer-dist )
B
    ;;
  esac
}
ci_block() {  # kind dir
  case $1 in
    flutter) sed "s|__DIR__|$2|g" <<'B'
( cd "__DIR__"
  if command -v fvm >/dev/null; then F="fvm flutter"; D="fvm dart"; else F=flutter; D=dart; fi
  if [[ -f melos.yaml ]]; then
    melos exec -- $D format . --set-exit-if-changed && melos analyze && melos test
  else
    $D format . --set-exit-if-changed && $F analyze && $F test
  fi )
B
    ;;
    php) sed "s|__DIR__|$2|g" <<'B'
( cd "__DIR__"
  if [[ -x vendor/bin/pint ]]; then vendor/bin/pint --test; fi
  if [[ -x vendor/bin/php-cs-fixer ]]; then vendor/bin/php-cs-fixer fix --dry-run --diff; fi
  if [[ -x vendor/bin/phpstan ]]; then vendor/bin/phpstan analyse --no-progress; fi
  if grep -q '"test"' composer.json; then composer run-script test
  elif [[ -x vendor/bin/phpunit ]]; then vendor/bin/phpunit
  else echo "no PHP test runner found: edit tool/ci_local.sh" >&2; exit 1; fi )
B
    ;;
  esac
}
code_dirs() {  # kind
  case $1 in
    flutter) echo lib test integration_test android ios;;
    php) echo app src tests database routes resources config public;;
  esac
}

wi='.env
.env.local'
deny=""
setup_body="" ci_body=""
while IFS=: read -r kind dir; do
  [[ -n $kind ]] || continue
  setup_body="$setup_body$(setup_block "$kind" "$dir")
"
  ci_body="$ci_body$(ci_block "$kind" "$dir")
"
  p=""; [[ $dir == . ]] || p="$dir/"
  case $kind in
    flutter) wi="$wi
${p}android/key.properties
${p}android/app/google-services.json
${p}ios/Runner/GoogleService-Info.plist";;
    php) wi="$wi
${p}.env
${p}auth.json";;
  esac
  for c in $(code_dirs "$kind"); do
    if [[ -d ${p}$c ]]; then deny="$deny${p}$c
"; fi
  done
done <<<"$stacks"

if [[ -z $stacks ]]; then
  echo "no stack detected (no pubspec.yaml or composer.json): write tool/setup.sh and tool/ci_local.sh by hand" >&2
fi
mk() {  # file body
  [[ -f $1 || -z $2 ]] && return 0
  { printf '#!/usr/bin/env bash\n# Generated by agent-init from the detected stack. The repo owns this file: review and edit it.\nset -euo pipefail\ncd "$(dirname "$0")/.."\n'; printf '%s\n' "$2"; } > "$1"
  chmod +x "$1"
}
mk tool/setup.sh "$setup_body"
mk tool/ci_local.sh "$ci_body"
[[ -f .worktreeinclude ]] || printf '%s\n' "$wi" | awk 'NF && !seen[$0]++' > .worktreeinclude
# no code dirs found: write nothing, repo-tab then falls back to the kit's ngisa-settings.json
if [[ ! -f .claude/ngisa-settings.json && -n $deny ]]; then printf '%s' "$deny" | jq -R -s '(split("\n") | map(select(length>0)) | map(["Edit(\(.)/**)"]) | add // []) as $d | {permissions: {deny: $d}}' > .claude/ngisa-settings.json; fi
echo "done: review tool/setup.sh, tool/ci_local.sh and .worktreeinclude (secrets), then commit"
EOF

cat > ~/bin/make-lab <<'EOF'
#!/usr/bin/env bash
set -euo pipefail
kit=${LAB_KIT:-/Users/khoamai/Projects/my_proj/ngisa}
[[ -d "$kit/agents" ]] || { echo "no kit at $kit" >&2; exit 1; }
src=$(cd "$1" && pwd); name=$(basename "$src"); lab="$HOME/lab/$name"
[[ -e "$lab" ]] && { echo "$lab exists; delete it first" >&2; exit 1; }
git clone --quiet "$src" "$lab"
cd "$lab"
git remote set-url --push origin DISABLED
# real remote for agent-pr only (direct `git push` stays denied in settings.local.json)
if up=$(git -C "$src" remote get-url origin 2>/dev/null); then git remote add upstream "$up"; fi
mkdir -p .claude/agents
cp "$kit"/agents/*.md .claude/agents/
cp "$kit/settings.local.json" .claude/settings.local.json
cp "$kit/orchestrating.md" CLAUDE.local.md
printf '.claude/agents/\n.claude/ngisa-settings.json\n.claude/worktrees/\nCLAUDE.local.md\n.worktreeinclude\ntool/setup.sh\ntool/ci_local.sh\n' >> .git/info/exclude
agent-init
# copy the gitignored secrets that .worktreeinclude lists (literal paths only) from the source repo
while IFS= read -r f || [[ -n $f ]]; do
  case $f in ''|'#'*|*'*'*|*'?'*|*'['*|/*|*..*) continue;; esac
  if [[ -f "$src/$f" ]]; then mkdir -p "$(dirname "$f")"; cp "$src/$f" "$f"; fi
done < .worktreeinclude
printf 'tool/setup.sh\ntool/ci_local.sh\n' >> .worktreeinclude    # untracked here, so each agent worktree needs them copied in
echo "lab ready: repo-tab $lab"
EOF

cat > ~/bin/repo-tab <<'EOF'
#!/usr/bin/env bash
set -euo pipefail
dir=$(cd "$1" && pwd); name=$(basename "$dir")
kit=${LAB_KIT:-/Users/khoamai/Projects/my_proj/ngisa}
# the repo's own deny list (agent-init writes it from the detected stack); else the kit's Flutter default
cfg="$dir/.claude/ngisa-settings.json"; [[ -f $cfg ]] || cfg="$kit/ngisa-settings.json"
pane=$(wezterm cli spawn --cwd "$dir" -- claude --name "ngisa-$name" --model opus --settings "$cfg")
wezterm cli set-tab-title --pane-id "$pane" "$name"
EOF

cat > ~/bin/agent-wall.sh <<'EOF'
#!/usr/bin/env bash
set -euo pipefail
task=$1 agent=$2 model=$3 prompt=$4
repo=$(basename "$(git rev-parse --show-toplevel)")
name="$repo-$task"
me=${WEZTERM_PANE:?run from inside WezTerm}
json=$(wezterm cli list --format json)
tab=$(jq --argjson p "$me" '.[] | select(.pane_id==$p) | .tab_id' <<<"$json")
others=($(jq --argjson t "$tab" --argjson p "$me" '.[] | select(.tab_id==$t and .pane_id!=$p) | .pane_id' <<<"$json"))
(( ${#others[@]} < 3 )) || { echo "tab full: 3 agents already shown for $repo" >&2; exit 1; }
claude --bg --name "$name" --agent "$agent" --model "$model" \
  "$prompt  When finished, send your final report to @ngisa-$repo with SendMessage."
if (( ${#others[@]} == 0 )); then
  wezterm cli split-pane --pane-id "$me" --right --percent 55 -- claude attach "$name"
else
  wezterm cli split-pane --pane-id "${others[${#others[@]}-1]}" --bottom -- claude attach "$name"
fi
EOF

cat > ~/bin/caveman-ultra-hook <<'EOF'
#!/usr/bin/env bash
# SessionStart / UserPromptSubmit hook: keeps the NGISA and its workers in caveman ultra.
set -euo pipefail
ev=$(jq -r '.hook_event_name // "SessionStart"' 2>/dev/null || true)
[[ -n $ev ]] || ev=SessionStart
if [[ $ev == UserPromptSubmit ]]; then
  msg='CAVEMAN ULTRA active. Drop articles, filler, pleasantries, hedging. Fragments OK. Abbreviate (DB, auth, config, req, res, fn). Arrows for causality. Code, commits, PR text, security warnings, irreversible-action confirmations: write normal.'
else
  msg='CAVEMAN ULTRA active every response until the user says "stop caveman" or "normal mode". Drop articles, filler, pleasantries, hedging. Fragments OK. Short synonyms. Abbreviate prose words (DB, auth, config, req, res, fn). Arrows for causality (X -> Y). Technical terms, code symbols, paths, branch names, commands, quoted errors: exact, never abbreviated. Code, commits, PR titles/bodies, security warnings, irreversible-action confirmations: write normal. Worker final reports stay in caveman ultra but keep branch name, files changed, test command + result, and unverified items exact.'
fi
jq -n --arg ev "$ev" --arg m "$msg" '{hookSpecificOutput: {hookEventName: $ev, additionalContext: $m}}'
EOF

cat > ~/bin/agent-pr <<'EOF'
#!/usr/bin/env bash
# usage: agent-pr "<title>" "<body>" [base]
# Pushes the current branch to the `upstream` remote and opens a DRAFT PR (gh for github.com, tea otherwise).
# The only push path in a lab; each call needs the user's approval because it is not in any allow list.
set -euo pipefail
title=${1:?usage: agent-pr "<title>" "<body>" [base]} body=${2:-}
git remote get-url upstream >/dev/null 2>&1 || { echo "no 'upstream' remote; make-lab adds it" >&2; exit 1; }
url=$(git remote get-url upstream)
branch=$(git rev-parse --abbrev-ref HEAD)
base=${3:-$(git ls-remote --symref upstream HEAD | awk '/^ref:/ {sub("refs/heads/", "", $2); print $2}')}
[[ -n $base ]] || { echo "cannot detect the base branch; pass it as arg 3" >&2; exit 1; }
case $branch in
  "$base"|main|master|develop|HEAD) echo "refusing to push '$branch': use a feature branch" >&2; exit 1;;
  worktree-*) echo "rename the branch first: remote names must not start with 'worktree-'" >&2; exit 1;;
esac
[[ -z $(git status --porcelain) ]] || { echo "uncommitted changes; commit first" >&2; exit 1; }
run() { if [[ -n ${AGENT_PR_DRY_RUN:-} ]]; then echo "+ $*"; else "$@"; fi; }
run git push -u upstream "$branch"
case $url in
  *github.com*) run gh pr create --draft --base "$base" --head "$branch" --title "$title" --body "$body";;
  *) run tea pulls create --base "$base" --head "$branch" --title "$title" --description "$body";;
esac
EOF

chmod +x ~/bin/agent-init ~/bin/make-lab ~/bin/repo-tab ~/bin/agent-wall.sh ~/bin/caveman-ultra-hook ~/bin/agent-pr
which make-lab repo-tab agent-wall.sh agent-pr caveman-ultra-hook      # all five must print a path
```

(macOS ships bash 3.2, so `agent-wall.sh` here avoids `mapfile` and negative array indexes.)

## Step 4. Make the lab copy and open it

```bash
claude update                                  # agent view and --bg need a recent version
make-lab ~/Projects/vn_citizen_id_scan         # your repo path here
repo-tab ~/lab/vn_citizen_id_scan              # opens a new tab with the NGISA
```

The first time, Claude asks you to trust `~/lab/vn_citizen_id_scan`. Say yes.

### How a repo says what its stack is

The implementer prompt names no tool. It runs two files the repo owns, and `agent-init` writes them once from what it finds:

| File | Written from | Used for |
|---|---|---|
| `tool/setup.sh` | `pubspec.yaml` (Flutter, fvm, melos, build_runner), `composer.json` (PHP, `composer install`) | implementer step 1 |
| `tool/ci_local.sh` | the same detection: Flutter format/analyze/test, PHP pint or php-cs-fixer, phpstan, then `composer test` or phpunit | the done gate |
| `.worktreeinclude` | per stack secrets paths (Flutter signing and Firebase files, PHP `.env` and `auth.json`) | files each worktree needs |
| `.claude/ngisa-settings.json` | the code dirs that exist for the stack (Flutter `lib`, `test`, ...; PHP `app`, `src`, `tests`, ...) | NGISA edit deny list, used by `repo-tab` |

- A manifest at the repo root wins; otherwise `agent-init` looks one level down, so a Flutter app in `app/` plus a PHP backend in `backend/` gets one gate that runs both.
- The generated files are a starting point. Review them against the repo's real CI, then commit them. `agent-init` never overwrites a file that exists.
- No manifest found (another stack): it writes no setup or gate and says so. Write both by hand; nothing else changes.
- Put stack conventions that are not commands (for example "run migrations on the test DB before phpunit") in the repo's `CLAUDE.md`. Workers read it.
- Each task the NGISA hands out lists its paths, stack and test command; the worker uses those first and the repo files as the fallback.
- Gate integrity: `settings.local.json` denies Edit on `tool/setup.sh` and `tool/ci_local.sh` (change them by hand), and the reviewer BLOCKs if a worktree's copy differs from the main checkout or if checks were weakened. Known gap: shell edits such as `sed -i`.

## Step 5. First test (small on purpose)

In the NGISA tab, type something tiny with 2 independent parts, e.g.:

> Add a `toString()` to `OcrResult` and a unit test for `BoundsSerializer` edge cases. Brainstorm, then plan, then wait for me.

Approve the spec, approve the plan, then say `go`. The NGISA answers in caveman ultra (the hook in `settings.local.json`). You should see:
- 2 panes open on the right of the NGISA, one per agent
- each agent finishes with tests green, then the NGISA says it got a report
- the NGISA runs the reviewer and shows you one table

Optional: open another tab and run `claude agents` to see every agent in one list.

## Step 6. Clean up or keep

```bash
rm -rf ~/lab/vn_citizen_id_scan                                  # throw it away
git -C ~/Projects/vn_citizen_id_scan fetch ~/lab/vn_citizen_id_scan <branch>   # or keep a branch
```

To open a draft PR from the lab instead, tell the NGISA "open a PR" once the feature branch is green. It runs
`agent-pr`, and Claude asks you to approve that one command (`git push` itself stays denied).

## If something breaks

| Symptom | Fix |
|---|---|
| `make-lab: command not found` | `source ~/.zshrc`, or open a new WezTerm tab |
| `no kit at …` | step 2 didn't run; `ls /Users/khoamai/Projects/my_proj/ngisa` |
| NGISA never gets the agent's report | NGISA or agents are in bypass-permissions mode; restart without it |
| `claude agents` prints a list and exits | `claude update` |
| agent stuck on "Needs you" | it hit a command not in the allow list; approve it in its pane, then add it to `settings.local.json` in the kit |
| `agent-pr: no 'upstream' remote` | the lab was made before this script existed: `git remote add upstream <real-url>` in the lab |
| NGISA not in caveman | `which caveman-ultra-hook` must print a path; `ls ~/lab/<repo>/.claude/settings.local.json` must have a `hooks` block |
| implementer says setup or the gate cannot run | `agent-init` guessed the stack wrong, or found none. Edit `tool/setup.sh` and `tool/ci_local.sh` in the lab (and in the real repo) by hand: the repo owns them |
| `tab full` | 3 agents already in this tab; wait or `wezterm cli kill-pane --pane-id N` a finished one |
