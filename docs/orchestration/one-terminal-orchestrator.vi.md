# Một cửa sổ, mỗi repo một NGISA, nhiều agent

> Xem hình trước: trang sơ đồ [NGISA và Agent Wall](https://claude.ai/artifact/ENAt99SX1UwoaG5Lm3nzBa). File này là bản chi tiết.
> Code, lệnh, config giữ nguyên tiếng Anh để copy chạy được.

**Tóm lại:**
- Không tự build framework, không cài thêm tool quản lý tmux. Claude Code đã có đủ.
- Mỗi repo có **một NGISA** (session Sonnet: nhanh hơn, mà NGISA chỉ lên kế hoạch và giao việc, xem mục "Worker khởi động sẵn"): lên kế hoạch, chia task, giao cho các **implementer** (Sonnet, chạy nền, mỗi con một **worktree** riêng), rồi đọc kết quả từ commit cuối của từng worker bằng `worker-result` (bạn tự đọc diff).
- WezTerm: **một cửa sổ, mỗi tab là một repo**. NGISA bên trái, tối đa 3 agent xếp chồng bên phải.
- Agent teams: **chưa dùng cho code** (thử nghiệm, không có worktree, tốn ~7× token, không chạy được split của WezTerm).
- Chưa có hook + CI gate thì đừng chạy song song: chỉ nhân số thứ bạn phải tự kiểm. Làm [cut-verification-time.md](../verification/cut-verification-time.md) trước.

Đã đối chiếu docs Claude Code hiện tại (10/2026): [agents](https://code.claude.com/docs/en/agents), [agent view](https://code.claude.com/docs/en/agent-view), [agent teams](https://code.claude.com/docs/en/agent-teams), [worktrees](https://code.claude.com/docs/en/worktrees), [workflows](https://code.claude.com/docs/en/workflows), [costs](https://code.claude.com/docs/en/costs). Tên tính năng đổi nhanh, chạy `claude update` trước.

---

## 1. Có gì, dùng cái nào

| Lựa chọn | Ai điều phối | Cách ly file | Kết luận |
|---|---|---|---|
| **Background session** (`claude --bg`) + **subagent** (`~/.claude/agents/*.md`) | NGISA của repo | Mỗi agent một worktree | **Dùng.** Đây chính là cái "NGISA" bạn muốn. |
| **Agent view** (`claude agents`) | Bạn | Worktree tự động | **Dùng khi cần xem hết**: chạy ở một tab trống, thấy mọi agent, vàng = đang chờ bạn. |
| **Agent teams** | Một lead session | **Không có**, dùng chung checkout | Chỉ cho research, review, debug. **Không** cho code. |
| **Dynamic workflows** (`ultracode: …`) | Script Claude viết | Theo từng item | Cho việc cơ học diện rộng ("migrate mọi widget"). Không cho feature. |
| **`/batch`** | Claude | 5–30 worktree | Như workflows, cho 1 thay đổi lớn mang tính cơ học. |
| claude-squad, ccmanager, Conductor, script tmux | Bạn | Worktree | **Bỏ qua.** Trùng với agent view, thêm tool thêm lỗi. |
| Agent SDK tự viết NGISA | Code của bạn | Tự làm | **Bỏ qua.** Build framework là non-goal của project. |

## 2. Cài đặt

### Cài một lần cho máy vs cho từng repo

Gần như mọi thứ nằm ở thư mục home, dùng chung mọi repo. Mỗi repo chỉ cần 3 file nhỏ.

| Thành phần | Đặt ở đâu | Phạm vi |
|---|---|---|
| `implementer.md` | `~/.claude/agents/` | 1 lần, mọi repo |
| Luật cho NGISA | `~/.claude/CLAUDE.md` (hoặc skill `~/.claude/skills/orchestrate/`) | 1 lần |
| Hook format, Stop gate, chặn lệnh không đảo ngược được, allowlist quyền | `~/.claude/settings.json` | 1 lần |
| `agent-wall.sh`, `repo-tab`, `agent-init` | `~/bin/` (có trong PATH) | 1 lần |
| WezTerm | không cần config, script dùng `wezterm cli` | 1 lần |
| `tool/ci_local.sh` | trong repo | **từng repo** (lệnh format/analyze/test riêng; CI gọi chính file này) |
| `.worktreeinclude` | gốc repo | **từng repo** (file bị gitignore mà worktree cần, vd `.env`) |
| dòng `.claude/worktrees/` trong `.gitignore` | trong repo | **từng repo** |

Hook ở user-level không được giả định cấu trúc repo: Stop gate = "có `./tool/ci_local.sh` thì chạy, không có thì thôi"; hook format chỉ format `*.dart` (bỏ file generate). Repo chưa có `ci_local.sh` thì chỉ là chưa được NGISA, không hỏng gì.

**Mỗi repo: một lệnh.** `~/bin/agent-init`:

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

Khối trên là bản gốc chỉ cho Flutter. `agent-init` hiện tại tự nhận diện stack (Flutter, PHP), tạo `tool/setup.sh` và `tool/ci_local.sh` theo stack đó, và thêm `.claude/ngisa-settings.json` riêng cho repo. Các agent chạy hai file này thay vì gọi thẳng tool nào. Bản script hiện tại nằm ở [`lab-quickstart.md`](lab-quickstart.md) bước 3 và thắng khối này.


Chạy xong: xem lại `.worktreeinclude` có đúng các file secret của repo không, rồi commit.

Repo nào có `.claude/agents/` hoặc `.claude/settings.json` riêng thì cái đó thắng bản user-level. Chỉ dùng khi repo thật sự khác (vd app công ty trên GitLab).

### 2a. Định nghĩa agent

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
Task text format: `Branch: <name>. Base: <ref>. <task text>` (<ref> = full sha of NGISA's HEAD, or the branch name of an earlier task this one depends on). Cold start: the task is given in the prompt. First decide whether you are isolated: `git rev-parse --show-toplevel` equal to the first path printed by `git worktree list --porcelain` (the main checkout) means you are NOT isolated. Not isolated: create your own worktree `git worktree add .claude/worktrees/<last path segment of Branch> -b <name> <ref>`, `cd` into it, run `worktree-include`, and work ONLY there; NEVER run `git checkout`, `git switch`, `git reset` or commit in the main checkout. Already in a linked worktree (path under `.claude/worktrees/`): run `git checkout -B <name> <ref>` there. Then steps 1-5 as written. A task given in the prompt (cold start) is not a message: the no-branch stop below never applies to it.
Warm start: task message begins `Branch: <name>. Base: <ref>.` and your worktree path matches `.claude/worktrees/warm-*`: run `git checkout -B <name> <ref>` there (use the Base ref, never origin/HEAD). Skip step 1. A test or analyze run then fails on missing packages: run `./tool/setup.sh` once, continue at step 2. In a `warm-*` worktree, a task message with no `Branch:` line: stop, edit nothing, final line `no branch given`.
A reused worker (it already did an earlier task): start from this Base ref, ignore the earlier task's scope, touch only this task's listed paths.
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
Call pattern for quick mode (target 5 to 6 requests; direct mode keeps red first and then uses steps 3 and 4; a multi-step task runs it once per numbered step): fewer requests means fewer tokens, because every request re-reads the whole conversation.
1) Warm start: ONE Bash call `git checkout -B <name> <ref>` first. Read the files you need only after it, never before (Edit and Write on an existing file need a Read of the checked-out content). The cold start does its isolation and worktree steps first.
2) ONE turn, parallel Write/Edit calls for all listed files.
3) ONE Bash call for all listed checks: `log=$(mktemp); rc=0; { <check 1> || rc=1; <check 2> || rc=1; } > "$log" 2>&1; echo "exit=$rc"; tail -n 40 "$log"`. A red result: also run `grep -n -m 20 -E 'FAIL|Error|error:' "$log"`, fix, re-run the chain.
4) ONE Bash call to commit: `git add` the listed paths, `git commit` with the body lines.
5) The one-line final message. Plan mode keeps its own procedure.
Direct mode is unchanged: full TDD, red first. Task text may hold several numbered steps: do them in order in this worktree, one commit per step, the LAST commit carries the `checks:`/`unverified:`/`asks:` lines for all steps.

