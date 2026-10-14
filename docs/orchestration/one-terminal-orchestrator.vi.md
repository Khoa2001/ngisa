# Một cửa sổ, mỗi repo một NGISA, nhiều agent

> Xem hình trước: trang sơ đồ [NGISA và Agent Wall](https://claude.ai/artifact/ENAt99SX1UwoaG5Lm3nzBa). File này là bản chi tiết.
> Code, lệnh, config giữ nguyên tiếng Anh để copy chạy được.

**Tóm lại:**
- Không tự build framework, không cài thêm tool quản lý tmux. Claude Code đã có đủ.
- Mỗi repo có **một NGISA** (session Opus): lên kế hoạch, chia task, giao cho các **implementer** (Sonnet, chạy nền, mỗi con một **worktree** riêng), rồi cho **reviewer** (Opus) kiểm từng kết quả.
- WezTerm: **một cửa sổ, mỗi tab là một repo**. NGISA bên trái, tối đa 3 agent xếp chồng bên phải. Tab đầu là `overview` để xem hết mọi agent.
- Agent teams: **chưa dùng cho code** (thử nghiệm, không có worktree, tốn ~7× token, không chạy được split của WezTerm).
- Chưa có hook + CI gate thì đừng chạy song song: chỉ nhân số thứ bạn phải tự kiểm. Làm [cut-verification-time.md](../verification/cut-verification-time.md) trước.

Đã đối chiếu docs Claude Code hiện tại (10/2026): [agents](https://code.claude.com/docs/en/agents), [agent view](https://code.claude.com/docs/en/agent-view), [agent teams](https://code.claude.com/docs/en/agent-teams), [worktrees](https://code.claude.com/docs/en/worktrees), [workflows](https://code.claude.com/docs/en/workflows), [costs](https://code.claude.com/docs/en/costs). Tên tính năng đổi nhanh, chạy `claude update` trước.

---

## 1. Có gì, dùng cái nào

| Lựa chọn | Ai điều phối | Cách ly file | Kết luận |
|---|---|---|---|
| **Background session** (`claude --bg`) + **subagent** (`~/.claude/agents/*.md`) | NGISA của repo | Mỗi agent một worktree | **Dùng.** Đây chính là cái "NGISA" bạn muốn. |
| **Agent view** (`claude agents`) | Bạn | Worktree tự động | **Dùng làm tab `overview`**: thấy mọi agent, vàng = đang chờ bạn. |
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
| `implementer.md`, `reviewer.md` | `~/.claude/agents/` | 1 lần, mọi repo |
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

Chạy xong: xem lại `.worktreeinclude` có đúng các file secret của repo không, rồi commit.

Repo nào có `.claude/agents/` hoặc `.claude/settings.json` riêng thì cái đó thắng bản user-level. Chỉ dùng khi repo thật sự khác (vd app công ty trên GitLab).

### 2a. Định nghĩa agent

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
1. Run setup first: `fvm flutter pub get` (or `melos bootstrap`), then `dart run build_runner build -d` if the package uses codegen.
2. TDD: write the failing test, show it red, make it green.
3. `./tool/ci_local.sh` must exit 0 before you stop.
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
(would they fail without the change), any edits outside the task's paths, PII/logging of card data,
anything irreversible. Output: APPROVE or BLOCK, then a numbered list of findings with file:line.
Do not edit files.
```

### 2b. Worktree với Flutter

- Mỗi worktree là một bản checkout mới: phải `pub get` + `build_runner` lại. Tốn ổ đĩa và vài phút. Đó là giá của việc cách ly, chấp nhận.
- **Chỉ có một emulator/simulator dùng chung.** Mỗi lúc chỉ một agent được chạy `integration_test`. Unit/widget test chạy song song thoải mái.
- Nếu implementer phải tách nhánh từ feature branch mà NGISA đang đứng (thường là vậy): `"worktree": { "baseRef": "head" }`. Mặc định `"fresh"` tách từ `main`.

### 2c. Luật cho NGISA (`~/.claude/CLAUDE.md`)

```md
## Orchestrating
You are the orchestrator (NGISA) for this repo. You do not write feature code yourself.
1. Spec → plan with superpowers (brainstorming, writing-plans). STOP and wait for my approval of the plan.
2. Split the approved plan into tasks. Each task lists the exact paths it may touch.
   Two tasks that touch the same file are NOT parallel; chain them.
3. Spawn each parallel task with `agent-wall.sh <task-slug> implementer sonnet "<task text>"`.
   Max 3 at once. Never open WezTerm windows, tabs or panes any other way.
4. When a worker's report arrives, run the `reviewer` subagent (in-process) on its branch.
   BLOCK -> message that worker with the findings (same session, same branch). Max 2 rounds, then ask me.
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

### 2d. Hook: bắt buộc, không phải "nhắc nhở"

Trong `~/.claude/settings.json`, thêm vào hook format + Stop gate của playbook trước:

- **`PreToolUse` cho `Bash`**: chặn `git push.*(main|master)`, `git push --force`, `flutter pub publish`, `fastlane`, `firebase deploy`, mọi thứ đụng remote config. Exit 2 kèm lý do. Đây mới là thứ thật sự giữ các thao tác không đảo ngược được ở tay bạn; chỉ dặn trong prompt là không đủ.
- **`Notification`** (`agent_needs_input`, `agent_completed`) → thông báo desktop/điện thoại, khỏi ngồi canh màn hình.
- Cho phép sẵn các lệnh nhàm chán (`fvm flutter test`, `melos *`, `dart format`, `git add/commit/diff/log`, `agent-wall.sh`) trong `permissions.allow`. Không thì agent nền nào cũng đứng ở "Needs input" và song song chỉ là giả.
- **Không** cho phép rộng `Bash(wezterm cli:*)`. Chỉ đi qua `agent-wall.sh` để layout không bị loạn.
- NGISA và báo cáo của worker nói kiểu caveman ultra nhờ hook `SessionStart` + `UserPromptSubmit` chạy `caveman-ultra-hook` (chỉ thêm context, không chặn gì). Code, commit, PR vẫn viết bình thường. Bản luật cho lab, đi PR qua `agent-pr`, nằm trong `lab-quickstart.md`.
- **Không** chạy NGISA hay agent ở `bypassPermissions`: ở chế độ đó, báo cáo từ session khác bị giữ lại chờ duyệt, không tự đến NGISA.

## 3. WezTerm: một cửa sổ, mỗi tab một repo

```
┌ overview ┬ scanner ┬ owen-host-app ┬ work-app ┐
│ ngisa-scanner (Opus)   │ scanner-cache   [Done]     │
│ bạn gõ ý tưởng ở đây    ├────────────────────────────┤
│                        │ scanner-sync    [Working]  │
│                        ├────────────────────────────┤
│                        │ scanner-ui      [Needs you]│
└────────────────────────┴────────────────────────────┘
```

- Tab `overview` chạy `claude agents`: mọi agent của mọi repo. `Ctrl+S` gom theo repo. `Space` xem nhanh, `Enter` vào hẳn, `←` thoát ra. Dòng vàng = đang chờ bạn.
- Mỗi tab repo: NGISA bên trái, tối đa 3 pane agent bên phải.
- Pane chỉ để **xem** (`claude attach`). Đóng pane **không** dừng agent.

### Vì sao mỗi repo một NGISA, không phải một NGISA chung

Một NGISA chung cho mọi repo làm được, nhưng đừng:
- **Lên plan mù.** Session chỉ load `CLAUDE.md`, settings, skill của thư mục nó khởi động. NGISA đặt ở `~/code` sẽ không đọc `CLAUDE.md` của scanner khi viết plan, mà plan là bước quan trọng nhất.
- **Một context cho tất cả.** Spec, plan, kết quả review của 3 repo dồn vào một cuộc hội thoại, compact sớm, và compact thì mất chi tiết plan trước.
- **Một chỗ kẹt là kẹt hết.** NGISA chờ một permission prompt hoặc chờ reset usage limit thì mọi repo đều đứng.

"Global" vẫn đúng ở chỗ cần: agent, luật, hook, script đều ở user-level, và tab `overview` thấy hết.

### Script (cả hai ở `~/bin`)

`repo-tab`: mở một repo thành tab mới, kèm NGISA của nó.

```bash
#!/usr/bin/env bash
# usage: repo-tab ~/code/scanner
set -euo pipefail
dir=$(cd "$1" && pwd); name=$(basename "$dir")
[[ -x "$dir/tool/ci_local.sh" ]] || echo "warning: $name has no tool/ci_local.sh, run agent-init there first" >&2
pane=$(wezterm cli spawn --cwd "$dir" -- claude --name "ngisa-$name" --model opus)
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
  "$prompt  When finished, send your final report to @ngisa-$repo with SendMessage."

if (( ${#others[@]} == 0 )); then
  wezterm cli split-pane --pane-id "$me" --right --percent 55 -- claude attach "$name"
else
  wezterm cli split-pane --pane-id "${others[-1]}" --bottom -- claude attach "$name"
fi
```

Lưu ý:
- Tên agent là `<repo>-<task>`: hai repo cùng có task `cache` cũng không đụng nhau, và agent báo cáo về đúng NGISA của repo mình (`@ngisa-scanner`).
- Agent khởi động từ repo, nên worktree nằm trong `.claude/worktrees/` của repo đó. Các repo không bao giờ dùng chung worktree.
- Kiểm tra "tab full" đếm **pane**, không đếm agent đang chạy. Lỡ đóng pane sớm thì agent vẫn chạy, vẫn tốn quota; xem tab `overview`.
- Chưa test trên máy bạn: kiểm tra `wezterm cli list --format json` có in `tab_id` (bản mới đều có).

## 4. Một ngày làm việc

```bash
repo-tab ~/code/my_app        # tab mới: NGISA của repo. Chỉ nói chuyện với nó.
> /superpowers:brainstorming  … → spec. Bạn đọc spec.               # CỔNG 1: ý định
> writing-plans …             → plan + file mỗi task. Bạn duyệt.    # CỔNG 2: plan
> "execute the plan per Orchestrating rules"
   → implementer chạy nền trong worktree, reviewer kiểm từng cái
   → bạn nhận 1 bảng + link draft PR
# CI xanh + reviewer APPROVE hết → bạn xem tóm tắt PR + golden diff  # CỔNG 3
# Bạn merge.                                                          # CỔNG 4: không đảo ngược
```

Agent view xoá worktree do Claude tạo khi bạn xoá session. Implementer có commit nên việc không mất, nhưng đừng bấm `Ctrl+X` hai lần trên dòng còn thay đổi chưa commit.

## 5. Những việc chỉ bạn làm (không thương lượng)

1. **Spec / tiêu chí nghiệm thu.** Ý định thật của bạn, agent không đoán được.
2. **Duyệt plan, kể cả cách chia task.** Chia sai = conflict nhân với số agent.
3. **Reviewer và implementer cãi nhau quá 2 vòng.** Bạn quyết.
4. **Merge vào main, release, pub.dev, store, remote config, signing, secret.** Hook chặn, chỉ bạn làm được.
5. **Mọi thứ đụng dữ liệu CCCD/PII.** Tự đọc, lần nào cũng đọc.
6. **Cảm giác trên máy thật** (camera, UX quét thẻ). Mỗi feature một lần, lúc cuối.

Còn lại (format, analyze, test, chia việc, review từng task) là việc của máy.

## 6. Gói Max: sẽ chạm limit

- Mọi agent nền, subagent, workflow agent của **mọi repo** dùng **chung** quota 5 tiếng và quota tuần. 10 agent song song = tốn quota nhanh ~10 lần. Agent teams ~7 lần một session.
- Opus chỉ cho NGISA + reviewer. Sonnet cho implementer. Haiku cho việc cơ học. Ghim `model: sonnet` trong file agent, đừng để implementer kế thừa Opus củan NGISA.
- **Tối đa 3 agent mỗi tab repo, khoảng 4–5 agent chạy cùng lúc tổng cộng.** Chạy nặng ở một repo một lúc; repo khác để lên plan hoặc review.
- Bật `autoContinueAtUsageLimit` để chờ reset thay vì hỏng giữa chừng.
- Xem `/usage` (phần attribution) hàng tuần để biết agent nào ăn quota.
- Chạy 3 agent cả ngày mỗi ngày thì sẽ chạm limit tuần. Đó là trần thật của "nhiều agent", không phải tool.

## 7. Khi nào KHÔNG nên chạy song song

- Task đụng cùng file (model dùng chung, `pubspec.yaml`, routing, code generate). Cho chạy nối tiếp.
- Feature nhỏ (dưới ~3 task). Một session với `subagent-driven-development` của superpowers nhanh hơn.
- Khi hook/CI gate chưa có. Bạn sẽ ngập trong review.

## 8. Đo lường (gắn với giả thuyết của project)

Project đặt cược: agent song song trong worktree thắng một agent context dài trên task lớn. Kiểm chứng: làm 2 feature tương đương, mỗi cách một cái, ghi lại mỗi feature:
`wall-clock | your minutes | interventions (intent / plan-wrong / merge-conflict / test-gap / taste / irreversible / agent-error) | reviewer BLOCKs | CI red after merge | % of 5h window used`.
Nếu "merge-conflict" và "plan-wrong" chiếm phần lớn ở bản song song, thì lỗi ở cách chia task, không phải ở agent.

## Thứ tự triển khai

1. Hook verification + `ci_local.sh` (playbook trước) nếu chưa có.
2. `implementer.md` + `reviewer.md` + `agent-init` trong repo đầu tiên.
3. Luật NGISA + hook chặn `PreToolUse` + allowlist quyền.
4. `repo-tab` + `agent-wall.sh`. Chạy một feature với tối đa 2 implementer. Sửa chỗ hỏng.
5. Lên 3 implementer, rồi mở tab repo thứ hai.
6. Agent teams: chỉ thử cho một buổi review hoặc debug. Không dùng cho code.
