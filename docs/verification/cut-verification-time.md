# Cutting your verification time (superpowers + Claude Max)

Bottom line: your time goes into checking things a machine could check. Superpowers
already *tells* the agent to verify (`verification-before-completion`, task reviewers in
`subagent-driven-development`), but those are prompts. A prompt can be skipped. Hooks and CI cannot.
Move every check that has a command into a hook or CI. Move your own attention from reviewing diffs to
reviewing the spec and plan. Keep superpowers exactly as it is; everything below sits around it.

Evidence I looked at: superpowers `main` (skills + `hooks/hooks.json`, which only has a SessionStart hook),
`Khoa2001/vn_citizen_id_scan` (`ci.yml`, `melos.yaml`, `CLAUDE.md`, 30 Dart test files, no
`integration_test/`, no `.claude/settings.json`, no Android/iOS unit tests wired to CI).
`owen-host-app` is private, so I couldn't read it. The GitLab work app I couldn't reach either.

---

## 1. Hooks: enforce, don't ask (do this first, ~30 min)

Your CI failed on `dart format` after agent commits. That should never happen again, and it won't if
formatting is a hook instead of something the agent should remember.

`.claude/settings.json` in each repo (committed, so every session gets it):

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

`tool/hooks/format_dart.sh`: format whatever file was just touched.

```bash
#!/usr/bin/env bash
f=$(jq -r '.tool_input.file_path // empty')
[[ "$f" == *.dart && "$f" != *.g.dart && "$f" != *.freezed.dart ]] && fvm dart format "$f" >/dev/null
exit 0
```

`tool/hooks/gate.sh`: the agent can't say "done" while analyze/tests are red. Exit 2 on a
Stop hook sends stderr back to the agent and makes it keep working.

```bash
#!/usr/bin/env bash
in=$(cat)
[[ $(jq -r '.stop_hook_active' <<<"$in") == "true" ]] && exit 0   # no infinite loop
git diff --quiet HEAD -- '*.dart' && exit 0                        # nothing Dart changed
out=$(./tool/ci_local.sh 2>&1) || { echo "$out" | tail -60 >&2; exit 2; }
```

`tool/ci_local.sh`: one script that mirrors `ci.yml` step for step. CI calls this exact script too,
so "passes locally" and "passes CI" can't drift apart.

```bash
#!/usr/bin/env bash
set -euo pipefail
melos exec -- dart format . --set-exit-if-changed
melos analyze
melos test
```

Add a `git commit` guard too (a `PreToolUse` hook on `Bash` matching `git commit`, or a lefthook/pre-commit
git hook running `ci_local.sh`). Then "commit changes" can't produce a red commit.

What this kills: format failures, "tests pass" claims that weren't run, analyzer warnings you spot by eye.

## 2. Tell the agent what "done" means, in commands

`verification-before-completion` asks *"what command proves this claim?"* Answer it once in
`CLAUDE.md` so a Haiku/Sonnet subagent doesn't guess:

```md
## Definition of done
- `./tool/ci_local.sh` exits 0 (format, analyze, test)
- New behavior has a test that failed before the change (TDD red step shown)
- Native changes: `./gradlew :vn_citizen_id_scan_android:testDebugUnitTest` / `xcodebuild test` on RunnerTests
- UI changes: golden tests updated and diff reviewed in the PR, not by running the app
- Never mark anything "deferred, needs device" without writing the integration test that would cover it
```

The last line matters. "Deferred because it needs a device" is the agent handing the work back to you.
Make it write the test even if only you or CI can run it.

## 3. Use Max on the right stages, not everywhere

You run mostly Haiku. That is the cheapest model doing the most expensive decision (the plan). The plan
you had to undo is what you get from that.

| Stage | Model | Why |
|---|---|---|
| brainstorming, writing-plans, spec review | Opus | Wrong plan = wasted day. Highest leverage. |
| implementer subagents | Sonnet | Plan is detailed; execution is mechanical. |
| task reviewer + final whole-branch review | Opus | Reviewer must be at least as strong as the writer. |
| formatting, renames, boilerplate | Haiku | Fine. |

Simplest switch: `/model opusplan` (Opus in plan mode, Sonnet for execution). To pin subagents, set
`CLAUDE_CODE_SUBAGENT_MODEL` or define a reviewer agent in `.claude/agents/` with `model: opus`.
Check these against your current Claude Code version; names move.

## 4. Move your gate to the plan, not the diff

