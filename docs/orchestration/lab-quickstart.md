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
1. Before you touch any file, run `./tool/setup.sh`. No such file: your worktree was probably made with a plain `git worktree add`, which skips `.worktreeinclude`. Run `worktree-include` once (it copies the gate files and secrets that `.worktreeinclude` lists from the main checkout), then run `./tool/setup.sh` again. Still no such file: run the setup commands in CLAUDE.md. Neither exists: stop and report now, edit nothing, do not guess a stack.
2. TDD: write the failing test, show it red, make it green. Use the task's test command, else the one in CLAUDE.md or `tool/ci_local.sh`.
3. `./tool/ci_local.sh` must exit 0 before you stop. Never edit `tool/ci_local.sh`, `tool/setup.sh` or `tool/known_failures.txt`, and never run `--record-baseline`. `./tool/ci_local.sh <test paths>` runs just those tests for quick checks; the full gate must still exit 0 before you stop. A test listed in `tool/known_failures.txt` was already failing before you; leave it. Never skip, delete or loosen tests, lint rules or analyzer config to get green. If setup or the gate cannot run, or fails for a reason outside your task, stop and report the exact error. A red gate in the report is fine; a faked green is not.
4. Commit on your branch. Never push, never merge, never touch main.
5. Final message, exactly: branch name, files changed, test command + result, anything you could NOT verify and why. Write it in caveman ultra (no articles or filler, fragments OK); branch, paths, commands and errors stay exact.
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
Gate integrity: run `diff` on `tool/ci_local.sh`, `tool/setup.sh` and (if it exists) `tool/known_failures.txt` between the branch's worktree and the
main checkout (`$(git rev-parse --path-format=absolute --git-common-dir)/..`). In a lab these files are untracked,
so the git diff will not show them. Any difference is a BLOCK unless the task asked for it. Also BLOCK on weakened
checks: a new line in `tool/known_failures.txt`, tests removed or skipped, assertions relaxed, lint or analyzer config loosened, new ignore/suppress comments.
Output: APPROVE or BLOCK, then a numbered list of findings with file:line. Write it in caveman ultra (no articles or filler, fragments OK); paths, commands and quoted errors stay exact.
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
   If you create a worker's worktree yourself with `git worktree add`, git skips `.worktreeinclude`: tell the worker in its task text
   to run `worktree-include` before anything else, so it gets `tool/setup.sh` and `tool/ci_local.sh`.
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
  that worker (same session, same branch). For carve: tell it to run /carve; I answer its prompts with `claude attach <name>` (worker panes are read-only).
Pull request: only when I ask, from the local feature branch, after ci_local.sh is green. Run
  `agent-pr "<title>" "<body>"` (draft PR; it pushes to the `upstream` remote). I approve each call.
  Never use `git push` or `gh`/`tea` directly. Branch name must not start with `worktree-`.
Style: caveman ultra in EVERY message to me (status, spawn notices, summaries, questions, report tables): drop articles, filler,
  pleasantries, hedging; fragments OK; abbreviate (DB, auth, config, req, res, fn); arrows for causality. Paths, branches, commands,
  session ids, quoted errors: exact. Code, commits, PR text, security warnings: normal.
  Not: "I have started the implementer worker. It is still running." Yes: "Implementer spawned (c0be2fe3, fix/x). Running. Reviewer next."
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
      "Bash(php -l:*)", "Bash(php tests/:*)", "Bash(diff:*)",
      "Bash(./tool/setup.sh)", "Bash(./tool/ci_local.sh)", "Bash(./tool/ci_local.sh test/*)", "Bash(./tool/ci_local.sh tests/*)",
      "Bash(git status)", "Bash(git diff:*)", "Bash(git log:*)", "Bash(git add:*)", "Bash(git commit:*)",
      "Bash(git merge:*)", "Bash(git checkout:*)", "Bash(agent-wall.sh:*)", "Bash(worktree-include)"
    ],
    "deny": [
      "Bash(git push:*)", "Bash(flutter pub publish:*)", "Bash(dart pub publish:*)",
      "Bash(fastlane:*)", "Bash(firebase deploy:*)",
      "Edit(tool/ci_local.sh)", "Edit(tool/setup.sh)", "Edit(tool/known_failures.txt)"
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
# plain PHP (no composer.json, e.g. a DotB/SugarCRM-style app with vendored deps): an index.php at the root
if ! printf '%s' "$stacks" | grep -q '^php:'; then
  if [[ -f index.php ]]; then stacks="${stacks}phpplain:.
"; fi
fi

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
    phpplain) sed "s|__DIR__|$2|g" <<'B'
