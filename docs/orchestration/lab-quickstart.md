# Lab quickstart (copy-paste)

Run every block in WezTerm, in order. Replace `~/Projects/vn_citizen_id_scan` in step 4 with the repo you
want to test on. Nothing here touches `~/.claude` or your real repo.

## Step 1. Tools

```bash
brew install jq            # the scripts read WezTerm's pane list with jq
python3 --version          # agent-view and ngisa-statusline are Python 3 scripts (standard library only)
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
tools: Read, Grep, Glob, Bash, SendMessage
---
Diff the given branch against its base. Check: does it do the task as written, are tests real
(would they fail without the change), any edits outside the task's paths, logging or leaking of
sensitive data (PII, card data, tokens, secrets), anything irreversible.
Gate integrity: run `diff` on `tool/ci_local.sh`, `tool/setup.sh` and (if it exists) `tool/known_failures.txt` between the branch's worktree and the
main checkout (`$(git rev-parse --path-format=absolute --git-common-dir)/..`). In a lab these files are untracked,
so the git diff will not show them. Any difference is a BLOCK unless the task asked for it. Also BLOCK on weakened
checks: a new line in `tool/known_failures.txt`, tests removed or skipped, assertions relaxed, lint or analyzer config loosened, new ignore/suppress comments.
Output: APPROVE or BLOCK, then a numbered list of findings with file:line. Write it in caveman ultra (no articles or filler, fragments OK); paths, commands and quoted errors stay exact.
You run as a background worker with a pane the user watches. Send the verdict to the NGISA named in your task with SendMessage: summary = `APPROVE` or `BLOCK`, then the number of findings; message = the full numbered list. Do not edit files.
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
4. When a worker's report arrives, start its reviewer in a visible pane to the right of that worker's pane:
   `agent-wall.sh <task-slug>-review reviewer opus "<branch, base branch, worktree path, the plan task text>"` (round 2: `<task-slug>-review2`).
   The verdict arrives as a message (APPROVE or BLOCK first): wait for it, do not poll. Reviewers do not count toward the 3 workers.
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
  Long text too (reviewer verdicts, findings, decisions): numbered fragments, never prose paragraphs.
  Not: "Because every birthdate is the 1st, the age step never runs." Yes: "1. All birthdates 1st -> dart:45-47 never runs. Add test? Rec yes."
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
style='Caveman ultra applies to EVERY message you write to the user: status updates, spawn notices, summaries, questions, report tables. Drop articles (a/an/the), filler, pleasantries, hedging. Fragments OK. Abbreviate (DB, auth, config, req, res, fn). Arrows for causality. Paths, branch names, commands, session ids, quoted errors: exact. Code, commits, PR text, security warnings, irreversible-action confirmations: normal prose. Not: "I have started the implementer worker on this fix. It is still running." Yes: "Implementer spawned (c0be2fe3, fix/x). Running. Reviewer next." Long text too (reviewer verdicts, findings, decisions): numbered fragments, never prose paragraphs. Not: "Because every birthdate is the 1st, the age step never runs." Yes: "1. All birthdates 1st -> dart:45-47 never runs. Add test? Rec yes."'
# status line: the user's own line, then a roster of this repo's workers (ngisa-statusline). Merged into a temp copy of the settings.
sl=$(command -v ngisa-statusline || true)
if [[ -n $sl ]] && jq -e . "$cfg" >/dev/null 2>&1; then
  tmpcfg=$(mktemp -t ngisa-settings).json
  jq --arg c "$sl" '. + {statusLine: {type: "command", command: $c}}' "$cfg" > "$tmpcfg" && cfg=$tmpcfg
fi
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
# pane ids of the panes this script opened, one file per session name; files of closed panes are dropped
state="${XDG_CACHE_HOME:-$HOME/.cache}/ngisa/panes"
mkdir -p "$state"
# equal heights for the given panes (a column), top to bottom: move each pane's lower border until the heights match.
# WezTerm resizes the active pane's border, so each pane is activated first. Gives up after a few tries; never fails the caller.
equalize_column() {
  local ids_json n=$# tries=0 lines total target id rows k i pane_rows
  (( n > 1 )) || return 0
  ids_json=$(printf '%s\n' "$@" | jq -s -c .)
  while (( tries++ < 8 )); do
    lines=$(wezterm cli list --format json | jq -r --argjson a "$ids_json" \
      '[.[] | select(.pane_id as $i | $a | index($i))] | sort_by(.top_row) | .[] | "\(.pane_id) \(.size.rows)"') || return 0
    total=0; i=0; pane_rows=()
    while read -r id rows; do pane_rows+=("$id:$rows"); total=$(( total + rows )); done <<<"$lines"
    target=$(( total / n ))
    k=0; moved=0
    for entry in "${pane_rows[@]}"; do
      id=${entry%%:*} rows=${entry##*:}
      (( ++k < n )) || break
      if (( rows - target > 1 || target - rows > 1 )); then
        wezterm cli activate-pane --pane-id "$id" >/dev/null 2>&1 || return 0
        if (( rows < target )); then dir=Down amt=$(( target - rows )); else dir=Up amt=$(( rows - target )); fi
        wezterm cli adjust-pane-size --pane-id "$id" "$dir" --amount "$amt" >/dev/null 2>&1 || return 0
        moved=1; break
      fi
    done
    (( moved )) || return 0
  done
  return 0
}
alive() { local id; for id in ${others[@]+"${others[@]}"}; do [[ $id == "$1" ]] && return 0; done; return 1; }
for f in "$state/$repo"-*; do [[ -f $f ]] && ! alive "$(cat "$f")" && rm -f "$f"; done
# the right-hand column holds the implementer panes; reviewer panes (names ending in -review, -review2 ...) sit beside them
impl=()
for id in ${others[@]+"${others[@]}"}; do
  is_review=0
  for f in "$state/$repo"-*-review*; do [[ -f $f && $(cat "$f") == "$id" ]] && is_review=1; done
  (( is_review )) || impl+=("$id")
done
target=""
if [[ $task =~ ^(.+)-review([0-9]*)$ ]]; then
  base=${BASH_REMATCH[1]} cur=${BASH_REMATCH[2]:-1}
  # right of the previous review round if its pane is open, else right of the implementer's pane
  cands=()
  for (( r = cur - 1; r >= 2; r-- )); do cands+=("$repo-$base-review$r"); done
  if (( cur > 1 )); then cands+=("$repo-$base-review"); fi
  cands+=("$repo-$base")
  for cn in "${cands[@]}"; do
    if [[ -f $state/$cn ]]; then target=$(cat "$state/$cn"); break; fi
  done
elif (( ${#impl[@]} >= 3 )); then
  echo "tab full: 3 agents already shown for $repo" >&2; exit 1
fi
claude --bg --name "$name" --agent "$agent" --model "$model" \
  "$prompt  When finished, send your final report to @ngisa-$repo with SendMessage."
# panes are read-only views by default (agent-view); AGENT_VIEW=attach gives the full claude attach pane with an input box
if [[ ${AGENT_VIEW:-view} == attach ]]; then viewer=(claude attach "$name"); else viewer=("$(command -v agent-view)" "$name"); fi
if [[ -n $target ]]; then
  new=$(wezterm cli split-pane --pane-id "$target" --right --percent 50 -- "${viewer[@]}")
elif (( ${#impl[@]} == 0 )); then
  new=$(wezterm cli split-pane --pane-id "$me" --right --percent 55 -- "${viewer[@]}")
else
  # first guess at equal heights; equalize_column below fixes what the split leaves uneven
  n=${#impl[@]}
  new=$(wezterm cli split-pane --pane-id "${impl[n-1]}" --bottom --percent $(( 100 * n / (n + 1) )) -- "${viewer[@]}")
fi
echo "$new" > "$state/$name"
if [[ -z $target ]]; then
  equalize_column ${impl[@]+"${impl[@]}"} "$new"
  wezterm cli activate-pane --pane-id "$me" >/dev/null 2>&1 || true
fi
EOF

cat > ~/bin/agent-view <<'EOF'
#!/usr/bin/env python3
"""Read-only view of one background worker: state, phases, counters and a plain-language activity log.

No input box, so nothing typed here reaches the worker. To answer a worker that is stuck: claude attach <name>.
Reads the session transcript under ~/.claude/projects (an internal format; read only) plus git and `claude agents --json`.
Env: AGENT_VIEW_INTERVAL (seconds between refreshes, default 2), AGENT_VIEW_ONCE=1 (draw once and exit),
AGENT_VIEW_DETAIL=1 (the full view: phases, counters, now line and log; the default is status only).
In the full view phases and the gate result are best-effort guesses from the transcript; the activity log is always shown.
"""
import calendar, glob, json, os, re, shutil, subprocess, sys, time

# four semantic colours; everything else is dim or plain. Every state also has a word or a symbol.
TEAL, AMBER, GREEN, RED = "38;2;60;196;178", "38;2;231;164;71", "38;2;76;198;138", "38;2;255;107;95"
RST = "\033[0m"
DETAIL = os.environ.get("AGENT_VIEW_DETAIL") == "1"
ANSI = re.compile(r"\x1b\[[0-9;?]*[A-Za-z]")


def c(code, s):
    return f"\033[{code}m{s}{RST}"


def dim(s):
    return c("2", s)


def bold(s):
    return c("1", s)


def vis(s):
    return len(ANSI.sub("", s))


def fit(s, width):
    """Truncate to `width` visible characters, keeping colour codes intact (safety net after clip)."""
    out, n, i = [], 0, 0
    while i < len(s):
        m = ANSI.match(s, i)
        if m:
            out.append(m.group(0)); i = m.end(); continue
        if n >= width:
            break
        out.append(s[i]); n += 1; i += 1
    return "".join(out) + RST


def clip(s, width):
    """Cut a plain string at a word boundary, with an ellipsis."""
    s = " ".join(str(s).split())
    if width < 2:
        return ""
    if len(s) <= width:
        return s
    cut = s[: width - 1]
    if " " in cut[width // 2:]:
        cut = cut[: cut.rstrip().rfind(" ")]
    return cut.rstrip(" ,;:/") + "…"


def split(left, right, width):
    gap = width - vis(left) - vis(right)
    return left + " " * max(gap, 2) + right


def run(args, cwd=None, timeout=5):
    try:
        return subprocess.run(args, cwd=cwd, capture_output=True, text=True, timeout=timeout).stdout
    except Exception:
        return ""


def git(wt, *args):
    return run(["git", "-C", wt, *args]).strip()


def short_path(p, wt):
    if not p:
        return ""
    for base in (wt, os.path.expanduser("~")):
        if base and p.startswith(base.rstrip("/") + "/"):
            return p[len(base.rstrip("/")) + 1:]
    return p


def plain_error(text):
    """One readable line from a tool error, without JSON or tags."""
    text = re.sub(r"</?tool_use_error>", "", text or "").strip()
    try:
        d = json.loads(text)
        text = str(d.get("message") or d.get("error") or text) if isinstance(d, dict) else text
    except Exception:
        pass
    return text.splitlines()[0] if text else ""


def result_text(res):
    if res is None:
        return ""
    cont = res.get("content")
    if isinstance(cont, list):
        cont = " ".join(b.get("text", "") for b in cont if isinstance(b, dict))
    return str(cont or "")


TEST_RE = re.compile(r"(flutter|dart) test|phpunit|php tests/|pytest|npm (run )?test|cargo test|go test")
CODE_RE = re.compile(r"(sed -i|perl -pi|\btee\b|cat\s*>|>>|apply_patch|python3? .*(write|open\())")
FAIL_RE = re.compile(r"fail|error|exit [1-9]|not clean|FAILED|\bBLOCK", re.I)
PASS_RE = re.compile(r"\bok\b|exit 0|passed|all tests passed|\bOK \(", re.I)
# shell commands that only look around; they fold into "checked repo state"
LOOK = {"pwd", "ls", "cat", "head", "tail", "echo", "test", "wc", "which", "stat", "find", "grep", "rg", "sort", "cd",
        "true", "printf", "basename", "dirname", "readlink", "tree", "file", "sed", "awk", "cut", "tr", "uniq", "xargs"}
GIT_LOOK = {"status", "branch", "log", "diff", "rev-parse", "show", "rev-list", "remote", "config", "ls-files",
            "describe", "merge-base", "symbolic-ref", "blame", "fetch", "stash"}


def segments(cmd):
    """Split a shell command on && || ; | and newlines, but not inside quotes."""
    out, buf, quote, i = [], [], None, 0
    while i < len(cmd):
        ch = cmd[i]
        if quote:
            buf.append(ch)
            if ch == "\\" and quote == '"' and i + 1 < len(cmd):
                buf.append(cmd[i + 1]); i += 1
            elif ch == quote:
                quote = None
        elif ch in "'\"":
            quote = ch; buf.append(ch)
        elif ch in ";\n|" or cmd.startswith("&&", i):
            out.append("".join(buf)); buf = []
            if cmd.startswith(("&&", "||"), i):
                i += 1
        else:
            buf.append(ch)
        i += 1
    out.append("".join(buf))
    return [x.strip() for x in out if x.strip()]


def only_looks(cmd):
    segs = segments(cmd)
    if not segs:
        return False
    for seg in segs:
        w = seg.split()
        if "=" in w[0] and not w[0].startswith("-"):
            continue
        if w[0] == "git":
            w = [x for i, x in enumerate(w) if not (x == "-C" or (i and w[i - 1] == "-C"))]
            sub = next((x for x in w[1:] if not x.startswith("-")), "")
            if sub == "worktree":
                if "add" in w or "remove" in w:
                    return False
            elif sub not in GIT_LOOK:
                return False
        elif w[0] not in LOOK:
            return False
    return True


def first_action(cmd):
    """First segment that is not just looking around; names the command in the log."""
    for seg in segments(cmd):
        w = seg.split()
        if not w or ("=" in w[0] and not w[0].startswith("-")) or w[0] in LOOK:
            continue
        return seg
    return segments(cmd)[0] if segments(cmd) else ""


def classify(name, inp, wt):
    """-> (phase|None, kind, doing, did). `doing` is the present form for the now line, `did` the log form."""
    inp = inp or {}
    if name == "Read":
        f = short_path(inp.get("file_path"), wt)
        return None, "read", "reading " + f, "read " + f
    if name in ("Edit", "MultiEdit", "NotebookEdit"):
        f = short_path(inp.get("file_path") or inp.get("notebook_path"), wt)
        return "code", "code", "editing " + f, "edited " + f
    if name == "Write":
        f = short_path(inp.get("file_path"), wt)
        return "code", "code", "writing " + f, "wrote " + f
    if name == "Grep":
        p = str(inp.get("pattern", ""))
        return None, "read", f"searching for {p}", f"searched for {p}"
    if name == "Glob":
        p = str(inp.get("pattern", ""))
        return None, "read", f"looking for files {p}", f"looked for files {p}"
    if name == "SendMessage":
        to = str(inp.get("to", ""))
        if "ngisa" in to:
            return "report", "report", "sending the report to the NGISA", "reported to the NGISA"
        return "report", "report", "messaging " + to, "messaged " + to
    if name in ("ToolSearch", "ListAgents", "TodoWrite", "Skill"):
        return None, "noise", "", ""
    if name == "Bash":
        cmd = str(inp.get("command", "")).strip()
        first = first_action(cmd)
        if "worktree-include" in cmd:
            return "setup", "setup", "copying gate files into the worktree", "copied gate files into the worktree"
        if "tool/setup.sh" in cmd:
            return "setup", "setup", "running setup", "ran setup"
        if "ci_local.sh" in cmd:
            arg = re.split(r"\s+(?:\d?>|\||&&|;)", cmd.split("ci_local.sh", 1)[1].strip().split("\n")[0])[0].strip()[:60]
            on = f" on {arg}" if arg and not arg.startswith(("-", "2>", ">")) else ""
            return "gate", "gate", "running the gate" + on, "ran the gate" + on
        if re.search(r"git\s+commit", cmd):
            m = re.search(r"-m\s+[\"']?(?:\$\(cat <<'?EOF'?\s*)?([^\"'\n]{3,60})", cmd)
            msg = f' "{m.group(1).strip()}"' if m else ""
            return "commit", "commit", "committing" + msg, "committed" + msg
        if re.search(r"git\s+worktree\s+add", cmd):
            return "setup", "setup", "creating the worktree", "created the worktree"
        if TEST_RE.search(cmd):
            m = re.search(r"(test/\S+|tests/\S+)", cmd)
            f = m.group(1).rstrip("'\"") if m else ""
            return "test", "test", ("running tests " + f).strip(), ("ran tests " + f).strip()
        if re.search(r"(dart format|flutter analyze|dart analyze|php -l|vendor/bin/(pint|phpstan))", cmd):
            return None, "test", "checking the code", "checked the code"
        if re.search(r"(flutter|dart) pub (get|upgrade)|composer install|npm (ci|install)", cmd):
            return None, "setup", "fetching packages", "fetched packages"
        if only_looks(cmd):
            return None, "look", "checking repo state", "checked repo state"
        if re.match(r"git\s+add\b", first):
            return None, "git", "staging changes", "staged changes"
        if re.match(r"git\s+(checkout|restore)\s+--", first):
            tgt = first.split("--", 1)[1].strip()
            return None, "git", "reverting " + tgt, "reverted " + tgt
        if re.match(r"git\s+branch\s+-m", first):
            return None, "git", "renaming the branch", "renamed the branch"
        if CODE_RE.search(cmd):
            return "code", "code", "editing files with a shell command", "edited files with a shell command"
        w = " ".join(first.split()[:4])
        if not re.match(r"[\w./-]+( |$)", w):
            tool = re.search(r"[A-Za-z][\w.-]*", first)
            hint = f" ({tool.group(0)})" if tool else ""
            return None, "run", "running a shell command" + hint, "ran a shell command" + hint
        return None, "run", "running " + w, "ran " + w
    nice = {"Monitor": ("waiting on a background command", "waited on a background command"),
            "TaskStop": ("stopping a task", "stopped a task"),
            "EnterWorktree": ("entering a worktree", "entered a worktree"),
            "ExitWorktree": ("leaving the worktree", "left the worktree")}
    if name in nice:
        return None, "run", *nice[name]
    n = name.lower()
    return None, "run", "running " + n, "ran " + n


REVIEW_PHASES = ["diff", "gate files", "tests", "verdict", "report"]
VERDICT_RE = re.compile(r"\b(APPROVED?|BLOCK(?:ED)?)\b")


def review_phase(name, inp):
    """Reviewer panes use their own strip. -> (phase, doing, did) or None."""
    inp = inp or {}
    if name == "SendMessage" and "ngisa" in str(inp.get("to", "")):
        return "report", None, None
    if name == "Bash":
        cmd = str(inp.get("command", ""))
        if re.search(r"\bdiff\b", cmd) and re.search(r"tool/|known_failures", cmd):
            return "gate files", "comparing gate files", "compared gate files"
        if TEST_RE.search(cmd) or "ci_local.sh" in cmd:
            return "tests", None, None
        if re.search(r"git\s+(-C\s+\S+\s+)?(diff|log|show|merge-base)", cmd):
            return "diff", "reading the diff", "read the diff"
    return None


def load_session(name):
    out = run(["claude", "agents", "--json", "--all"])
    try:
        rows = [r for r in json.loads(out) if r.get("name") == name]
    except Exception:
        rows = []
    return rows[-1] if rows else None


def iso_to_epoch(ts):
    try:
        return calendar.timegm(time.strptime(ts[:19], "%Y-%m-%dT%H:%M:%S"))
    except Exception:
        return None


def parse(path):
    """-> events (list of dict), cwd, model, last_ts, last_text"""
    calls, events, cwd, model, last_ts, last_text = {}, [], None, "", None, ""
    try:
        with open(path, errors="replace") as f:
            lines = f.readlines()[-2500:]
    except Exception:
        return [], None, "", None, ""
    for line in lines:
        try:
            r = json.loads(line)
        except Exception:
            continue
        if r.get("cwd"):
            cwd = r["cwd"]
        ts = iso_to_epoch(r["timestamp"]) if r.get("timestamp") else None
        if r.get("timestamp"):
            last_ts = r["timestamp"]
        msg = r.get("message") or {}
        content = msg.get("content")
        if r.get("type") == "assistant":
            model = msg.get("model") or model
            for b in content if isinstance(content, list) else []:
                if b.get("type") == "text" and b.get("text", "").strip():
                    last_text = b["text"].strip()
                    events.append({"kind": "say", "text": last_text, "ts": ts})
                elif b.get("type") == "tool_use":
                    ev = {"kind": "call", "id": b.get("id"), "name": b.get("name"), "input": b.get("input"),
                          "result": None, "ts": ts}
                    calls[b.get("id")] = ev
                    events.append(ev)
        elif r.get("type") == "user" and isinstance(content, list):
            for b in content:
                if b.get("type") == "tool_result" and b.get("tool_use_id") in calls:
                    calls[b["tool_use_id"]]["result"] = b
                    calls[b["tool_use_id"]]["rts"] = ts
    return events, cwd, model, last_ts, last_text


def find_worktree(events, cwd):
    """The session starts in the main checkout; the worker then creates or enters its own worktree.
    Follow `git worktree add <path>` and `cd <path>` in its shell commands to find where it really works."""
    cur = cwd or "."
    found = None
    for ev in events:
        if ev["kind"] != "call" or ev["name"] != "Bash":
            continue
        cmd = str((ev["input"] or {}).get("command", ""))
        for seg in segments(cmd):
            w = seg.split()
            if len(w) >= 2 and w[0] == "cd":
                p = os.path.expanduser(w[1].strip("'\""))
                p = p if os.path.isabs(p) else os.path.join(found or cur, p)
                if os.path.isdir(p):
                    found = os.path.realpath(p)
            m = re.match(r"git(?:\s+-C\s+\S+)?\s+worktree\s+add\s+(.*)", seg)
            if m:
                args = [a.strip("'\"") for a in m.group(1).split() if not a.startswith("-")]
                # `-b <branch>` takes a value; the path is the first non-flag word that is not that value
                flagged = re.findall(r"-[bB]\s+(\S+)", m.group(1))
                paths = [a for a in args if a not in flagged]
                if paths:
                    p = os.path.expanduser(paths[0])
                    p = p if os.path.isabs(p) else os.path.join(found or cur, p)
                    if os.path.isdir(p):
                        found = os.path.realpath(p)
    return found or cur


def fmt_dur(sec):
    sec = max(0, int(sec))
    if sec >= 3600:
        return f"{sec // 3600}h {sec % 3600 // 60:02d}m"
    if sec >= 60:
        return f"{sec // 60}m {sec % 60:02d}s"
    return f"{sec}s"


def fmt_mark(sec):
    sec = max(0, int(sec))
    return f"{sec // 60}:{sec % 60:02d}"


PHASES = ["setup", "code", "test", "gate", "commit", "report"]


def strip(hit, cur, state, bad, phases=PHASES):
    out = []
    for p in phases:
        if p in bad:
            out.append(c(RED, "✗ " + p))
        elif p in hit and (p != cur or state == "done"):
            out.append(c(GREEN, "✓ ") + dim(p))
        elif p == cur and state != "done":
            out.append(c(TEAL, "▶ ") + bold(p))
        else:
            out.append(dim("· " + p))
    return "   ".join(out)


def count_lines(path):
    try:
        with open(path, errors="replace") as f:
            return sum(1 for _ in f)
    except Exception:
        return 0


def simple_view(name, w, state, reviewer, elapsed, branch, commit, subject, verdict, verdict_text, report, pending, last_text,
                last_activity):
    """Status only: working, needs you or done (reviewers: APPROVED or BLOCK). Nothing about what the worker is doing."""
    if state == "blocked":
        chip = c(AMBER, "needs you")
    elif state == "done":
        chip = c(GREEN if verdict != "BLOCK" else RED, verdict or "done") if reviewer and verdict else c(GREEN, "done")
        if reviewer and verdict == "APPROVED":
            chip = c(GREEN, "APPROVED")
    elif state in ("working", "running", "busy"):
        chip = c(TEAL, "reviewing" if reviewer else "working")
    else:
        chip = dim(state)
    right = chip + dim(f" · {elapsed}")
    repo = os.path.basename(git(".", "rev-parse", "--show-toplevel"))
    short = name[len(repo) + 1:] if repo and name.startswith(repo + "-") else name  # the repo prefix says nothing in a pane
    lines = [split(bold(clip(short, w - vis(right) - 2)), right, w)]
    task = re.sub(r"-review\d*$", "", short)
    sub = "reviewing " + task if reviewer else branch
    if sub:
        lines.append(dim(clip(sub, w)))
    lines.append("")
    if state == "blocked":
        text = pending["doing"] if pending else (last_text.splitlines()[0] if last_text else "waiting for you")
        lines.append(c(AMBER, "waiting  ") + clip(text, w - 9))
        lines.append(dim("answer with: ") + f"claude attach {name}")
    elif state == "done":
        if reviewer:
            m = re.search(r"(\d+)\s+findings?", verdict_text or "") or re.fullmatch(r"\D*(\d+)\D*", verdict_text or "")
            lines.append(clip(f"{m.group(1)} finding{'s' if m.group(1) != '1' else ''}" if m else (verdict_text or ""), w))
        else:
            lines.append(clip(f'{commit} "{subject}"', w) if commit else dim("no commit"))
    elif last_activity and time.time() - last_activity >= 120:
        lines.append(dim(f"quiet for {fmt_dur(time.time() - last_activity)}"))
    if report == "failed":
        lines.append(c(RED, "the NGISA did not get the result"))
    while lines and lines[-1] == "":
        lines.pop()
    return [fit(l, w) for l in lines]


def draw(name):
    size = shutil.get_terminal_size((100, 30))
    w, height = max(size.columns, 40), size.lines
    info = load_session(name)
    if not info:
        return [f"{name}: no such background session (yet)"]
    state = info.get("state") or info.get("status") or "?"
    sid = info.get("sessionId", "")
    found = glob.glob(os.path.expanduser(f"~/.claude/projects/*/{sid}.jsonl"))
    events, cwd, model, last_ts, last_text = parse(found[0]) if found else ([], None, "", None, "")
    reviewer = bool(re.search(r"-review\d*$", name))
    wt = find_worktree(events, cwd or info.get("cwd") or ".")
    started = (info.get("startedAt") or 0) / 1000 or next((e["ts"] for e in events if e.get("ts")), None)

    # classify every event once
    log, hit, cur, gate, gate_text, report, report_why, pending = [], set(), None, None, "", None, "", None
    verdict, verdict_text, steps, reviewed = "", "", 0, ""
    last_activity = None
    for ev in events:
        last_activity = max([t for t in (last_activity, ev.get("ts"), ev.get("rts")) if t], default=None)
        if ev["kind"] == "say":
            log.append({"ts": ev["ts"], "kind": "say", "did": ev["text"].splitlines()[0]})
            continue
        phase, kind, doing, did = classify(ev["name"], ev["input"], wt)
        if reviewer:
            rp = review_phase(ev["name"], ev["input"])
            phase = rp[0] if rp else None
            if rp and rp[1]:
                doing, did = rp[1], rp[2]
            if ev["name"] == "Bash":
                m = re.search(r"git\s+(?:-C\s+\S+\s+)?(?:diff|log)\s+(?:--?\S+\s+)*\S+?\.{2,3}([\w./-]+)", str((ev["input"] or {}).get("command", "")))
                reviewed = m.group(1) if m else reviewed
            if ev["name"] == "SendMessage" and "ngisa" in str((ev["input"] or {}).get("to", "")):
                body = json.dumps(ev["input"], ensure_ascii=False)
                m = VERDICT_RE.search(body)
                if m:
                    verdict = "APPROVED" if m.group(1).startswith("APPROVE") else "BLOCK"
                    tail_txt = str((ev["input"] or {}).get("summary") or "")
                    verdict_text = re.sub(VERDICT_RE, "", tail_txt, count=1).strip(" :-.,") or ""
        steps += 1
        res, text = ev["result"], result_text(ev["result"])
        failed = bool(res and res.get("is_error"))
        if kind == "noise":
            continue
        if ev["name"] == "SendMessage" and "ngisa" in str((ev["input"] or {}).get("to", "")) and res is not None:
            if failed or re.search(r'"success"\s*:\s*false|not reachable|tool_use_error', text):
                failed, report, did = True, "failed", "report NOT delivered"
                report_why = plain_error(text)
            else:
                report = "ok"
        if phase in ("test", "tests") and res is not None:
            tail = text[-400:]
            did += ", failed" if FAIL_RE.search(tail) and not PASS_RE.search(tail) else (", passed" if PASS_RE.search(tail) else "")
        if phase == "gate":
            if res is None:
                gate, gate_text = "running", ""
            else:
                body = [l.strip() for l in text.splitlines() if l.strip()]
                gate_text = body[-1] if body else ""
                tail = " ".join(body[-6:])
                gate = "failed" if FAIL_RE.search(tail) and not (PASS_RE.search(gate_text) and not FAIL_RE.search(gate_text)) \
                    else ("passed" if PASS_RE.search(tail) else "ran")
        if phase:
            hit.add(phase)
            cur = phase
        entry = {"ts": ev["ts"], "kind": kind, "doing": doing, "did": did, "failed": failed, "pending": res is None}
        log.append(entry)
        if res is None:
            pending = entry

    # git facts from the worker's own worktree
    main_wt = git(wt, "worktree", "list", "--porcelain").splitlines()
    main_wt = main_wt[0][9:] if main_wt and main_wt[0].startswith("worktree ") else wt
    base = git(main_wt, "branch", "--show-current") or "main"
    branch = git(wt, "branch", "--show-current") or "?"
    in_own = os.path.realpath(wt) != os.path.realpath(main_wt)
    changed, add, rem, commit, subject, preparing = set(), 0, 0, "", "", False
    if in_own:
        mb = git(wt, "merge-base", base, "HEAD") or base
        rows = [(l.split("\t") + ["", "", ""])[:3] for l in git(wt, "diff", "--numstat", mb).splitlines()]
        # a worktree that is still being checked out looks like thousands of deleted files
        gone = [f for a, r, f in rows if a == "0" and r.isdigit() and not os.path.exists(os.path.join(wt, f))]
        preparing = len(gone) > 100 or os.path.exists(git(wt, "rev-parse", "--git-path", "index.lock") or "/nonexistent")
        for a, r, f in ([] if preparing else rows):
            if f.startswith("tool/"):
                continue
            changed.add(f)
            add += int(a) if a.isdigit() else 0
            rem += int(r) if r.isdigit() else 0
        for l in git(wt, "status", "--porcelain", "-uall").splitlines():
            f = l[3:].strip()
            if l.startswith("??") and f and not f.startswith("tool/") and f not in changed:
                changed.add(f)
                add += count_lines(os.path.join(wt, f))
        if git(wt, "rev-list", "--count", f"{base}..HEAD") not in ("", "0"):
            commit, subject = git(wt, "log", "-1", "--format=%h"), git(wt, "log", "-1", "--format=%s")
    if changed:
        hit.add("code")
    if commit:
        hit.add("commit")

    end = iso_to_epoch(last_ts) if state == "done" and last_ts else time.time()
    elapsed = fmt_dur((end or time.time()) - started) if started else "?"
    working = "reviewing" if reviewer else "working"
    chip = {"working": c(TEAL, working), "running": c(TEAL, working), "busy": c(TEAL, working),
            "blocked": c(AMBER, "needs you"), "done": c(GREEN, "done"), "idle": dim("idle")}.get(state, dim(state))
    short_model = model.replace("claude-", "") or "?"

    if not DETAIL:
        return simple_view(name, w, state, reviewer, elapsed, branch if in_own else "", commit, subject, verdict,
                           verdict_text, report, pending, last_text, last_activity)
    right = chip + dim(f" · {short_model} · {elapsed}")
    lines = [split(bold(clip(name, w - vis(right) - 2)), right, w)]
    shown = os.path.relpath(wt, main_wt) if in_own and wt.startswith(main_wt.rstrip("/") + "/") else wt.replace(os.path.expanduser("~"), "~", 1)
    if reviewer:
        lines.append(dim(clip("reviewing " + (reviewed or re.sub(r"-review\d*$", "", name)), w)))
    else:
        lines.append(dim(clip(f"{branch} · {shown}" if in_own else f"{branch if branch != '?' else 'no branch'} · in the main checkout", w)))
    lines.append("")

    # state line: what needs the human, or how it ended
    bad = set()
    if verdict == "BLOCK":
        bad.add("verdict")
    if verdict:
        hit.add("verdict")
    if gate == "failed":
        bad.add("gate")
    if report == "failed":
        bad.add("report")
    if state == "blocked":
        if pending:
            lines.append(c(AMBER, "waiting  ") + clip(pending["doing"], w - 9))
        elif last_text:
            lines.append(c(AMBER, "asks  " if last_text.rstrip().endswith("?") else "stopped  ")
                         + clip(last_text.splitlines()[0], w - 8))
        else:
            lines.append(c(AMBER, "waiting for you"))
        lines.append(dim("answer with: ") + f"claude attach {name}")
        lines.append("")
    elif state == "done" and reviewer:
        col = GREEN if verdict == "APPROVED" else (RED if verdict else "2")
        tail = c(GREEN, "report delivered") if report == "ok" else (c(RED, "report NOT delivered") if report == "failed"
                                                                     else dim("no report sent"))
        lines.append(c(col, (verdict or "done") + "  ") + clip(verdict_text, max(w - len(verdict or "done") - 26, 10)) + dim(" · ") + tail)
        lines.append("")
    elif state == "done":
        tail = c(GREEN, "report delivered") if report == "ok" else (c(RED, "report NOT delivered") if report == "failed"
                                                                     else dim("no report sent"))
        what = (f'{commit} "{subject}"' if commit else "no commit")
        lines.append(c(GREEN, "done  ") + clip(what, w - 6 - 22) + dim(" · ") + tail)
        lines.append("")
    if gate == "failed" and state != "done":
        lines.append(c(RED, "gate failed  ") + clip(gate_text, w - 13))
    if report == "failed":
        lines.append(c(RED, "report NOT delivered  ") + dim(clip(report_why or "the NGISA was not reachable", w - 22)))
    if (gate == "failed" and state != "done") or report == "failed":
        lines.append("")

    lines.append(strip(hit, cur, state, bad, REVIEW_PHASES if reviewer else PHASES))
    if reviewer:
        ctr = [f"{steps} step{'s' if steps != 1 else ''}", "verdict " + (verdict.lower() if verdict else "pending")]
    else:
        ctr = ["preparing worktree"] if preparing else [f"{len(changed)} file{'s' if len(changed) != 1 else ''}"]
        if changed:
            ctr.append(f"+{add} −{rem}")
        ctr.append({"running": "gate running", "failed": "gate failed", "passed": "gate passed", "ran": "gate ran"}.get(gate, "gate not run"))
    lines.append(dim(" · ".join(ctr)))
    lines.append("")

    if state in ("working", "running", "busy"):
        if pending:
            lines.append(dim("now  ") + clip(pending["doing"], w - 5))
        else:
            idle = time.time() - last_activity if last_activity else 0
            lines.append(dim("now  ") + "thinking" + (dim(f" {fmt_dur(idle)}") if idle >= 20 else ""))
        lines.append("")

    # history: newest first, plumbing folded, repeats counted
    rows = []
    for e in reversed([x for x in log if not x.get("pending")]):
        text = e["did"] if e["kind"] != "say" else "» " + e["did"]
        if rows and rows[-1]["text"] == text and e["kind"] in ("look", "read", "run"):
            rows[-1]["n"] += 1
            rows[-1]["ts"] = e["ts"]
            continue
        rows.append({"ts": e["ts"], "text": text, "n": 1, "failed": e.get("failed"), "kind": e["kind"]})
    room = max(2, height - len(lines) - 1)
    for r in rows[:room]:
        mark = fmt_mark(r["ts"] - started) if r["ts"] and started else ""
        text = r["text"].replace(os.path.expanduser("~"), "~") + (f" ×{r['n']}" if r["n"] > 1 and r["kind"] != "look" else "")
        row = dim(f"{mark:>5}  ") + (c(RED, clip(text, w - 7)) if r["failed"] else dim(clip(text, w - 7)))
        lines.append(row)
    while lines and lines[-1] == "":
        lines.pop()
    return [fit(l, w) for l in lines]


def main():
    name = sys.argv[1] if len(sys.argv) > 1 else sys.exit("usage: agent-view <session-name>")
    interval = float(os.environ.get("AGENT_VIEW_INTERVAL", "2"))
    once = os.environ.get("AGENT_VIEW_ONCE") == "1"

    def paint():
        lines = draw(name)
        sys.stdout.write("\033[H" + "".join(l + "\033[K\n" for l in lines) + "\033[J")
        sys.stdout.flush()
    if once:
        paint(); return
    sys.stdout.write("\033[?25l\033[2J")
    try:
        while True:
            paint(); time.sleep(interval)
    except KeyboardInterrupt:
        pass
    finally:
        sys.stdout.write("\033[?25h"); sys.stdout.flush()


if __name__ == "__main__":
    main()
EOF

cat > ~/bin/ngisa-statusline <<'EOF'
#!/usr/bin/env python3
"""Status line for the NGISA: your own status line, then one extra line listing this repo's background workers.

Reads the status-line JSON on stdin. Runs your own status-line command (NGISA_BASE_STATUSLINE, else statusLine.command from
~/.claude/settings.json, which is only read) with the same input and prints its output first. Any failure here leaves your
own line untouched. The reviewer is also a background worker (a `-review` pane) and is listed like the others.
"""
import hashlib, json, os, subprocess, sys, tempfile, time

TEAL, AMBER, GREEN = "38;2;60;196;178", "38;2;231;164;71", "38;2;76;198;138"


def col(code, s):
    return f"\033[{code}m{s}\033[0m"


def base_output(raw):
    cmd = os.environ.get("NGISA_BASE_STATUSLINE")
    if not cmd:
        try:
            cmd = json.load(open(os.path.expanduser("~/.claude/settings.json"))).get("statusLine", {}).get("command")
        except Exception:
            cmd = None
    if not cmd:
        return ""
    try:
        return subprocess.run(["sh", "-c", cmd], input=raw, capture_output=True, text=True, timeout=5).stdout
    except Exception:
        return ""


def agents(cwd):
    cache = os.path.join(tempfile.gettempdir(), ".ngisa_roster_" + hashlib.md5(cwd.encode()).hexdigest())
    try:
        if time.time() - os.path.getmtime(cache) < 3:
            return json.load(open(cache))
    except Exception:
        pass
    out = subprocess.run(["claude", "agents", "--json", "--cwd", cwd], capture_output=True, text=True, timeout=3).stdout
    data = json.loads(out)
    try:
        json.dump(data, open(cache, "w"))
    except Exception:
        pass
    return data


def roster(j):
    cwd = (j.get("workspace") or {}).get("current_dir") or j.get("cwd") or os.getcwd()
    rows = agents(cwd)
    me = [r for r in rows if r.get("kind") == "interactive" and str(r.get("name", "")).startswith("ngisa-")]
    t0 = max((r.get("startedAt") or 0) for r in me) if me else 0
    prefix = os.path.basename(cwd.rstrip("/")) + "-"
    parts = []
    for r in sorted((r for r in rows if r.get("kind") == "background" and (r.get("startedAt") or 0) >= t0),
                    key=lambda r: r.get("startedAt") or 0):
        name = str(r.get("name", ""))
        name = name[len(prefix):] if name.startswith(prefix) else name
        st = r.get("state") or r.get("status") or "?"
        age = int(time.time() - (r.get("startedAt") or 0) / 1000)
        t = f"{age // 3600}h" if age >= 3600 else (f"{age // 60}m" if age >= 60 else f"{age}s")
        if st == "blocked":
            parts.append(f"{name} " + col(AMBER, "needs you"))
        elif st == "done":
            parts.append(f"{name} " + col(GREEN, "done ✓"))
        elif st in ("working", "running"):
            parts.append(f"{name} " + col(TEAL, f"working {t}"))
        else:
            parts.append(f"{name} \033[2m{st}\033[0m")
    return ("\033[2mworkers\033[0m  " + "  \033[2m|\033[0m  ".join(parts)) if parts else ""


def main():
    raw = sys.stdin.read()
    out = base_output(raw)
    sys.stdout.write(out if out.endswith("\n") or not out else out + "\n")
    try:
        line = roster(json.loads(raw))
        if line:
            sys.stdout.write(line + "\n")
    except Exception:
        pass


main()
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
  msg='CAVEMAN ULTRA REMINDER. Caveman ultra applies to EVERY message you write to me: status updates, spawn notices, summaries, questions, report tables. Drop articles (a/an/the), filler, pleasantries, hedging. Fragments OK. Abbreviate (DB, auth, config, req, res, fn). Arrows for causality (X -> Y). Paths, branch names, commands, session ids, quoted errors: exact. Code, commits, PR titles and bodies, security warnings, irreversible-action confirmations: normal prose. Not: "I'\''ve started the implementer worker on this fix. Nothing is fixed yet, it is still running." Yes: "Implementer spawned (c0be2fe3, fix/moment-edit-save-during-load). Running. Reviewer next." Long text too (reviewer verdicts, findings, decisions): numbered fragments, never prose paragraphs. Not: "Because every birthdate is the 1st, the age step never runs." Yes: "1. All birthdates 1st -> dart:45-47 never runs. Add test? Rec yes."  Worker final reports stay in caveman ultra but keep branch name, files changed, test command + result, and unverified items exact.'
else
  msg='CAVEMAN ULTRA active every response until the user says "stop caveman" or "normal mode". Caveman ultra applies to EVERY message you write to me: status updates, spawn notices, summaries, questions, report tables. Drop articles (a/an/the), filler, pleasantries, hedging. Fragments OK. Abbreviate (DB, auth, config, req, res, fn). Arrows for causality (X -> Y). Paths, branch names, commands, session ids, quoted errors: exact. Code, commits, PR titles and bodies, security warnings, irreversible-action confirmations: normal prose. Not: "I'\''ve started the implementer worker on this fix. Nothing is fixed yet, it is still running." Yes: "Implementer spawned (c0be2fe3, fix/moment-edit-save-during-load). Running. Reviewer next." Long text too (reviewer verdicts, findings, decisions): numbered fragments, never prose paragraphs. Not: "Because every birthdate is the 1st, the age step never runs." Yes: "1. All birthdates 1st -> dart:45-47 never runs. Add test? Rec yes."  Worker final reports stay in caveman ultra but keep branch name, files changed, test command + result, and unverified items exact.'
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

chmod +x ~/bin/agent-init ~/bin/make-lab ~/bin/repo-tab ~/bin/agent-wall.sh ~/bin/agent-view ~/bin/ngisa-statusline ~/bin/worktree-include ~/bin/caveman-ultra-hook ~/bin/agent-pr
which make-lab repo-tab agent-wall.sh agent-view ngisa-statusline worktree-include agent-pr caveman-ultra-hook      # all eight must print a path
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
- 2 panes open on the right of the NGISA, one per agent. They are read-only views (`agent-view`) that show only status: the name, `working`, `needs you` or `done` with the time, one dim line (the branch), and one result line (the commit for an implementer, `N findings` for a reviewer). A reviewer's status reads `reviewing`, then `APPROVED` or `BLOCK`. A worker that has made no move for 2 minutes gets a dim `quiet for Nm` line; a worker that needs you shows the question and `claude attach <name>`; a red line says so if the NGISA never got the worker's result. There is no input box. `AGENT_VIEW_DETAIL=1` brings back the full view (phase strip, counters, a `now` line and a log). The NGISA's status line adds a `workers` roster (`ngisa-statusline`). To answer a worker that shows `needs you`, run `claude attach <name>` in a spare pane. `AGENT_VIEW=attach` makes `agent-wall.sh` open the full `claude attach` pane instead.
- each agent finishes with tests green, then the NGISA says it got a report
- a reviewer pane opens to the right of that agent's pane (`<task>-review`, a read-only status view like the others); its verdict `APPROVED` or `BLOCK` shows in the pane header
- the NGISA collects the verdicts and shows you one table

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
| worker pane shows a wrong phase tick (only with `AGENT_VIEW_DETAIL=1`) | the phase strip and gate line are guesses from the transcript (shell commands are classified by pattern); the log under it is the ground truth. `AGENT_VIEW=attach` for the full pane |
| no `workers` line in the NGISA status line | `which ngisa-statusline` must print a path, and the NGISA must be started with the new `repo-tab`. Only workers started after the NGISA appear (reviewers too, since they are workers) |
| worker pane blank or garbled | `agent-view` reads the session transcript under `~/.claude/projects/`, an internal format. Use `AGENT_VIEW=attach` until it is fixed |
| tweakcc customisations gone | Claude Code auto-updated and the new binary is unpatched. Re-run your tweakcc apply script, restart the NGISA, then `claude daemon stop` between tasks so new workers start from the patched binary. `DISABLE_AUTOUPDATER=1` in your shell profile stops the surprise |
| implementer says setup or the gate cannot run | `agent-init` guessed the stack wrong, or found none. Edit `tool/setup.sh` and `tool/ci_local.sh` in the lab (and in the real repo) by hand: the repo owns them |
| worker says `tool/setup.sh` is missing | its worktree came from a plain `git worktree add` (git skips `.worktreeinclude`). `worktree-include`, run inside that worktree, copies the files; the implementer is told to run it |
| `tab full` | 3 agents already in this tab; wait or `wezterm cli kill-pane --pane-id N` a finished one |
