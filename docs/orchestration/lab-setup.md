# Try the orchestrator in a lab, without touching your global config

Bottom line: **don't install anything into `~/.claude` yet.** Put the whole setup at *project level*
inside a throwaway clone of one repo. Claude Code loads project-level agents, settings and
`CLAUDE.local.md` on top of your global ones, so your global `CLAUDE.md`, superpowers and hooks keep
working unchanged, and deleting the clone removes every trace.

```
~/.claude/                 untouched (your CLAUDE.md, superpowers, hooks)
~/Projects/my_proj/ngisa/   the orchestrator files, versioned in your personal repo
~/lab/scanner/             throwaway clone: kit copied in as local, git-ignored files
   ├─ CLAUDE.local.md      orchestrator rules (loads on top of your global CLAUDE.md)
   ├─ .claude/agents/      implementer.md, reviewer.md
   ├─ .claude/settings.local.json   block hook + permission allowlist
   ├─ tool/setup.sh        from agent-init (stack detected: Flutter, PHP)
   ├─ tool/ci_local.sh     from agent-init (the done gate)
   └─ .claude/ngisa-settings.json   from agent-init (NGISA edit deny list)
```

## 1. Make the kit once

The kit lives in your personal repo at `/Users/khoamai/Projects/my_proj/ngisa`. Commit it there so changes are versioned.

```bash
mkdir -p /Users/khoamai/Projects/my_proj/ngisa/agents
# paste from one-terminal-orchestrator.md:
#   section 2a  -> ngisa/agents/implementer.md, ngisa/agents/reviewer.md
#   section 2c  -> ngisa/orchestrating.md          (the "## Orchestrating" block)
#   section 2d  -> ngisa/settings.local.json       (PreToolUse block hook + permissions.allow)
# scripts (new commands only, they change nothing in Claude Code by existing):
#   agent-init, repo-tab, agent-wall.sh -> ~/bin, chmod +x
```

## 2. Make a lab copy of a repo: `~/bin/make-lab`

```bash
#!/usr/bin/env bash
# usage: make-lab ~/code/scanner   -> ~/lab/scanner with the orchestrator set up locally
set -euo pipefail
kit=${LAB_KIT:-/Users/khoamai/Projects/my_proj/ngisa}           # override with LAB_KIT=... if you move it
[[ -d "$kit/agents" ]] || { echo "no kit at $kit" >&2; exit 1; }
src=$(cd "$1" && pwd); name=$(basename "$src"); lab="$HOME/lab/$name"
[[ -e "$lab" ]] && { echo "$lab exists; delete it first" >&2; exit 1; }
git clone --quiet "$src" "$lab"                # origin = your local repo, not GitHub
cd "$lab"
git remote set-url --push origin DISABLED      # any push fails, by design

# gitignored files the app needs (not cloned): copy the ones that exist
for f in .env .env.local android/key.properties android/app/google-services.json ios/Runner/GoogleService-Info.plist; do
  [[ -f "$src/$f" ]] && mkdir -p "$(dirname "$f")" && cp "$src/$f" "$f"
done

mkdir -p .claude/agents
cp "$kit"/agents/*.md .claude/agents/
cp "$kit/settings.local.json" .claude/settings.local.json
cp "$kit/orchestrating.md" CLAUDE.local.md
printf '.claude/agents/\n.claude/worktrees/\nCLAUDE.local.md\n' >> .git/info/exclude   # keep git status clean
agent-init
echo "lab ready: repo-tab $lab"
```

Then `repo-tab ~/lab/scanner` and work exactly as in the main doc. Because `CLAUDE.local.md`
and the agents live in the lab clone, they only exist in that tab. Your normal `claude` in
`~/code/scanner` behaves as before.

Shortcut for the rules only: Claude Code also loads `CLAUDE.md` from parent folders, so
`cp ~/Projects/my_proj/ngisa/orchestrating.md ~/lab/CLAUDE.md` once gives every clone under `~/lab` the rules and you can
drop the `CLAUDE.local.md` line. Agents and settings still have to sit in each clone's `.claude/`.

## 3. What is and isn't isolated

| | Lab clone | Your real setup |
|---|---|---|
| Global `~/.claude/CLAUDE.md`, superpowers, global hooks | still load (on top) | unchanged |
| Orchestrator rules, agents, block hook | only here | not present |
| Code changes, branches, worktrees | only here | untouched |
| Push to GitHub/GitLab | blocked (`DISABLED` push URL) | normal |
| **Max usage quota** | **shared** | **shared** |

The quota is the one thing a lab can't isolate. Run the lab when you're not doing heavy real work.

To throw it away: `rm -rf ~/lab/scanner`. To keep a result from the lab, pull the branch into the
real repo: `git -C ~/code/scanner fetch ~/lab/scanner <branch>`.

## 4. When you're happy

Promote the kit: agents to `~/.claude/agents/`, the rules into `~/.claude/CLAUDE.md`, settings into
`~/.claude/settings.json`. Then use `agent-init` on real repos.

## Want full isolation instead?

If you want even the global `CLAUDE.md`, plugins and hooks out of the picture, run Claude with a
separate config folder: `CLAUDE_CONFIG_DIR=$HOME/.claude-lab claude`. Every `~/.claude` path then
lives under `~/.claude-lab` ([docs](https://code.claude.com/docs/en/claude-directory)). The cost: no
superpowers until you install it again there, you may need to log in again, and every command in the
scripts (`repo-tab`, the `agent-view` panes) must carry the same variable, because panes WezTerm
opens don't inherit it. More moving parts; only worth it if your global hooks get in the way.