( cd "__DIR__" && php -v >/dev/null )   # dependencies are vendored: nothing to install
B
    ;;
  esac
}
ci_block() {  # kind dir
  case $1 in
    flutter) sed "s|__DIR__|$2|g" <<'B'
( cd "__DIR__"
  if command -v fvm >/dev/null; then F="fvm flutter"; D="fvm dart"; else F=flutter; D=dart; fi
  # format: only the .dart files this branch changed (committed or not), so old unformatted code never blocks a worker
  base=$(git merge-base HEAD origin/HEAD 2>/dev/null || git rev-parse HEAD)
  changed=$( { git diff --name-only --relative --diff-filter=ACMR "$base" -- '*.dart'; git ls-files --others --exclude-standard -- '*.dart'; } | sort -u )
  if [[ -n $changed ]]; then printf '%s\n' "$changed" | tr '\n' '\0' | xargs -0 $D format --output=none --set-exit-if-changed; fi
  if [[ -f melos.yaml ]]; then
    melos analyze && melos test
  else
    # errors anywhere fail the gate; warnings only in the files this branch changed (old code has hundreds)
    $F analyze --no-fatal-warnings --no-fatal-infos
    if [[ -n $changed ]]; then printf '%s\n' "$changed" | tr '\n' '\0' | xargs -0 $F analyze --no-fatal-infos; fi
    # tests: fail only on failures that are not listed in tool/known_failures.txt (old failures of a repo that is red).
    # Extra args go to `flutter test` (paths, --plain-name). `--record-baseline` rewrites the list from this run.
    # --record-baseline only counts as the first argument, so the allow rule for `./tool/ci_local.sh test/*` cannot record one
    record=0; if [[ ${1:-} == --record-baseline ]]; then record=1; shift; fi
    targs=("$@")
    out=$(mktemp); rc=0
    $F test --reporter json ${targs[@]+"${targs[@]}"} > "$out" || rc=$?
    failing=$(jq -R 'fromjson? // empty' "$out" | jq -sr --arg root "$PWD/" '
      (map(select(.type=="suite")) | map({key: (.suite.id|tostring), value: (.suite.path|ltrimstr($root))}) | from_entries) as $s
      | (map(select(.type=="testStart")) | map({key: (.test.id|tostring), value: "\($s[(.test.suiteID|tostring)])::\(.test.name | split($root) | join(""))"}) | from_entries) as $t
      | map(select(.type=="testDone" and .result!="success" and (.skipped|not)) | $t[(.testID|tostring)]) | unique | .[]' | sed '/^$/d')
    known="$ROOT/tool/known_failures.txt"
    if [[ $record == 1 ]]; then
      printf '%s\n' "$failing" | sed '/^$/d' > "$known"
      echo "recorded $(wc -l < "$known" | tr -d ' ') known failures in tool/known_failures.txt"
    else
      known_list=$( [[ -f $known ]] && sort -u "$known" || true )
      new=$(comm -13 <(printf '%s\n' "$known_list") <(printf '%s\n' "$failing" | sort -u) | sed '/^$/d')
      if [[ -n $new ]]; then echo "NEW test failures (not in tool/known_failures.txt):" >&2; printf '%s\n' "$new" >&2; exit 1; fi
      if [[ $rc -ne 0 && -z $failing ]]; then echo "flutter test exited $rc without a failing test (compile error?):" >&2; tail -n 20 "$out" >&2; exit 1; fi
      echo "tests ok: $(printf '%s\n' "$failing" | sed '/^$/d' | wc -l | tr -d ' ') known failures still failing"
    fi
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
    phpplain) sed "s|__DIR__|$2|g" <<'B'
( cd "__DIR__"
  # lint only the .php files this branch changed (committed or not); vendored and old code is not re-linted
  base=$(git merge-base HEAD origin/HEAD 2>/dev/null || git rev-parse HEAD)
  changed=$( { git diff --name-only --relative --diff-filter=ACMR "$base" -- '*.php'; git ls-files --others --exclude-standard -- '*.php'; } | sort -u )
  while IFS= read -r f; do
    [[ -n $f ]] || continue
    out=$(php -l "$f" 2>&1) || { printf '%s\n' "$out" >&2; exit 1; }
  done <<<"$changed"
  # tests: every tests/**/*_test.php script (or the paths given as args); each must exit 0
  if [[ $# -gt 0 ]]; then tests=$(printf '%s\n' "$@"); else tests=$( { git ls-files -- 'tests/*_test.php'; git ls-files --others --exclude-standard -- 'tests/*_test.php'; } | sort -u ); fi
  while IFS= read -r t; do
    [[ -n $t ]] || continue
    echo "== php $t"; php "$t"
  done <<<"$tests" )
B
    ;;
  esac
}
code_dirs() {  # kind
  case $1 in
    flutter) echo lib test integration_test android ios;;
    php) echo app src tests database routes resources config public;;
    phpplain) ;;
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
tool/known_failures.txt
${p}android/key.properties
${p}android/app/google-services.json
${p}ios/Runner/GoogleService-Info.plist";;
    php) wi="$wi
