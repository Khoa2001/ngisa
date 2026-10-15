# Read-only worker panes, caveman rule, tweakcc (2026-10-15)

From a busy-bees screenshot: worker panes showed an input box, the NGISA answered in full sentences, and tweakcc customisations were missing.

## Findings
- **tweakcc:** `~/.tweakcc/config.json` records Claude Code 2.1.299. `2.1.299` still carries the tweakcc marker; `2.1.300` (installed 2026-10-15 07:49, what `~/.local/bin/claude` points at) has none. NGISA, the `claude daemon` that runs the `--bg` workers and the user's own sessions all ran the unpatched binary. Fix is the user's: re-run their tweakcc apply script, restart the NGISA, `claude daemon stop` between tasks. Not done here.
- **Caveman:** the hook was registered in the lab and fired (7 injections in the NGISA transcript, 4 in a worker; no "command not found"). The model ignored a one-line reminder. Not a wiring bug.
- **Panes:** `claude attach` has no read-only flag, and `claude logs` prints the raw terminal stream (cursor escapes, spinner redraws), so it cannot be a clean view.

## Changes
- `agent-view <name>` (new `~/bin` script, in the quickstart): header with state, model, worktree and branch, then the session transcript rendered with `jq`; no input box. `needs you: claude attach <name>` shows when the state is `blocked`. `agent-wall.sh` uses it; `AGENT_VIEW=attach` restores `claude attach`.
- Caveman rule with scope and a before/after example in `caveman-ultra-hook`, in `orchestrating.md`, in the NGISA system prompt (`repo-tab --append-system-prompt`) and as one line in each agent's report instruction.
- "Have it carve": the user now answers carve prompts with `claude attach <name>`, since the pane is read-only.

## Checked
- `agent-view` renders header and body for a finished worker and for a `blocked` one (shows the `needs you` line), and runs as a refresh loop in a pty.
- One headless Opus call (`claude -p --model opus --append-system-prompt <rule>` in the busy-bees lab) answered in caveman ultra: "Worker ... running on ... No report yet → nothing fixed ...". One sample, not proof.
- Both labs re-synced with the three `cp` lines; lab files equal the kit.
- Script blocks in `lab-quickstart.md` equal the `~/bin` files.

## Not tested
- `agent-wall.sh` splitting real WezTerm panes with `agent-view` (running it from this session would have split the user's own pane).
- The NGISA's replies over a whole task after the change. Log any drift next run.
- Whether the transcript format survives a Claude Code update: `agent-view` reads `~/.claude/projects/*/<sessionId>.jsonl`, an internal format (read-only).
