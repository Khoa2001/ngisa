# Product

<!-- impeccable:product-schema 1 -->

## Platform

terminal

## Users
A solo developer who works on many repos at once, mostly Flutter (managed with fvm), on macOS in WezTerm. They hand a task to the NGISA of one repo, then do other work while background workers (implementer) run. They glance at a worker pane to see what it is doing, and step in only when a worker is blocked or a gate fails.

## Product Purpose
NGISA is a kit that lets one orchestrator session per repo run implementer workers in isolated worktrees, behind a local gate, so the developer keeps the human floor (intent, taste, risk, irreversible actions) and the agents do the rest. Success: a task goes in, a branch that passed its gate comes out, and the developer always knows in a few seconds what each worker is doing and whether it needs them. The runs also produce research data (interventions, gate-check FAILs, cost) logged under `docs/runs/`.

## Positioning
The developer watches workers without being able to disturb them: worker panes are read-only views, answers go through `claude attach <name>`. One NGISA per repo, workers listed in its status line.

## Operating Context
- Surfaces: the worker pane (`agent-view`), the NGISA status line with the `workers` roster (`ngisa-statusline`), the report board (`ngisa-report view`, a strip under the NGISA pane), and the pane layout (`agent-wall.sh`). The GitHub Pages site and README are documentation, not the product.
- Panes live in WezTerm; width can be narrow (80 columns) or wide. The pane runs for the whole length of a worker and refreshes about every 2 seconds.
- Data comes from the worker transcript under `~/.claude/projects` (an internal format, read only), `git`, and `claude agents --json`. Phases and gate results are best-effort guesses; the plain feed is always shown.

## Capabilities and Constraints
- Worker panes are read-only: no input box, nothing typed there reaches the worker.
- Language is plain: the feed says what is happening in words, never the raw tool call or JSON.
- Every doc has an English and a Vietnamese copy; code, commands and config stay in English.
- Scripts use only Python 3 standard library and call `fvm flutter` / `fvm dart`, never bare `flutter`.
- The kit files and the docs they come from change together in the same commit.
- Open decisions: how the Flutter gate (about 11 minutes) is scheduled (per task or at merge); the worker shell-edit gap (workers edit through `Bash`, so edits are not tool calls).

## Evidence on Hand
- Real runs and their logs in `docs/runs/`, screenshots in `docs/`. There are no user testimonials or external adopters yet; do not invent any.

## Product Principles
- The developer's attention is the scarce resource: show state first, detail second.
- Say what is happening in plain words, not what tool was called.
- A view that can be wrong must say so (best-effort phases) and fall back to the plain feed.
- Observing must never change the worker: read only.
- Colour carries meaning only (working, needs you, done, error); everything else is dim.

## Accessibility & Inclusion
Meaning must not depend on colour alone: every state also has a word or a symbol. Vietnamese and English readers are both first-class.