Plan mode (`mode: plan <path>`): read the plan file (never edit it), then do step 1 (warm start: as the Warm start line says) and run `superpowers:subagent-driven-development` on the task numbers the task text names. It dispatches a fresh implementer subagent per task, a task review after each and a final review of your branch; let it. Differences from the skill:
- Autonomous: decide conflicts and ambiguities yourself, as the skill says, and write each as `Ruling: <what> - <why> - <cost if wrong>` in its ledger. Do not ask about rulings.
- Stop and put it in `asks:` (commit body) only for the skill's four cases: an irreversible or destructive operation, a security-sensitive action, a side effect outside this worktree (merge, push, publish), a plan so broken every path is a guess.
- Do not run `finishing-a-development-branch`: no merge, no PR, no push. Leave the work committed on your branch.
- Steps 3 and 4 still apply: run the repo's checks (a red result is reported in `checks:`, never faked).
- Commit body adds `ledger: <path of the ledger file>` (also on the last commit). Direct mode: no `ledger:` line.
```

Không có reviewer agent. Bạn tự đọc diff; `gate-check` (xem `lab-quickstart.md`, bước 3) chỉ bảo vệ các file gate và cấu hình lint.

### 2b. Worktree với Flutter

- Mỗi worktree là một bản checkout mới: phải `pub get` + `build_runner` lại. Tốn ổ đĩa và vài phút. Đó là giá của việc cách ly, chấp nhận.
- **Chỉ có một emulator/simulator dùng chung.** Mỗi lúc chỉ một agent được chạy `integration_test`. Unit/widget test chạy song song thoải mái.
- Nếu implementer phải tách nhánh từ feature branch mà NGISA đang đứng (thường là vậy): `"worktree": { "baseRef": "head" }`. Mặc định `"fresh"` tách từ `main`.

### 2c. Luật cho NGISA (`~/.claude/CLAUDE.md`)

```md
## Orchestrating
You are the orchestrator (NGISA) for this repo. You do not write feature code yourself.
1. Size the task first (see Size below). Big tasks: spec → plan with superpowers (brainstorming, writing-plans). STOP and wait for my approval of the plan.
2. Split the approved plan into tasks. Each task lists the exact paths it may touch, the stack (e.g. flutter, php) and the test command, and that text goes into the worker's prompt. Task text starts `mode: quick|direct|plan <path>`. A repo can mix stacks: name the stack per task.
   Say what to verify, not how: "verify as the repo's CLAUDE.md says". Never write a raw runner (`flutter test`, `phpunit`, ...) in a task text.
   Tasks that depend on each other (one needs a file or change the other makes) or that touch the same file go to ONE worker as a single task text, tasks in order. Only independent tasks get separate workers.
   Combined task text: numbered steps in order, each with its own paths and checks, ONE `mode:` prefix for the whole text, one Branch/Base.
   At the message that gives the task, size it in one line first (no tool call). Only one worker task in the whole request, of size `tiny` or `small`, and not a relay or follow-up to a running worker: reply `one task: run it in plain Claude` and stop. No worker, no stamps, no board.
