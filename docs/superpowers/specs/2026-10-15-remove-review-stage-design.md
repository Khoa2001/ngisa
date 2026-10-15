# Remove review stage from NGISA kit

## Context
User reviews all work personally, so the reviewer agent (Opus), `-review` panes and APPROVE/BLOCK loop only add latency. Goal: faster workflow. Path: architectural (kit + scripts + docs en/vi + diagrams + demo). Branch: feature branch, never main.

## Agreed
- Remove reviewer agent, review pane, BLOCK loop (max 2 rounds), reviewer verdict UI.
- Gate-file integrity moves to a cheap, non-LLM script check (user choice).
- Keep `docs/runs/*` untouched (research data). Add new run log for this change per project rules.

## New flow
1. User task -> NGISA brainstorms, plan, user approves.
2. Implementers (max 3) work in worktrees: TDD, `ci_local.sh` exit 0, commit on own branch, final report.
3. NGISA on each report: run gate check script (below), then merge branch into local feature branch, run `./tool/ci_local.sh`.
4. Gate check FAIL -> NGISA stops and shows user the diff; no auto-merge.
5. User reviews merged result; `agent-pr` only on user ask; CI + Claude review on remote stays as second reviewer.

## Gate check script (replaces reviewer's integrity role)
- `git diff <main>...<branch> -- tool/ci_local.sh tool/setup.sh tool/known_failures.txt` plus lint/analyzer config paths; any non-empty diff = FAIL, print diff.
- Also flag lines added to `known_failures.txt`.
- Out of scope (was reviewer-only, now human): PII/secrets scan, edits outside task paths, tests-pass-without-change.
- Shipped as a script in `~/bin` via the `lab-quickstart.md` heredocs (same as other scripts); NGISA calls it from `orchestrating.md` step. Allow it in `settings.local.json` permissions. Exact name/location to confirm against lab-quickstart conventions during planning.

## Changes (source docs and kit in same commit; every doc has .vi copy)
| Area | Change |
|---|---|
| `agents/reviewer.md` | delete (and heredoc in `lab-quickstart.md:40-55`, `one-terminal-orchestrator.md` 2a section, `.vi.md`) |
| `orchestrating.md:12-21,33` | drop review step, verdict column, quick-task reviewer mention, caveman wording; add gate-check step |
| `agent-wall.sh` | remove `is_review` pane layout |
| `agent-view` | remove `REVIEW_PHASES`, `VERDICT_RE`, `review_phase`, reviewer chip/strip/verdict; drop `\bBLOCK` from `FAIL_RE` only if unused elsewhere |
| `ngisa-statusline`, `caveman-ultra-hook`, `repo-tab` | comment/text cleanup |
| `CLAUDE.md`, `CONTEXT.md`, `README(.vi).md`, `PRODUCT.md`, `docs/README.md` | reword; CONTEXT kit map and decisions updated, record decision + rationale |
| `docs/orchestration/*` (en+vi), `lab-setup.md` | remove reviewer sections, tree entry; fix stale PreToolUse-hook claims only if touched by edit |
| `docs/verification/cut-verification-time*` | light edit: note reviewer agent dropped in kit, concept discussion stays |
| diagrams `ngisa-and-agent-wall*.html`, `index*.html`, `site.css` | remove Reviewer box, BLOCK loop, `review` step, `--review` colour |
| `ngisa-demo.html` | rewrite scripted timeline without reviewer/BLOCK; regenerate both GIFs via `docs/diagrams/render-demo-gif.sh` |
| `~/lab/busy-bees/.claude/agents/reviewer.md` | outside repo, remove via `make-lab` re-run in lab only; do not touch `~/.claude` |

## Verification
- `grep -ri "review"` over kit + docs: only intended leftovers (CI/Claude remote review, research logs, concept doc).
- Gate script: test pass case, and FAIL case with edited `tool/ci_local.sh` and added `known_failures.txt` line.
- Run `make-lab` into `~/lab`, run a small NGISA task end to end: panes show workers only, gate check runs, merge, `ci_local.sh` passes. Log run under `docs/runs/`.
- Pixel-check updated diagrams and regenerated GIFs (en + vi).
- Scripts use `fvm flutter`/`fvm dart` only.