Reviewing a 40-line plan takes 5 minutes. Reviewing the 800-line diff it produces takes an hour and you
still miss things. So:

1. Brainstorm → spec. **You** read the spec. This is the real human gate: intent and acceptance criteria.
2. writing-plans → plan. Before execution, dispatch a fresh Opus subagent: "read this plan and the actual
   code; list every step that's wrong, missing, or contradicts the codebase." Superpowers has
   `spec-document-reviewer-prompt.md`; do the same for the plan.
3. **You** skim the plan + the reviewer's objections. Approve.
4. subagent-driven-development runs unattended. Hooks + reviewers catch the rest.
5. You look at: CI status, the final review summary, and the golden diffs. Not every line.

## 5. Make the "needs a human to test" stuff testable

This is where most of your time goes, and it's mostly fixable.

**Remote config bug, several rounds of manual app testing.** That's a missing test seam. Wrap remote
config behind an interface, inject a fake, and write widget tests for every flag state (on, off, missing,
malformed, fetch failed). Then the regression test for the bug is the first thing the agent writes
(`systematic-debugging` + TDD red step). You should never test a remote-config bug by hand twice.

**Native camera / EventChannel ("deferred, needs a device").** Split it:
- Pure native logic (`CardImageCropper`, `BoundsSerializer`, `OcrResultSerializer`, `JpegToCGImage`…) needs
  no camera. Unit test it with JUnit/XCTest. `example/ios/RunnerTests` exists but nothing runs it in CI.
- The channel contract (event shapes, error codes, cancellation) can be tested from Dart with mocked
  `MethodChannel`/`EventChannel` handlers.
- End-to-end: `integration_test/` in the example app, fed by a debug-only frame source that plays
  recorded JPEG frames of a real card instead of the camera. The agent can then run the full pipeline on an
  emulator with no hardware. In CI: `reactivecircus/android-emulator-runner` on Linux.
  Note: `example/` has no `android/` folder, so add it.

**UI correctness.** Golden tests (`matchesGoldenFile`, or `alchemist` for CI-stable goldens). The agent
updates goldens; you review image diffs in the PR in seconds instead of launching the app.

**Letting the agent look at the app itself.** With an emulator running, the agent can
`adb exec-out screencap -p` and read the screenshot, or use a mobile automation MCP server. Good for
"does the screen render", not a replacement for the tests above.

## 6. CI as the second reviewer

Have the agent finish on a branch + PR (`finishing-a-development-branch` already offers this) instead of
committing straight to main. Then:
- `ci.yml` runs `tool/ci_local.sh` + native unit tests + the emulator integration job.
- Install the Claude GitHub app / Claude Code Review so every PR gets an independent review pass.
- You merge only when CI is green and the review has no blocking findings. Your "commit changes" habit
  still works; it just commits to a branch.

## 7. Parallel work on Max

Max makes parallel sessions affordable: `using-git-worktrees` + one session per independent feature. Only
do it after steps 1–5. Parallel agents without automated gates just multiply the amount you have to check.

---

## What stays human (the floor)

Don't automate these away. They're cheap for you and expensive to get wrong.

- **Intent:** the spec and its acceptance criteria. Agents can't know what you meant.
- **Plan approval:** 5 minutes, saves the undo.
- **Taste/feel on a real device:** camera responsiveness, scan UX, animation feel. Once per feature at the
  end, not per task.
- **PII and privacy:** this plugin scans national ID cards. Logging, storage, and network of card data get
  human eyes every time.
- **Irreversible actions:** store releases, production remote-config changes, signing keys, secrets,
  pushing to main/publishing to pub.dev, GitLab merges on the work app.
- **Overriding a reviewer:** if the review agent and the implementer disagree on something load-bearing,
  you decide.

## Order to roll out

1. Hooks + `ci_local.sh` (kills format/analyze/test noise immediately).
2. "Definition of done" in `CLAUDE.md`.
3. Opus for plans and reviews.
4. Plan-review gate.
5. Test seams: remote config fake, native unit tests in CI, recorded-frame integration test, goldens.
6. Branch + PR + Claude review.
7. Parallel worktrees.

## Measure it (ties to this project's goal)

Per task, log one line: `date | repo | task | interventions (count + category: intent / plan-wrong /
test-gap / taste / irreversible / agent-error) | minutes you spent checking`. Compare two weeks before and
after steps 1–5. If "test-gap" and "agent-error" don't drop, the hooks or test seams aren't working.