3. Spawn the parallel tasks. First `ngisa-start --need N` right after sizing, once per request (N = number of quick/direct tasks (max 3); add `--new-plan` for every new request that is not an extra request to a running worker; never on my OK or answers). If fewer than N warm workers are free it starts the missing ones and waits up to 60 s for them: do not start cold meanwhile. In the same turn as `ngisa-start`, run `ToolSearch` `select:SendMessage`. It stamps the request and prints `base: <sha>`, each finished warm worker as `warm-N branch=<b> dirty=<yes|no> ctx=<n>k idle=<n>m tasks=<n>`, and `free: <n>`. Free = state `done` or `idle` and `branch=warm/N` (a used worker is on its task branch).
   Plan-mode tasks take the cold path and never reuse a worker. Do not count them in N.
   Reuse a finished worker only when ALL hold: its `dirty=no`; the new task's paths overlap its last task's paths or directory, or the new task depends on it; `ctx` under 100k; `idle` under 55 min; `tasks` under 3. Unknown last paths: not reusable. Not reusable: `worker-retire <repo>-warm-N` (closes pane and session, removes the worktree, keeps the task branch).
   A task that depends on a worker's earlier task gets `Base:` = that task's branch name, for a reused or a fresh worker.
   Free or reused worker: ONE `SendMessage {to: "<repo>-warm-N", notify_when_idle: true, message: "Branch: <name>. Base: <base>. <task text>"}` per task, all in one turn (branch = clean name like `feat/<slug>`, never `worktree-*`; task text incl. `mode:`). Then ONE `ngisa-spawned <slug>=<repo>-warm-N ...` (stamps, panes, refill).
   No free warm worker: cold path `agent-wall.sh <slug> implementer sonnet "Branch: <name>. Base: <base>. <task text>"`, then `ngisa-report mark <slug> spawn` and a pure subscription `SendMessage {to: "<repo>-<slug>", notify_when_idle: true}`.
   Keep a list `slug -> warm-N` with each worker's task count and last paths in your reply; never give a NEW assignment a name already on it this run (a finished worker shows `done` again and only gets another task through the reuse rule); an idle notice maps to its slug through it.
   Max 3 at once; more tasks than free slots wait in a queue in your reply, started at each idle notice. Never open WezTerm windows, tabs or panes any other way.
   If you create a worker's worktree yourself with `git worktree add`, tell the worker in its task text to run `worktree-include` first (git skips `.worktreeinclude`).
   You may not edit code yourself (your settings deny the code dirs), even for a one-line fix. Every code change goes to a worker. A bug report is a task too: repro, root cause and fix all go to a worker (say "repro first"). You never run tests, write repro files or edit code with shell commands (`ngisa-guard` blocks them).
   Stamps are silent (no chat line). `ngisa-report mark <slug> decided` when I answer the ask, say merge, or when you start merging an ok branch with no ask. After an ask is answered, an override to `ok`, or a merge: `agent-wall.sh --close <session>` for each pane still open. `ngisa-report mark <slug> pr` for every slug in that PR, after `agent-pr`. Do not print timing; I run `ngisa-report timing` myself.
4. At a worker's idle notice (not a report): ONE call `ngisa-collect <slug> <session> <base> <branch>`. It prints the `worker-result` (`commits: N`, `branch:`, `dirty:`, `--- body`, `--- stat`), stamps, records the row, prints `state: ok|fail|blocked` and the board, and closes the pane only for `ok`. It already did all that: do not re-run `ngisa-report set` or `agent-wall.sh --close` unless you override a state.
   `blocked` = no new commit, no `checks:` line (never `ok`), or `asks:` not `none` (the pane has the question: say so in one line). `fail` = a red `checks:`. Else `ok`. Read something else: override with `ngisa-report set <slug> --base <base> --branch <branch> --state ok|fail|blocked`. A worker still running is `--state working`.
   I read the diff myself, so do not add your own review. Findings and unverified items stay in the commit body and pane, not on the board. Ignore `ledger:`: give its path only when I ask. An ask from `asks:` goes to me through `AskUserQuestion`.
5. Only one agent runs integration tests / the emulator at a time.
6. Merge task branches that finished ok (or that I allowed) into a local feature branch. Never push on your own.
   Do the merge in its own worktree (`git worktree add .claude/worktrees/integration -b <feature branch>`). Never check out or merge in the main checkout: it may hold my uncommitted work.
7. Report to me: paste the output of the last `ngisa-report set` or `ngisa-collect` board unchanged, then the PR link if any. Never retype or reword it.
   When a worker is `fail` or holds an ask: after the board add ONE line saying why (12 words at most), then ask me with the `AskUserQuestion` tool (see Ask). Never print the question again as text.
