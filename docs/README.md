# hand-off docs

Docs from the "hand-off" project: can an agent system ship production software from a spec, and where must a human stay in the loop. The kit files one level up (`agents/`, `orchestrating.md`, `settings.local.json`) are built from these docs.

`.vi.md` / `.vi.html` files are Vietnamese versions of the English file with the same name.

## orchestration/
- `one-terminal-orchestrator.md` (+ `.vi.md`): the main design. One WezTerm window, one NGISA per repo, implementer and reviewer agents in worktrees, hooks, human gates, Max plan limits. Section 2a = `agents/*.md`, 2c = `orchestrating.md`, 2d = `settings.local.json`.
- `lab-setup.md`: try the orchestrator in a lab copy (`~/lab/<repo>`) without touching global config; defines this kit and `make-lab`.
- `lab-quickstart.md`: copy-paste version of the lab setup, including the six `~/bin` scripts (agent-init, repo-tab, agent-wall.sh, make-lab, agent-pr, caveman-ultra-hook).

## verification/
- `cut-verification-time.md` (+ `.vi.md`): cutting the time you spend checking agent output: enforcing hooks, definition of done as commands, gating the plan instead of the diff, CI as second reviewer, what stays human.

## diagrams/
- `ngisa-and-agent-wall.html` (+ `.vi.html`): one-page diagram of the window layout and the idea-to-merge flow. GitHub shows HTML as source, so view it at https://khoa2001.github.io/ngisa/diagrams/ngisa-and-agent-wall.html (GitHub Pages, served from `main` `/docs`; `.nojekyll` keeps the Markdown files raw) or open the file in a browser.
- `ngisa-demo.html`: source of the README GIF. Open with `?step=N&lang=en|vi` for one frame. `render-demo-gif.sh` renders it to `assets/ngisa-demo.gif` and `assets/ngisa-demo.vi.gif` (needs Chrome and `ffmpeg`).

## assets/
- `ngisa-demo.gif` (+ `.vi.gif`): the illustrative mock-up animation shown in the root `README.md` / `README.vi.md`. Not a recording.
- `gate-run-busy-bees.png`: screenshot of a real run (taken before the rename, so the session still reads `gate-busy-bees`) on `~/lab/busy-bees` with two Sonnet workers.

## Repo files at a glance
| Path | What |
|---|---|
| `agents/implementer.md`, `agents/reviewer.md` | Agent definitions |
| `orchestrating.md` | NGISA rules, copied to `CLAUDE.local.md` in a lab clone |
| `settings.local.json` | Permission allow and deny list (push and publish are denied) |
| `CONTEXT.md` | Goals, hypotheses, decisions so far, open items. Start here |
| `CLAUDE.md` | Rules for agents working in this repo |

The kit files are generated from the docs, so change both together. Every doc has a Vietnamese copy (`*.vi.md`, `*.vi.html`), except `lab-setup.md` and `lab-quickstart.md`.

## runs/
- `2026-10-15-stack-agnostic-checks.md`: headless checks of the stack-agnostic implementer on a PHP lab and a Flutter lab. Results, fixes, what was not tested.
- `2026-10-15-readme-gif.md`: how the README GIF was made.
