# hand-off docs

Docs from the "hand-off" project: can an agent system ship production software from a spec, and where must a human stay in the loop. The kit files one level up (`agents/`, `orchestrating.md`, `settings.local.json`) are built from these docs.

`.vi.md` / `.vi.html` files are Vietnamese versions of the English file with the same name.

## orchestration/
- `one-terminal-orchestrator.md` (+ `.vi.md`): the main design. One WezTerm window, one NGISA per repo, implementer agents in worktrees, hooks, human gates, Max plan limits. Section 2a = `agents/*.md`, 2c = `orchestrating.md`, 2d = `settings.local.json`.
- `lab-setup.md`: try the orchestrator in a lab copy (`~/lab/<repo>`) without touching global config; defines this kit and `make-lab`.
- `lab-quickstart.md`: copy-paste version of the lab setup, including the thirteen `~/bin` scripts (agent-tail, real-init, ngisa-guard, agent-init, repo-tab, agent-wall.sh, agent-view, ngisa-statusline, ngisa-report, worktree-include, make-lab, agent-pr, caveman-ultra-hook).

## verification/
- `cut-verification-time.md` (+ `.vi.md`): cutting the time you spend checking agent output: enforcing hooks, definition of done as commands, gating the plan instead of the diff, CI as second reviewer, what stays human.

## diagrams/
- `ngisa-and-agent-wall.html` (+ `.vi.html`): one-page diagram of the window layout and the idea-to-merge flow. GitHub shows HTML as source, so view it at https://khoa2001.github.io/ngisa/diagrams/ngisa-and-agent-wall.html (GitHub Pages, served from `main` `/docs`; `.nojekyll` keeps the Markdown files raw) or open the file in a browser.
- `ngisa-demo.html`: source of the README GIF and the live demo on `index.html` (`?embed=1`, pausable by postMessage). Open with `?step=N&lang=en|vi` for one frame. `render-demo-gif.sh` renders it to `assets/ngisa-demo.gif` and `assets/ngisa-demo.vi.gif` (needs Chrome and `ffmpeg`).

## assets/
- `site.css`: shared look (tokens, type, header, ruled lists, terminal blocks) for `index.html` and the diagram pages. Dark base, light follows the system.
- `ngisa-demo.gif` (+ `.vi.gif`): the illustrative mock-up animation shown in the root `README.md` / `README.vi.md`. Not a recording.
- `gate-run-busy-bees.png`: screenshot of a real run (taken before the rename, so the session still reads `gate-busy-bees`) on `~/lab/busy-bees` with two Sonnet workers.

## Repo files at a glance
| Path | What |
|---|---|
| `agents/implementer.md` | Agent definition |
| `orchestrating.md` | NGISA rules, copied to `CLAUDE.local.md` in a lab clone |
| `settings.local.json` | Permission allow and deny list (push and publish are denied) |
| `CONTEXT.md` | Goals, hypotheses, decisions so far, open items. Start here |
| `CLAUDE.md` | Rules for agents working in this repo |

The kit files are generated from the docs, so change both together. Every doc has a Vietnamese copy (`*.vi.md`, `*.vi.html`), except `lab-setup.md` and `lab-quickstart.md`.

## runs/
- `2026-10-15-stack-agnostic-checks.md`: headless checks of the stack-agnostic implementer on a PHP lab and a Flutter lab. Results, fixes, what was not tested.
- `2026-10-15-readme-gif.md`: how the README GIF was made.
- `2026-10-16-baseline-protocol.md`: speed parity protocol. Three tasks, run order, stage names, blind diff review, the "equal" rule, run tables.
- `2026-10-16-baseline-run1.md`: speed parity baseline run 1 (headless proxy). How it differs from the protocol, and the numbers.
- `2026-10-16-warm-worker-spike.md`: warm worker spike (phase 0). One warm worker, one task (the ColorEx tests).
- `2026-10-17-baseline-run2.md`: speed parity re-measure with warm workers, no report loop and a Sonnet NGISA (headless proxy). Pair: 2m46s wall against plain Claude's 2m43s: a tie, not shown met.
- `2026-10-17-baseline-run3-tiny.md`: replacement tiny task (`capitalize()` empty-string fix), plain Claude against the warm NGISA. Same code, same tests; NGISA 2m07s against 1m09s: slower on tiny tasks.
- `2026-10-17-options-abc-tiny.md`: three ways to speed up a tiny task (plain Claude, inline lane, lean worker). Inline lane ties plain Claude (1m12s against 1m09s), lean worker is within about 20% (1m24s).
- `2026-10-17-bench-medium-parallel.md`: medium parallel bench (three model test files: NGISA about 40% faster), dependent tasks (slower with two workers, a tie with one), and the large plan-mode bench (about 38% faster), with the problems found while running them.
- `2026-10-17-worker-reuse-measure.md`: worker reuse against fresh warm workers against plain Claude, four small tasks in two batches (one run per side): reuse 239s, fresh warm 206s, plain 230s; NGISA about 6x the cache-read tokens of plain.
- `2026-10-18-cost-cut-measure.md`: re-measure after the cost cut: 4 small tasks 194s against plain 230s, 3 parallel tasks 148s against 188s, at an estimated 2.25x and 1.73x plain Claude's cost (was about 4.2x); the 1.5x bar is not met.
- `2026-10-18-cost-cut-spikes.md`: NGISA tool-list profile (works, but only -16% base and no Agent tool: not used) and a lean worker on a real task (works, no permission prompt).
- `2026-10-17-trim-spike.md`: trimming a worker's base context with `--tools`, `--setting-sources`, `--strict-mcp-config`, `--disable-slash-commands`: 52.5k down to 26.1k tokens at the first request, Write/Edit/Read/Bash still work.
- `2026-10-17-compaction-spike.md`: can a background worker compact itself? No: neither `--autocompact` nor `autoCompactWindow` compacted a `--bg` session at 184k tokens; so workers are reused or retired instead.
