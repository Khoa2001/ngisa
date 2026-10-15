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

## Follow-up: worker worktrees without gate files
- busy-bees run: the worker report said its worktree had no `tool/`, so it never ran `./tool/setup.sh` or the gate. The task text told it to create the worktree with a plain `git worktree add` (the NGISA's saved memory says EnterWorktree workers get git blocked, so use `git worktree add`). Git skips `.worktreeinclude`; a worktree that Claude creates does not.
- Fix: new `~/bin/worktree-include` (in the quickstart): run inside a worktree, it copies the literal paths that the main checkout's `.worktreeinclude` lists and the worktree lacks. `Bash(worktree-include)` is in the allow list; implementer step 1 runs it when `tool/setup.sh` is missing; `orchestrating.md` tells the NGISA to say so in the task text when it makes the worktree itself.
- Checked: in a throwaway repo a plain worktree had no `tool/`; `worktree-include` copied the files, skipped `..`, glob and absolute entries, and did nothing on a second run or in the main checkout. A real `claude -p --agent implementer` run in such a worktree (cost 0.13): setup.sh failed with exit 127, the worker ran `worktree-include`, retried, and got SETUP-RAN.
- Not changed: the user's NGISA memory (outside this repo). Still open: the busy-bees baseline (`tool/known_failures.txt` missing) is the user's `--record-baseline` run.

## Follow-up: pane status (2026-10-15)
- The read-only pane printed raw transcript lines (`SendMessage {"to":...`). `agent-view` is now a Python 3 script (standard library only): header (state, model, branch, worktree), a phase strip (setup, code, test, gate, commit, report), counters (elapsed, files changed, commit hash, last gate line), a blocked line that says what the worker waits for, and a plain-language activity feed. Four colours: teal working, amber needs you, green done, red error; everything else dim.
- Files changed and the commit come from git, not from tool calls: the busy-bees worker edited through `Bash`, never `Edit`. Gate pass or fail is read from output text because a failing shell command still has `is_error: false`. Phases are best-effort guesses; the feed is the ground truth.
- A failed `SendMessage` to the NGISA now shows in red as `report NOT delivered`. The user's `inputtest` worker hit this ("No agent named 'ngisa-busy-bees' is reachable"): the NGISA in tab 2 was started after the worker, so it may be timing. Not yet re-tested with the NGISA already open.
- `ngisa-statusline` (new): runs the user's own status-line command first (read from `~/.claude/settings.json`, never written), then one `workers` line from `claude agents --json --cwd`, only workers started after this NGISA, cached 3 s. `repo-tab` merges it into a temp copy of the lab's settings, so existing labs work. The in-process reviewer is not a background session and is not listed.

### Checked
- Replay on three real transcripts at width 80 and 110: finished worker (phases and 3 files, commit 1d430a7, 4m31s), blocked worker (`stopped:` line with the attach hint), `inputtest` (red report line). No raw JSON in the feed.
- `ngisa-statusline` with the user's real status line: output identical to the base line when there are no workers; with a fake `claude` it adds `workers  api done ✓ | sync needs you | cache working 2m` and drops a worker older than the NGISA. With `claude` missing from PATH or bad stdin, the base line still prints.
- `repo-tab` syntax; merged settings keep the deny rules and add the status line. The viewer loop runs in a pty and stops cleanly.
- Quickstart script blocks equal `~/bin`.

### Not tested
- A real WezTerm run: panes and the roster over a whole task, and whether report delivery works with the NGISA already open.
- The old bash `agent-view` is kept at `~/bin/agent-view.bash-backup` until the merge.