${p}.env
${p}auth.json";;
    phpplain) wi="$wi
${p}.env";;
  esac
  for c in $(code_dirs "$kind"); do
    if [[ -d ${p}$c ]]; then deny="$deny${p}$c/**
"; fi
  done
  # plain PHP has no fixed code dirs: the NGISA may not edit any .php file
  if [[ $kind == phpplain ]]; then deny="$deny${p}**/*.php
"; fi
done <<<"$stacks"

if [[ -z $stacks ]]; then
  echo "no stack detected (no pubspec.yaml, composer.json or root index.php): write tool/setup.sh and tool/ci_local.sh by hand" >&2
fi
mk() {  # file body
  [[ -f $1 || -z $2 ]] && return 0
  { printf '#!/usr/bin/env bash\n# Generated by agent-init from the detected stack. The repo owns this file: review and edit it.\nset -euo pipefail\ncd "$(dirname "$0")/.."\nROOT=$PWD\n'; printf '%s\n' "$2"; } > "$1"
  chmod +x "$1"
}
mk tool/setup.sh "$setup_body"
mk tool/ci_local.sh "$ci_body"
[[ -f .worktreeinclude ]] || printf '%s\n' "$wi" | awk 'NF && !seen[$0]++' > .worktreeinclude
# no code dirs found: write nothing, repo-tab then falls back to the kit's ngisa-settings.json
if [[ ! -f .claude/ngisa-settings.json && -n $deny ]]; then printf '%s' "$deny" | jq -R -s '(split("\n") | map(select(length>0)) | map(["Edit(\(.))"]) | add // []) as $d | {permissions: {deny: $d}}' > .claude/ngisa-settings.json; fi
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
printf '.claude/agents/\n.claude/ngisa-settings.json\n.claude/worktrees/\nCLAUDE.local.md\n.worktreeinclude\ntool/setup.sh\ntool/ci_local.sh\ntool/known_failures.txt\n' >> .git/info/exclude
agent-init
# copy the gitignored secrets that .worktreeinclude lists (literal paths only) from the source repo
while IFS= read -r f || [[ -n $f ]]; do
  case $f in ''|'#'*|*'*'*|*'?'*|*'['*|/*|*..*) continue;; esac
  if [[ -f "$src/$f" ]]; then mkdir -p "$(dirname "$f")"; cp "$src/$f" "$f"; fi
done < .worktreeinclude
printf 'tool/setup.sh\ntool/ci_local.sh\n' >> .worktreeinclude    # untracked here, so each agent worktree needs them copied in
# a CLAUDE.md or AGENTS.md that git does not track (gitignored or untracked in the source) is not in the clone:
# copy it, and list it so every agent worktree gets it too
for f in CLAUDE.md AGENTS.md; do
  if [[ -f "$src/$f" && ! -e $f ]]; then cp "$src/$f" "$f"; printf '%s\n' "$f" >> .git/info/exclude; printf '%s\n' "$f" >> .worktreeinclude; fi
done
# pre-accept Claude's folder-trust dialog (and its permissions warning) for this lab: it is our own clone.
# Edits Claude's state file ~/.claude.json atomically and keeps a backup next to it.
cj="$HOME/.claude.json"
if [[ -f $cj ]]; then
  tmp=$(mktemp)
  jq --arg p "$lab" '.projects[$p].hasTrustDialogAccepted = true' "$cj" > "$tmp" && cp "$cj" "$cj.bak-make-lab" && mv "$tmp" "$cj"
fi
echo "lab ready: repo-tab $lab"
EOF

cat > ~/bin/repo-tab <<'EOF'
#!/usr/bin/env bash
set -euo pipefail
dir=$(cd "$1" && pwd); name=$(basename "$dir")
kit=${LAB_KIT:-/Users/khoamai/Projects/my_proj/ngisa}
# the repo's own deny list (agent-init writes it from the detected stack); else the kit's Flutter default
cfg="$dir/.claude/ngisa-settings.json"; [[ -f $cfg ]] || cfg="$kit/ngisa-settings.json"
# the caveman rule also goes in the system prompt, where Opus weighs it more than a hook reminder
style='Caveman ultra applies to EVERY message you write to the user: status updates, spawn notices, summaries, questions, report tables. Drop articles (a/an/the), filler, pleasantries, hedging. Fragments OK. Abbreviate (DB, auth, config, req, res, fn). Arrows for causality. Paths, branch names, commands, session ids, quoted errors: exact. Code, commits, PR text, security warnings, irreversible-action confirmations: normal prose. Not: "I have started the implementer worker on this fix. It is still running." Yes: "Implementer spawned (c0be2fe3, fix/x). Running. Reviewer next."'
args=(--name "ngisa-$name" --model opus --settings "$cfg" --append-system-prompt "$style")
# run from a tab that is a lone shell pane: become the NGISA right here, so no blank shell tab is left behind.
# Otherwise (several panes, or not in WezTerm) open a new tab.
me=${WEZTERM_PANE:-}
if [[ -n $me ]] && jq -e --argjson p "$me" '(.[] | select(.pane_id==$p) | .tab_id) as $t | [.[] | select(.tab_id==$t)] | length == 1' \
    <<<"$(wezterm cli list --format json)" >/dev/null; then
  wezterm cli set-tab-title --pane-id "$me" "$name"
  cd "$dir"
  exec claude "${args[@]}"
fi
pane=$(wezterm cli spawn --cwd "$dir" -- claude "${args[@]}")
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
# panes are read-only views by default (agent-view); AGENT_VIEW=attach gives the full claude attach pane with an input box
if [[ ${AGENT_VIEW:-view} == attach ]]; then viewer=(claude attach "$name"); else viewer=("$(command -v agent-view)" "$name"); fi
if (( ${#others[@]} == 0 )); then
  wezterm cli split-pane --pane-id "$me" --right --percent 55 -- "${viewer[@]}"
else
  wezterm cli split-pane --pane-id "${others[${#others[@]}-1]}" --bottom -- "${viewer[@]}"
fi
EOF

cat > ~/bin/agent-view <<'EOF'
#!/usr/bin/env bash
# Read-only view of one background worker: header (state, model, worktree, branch) plus the tail of its transcript.
# No input box, so nothing typed here can reach the worker. To answer a worker that is stuck: claude attach <name>.
# Env: AGENT_VIEW_INTERVAL (seconds between refreshes, default 2), AGENT_VIEW_ONCE=1 (draw once and exit).
set -uo pipefail
name=${1:?usage: agent-view <session-name>}
interval=${AGENT_VIEW_INTERVAL:-2}

render='
  def short: (.command // .file_path // .pattern // .description // .prompt // (tostring)) | tostring | gsub("\n"; " ") | .[0:160];
  fromjson? | select(.type == "assistant" or .type == "user") |
  if .type == "assistant" then
    (.message.content[]? | if .type == "text" then "● " + .text
      elif .type == "tool_use" then "  ⎿ " + .name + " " + (.input | short)
      else empty end)
  else
    (.message.content | if type == "string" then "> " + .[0:240]
      else (.[]? | if .type == "tool_result" then "    " + ((.content | if type == "array" then (map(.text // "") | join(" ")) else tostring end) | gsub("\n"; " ") | .[0:110]) else empty end)
      end)
  end'

draw() {
  local cols rows info state sid file wt branch model body head
  cols=$(tput cols 2>/dev/null || echo 100); rows=$(tput lines 2>/dev/null || echo 30)
  info=$(claude agents --json --all 2>/dev/null | jq -c --arg n "$name" '[.[] | select(.name == $n)] | last // empty' 2>/dev/null)
  if [[ -z $info ]]; then printf '\033[H\033[2J%s: no such background session (yet)\n' "$name"; return; fi
  state=$(jq -r '.state // .status // "?"' <<<"$info"); sid=$(jq -r '.sessionId' <<<"$info")
  file=$(ls "$HOME"/.claude/projects/*/"$sid".jsonl 2>/dev/null | head -1)
  wt=""; model=""; branch=""
  if [[ -n $file ]]; then
    wt=$(tail -n 300 "$file" | jq -r 'select(.cwd) | .cwd' 2>/dev/null | tail -1)
    model=$(tail -n 300 "$file" | jq -r 'select(.type == "assistant") | .message.model // empty' 2>/dev/null | tail -1)
  fi
  [[ -n $wt ]] || wt=$(jq -r '.cwd' <<<"$info")
  branch=$(git -C "$wt" branch --show-current 2>/dev/null)
  body=""
  [[ -n $file ]] && body=$(tail -n 400 "$file" | jq -R -r "$render" 2>/dev/null | cut -c1-"$cols" | tail -n $(( rows - 5 )))
  # redraw in place: home the cursor, overwrite each line, clear what is left
  printf '\033[H'
  printf '\033[1m%s\033[0m  \033[36m%s\033[0m  %s\033[K\n' "$name" "$state" "${model#claude-}"
  printf '\033[2mworktree\033[0m %s  \033[2mbranch\033[0m \033[35m%s\033[0m\033[K\n' "${wt/#$HOME/~}" "${branch:-?}"
  if [[ $state == blocked ]]; then
    printf '\033[33mneeds you: claude attach %s\033[0m\033[K\n' "$name"
  else
    printf '\033[K\n'
  fi
  printf '\033[2m%*s\033[0m\033[K\n' "$cols" '' | tr ' ' '-'
  [[ -n $body ]] && printf '%s\n' "$body" | awk '{ printf "%s\033[K\n", $0 }'
  printf '\033[J'
}

