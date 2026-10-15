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

## Follow-up: cleaner worker pane (2026-10-15)
- First real run of the pane on a busy-bees test task (`resolveTeacherLink` unit tests). Seen: the feed leaked a raw shell one-liner cut mid-word (`run pwd; git branch --show-current; ls tool 2>&1 | head; git status --shor`), the header showed `branch main` and the main checkout while the worker was meant to be in its own worktree, bullets were inconsistent, and nothing said what was happening now. The NGISA roster and caveman replies worked, tweakcc patches were applied.
- Design (approved in chat, previewed with a throwaway mock script before any change): two-line header (name, state chip, model, elapsed; branch and worktree dim), `waiting` / `gate failed` / `report NOT delivered` / `done <hash> "<subject>" - report delivered` line only when it matters, phase strip with a symbol per state (`✓ ▶ · ✗`, never colour alone), one counters line (`files · +added −removed · gate state`), a `now` line, then a dim log with mm:ss marks, newest first.
- `agent-view` rewritten to match: shell plumbing (`pwd`, `ls`, `git status`, ...) folds into `checked repo state`; the log says `ran tests <file>, passed|failed`, `ran the gate on <file>`, `staged changes`, `reverted lib/`; tool noise (`ToolSearch`, `ListAgents`) is hidden; words are cut at a word boundary with `…`; JSON in a failed report is reduced to its message.
- Bug fixed: the worktree was the session's start directory (the main checkout). It now follows `git worktree add <path>` and `cd <path>` in the worker's shell commands, and reports untracked files (the new test file) in the `+added` count. `PRODUCT.md` added at the repo root (impeccable init: users, constraints, principles; platform `terminal`).

### Checked
- Replay on four real transcripts (working, blocked, `inputtest` with an undelivered report, finished) at widths 40, 60, 80 and 140: no line is wider than the terminal, no raw JSON, counters match git (`1 file · +114 −0` for the new test file).
- Quickstart script block equals `~/bin/agent-view`.

### Not tested
- Colours and symbols in a real WezTerm pane over a whole task, and whether the report reaches the NGISA with the NGISA open first.

## Follow-up: first live run of the clean pane (2026-10-15)
- Two parallel busy-bees test tasks (`health-date-utils`, `health-age`): both panes showed their own branch and worktree, the roster showed both workers, and the finished worker's pane read `done be2bf61 ... report delivered`, so a report reached the NGISA with the NGISA opened first. Counters matched git (`1 file · +69 -0`).
- The date-utils pane looked stuck at `setup` for 3 min. The transcript showed one long model thinking step with no tool call, so `thinking` was true but gave no sign of time passing. Now `now  thinking 2m 40s` (shown from 20 s, time since the last tool call or result).
- A compound shell command fell back to `ran a shell command`. The command splitter did not respect quotes (a `\|` inside a grep pattern split the command), so look-around commands were not recognised. It is now quote-aware, and the fallback names the tool: `ran a shell command (python3)`.
- Caveman slipped again in the NGISA: the user had to ask "have caveman ultra applied on this session yet?" and it admitted earlier messages were full prose. The slips were long reviewer summaries and decision requests. The rule now also names long text (verdicts, findings, decisions: numbered fragments, never prose paragraphs, with a before/after example) in `orchestrating.md`, the `repo-tab` system prompt, both hook messages and the docs.
- Still open: the NGISA asked whether the health-age worker should also test the "birthday not yet reached this month" branch (`dart:45-47`), and `test/teacher-link` still has 15 unrelated red tests to plan. Both are the user's to answer.

### Checked
- Replay on three finished workers: no regressions; `checked repo state` now folds the grep/sed one-liners that used to show as `ran a shell command`.
- `bash -n` on `repo-tab` and `caveman-ultra-hook`; the hook output ends with the long-text rule. Quickstart script blocks equal `~/bin`. The lab's `CLAUDE.local.md` was refreshed from `orchestrating.md`.

### Not tested
- The `thinking 2m 40s` counter on a live worker; whether the longer caveman rule holds on a full task (needs a fresh `repo-tab` so the new system prompt applies).

## Follow-up: three workers at once (2026-10-15)
- First run with three parallel busy-bees test workers (`feed-html`, `color-ex`, `like-button-util`) and the clean pane. Roster, per-worker branch and worktree, `now`, `thinking` and the phase symbols all showed correctly; the NGISA summary came back as numbered fragments.
- Layout bug: the three panes were 1/2, 1/4 and 1/4 of the column, because each new pane split the last pane in half. `agent-wall.sh` now gives the new pane `n/(n+1)` of the last pane (`--percent`), so the column is split in equal thirds.
- Counter bug: a worker seconds after `git worktree add` showed `1531 files · +0 -221291`, because the diff against the base saw a half-checked-out worktree as thousands of deleted files. `agent-view` now shows `preparing worktree` when more than 100 listed files are missing on disk or the worktree has an `index.lock`.

