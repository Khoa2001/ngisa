# Giảm thời gian kiểm tra output của agent (superpowers + Claude Max)

Kết luận: thời gian của bạn đang đổ vào việc kiểm tra những thứ máy làm được. Superpowers đã *bảo* agent
phải verify (`verification-before-completion`, các task reviewer trong `subagent-driven-development`),
nhưng đó chỉ là prompt. Prompt thì agent có thể bỏ qua. Hook và CI thì không.
Chuyển mọi check có lệnh chạy được sang hook hoặc CI. Chuyển sự chú ý của bạn từ review diff sang review
spec và plan. Giữ nguyên superpowers; mọi thứ dưới đây chỉ bọc quanh nó.

Bằng chứng tôi đã xem: superpowers `main` (skills + `hooks/hooks.json`, chỉ có hook SessionStart),
`Khoa2001/vn_citizen_id_scan` (`ci.yml`, `melos.yaml`, `CLAUDE.md`, 30 file test Dart, không có
`integration_test/`, không có `.claude/settings.json`, không có unit test Android/iOS nào chạy trong CI).
`owen-host-app` là private nên tôi không đọc được. App công việc trên GitLab cũng không truy cập được.

---

## 1. Hook: ép buộc, không phải nhắc nhở (làm đầu tiên, ~30 phút)

CI của bạn đã fail vì `dart format` sau khi agent commit. Chuyện đó không được phép lặp lại, và sẽ không
lặp lại nếu format là hook thay vì việc agent "nên nhớ".

`.claude/settings.json` trong mỗi repo (commit vào repo để mọi session đều dùng):

```json
{
  "hooks": {
    "PostToolUse": [
      { "matcher": "Edit|Write|MultiEdit",
        "hooks": [{ "type": "command", "command": "\"$CLAUDE_PROJECT_DIR\"/tool/hooks/format_dart.sh" }] }
    ],
    "Stop": [
      { "hooks": [{ "type": "command", "command": "\"$CLAUDE_PROJECT_DIR\"/tool/hooks/gate.sh", "timeout": 600 }] }
    ]
  }
}
```

`tool/hooks/format_dart.sh`: format file vừa bị sửa.

```bash
#!/usr/bin/env bash
f=$(jq -r '.tool_input.file_path // empty')
[[ "$f" == *.dart && "$f" != *.g.dart && "$f" != *.freezed.dart ]] && fvm dart format "$f" >/dev/null
exit 0
```

`tool/hooks/gate.sh`: agent không được nói "xong" khi analyze/test còn đỏ. Stop hook trả exit 2 sẽ gửi
stderr ngược lại cho agent và bắt nó làm tiếp.

```bash
#!/usr/bin/env bash
in=$(cat)
[[ $(jq -r '.stop_hook_active' <<<"$in") == "true" ]] && exit 0   # tránh lặp vô hạn
git diff --quiet HEAD -- '*.dart' && exit 0                        # không có thay đổi Dart
out=$(./tool/ci_local.sh 2>&1) || { echo "$out" | tail -60 >&2; exit 2; }
```

`tool/ci_local.sh`: một script làm đúng từng bước như `ci.yml`. CI cũng gọi chính script này, nên "chạy
local pass" và "CI pass" không thể lệch nhau.

```bash
#!/usr/bin/env bash
set -euo pipefail
melos exec -- dart format . --set-exit-if-changed
melos analyze
melos test
```

Thêm chốt chặn cho `git commit` (hook `PreToolUse` trên `Bash` khớp `git commit`, hoặc git hook bằng
lefthook/pre-commit chạy `ci_local.sh`). Khi đó "commit changes" không thể tạo ra commit đỏ.

Cái này xử lý: lỗi format, câu "test pass" mà không hề chạy test, warning analyzer bạn phải soi bằng mắt.

## 2. Định nghĩa "xong" bằng lệnh cụ thể

`verification-before-completion` hỏi *"lệnh nào chứng minh điều này?"*. Trả lời một lần trong `CLAUDE.md`
để subagent Haiku/Sonnet khỏi đoán:

```md
## Definition of done
- `./tool/ci_local.sh` exits 0 (format, analyze, test)
- New behavior has a test that failed before the change (TDD red step shown)
- Native changes: `./gradlew :vn_citizen_id_scan_android:testDebugUnitTest` / `xcodebuild test` on RunnerTests
- UI changes: golden tests updated and diff reviewed in the PR, not by running the app
- Never mark anything "deferred, needs device" without writing the integration test that would cover it
```

Dòng cuối quan trọng nhất. "Hoãn lại vì cần thiết bị thật" là agent đẩy việc ngược về cho bạn. Bắt nó
viết test, kể cả khi chỉ bạn hoặc CI mới chạy được test đó.

## 3. Dùng Max đúng chỗ, không phải chỗ nào cũng dùng

Bạn đang chạy chủ yếu Haiku. Tức là model rẻ nhất đang ra quyết định đắt nhất (bản plan). Cái plan bạn
phải undo chính là hậu quả.

| Giai đoạn | Model | Lý do |
|---|---|---|
| brainstorming, writing-plans, review spec | Opus | Plan sai = mất cả ngày. Đòn bẩy lớn nhất. |
| implementer subagent | Sonnet | Plan đã chi tiết; thực thi là việc máy móc. |
| task reviewer + review toàn branch cuối cùng | Opus | Reviewer phải mạnh ít nhất bằng người viết. |
| format, đổi tên, boilerplate | Haiku | Đủ dùng. |

Cách đổi đơn giản nhất: `/model opusplan` (Opus ở plan mode, Sonnet khi thực thi). Để cố định model cho
subagent, đặt `CLAUDE_CODE_SUBAGENT_MODEL` hoặc tạo reviewer agent trong `.claude/agents/` với
`model: opus`. Kiểm tra lại với phiên bản Claude Code bạn đang dùng; tên cấu hình hay đổi.

## 4. Đặt cổng kiểm duyệt ở plan, không phải ở diff

Đọc một plan 40 dòng mất 5 phút. Đọc diff 800 dòng mà nó sinh ra mất một tiếng và bạn vẫn sót. Nên:

1. Brainstorm → spec. **Bạn** đọc spec. Đây là cổng con người thật sự: ý định và tiêu chí chấp nhận.
2. writing-plans → plan. Trước khi thực thi, giao cho một subagent Opus mới: "đọc plan này và code thật;
   liệt kê mọi bước sai, thiếu, hoặc mâu thuẫn với codebase." Superpowers có
   `spec-document-reviewer-prompt.md`; làm tương tự cho plan.
3. **Bạn** lướt plan + phản biện của reviewer. Duyệt.
4. subagent-driven-development chạy không cần giám sát. Hook + reviewer bắt phần còn lại.
5. Bạn chỉ xem: trạng thái CI, tóm tắt review cuối, và diff golden. Không đọc từng dòng.

## 5. Biến những thứ "cần người test" thành test được

Phần lớn thời gian của bạn nằm ở đây, và phần lớn sửa được.

**Bug remote config, phải test app bằng tay nhiều vòng.** Đó là thiếu điểm nối để test (test seam). Bọc
remote config sau một interface, inject bản fake, viết widget test cho mọi trạng thái flag (bật, tắt,
thiếu, sai định dạng, fetch lỗi). Khi đó test tái hiện bug là thứ đầu tiên agent viết
(`systematic-debugging` + bước red của TDD). Không bao giờ phải test tay một bug remote config đến lần thứ hai.

**Camera native / EventChannel ("hoãn lại, cần thiết bị").** Tách ra:
- Logic native thuần (`CardImageCropper`, `BoundsSerializer`, `OcrResultSerializer`, `JpegToCGImage`…) không
  cần camera. Unit test bằng JUnit/XCTest. `example/ios/RunnerTests` có sẵn nhưng CI không chạy nó.
- Hợp đồng của channel (cấu trúc event, mã lỗi, hủy) test được từ Dart bằng handler `MethodChannel`/
  `EventChannel` giả lập.
