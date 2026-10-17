# Run log: can a background worker compact itself? (2026-10-17, spikes)

Question: when a worker finishes, can it shed context by itself (a lower auto-compact window), so the NGISA can reuse it? Claude Code 2.1.302, Haiku 5.5 sessions started with `claude --bg` in the ngisa repo. Not a speed benchmark; no human wait, nothing pushed. Sessions and the `.claude/spike` files were removed afterwards.

## Method
Each session reads big random-text files with the Read tool. Context per request = `input_tokens + cache_read_input_tokens + cache_creation_input_tokens` of each assistant message in the transcript (`~/.claude/projects/*/<sessionId>.jsonl`). A compaction would show as a drop and as a compact summary marker (`isCompactSummary` / `compact_boundary`); none appeared.

## Results
| Spike | Lever | Context curve (k tokens) | Compaction |
|---|---|---|---|
| 1 | `--autocompact 100000` (+ `CLAUDE_CODE_AUTO_COMPACT_WINDOW=150000` env) | 49 ... 184 in one parallel batch, then the turn ended | none; inconclusive, no request after the threshold |
| 2 | `--settings` with `autoCompactWindow: 100000` | 49 ... 179, same shape | none; inconclusive |
| 3A | `--settings` with `autoCompactWindow: 100000`, one Read per request | 49, 73, 73, 96, 118, 140, 162, 184, 184 | none |
| 3B | `--autocompact 100000`, one Read per request | 49, 73, 73, 96, 118, 140, 162, 184, 184 | none |

Spike 3 had four requests above 100k in each session. Neither lever compacted a `--bg` session.

## Other findings
- The `claude --bg` session is a pre-started daemon process (`claude bg-spare`), so the caller's env vars do not reach it (`ps` shows no `AUTO_COMPACT` variable).
- A cross-session message from the NGISA-style session to a `--bg` session was held and expired unapproved (different permission modes); a slash command in a peer message would not run anyway.
- A worker's context size can be read from its transcript, which is what `worker-ctx` does.

## Decision
No NGISA-driven and no self-triggered compaction for workers. The NGISA reuses a worker while its context is small and retires it otherwise (see `docs/superpowers/specs/2026-10-17-worker-reuse-design.md`). A user can still `claude attach` and run `/compact`.