### Checked
- Replay on the four busy-bees workers: counters unchanged for finished and working workers. `bash -n agent-wall.sh`; the percent maths gives 50 for the second pane and 66 for the third. Quickstart blocks equal `~/bin`.

### Not tested
- The new split in a real WezTerm tab with three workers, and `preparing worktree` on a live checkout.

## Follow-up: reviewer in its own pane (2026-10-15)
- Request: the reviewer should not be hidden inside the NGISA; the user wants a terminal to the right of that implementer's pane. The reviewer was an in-process subagent, so there was no session to show.
- Design (approved in chat, read-only view chosen over a full interactive pane): the NGISA starts the reviewer through `agent-wall.sh <task>-review reviewer opus "<...>"` and waits for its verdict message; a BLOCK sends the findings back to the same implementer (max 2 rounds, `-review2` for the second review). Reviewers do not count toward the 3 worker slots.
- `agent-wall.sh` remembers every pane it opens in `~/.cache/ngisa/panes/<session>` (the id `wezterm cli split-pane` prints), drops files of closed panes, counts only implementer panes for the "tab full" check and the equal-height split, and opens a `-review` / `-reviewN` pane `--right` of the previous round's pane, else of the implementer's pane, else at the bottom of the column.
- `agent-view` detects the reviewer by its `-review` name: phases `diff · gate files · tests · verdict · report`, chip `reviewing`, second line `reviewing <branch>`, counters `N steps · verdict pending|approved|block`, and a final line `APPROVED` (green) or `BLOCK` (red) with the summary and `report delivered`. A BLOCK also marks `✗ verdict`.
- Kit: `agents/reviewer.md` gets `SendMessage` and a line telling it to send the verdict (summary `APPROVE` or `BLOCK` first); `orchestrating.md` step 4; `ngisa-statusline` and the quickstart no longer say the reviewer is invisible to the roster. Synced into `~/lab/busy-bees`.

### Checked
- `agent-wall.sh` with fake `wezterm`, `claude` and pane lists: implementer 1 opens right of the NGISA (55%), implementer 2 splits the bottom at 50%, the review of 1 opens right of pane 1, implementer 3 splits the last implementer pane at 66% (not the reviewer pane), the review round 2 opens right of round 1, and a fourth implementer stops with "tab full". State files are written per session name.
- `agent-view` on a synthetic reviewer transcript: `diff`, `gate files` and `tests` ticked, `✗ verdict` with `BLOCK  2 findings · report delivered`, counters `4 steps · verdict block`.
- Quickstart script blocks equal `~/bin`; `bash -n` on the scripts.

### Not tested
- A real reviewer started from the NGISA: whether the permission allow list covers its `git diff`, `diff` and `fvm flutter test` calls in a background session, whether the verdict message reaches the NGISA, and the async BLOCK loop with two rounds.
- WezTerm: the `--right` split of an implementer pane in a real tab.

## Follow-up: equal heights, for real (2026-10-15)
- The "equal thirds" fix from the previous PR was wrong. Splitting only the last pane cannot shrink the panes above it: with two panes at 1/2 each, a 66% split of the last one gives 1/2, 1/6, 1/3. The user's screenshot showed three uneven worker panes.
- Probe in a throwaway WezTerm window: `wezterm cli adjust-pane-size` ignores `--pane-id` and resizes the active pane's lower border, so the pane must be activated first (`activate-pane`, then `adjust-pane-size --pane-id`). Without `activate-pane` nothing moves, or the wrong border moves.
- New `equalize_column` in `agent-wall.sh`: after an implementer pane is opened it measures the column's pane heights (`wezterm cli list`), activates the first pane that is more than one row off the average, moves its lower border, and re-measures (up to 8 tries, never fails the caller), then gives focus back to the NGISA pane. Reviewer panes are not touched.

### Checked
- In a throwaway window the column went 11,4,7 -> 7,7,8 rows, and from two disturbed layouts (7,11,4 and 12,7,3) back to 7,7,8. End to end with `agent-wall.sh` (fake `claude`, real WezTerm): 1 pane, then 12+11 rows, then 7,7,8 rows; a review pane opened to the right of its implementer's row at the same height; a fourth implementer stopped with "tab full". The test window was closed afterwards.
- Quickstart `agent-wall.sh` block equals `~/bin`.

### Not tested
- A real task with three real workers and the user's window size.
