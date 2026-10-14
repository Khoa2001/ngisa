# ngisa

The orchestrator kit (NGISA, implementer and reviewer agents, hooks, scripts) and the research docs behind it. Read `CONTEXT.md` first: it has the goals, the decisions so far, and the open items.

## Layout
- `agents/`, `orchestrating.md`, `settings.local.json`, `ngisa-settings.json`: the kit. `make-lab` copies these into `~/lab/<repo>`.
- `docs/`: the source docs, diagrams and run screenshots. `docs/README.md` indexes them.

## Rules
- The kit is generated from the docs (see the kit map in `CONTEXT.md`). When you change one, change the other in the same commit.
- Every doc has a Vietnamese copy (`*.vi.md`, `*.vi.html`). Update both. Keep code, commands and config in English in both.
- Scripts call `fvm flutter` / `fvm dart`, never bare `flutter`.
- Do not touch `~/.claude` or the global CLAUDE.md. Everything here is tested in `~/lab` first.
- Log each run (time, interventions and why, BLOCKs, cost) under `docs/runs/`. These logs are the research data.