Quiet: my screen is for decisions, not a log. While workers run, say ONE line per event (spawn: `<slug> spawned.`).
  No board until a worker's idle notice arrives, no session ids or `claude attach` hints, and never mention hook blocks, retries or workarounds: fix them silently. Only asks, the board after an idle notice, and the PR link get more than one line.
Ask: when you need a decision, use the `AskUserQuestion` tool, never prose or a pasted card, then wait.
  One question per decision (several in one call are fine). `header` = the task slug cut to 12 characters. The first option is the worker's recommendation, labelled `<answer> (Recommended)`; its description is the worker's `why`, or one short line of yours. Add one or two real alternatives (usually the opposite). Plain words, no abbreviations like y/n/rec. A red check with no worker ask: ask `Merge anyway?` with `No (Recommended)` first.
Size: judge every task and say it in one line (`tiny`, `small` or `big`, and why). "quick" from me means tiny.
  tiny = clear, 1-2 named files or one obvious bug: no brainstorming, no plan. One worker, `mode: quick`, exactly those paths (alone in the request: see step 2).
  small = a few files, one concern: a 3-5 line plan in chat, wait for my OK, then `mode: quick` worker(s).
  big or unclear: brainstorming, writing-plans, plan file at `<repo>/.claude/plans/<slug>.md` (excluded from git), wait for my approval.
    Split the plan into independent groups (max 3 workers). Each task text starts `mode: plan <absolute plan path>` and names its task numbers.
    Tasks that depend on each other stay in one worker, in order. The worker runs subagent-driven-development (reviews inside); you add none.
  borderline (cannot tell): ask me `tiny, small or big?` with `AskUserQuestion` before anything else.
  `mode: direct` (full TDD) only when I ask for thorough or TDD. A tiny or small task never gets reviewers.
Relay: when I ask for something extra from a worker (e.g. "have it carve", "fix the lint"), SendMessage it to
  that worker (same session, same branch); a relay to a running or blocked worker carries `notify_when_idle: true`. For carve: lean workers have no skills, so tell me to run /carve myself in that worker's worktree.
Pull request: only when I ask, from the local feature branch: `agent-pr "<title>" "<body>"` (draft PR; it pushes to the `upstream` remote). I approve each call.
  Never use `git push` or `gh`/`tea` directly. Branch name must not start with `worktree-`.
Style: caveman ultra in EVERY message to me (status, spawn notices, summaries, questions, report tables): drop articles, filler,
  pleasantries, hedging; fragments OK; abbreviate (DB, auth, config, req, res, fn); arrows for causality. Paths, branches, commands,
  session ids, quoted errors: exact. Code, commits, PR text, security warnings: normal.
  Not: "I have started the implementer worker. It is still running." Yes: "fix-x spawned."
  Long text too (findings, decisions): numbered fragments, never prose paragraphs. Boards are templates: paste them, do not rewrite them.
Never: merge to main, push or open a PR without my ask, publish, touch store/remote-config/signing,
  delete branches with unmerged work, or run `git worktree prune`, `git worktree remove`, `claude stop` or `claude rm` yourself; end a worker only with `worker-retire`, only when it is `done` or `idle` (a worker lost its green fix that way).
  Optional, once per worker: a worker over 100k that holds clearly useful context: ask me with `AskUserQuestion` whether to `claude attach` and `/compact` it or retire it. Default retire, no question.