if [[ ${AGENT_VIEW_ONCE:-} == 1 ]]; then draw; exit 0; fi
trap 'printf "\033[?25h"; exit 0' INT TERM
printf '\033[?25l\033[2J'
while true; do draw; sleep "$interval"; done
EOF

cat > ~/bin/worktree-include <<'EOF'
#!/usr/bin/env bash
# Run inside a git worktree. Copies the files that the main checkout's .worktreeinclude lists and this worktree lacks
# (tool/setup.sh, tool/ci_local.sh, secrets, an untracked CLAUDE.md). A plain `git worktree add` skips .worktreeinclude;
# a worktree that Claude creates does not.
set -euo pipefail
here=$(git rev-parse --show-toplevel)
main=$(git worktree list --porcelain | awk '/^worktree /{print substr($0, 10); exit}')
if [[ $here == "$main" ]]; then echo "worktree-include: this is the main checkout, nothing to do"; exit 0; fi
list="$main/.worktreeinclude"
[[ -f $list ]] || { echo "worktree-include: no $list"; exit 0; }
n=0
while IFS= read -r f || [[ -n $f ]]; do
  case $f in ''|'#'*|*'*'*|*'?'*|*'['*|/*|*..*) continue;; esac     # literal relative paths only
  if [[ -f "$main/$f" && ! -e "$here/$f" ]]; then
    mkdir -p "$here/$(dirname "$f")"; cp "$main/$f" "$here/$f"; echo "copied $f"; n=$((n + 1))
  fi
done < "$list"
echo "worktree-include: $n file(s) copied"
EOF

cat > ~/bin/caveman-ultra-hook <<'EOF'
#!/usr/bin/env bash
# SessionStart / UserPromptSubmit hook: keeps the NGISA and its workers in caveman ultra.
set -euo pipefail
ev=$(jq -r '.hook_event_name // "SessionStart"' 2>/dev/null || true)
[[ -n $ev ]] || ev=SessionStart
if [[ $ev == UserPromptSubmit ]]; then
  msg='CAVEMAN ULTRA REMINDER. Caveman ultra applies to EVERY message you write to me: status updates, spawn notices, summaries, questions, report tables. Drop articles (a/an/the), filler, pleasantries, hedging. Fragments OK. Abbreviate (DB, auth, config, req, res, fn). Arrows for causality (X -> Y). Paths, branch names, commands, session ids, quoted errors: exact. Code, commits, PR titles and bodies, security warnings, irreversible-action confirmations: normal prose. Not: "I'\''ve started the implementer worker on this fix. Nothing is fixed yet, it is still running." Yes: "Implementer spawned (c0be2fe3, fix/moment-edit-save-during-load). Running. Reviewer next."  Worker final reports stay in caveman ultra but keep branch name, files changed, test command + result, and unverified items exact.'
else
  msg='CAVEMAN ULTRA active every response until the user says "stop caveman" or "normal mode". Caveman ultra applies to EVERY message you write to me: status updates, spawn notices, summaries, questions, report tables. Drop articles (a/an/the), filler, pleasantries, hedging. Fragments OK. Abbreviate (DB, auth, config, req, res, fn). Arrows for causality (X -> Y). Paths, branch names, commands, session ids, quoted errors: exact. Code, commits, PR titles and bodies, security warnings, irreversible-action confirmations: normal prose. Not: "I'\''ve started the implementer worker on this fix. Nothing is fixed yet, it is still running." Yes: "Implementer spawned (c0be2fe3, fix/moment-edit-save-during-load). Running. Reviewer next."  Worker final reports stay in caveman ultra but keep branch name, files changed, test command + result, and unverified items exact.'
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

chmod +x ~/bin/agent-init ~/bin/make-lab ~/bin/repo-tab ~/bin/agent-wall.sh ~/bin/agent-view ~/bin/worktree-include ~/bin/caveman-ultra-hook ~/bin/agent-pr
which make-lab repo-tab agent-wall.sh agent-view worktree-include agent-pr caveman-ultra-hook      # all seven must print a path
```

(macOS ships bash 3.2, so `agent-wall.sh` here avoids `mapfile` and negative array indexes.)

## Step 4. Make the lab copy and open it

```bash
claude update                                  # agent view and --bg need a recent version
make-lab ~/Projects/vn_citizen_id_scan         # your repo path here
repo-tab ~/lab/vn_citizen_id_scan              # this tab becomes the NGISA (a new tab if this one has several panes)
```

`make-lab` pre-accepts Claude's "trust this folder" dialog (and its permissions warning) for the lab path by setting `projects["<lab path>"].hasTrustDialogAccepted` in `~/.claude.json`, with a backup at `~/.claude.json.bak-make-lab`. Skip that block of `make-lab` if you would rather answer the dialog yourself.

### How a repo says what its stack is

The implementer prompt names no tool. It runs two files the repo owns, and `agent-init` writes them once from what it finds:

| File | Written from | Used for |
|---|---|---|
| `tool/setup.sh` | `pubspec.yaml` (Flutter, fvm, melos, build_runner), `composer.json` (PHP, `composer install`), or a root `index.php` with no `composer.json` (plain PHP with vendored deps: nothing to install) | implementer step 1 |
| `tool/ci_local.sh` | the same detection. Flutter: `dart format` on the files the branch changed, `flutter analyze` (errors fail anywhere, warnings fail in changed files), `flutter test` failing only on tests not listed in `tool/known_failures.txt`. PHP with Composer: pint or php-cs-fixer, phpstan, then `composer test` or phpunit. Plain PHP: `php -l` on the changed `.php` files, then every `tests/**/*_test.php` script must exit 0 | the done gate |
| `tool/known_failures.txt` | made by `./tool/ci_local.sh --record-baseline` (you run it once on a clean base; the worker cannot) | tests that already fail, so the Flutter gate stays green on a red repo |
| `.worktreeinclude` | per stack secrets paths (Flutter signing and Firebase files, PHP `.env` and `auth.json`) | files each worktree needs |
| `.claude/ngisa-settings.json` | the code dirs that exist for the stack (Flutter `lib`, `test`, ...; PHP `app`, `src`, `tests`, ...); plain PHP denies every `**/*.php` | NGISA edit deny list, used by `repo-tab` |

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
- 2 panes open on the right of the NGISA, one per agent. They are read-only views (`agent-view`): a header with state, model, worktree and branch, then the worker's transcript, and no input box. To answer a worker that shows `needs you`, run `claude attach <name>` in a spare pane. `AGENT_VIEW=attach` makes `agent-wall.sh` open the full `claude attach` pane instead.
- each agent finishes with tests green, then the NGISA says it got a report
- the NGISA runs the reviewer and shows you one table

Optional: run `claude agents` in a spare tab to see every agent in one list. `repo-tab` does not open an overview tab.

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
| agent stuck on "Needs you" | it hit a command not in the allow list; `claude attach <name>` in a spare pane, approve it, then add it to `settings.local.json` in the kit |
| `agent-pr: no 'upstream' remote` | the lab was made before this script existed: `git remote add upstream <real-url>` in the lab |
| NGISA not in caveman | `which caveman-ultra-hook` must print a path; `ls ~/lab/<repo>/.claude/settings.local.json` must have a `hooks` block. The rule also rides in the NGISA's system prompt (`repo-tab` passes `--append-system-prompt`), so restart the NGISA after changing it. Hook and prompt together only make drift rarer; log any drift in the run log |
| worker pane blank or garbled | `agent-view` reads the session transcript under `~/.claude/projects/`, an internal format. Use `AGENT_VIEW=attach` until it is fixed |
| tweakcc customisations gone | Claude Code auto-updated and the new binary is unpatched. Re-run your tweakcc apply script, restart the NGISA, then `claude daemon stop` between tasks so new workers start from the patched binary. `DISABLE_AUTOUPDATER=1` in your shell profile stops the surprise |
| implementer says setup or the gate cannot run | `agent-init` guessed the stack wrong, or found none. Edit `tool/setup.sh` and `tool/ci_local.sh` in the lab (and in the real repo) by hand: the repo owns them |
| worker says `tool/setup.sh` is missing | its worktree came from a plain `git worktree add` (git skips `.worktreeinclude`). `worktree-include`, run inside that worktree, copies the files; the implementer is told to run it |
| `tab full` | 3 agents already in this tab; wait or `wezterm cli kill-pane --pane-id N` a finished one |
