# Run log: cost-cut spikes (2026-10-18)

Two spikes before building `docs/superpowers/plans/2026-10-17-ngisa-cost-cut.md`. Claude Code 2.1.302, busy-bees base `a18a9f3`. Sessions, the worktree and the branch were removed afterwards.

## 1. NGISA tool list
`claude --bg --model sonnet <prompt> --strict-mcp-config --tools "Bash,Read,Glob,Grep,Skill,SendMessage,AskUserQuestion"`.
- All five tools were present; `SendMessage` to a named peer worked directly (no `ToolSearch` hop) and the peer answered.
- First-request context 45.5k, against 54.2k for the full NGISA profile (-8.7k, -16%). The user's plugin skill listing stays (the NGISA needs superpowers skills for big tasks), so the base stays above the 40k line set in the design.
- Ruling (design call 7): ship the NGISA with the full profile; do not use the tool list. Extra reason: brainstorming and writing-plans can dispatch subagents (`Agent` tool), which the list lacks, and the 16% gain is small against that risk.

## 2. Lean worker on a real task
`claude --bg --agent implementer --model sonnet "<Branch/Base/mode: quick task>" --strict-mcp-config --disable-slash-commands --setting-sources project,local --tools "Bash,Edit,Write,Read,Glob,Grep"`, cold start (so it also created its own worktree).
- Task: tests for `holiday_model.dart`. Result: one commit, 7 tests pass, `checks:`/`unverified:`/`asks:` lines present.
- No permission prompt blocked it: `fvm flutter test`, `fvm dart analyze`, `git worktree add`, `sed -i`, `fvm dart format`, `git commit` all ran, including the chained form `cmd > "$log" 2>&1; echo "exit=$?"; tail -n 40 "$log"` (it saw `exit=3` once from a wrong import, fixed it, then `exit=0`).
- Context 27.8k at the first request, 33.9k at the end; 8 requests for a cold start (a warm start skips the isolation and worktree steps).
- Observation: the session state stayed `working` after the commit (the same Stop-hook lag seen in the reuse measure).

## Decision
Build levers 1 (workers only), 2, 3, 4 and 5. No `--tools` list for the NGISA. No new allow entries needed for the lean worker.
