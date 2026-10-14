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
- `ngisa-and-agent-wall.html` (+ `.vi.html`): one-page diagram of the window layout and the idea-to-merge flow. Open in a browser.

## assets/
- `gate-run-busy-bees.png`: screenshot of a real run (taken before the rename, so the session still reads `gate-busy-bees`) on `~/lab/busy-bees` with two Sonnet workers.
