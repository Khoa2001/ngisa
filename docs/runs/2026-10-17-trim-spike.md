# Run log: trimming a worker's base context (2026-10-17, spike)

Question: how much of the 52 to 54k tokens every NGISA and worker session starts with can be cut by starting `claude --bg` with trimming flags? Every request re-reads that base, so it multiplies by the request count (see `docs/runs/2026-10-17-worker-reuse-measure.md`: NGISA and workers started at 52.7k to 54.2k, plain Claude at 35.7k). Claude Code 2.1.302, Haiku 5.5, `--agent implementer`, in busy-bees. Not a speed benchmark; sessions and the throwaway worktree were removed afterwards.

## Method
Start a trivial background session per flag set and read the first assistant message's `input + cache_read + cache_creation` from its transcript.

## Results
| Flag set | First-request context | Change |
|---|---|---|
| none (today's worker) | 52,475 | baseline |
| `--strict-mcp-config --disable-slash-commands` | 45,033 | -7.4k |
| + `--setting-sources project,local` | 40,927 | -11.5k |
| + `--exclude-dynamic-system-prompt-sections` | 40,927 | no further change |
| + `--tools "Bash,Edit,Write,Read,Glob,Grep"` | 26,112 | -26.4k (-50%) |

- The trimming flags are honored by `claude --bg`.
- Functional check with the last flag set, in a throwaway worktree: `Write`, `Edit`, `Read` and `Bash` all ran and the task finished (context 26.4k to 27.3k over 6 requests).
- With the tool list the base (26k) is below plain Claude's default (35.7k).

## Gotchas
- `--tools <tools...>` is variadic and swallows a positional prompt that follows it: the first try (`--tools "..." "<prompt>"`) started a session with an empty prompt (state `blocked`). Put the prompt before the flags.
- The `claude --bg` session starts from a pre-spawned daemon process; the flags were applied anyway.
- Not tested: whether the NGISA (needs `SendMessage`, `AskUserQuestion`, probably `ToolSearch`) can run with a tool list; whether skills or MCP are needed by any worker task (the `--disable-slash-commands` and `--strict-mcp-config` flags remove them); effect of `--setting-sources project,local` on the permission allow list (project settings still load; user settings do not).

## Decision
Lever 1 is real: a worker with the tool list starts at about half the tokens. Next: design the full cost cut (this lever plus fewer NGISA and worker requests) and re-measure.