- End-to-end: `integration_test/` trong example app, lấy dữ liệu từ một nguồn frame chỉ có ở bản debug,
  phát lại các frame JPEG đã ghi của một thẻ thật thay vì camera. Agent có thể chạy toàn bộ pipeline trên
  emulator mà không cần phần cứng. Trên CI: `reactivecircus/android-emulator-runner` trên Linux.
  Lưu ý: `example/` không có thư mục `android/`, cần thêm vào.

**Độ đúng của UI.** Golden test (`matchesGoldenFile`, hoặc `alchemist` để golden ổn định trên CI). Agent
cập nhật golden; bạn xem diff ảnh trong PR mất vài giây thay vì mở app.

**Cho agent tự nhìn app.** Khi emulator đang chạy, agent có thể `adb exec-out screencap -p` rồi đọc ảnh
chụp màn hình, hoặc dùng một MCP server tự động hóa mobile. Tốt cho câu hỏi "màn hình có render không",
không thay thế được các test ở trên.

## 6. CI là reviewer thứ hai

Cho agent kết thúc trên branch + PR (`finishing-a-development-branch` đã hỗ trợ sẵn) thay vì commit thẳng
lên main. Sau đó:
- `ci.yml` chạy `tool/ci_local.sh` + unit test native + job integration trên emulator.
- Cài Claude GitHub app / Claude Code Review để mỗi PR có một lượt review độc lập.
- Bạn chỉ merge khi CI xanh và review không có lỗi chặn. Thói quen "commit changes" vẫn giữ được; chỉ là
  commit vào branch.

## 7. Chạy song song trên Max

Max khiến việc chạy nhiều session song song trở nên rẻ: `using-git-worktrees` + mỗi tính năng độc lập một
session. Chỉ làm sau khi xong bước 1–5. Agent song song mà không có cổng tự động chỉ nhân lên lượng việc bạn
phải kiểm tra.

---

## Những gì vẫn phải là con người (mức sàn)

Đừng tự động hóa những thứ này. Chúng rẻ với bạn nhưng sai thì đắt.

- **Ý định:** spec và tiêu chí chấp nhận. Agent không thể biết bạn muốn gì.
- **Duyệt plan:** 5 phút, tránh được việc undo.
- **Cảm nhận/thẩm mỹ trên thiết bị thật:** độ nhạy camera, UX khi quét, cảm giác animation. Một lần mỗi
  tính năng ở cuối, không phải mỗi task.
- **Dữ liệu cá nhân (PII) và quyền riêng tư:** plugin này quét căn cước công dân. Mọi chỗ log, lưu trữ,
  gửi qua mạng dữ liệu thẻ đều phải có người xem, lần nào cũng vậy.
- **Hành động không đảo ngược được:** phát hành lên store, thay đổi remote config production, signing key,
  secret, push lên main/publish lên pub.dev, merge trên GitLab của app công việc.
- **Gạt bỏ ý kiến reviewer:** khi review agent và implementer bất đồng về điều quan trọng, bạn quyết định.

## Thứ tự triển khai

1. Hook + `ci_local.sh` (loại bỏ ngay nhiễu format/analyze/test).
2. "Definition of done" trong `CLAUDE.md`.
3. Opus cho plan và review.
4. Cổng review plan.
5. Test seam: fake remote config, unit test native trong CI, integration test bằng frame ghi sẵn, golden.
6. Branch + PR + Claude review.
7. Worktree song song.

## Đo lường (gắn với mục tiêu của project này)

Mỗi task ghi một dòng: `ngày | repo | task | số lần can thiệp (số lượng + loại: ý định / plan sai /
thiếu test / thẩm mỹ / không đảo ngược / agent lỗi) | số phút bạn bỏ ra kiểm tra`. So sánh hai tuần trước
và sau bước 1–5. Nếu "thiếu test" và "agent lỗi" không giảm, nghĩa là hook hoặc test seam chưa hoạt động.