# Compact instructions
When compacting, keep: the `slug -> warm-N` list with each worker's task count and last paths, the base refs, the last board, my decisions, open asks. If the list is lost, rebuild it from `claude agents --json`, `git worktree list --porcelain` and `worker-ctx`; unknown last paths mean: not reusable.
```

### 2d. Hook: bắt buộc, không phải "nhắc nhở"

Trong `~/.claude/settings.json`, thêm vào hook format + Stop gate của playbook trước:

- **`PreToolUse` cho `Bash`**: chặn `git push.*(main|master)`, `git push --force`, `flutter pub publish`, `fastlane`, `firebase deploy`, mọi thứ đụng remote config. Exit 2 kèm lý do. Đây mới là thứ thật sự giữ các thao tác không đảo ngược được ở tay bạn; chỉ dặn trong prompt là không đủ.
- **`Notification`** (`agent_needs_input`, `agent_completed`) → thông báo desktop/điện thoại, khỏi ngồi canh màn hình.
- Cho phép sẵn các lệnh nhàm chán (`fvm flutter test`, `melos *`, `dart format`, `git add/commit/diff/log`, `agent-wall.sh`) trong `permissions.allow`. Không thì agent nền nào cũng đứng ở "Needs input" và song song chỉ là giả.
- **Không** cho phép rộng `Bash(wezterm cli:*)`. Chỉ đi qua `agent-wall.sh` để layout không bị loạn.
- NGISA và báo cáo của worker nói kiểu caveman ultra nhờ hook `SessionStart` + `UserPromptSubmit` chạy `caveman-ultra-hook` (chỉ thêm context, không chặn gì), cộng với cùng luật đó trong system prompt của NGISA (`repo-tab` truyền `--append-system-prompt`), vì một dòng nhắc thôi không đủ với Opus. Code, commit, PR vẫn viết bình thường. Bản luật cho lab, đi PR qua `agent-pr`, nằm trong `lab-quickstart.md`.
- **Không** chạy NGISA hay agent ở `bypassPermissions`: ở chế độ đó, báo cáo từ session khác bị giữ lại chờ duyệt, không tự đến NGISA.
- Bảng của NGISA là mẫu cố định, không phải văn xuôi. NGISA ghi mỗi kết quả của worker (đọc từ commit cuối bằng `worker-result`) bằng `ngisa-report set` (khối script trong `lab-quickstart.md`) rồi dán nguyên output làm báo cáo cuối: mỗi task một dòng có ký hiệu trạng thái, phát hiện (`!`) và câu hỏi (`?`, kèm đề xuất) nằm ngay dưới dòng task, mục chưa kiểm chứng và chú giải (`✓ ok  ✗ fail  ▶ working  ? asks you  ! finding`). Không có pane riêng cho nó: board nằm trong chat, cạnh danh sách `workers` ở status line. Quyết định đến qua công cụ `AskUserQuestion` gốc, không dán thẻ vào chat. Báo cáo của worker là commit body: các dòng `checks:`, `unverified:`, `asks:` (thêm `ledger:` ở plan mode) và một dòng cuối ngắn, để NGISA ánh xạ sang các cờ và thiếu dòng `checks:` thì thấy ngay (không bao giờ là `ok`).

## 3. WezTerm: một cửa sổ, mỗi tab một repo

```
┌ scanner ┬ owen-host-app ┬ work-app ┐
│ ngisa-scanner (Sonnet) │ scanner-cache   [Done]     │
│ bạn gõ ý tưởng ở đây    ├────────────────────────────┤
│                        │ scanner-sync    [Working]  │
│                        ├────────────────────────────┤
│                        │ scanner-ui      [Needs you]│
└────────────────────────┴────────────────────────────┘
```

- Không có tab `overview` riêng. Cần xem hết thì chạy `claude agents` ở một tab trống: mọi agent của mọi repo. `Ctrl+S` gom theo repo. `Space` xem nhanh, `Enter` vào hẳn, `←` thoát ra. Dòng vàng = đang chờ bạn.
- Mỗi tab repo: NGISA bên trái, tối đa 3 pane agent bên phải.
- Pane chỉ để **xem**, không có ô nhập (`agent-view` chỉ hiện trạng thái: tên, `working` / `needs you` / `done` kèm thời gian, một dòng mờ (branch) và một dòng kết quả (commit); có dòng `quiet for Nm` khi worker im lặng từ 2 phút, và một dòng đỏ nếu NGISA không nhận được kết quả; không có ô nhập; `AGENT_VIEW_DETAIL=1` bật lại bản đầy đủ). Status line của NGISA có thêm dòng `workers` liệt kê worker (`ngisa-statusline`, `repo-tab` tự gắn vào). Muốn trả lời worker đang `needs you` thì chạy `claude attach <name>` ở một pane trống. Đóng pane **không** dừng agent.

### Vì sao mỗi repo một NGISA, không phải một NGISA chung

Một NGISA chung cho mọi repo làm được, nhưng đừng:
- **Lên plan mù.** Session chỉ load `CLAUDE.md`, settings, skill của thư mục nó khởi động. NGISA đặt ở `~/code` sẽ không đọc `CLAUDE.md` của scanner khi viết plan, mà plan là bước quan trọng nhất.
- **Một context cho tất cả.** Spec, plan, findings của 3 repo dồn vào một cuộc hội thoại, compact sớm, và compact thì mất chi tiết plan trước.
- **Một chỗ kẹt là kẹt hết.** NGISA chờ một permission prompt hoặc chờ reset usage limit thì mọi repo đều đứng.

"Global" vẫn đúng ở chỗ cần: agent, luật, hook, script đều ở user-level, và `claude agents` thấy hết.

### Script (cả hai ở `~/bin`)

`repo-tab`: biến tab hiện tại thành NGISA của repo (mở tab mới nếu tab hiện tại có nhiều pane). Bản mới nhất nằm ở `lab-quickstart.md` bước 3.

```bash
#!/usr/bin/env bash
# usage: repo-tab ~/code/scanner
set -euo pipefail
dir=$(cd "$1" && pwd); name=$(basename "$dir")
[[ -x "$dir/tool/ci_local.sh" ]] || echo "warning: $name has no tool/ci_local.sh, run agent-init there first" >&2
pane=$(wezterm cli spawn --cwd "$dir" -- claude --name "ngisa-$name" --model sonnet)
wezterm cli set-tab-title --pane-id "$pane" "$name"
```

`agent-wall.sh`: thứ duy nhất NGISA gọi để tạo agent. Nó chia đúng tab củan NGISA, nên agent luôn nằm cạnh NGISA sở hữu nó.

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

Lưu ý:
- Tên agent là `<repo>-<task>`: hai repo cùng có task `cache` cũng không đụng nhau, và agent báo cáo về đúng NGISA của repo mình (`@ngisa-scanner`).
- Agent khởi động từ repo, nên worktree nằm trong `.claude/worktrees/` của repo đó. Các repo không bao giờ dùng chung worktree.
- Kiểm tra "tab full" đếm **pane**, không đếm agent đang chạy. Lỡ đóng pane sớm thì agent vẫn chạy, vẫn tốn quota; xem `claude agents`.
- Chưa test trên máy bạn: kiểm tra `wezterm cli list --format json` có in `tab_id` (bản mới đều có).

## 4. Một ngày làm việc

```bash
repo-tab ~/code/my_app        # tab này thành NGISA của repo (tab mới nếu tab này có nhiều pane). Chỉ nói chuyện với nó.
> /superpowers:brainstorming  … → spec. Bạn đọc spec.               # CỔNG 1: ý định
> writing-plans …             → plan + file mỗi task. Bạn duyệt.    # CỔNG 2: plan
> "execute the plan per Orchestrating rules"
   → implementer chạy nền trong worktree, gate-check chạy trên từng cái
   → bạn nhận 1 board (`ngisa-report`) + link draft PR
# CI xanh + gate-check sạch hết → bạn xem tóm tắt PR + golden diff  # CỔNG 3
# Bạn merge.                                                          # CỔNG 4: không đảo ngược
```

Agent view xoá worktree do Claude tạo khi bạn xoá session. Implementer có commit nên việc không mất, nhưng đừng bấm `Ctrl+X` hai lần trên dòng còn thay đổi chưa commit.

## 5. Những việc chỉ bạn làm (không thương lượng)

1. **Spec / tiêu chí nghiệm thu.** Ý định thật của bạn, agent không đoán được.
2. **Duyệt plan, kể cả cách chia task.** Chia sai = conflict nhân với số agent.
3. **`gate-check` báo lỗi.** Bạn quyết định: giữ thay đổi (task có yêu cầu) hoặc trả lại cho worker.
4. **Merge vào main, release, pub.dev, store, remote config, signing, secret.** Hook chặn, chỉ bạn làm được.
5. **Mọi thứ đụng dữ liệu CCCD/PII.** Tự đọc, lần nào cũng đọc.
6. **Cảm giác trên máy thật** (camera, UX quét thẻ). Mỗi feature một lần, lúc cuối.

Còn lại (format, analyze, test, chia việc, `gate-check` từng task) là việc của máy.

## 6. Gói Max: sẽ chạm limit

- Mọi agent nền, subagent, workflow agent của **mọi repo** dùng **chung** quota 5 tiếng và quota tuần. 10 agent song song = tốn quota nhanh ~10 lần. Agent teams ~7 lần một session.
- Sonnet cho cả NGISA và implementer, chỉ dùng Opus khi bạn yêu cầu. Haiku cho việc cơ học. `repo-tab` ghim `--model sonnet` cho NGISA (Sonnet nhanh hơn, NGISA chỉ lên kế hoạch và giao việc; đủ cho plan lớn hay không thì chưa chứng minh). Vẫn ghim `model: sonnet` trong file agent.
- **Tối đa 3 agent mỗi tab repo, khoảng 4–5 agent chạy cùng lúc tổng cộng.** Chạy nặng ở một repo một lúc; repo khác để lên plan hoặc review.
- Bật `autoContinueAtUsageLimit` để chờ reset thay vì hỏng giữa chừng.
- Xem `/usage` (phần attribution) hàng tuần để biết agent nào ăn quota.
- Chạy 3 agent cả ngày mỗi ngày thì sẽ chạm limit tuần. Đó là trần thật của "nhiều agent", không phải tool.

## Dùng lại và dọn worker

Khi worker báo xong, NGISA đóng pane của nó (`agent-wall.sh --close <session>`); session vẫn chạy nền. Ở task kế tiếp NGISA hoặc dùng lại một worker nóng đã xong, hoặc cho nó nghỉ:

- Dùng lại (cùng SendMessage, pane mới bằng `agent-wall.sh <slug> --attach`) khi task mới đụng cùng đường dẫn hoặc thư mục với task trước của worker, hoặc phụ thuộc vào nó, và `worker-ctx <session>` cho `ctx` dưới 100k token, `idle` dưới 55 phút (prompt cache sống một giờ) và `tasks` dưới 3.
- Nếu không: `worker-retire <session>` dừng và xoá session, đóng pane, xoá worktree `warm-N`. Branch của task và commit giữ nguyên để merge. Lệnh từ chối worker chưa `done`/`idle` hoặc worktree còn thay đổi chưa commit.

Vì sao NGISA không compact worker: lệnh slash trong tin nhắn giữa các session chỉ là văn bản, không chạy; và worker `--bg` không tự compact với `--autocompact` hay `autoCompactWindow` (`docs/runs/2026-10-17-compaction-spike.md`). Bạn vẫn có thể `claude attach <worker>` rồi gõ `/compact`. Không có gói bên thứ ba nào giúp được: các công cụ điều phối chỉ quản lý worktree và pane, thư viện nén prompt chạy ở tầng API client.

## Cắt chi phí (2026-10-18)
Lần đo reuse cho thấy NGISA ngang Claude thường về thời gian nhưng tốn khoảng 6 lần token đọc cache (mỗi request đọc lại context nền của session, và một lần chạy NGISA có 5 đến 7 session với khoảng 50 request). Thay đổi:
- Cấu hình worker gọn: worker nóng và worker lạnh `quick`/`direct` khởi động với `--strict-mcp-config --disable-slash-commands --setting-sources project,local --tools "Bash,Edit,Write,Read,Glob,Grep"` (prompt đặt trước các cờ): context nền từ 52,5k xuống 26,1k token (`docs/runs/2026-10-17-trim-spike.md`, `docs/runs/2026-10-18-cost-cut-spikes.md`). Worker `mode: plan` giữ cấu hình đầy đủ (cần skill và subagent). NGISA cũng giữ cấu hình đầy đủ: danh sách tool chỉ tiết kiệm 16% và mất tool `Agent`.
- NGISA ít request hơn: `ngisa-start` (ghi mốc request, base sha, các worker đã xong với ctx/idle/tasks/dirty), `ngisa-spawned` (mốc, pane, bơm worker mới) và `ngisa-collect` (kết quả, mốc, dòng board với trạng thái tự động, chỉ đóng pane khi `ok`) thay cho các chuỗi lệnh đơn lẻ.
- Worker ít request hơn: mẫu gọi cố định trong `agents/implementer.md` (checkout và sửa file song song, một lệnh kiểm tra gộp in mã thoát và 40 dòng cuối, một lệnh commit).
- Worker nóng theo nhu cầu: `repo-tab` khởi động 1 worker nóng (`NGISA_WARM`, mặc định 1); NGISA bơm thêm bằng `agent-warm N` sau khi sizing.
- Chỉ một task tiny hoặc small: NGISA trả lời `one task: run it in plain Claude` và không tốn gì.
Thiết kế `docs/superpowers/specs/2026-10-17-ngisa-cost-cut-design.md`, kế hoạch `docs/superpowers/plans/2026-10-17-ngisa-cost-cut.md`.

## 7. Khi nào KHÔNG nên chạy song song

- Task đụng cùng file (model dùng chung, `pubspec.yaml`, routing, code generate). Cho chạy nối tiếp.
- Feature nhỏ (dưới ~3 task). Một session với `subagent-driven-development` của superpowers nhanh hơn.
- Khi hook/CI gate chưa có. Bạn sẽ ngập trong review.

## 8. Đo lường (gắn với giả thuyết của project)

Project đặt cược: agent song song trong worktree thắng một agent context dài trên task lớn. Kiểm chứng: làm 2 feature tương đương, mỗi cách một cái, ghi lại mỗi feature:
`wall-clock | your minutes | interventions (intent / plan-wrong / merge-conflict / test-gap / taste / irreversible / agent-error) | gate-check FAILs | CI red after merge | % of 5h window used`.
Nếu "merge-conflict" và "plan-wrong" chiếm phần lớn ở bản song song, thì lỗi ở cách chia task, không phải ở agent.

## Thứ tự triển khai

1. Hook verification + `ci_local.sh` (playbook trước) nếu chưa có.
2. `implementer.md` + `agent-init` trong repo đầu tiên.
3. Luật NGISA + hook chặn `PreToolUse` + allowlist quyền.
4. `repo-tab` + `agent-wall.sh`. Chạy một feature với tối đa 2 implementer. Sửa chỗ hỏng.
5. Lên 3 implementer, rồi mở tab repo thứ hai.
6. Agent teams: chỉ thử cho một buổi review hoặc debug. Không dùng cho code.

### Cỡ task và plan mode (2026-10-16)
- Lý do: chỉ có một cửa vào (NGISA), người dùng chỉ xem, và chi phí review phải tương xứng với cỡ task. NGISA chọn cỡ mỗi task bằng một dòng: tiny (không brainstorming, không plan, một worker), small (plan ngắn trong chat), big hoặc mơ hồ (brainstorming, writing-plans, plan được duyệt). Task ở ranh giới thì hỏi người dùng trước.
- Worker chạy `mode: direct` (TDD, checks, không reviewer) hoặc `mode: plan <path>`: `superpowers:subagent-driven-development` trên plan, review sau mỗi task và review cả nhánh ở cuối. Worker làm theo luật ruling của skill: tự quyết xung đột và ghi mỗi quyết định vào ledger, chỉ dừng trong bốn trường hợp của skill (phá hủy, nhạy cảm bảo mật, tác động ngoài worktree, plan hỏng). Worker không merge, không push, không mở PR.
- Ledger không nằm trên bảng; commit body có dòng `ledger:`, NGISA chỉ đưa đường dẫn khi được hỏi.
- Đã kiểm tra 2026-10-16: session nền `--agent implementer` gọi được subagent bằng công cụ Agent.

### Bỏ gate (2026-10-16)
- `gate-check`, `tool/ci_local.sh` và `tool/known_failures.txt` không còn trong kit. Lý do: ở repo thật còn test đỏ cũ, gate đầy đủ đỏ với mọi worker (khoảng 11 phút mỗi lần chạy), nên việc tốt bị đánh dấu `fail` và NGISA tự mở một worker không ai yêu cầu để sửa `main`. Người dùng vốn đọc diff.
- Worker giờ chạy các kiểm tra mà `CLAUDE.md` của repo nêu (format, analyze, test) và báo đã chạy gì ở dòng `gate:`. `agent-init` vẫn tạo `tool/setup.sh` (cài dependency cho worktree mới) và `.worktreeinclude`. Task text nói "verify as the repo's CLAUDE.md says", không bao giờ ghi lệnh runner thô.
- Các mục phía trên nhắc tới `gate-check`, `ci_local.sh`, Stop gate hay merge khi CI xanh là thiết kế cũ; hai khối implementer và orchestrating ở mục 2a và 2c là bản hiện tại.

### Hỏi bằng công cụ gốc (2026-10-16)
- Quyết định không còn là thẻ `ngisa-report ask` dán vào chat: NGISA dùng công cụ `AskUserQuestion` (terminal tự vẽ, mọi độ rộng). Lựa chọn đầu tiên là đề xuất của worker, gắn nhãn `(Recommended)`, mô tả là `why` của nó. `ngisa-report ask` đã bị xóa; `--ask` vẫn còn để bảng hiện dòng `?`. Các khối cũ trong tài liệu này nhắc tới `ngisa-report ask` là thiết kế trước.

### Ngang tốc độ (2026-10-16)
- NGISA đóng dấu các giai đoạn âm thầm bằng `ngisa-report mark <slug> request|spawn|report|decided|pr`; `ngisa-report clear` chuyển sang tin nhắn giao việc, trước stamp `request`. Người dùng chạy `ngisa-report timing` để đọc thời gian từng giai đoạn.
- Giao thức baseline (NGISA so với Claude thường): `docs/runs/2026-10-16-baseline-protocol.md`.

### Worker khởi động sẵn (2026-10-16)
- Lý do: lần chạy baseline cho thấy mỗi worker mất thêm 30-60 giây mà Claude thường không mất (tạo worktree, `worktree-include`, `tool/setup.sh`, tìm `SendMessage`, viết báo cáo 7 dòng). Spec `docs/superpowers/specs/2026-10-16-warm-workers-design.md`, spike `docs/runs/2026-10-16-warm-worker-spike.md` (tiết kiệm khoảng 50 giây trên một task).
- Pool: `agent-warm [n]` (mặc định 2, tối đa 3) chạy sẵn các session implementer rảnh `<repo>-warm-N` (`--bg --agent implementer --model sonnet`): mỗi con tạo `.claude/worktrees/warm-N` (nhánh `warm/N`) từ HEAD, chạy `worktree-include` và `./tool/setup.sh`, rồi dừng ở `warm ready`. `repo-tab` khởi động pool ở nền khi mở tab; `NGISA_WARM=0` tắt nó, số khác đặt kích thước. NGISA nạp lại bằng `agent-warm 1` sau khi dùng một con.
- Giao việc: một lệnh `SendMessage {to: <repo>-warm-N, notify_when_idle: true, message: "Branch: <name>. Base: <sha>. <task text>"}` (`<sha>` = `git rev-parse HEAD`), rồi `agent-wall.sh <slug> --attach <repo>-warm-N`, chỉ mở pane cho session đang chạy. Worker warm chỉ dùng một lần: rảnh = session `done` hoặc `idle` VÀ worktree của nó vẫn ở nhánh `warm/N` (`worker-result .claude/worktrees/warm-N HEAD` in `branch: warm/N`); `agent-warm` nạp pool lại cho đủ n worker rảnh với chỉ số tăng dần. Worker chạy `git checkout -B <name> <base>` trong worktree warm, bỏ qua setup, và chỉ chạy `./tool/setup.sh` một lần nếu test hoặc analyze lỗi vì thiếu package. Không còn worker warm rảnh: khởi động nguội `agent-wall.sh <slug> implementer sonnet "Branch: <name>. Base: <sha>. <task text>"` (task cũng mang Branch/Base), rồi đăng ký thông báo `notify_when_idle` thuần; NGISA tìm worktree của worker nguội bằng `git worktree list --porcelain`.
- Không có báo cáo của worker: worker không gửi tin nào về. Nó kết thúc bằng một commit có phần thân gồm các dòng `checks:`, `unverified:`, `asks:` (thêm `ledger:` ở plan mode) và một dòng cuối ngắn. Khi thông báo idle đến, NGISA chạy `worker-result <worktree> <base>` (số commit, nhánh, thân commit, diff stat) rồi ghi dòng bằng `ngisa-report set`. Không có commit mới, `asks:` khác `none`, hoặc commit cuối thiếu dòng `checks:` là `blocked`; `checks:` đỏ là `fail`.
- `Bash(git -C:*)` cố ý không được cho phép: nó sẽ vượt qua luật chặn `git push`. `worker-result` bọc các lệnh đọc `git -C` thay cho nó.
- Bằng chứng: mức tiết kiệm khoảng 50 giây chỉ là một mẫu, trên hai task khác cỡ (11 so với 14 test), và tổng của Claude thường ở task T3 (1m27s) vẫn thấp hơn NGISA warm (1m53s) trong spike.
- Mục này thay luồng "gửi báo cáo cuối về @ngisa-<repo>" và tin cuối bảy dòng ở các mục phía trên.

### Chế độ gọn (2026-10-17)
- Task tiny và small giờ giao cho worker với `mode: quick`: chỉ làm thay đổi và viết test mà task text liệt kê, không thêm test case, không chứng minh test đỏ trước, mỗi check được liệt kê chạy một lần. `mode: direct` (TDD đầy đủ) chỉ khi người dùng yêu cầu kỹ hoặc TDD; task big vẫn là `mode: plan <path>`.
- Bằng chứng: `docs/runs/2026-10-17-options-abc-tiny.md`, một chỉ dẫn gọn giảm worker từ 1m25s xuống 47s trên task tiny với code và test giống hệt. Kết quả kỳ vọng: chậm hơn Claude thường khoảng 20% ở task tiny (một lần chạy). Chất lượng ở task khó hơn chưa được chứng minh.
