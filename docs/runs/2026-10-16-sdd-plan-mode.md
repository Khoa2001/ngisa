# Run log: sizes and plan mode (2026-10-16)

## Why
User: one input (the NGISA), only watch; subagent-driven-development was the manual choice before this kit. Small tasks must not pay for brainstorming or reviewers.

## Decisions (user)
- Borderline task: the NGISA asks first. Clear cases: it decides and says one line.
- Worker reviews itself like the skill (task review plus final review) in plan mode; direct mode has no reviewers, matching obra: a quick or small task skips the plan, TDD plus verification only.
- Worker mimics the skill's autonomy (rulings, stops only for 4 cases). Rulings live in the worker's ledger, not on the board.

## Checked
- A `claude --bg --agent implementer` session dispatched a general-purpose subagent with the Agent tool (reply `pong`, run in `~/lab/busy-bees`, session removed afterwards).
- Not run: a full plan-mode run (worker doing a multi-task plan, ledger written, final report with `ledger:`), the NGISA sizing a real task, `ngisa-report ask` for a borderline task.

## To check in the next real run
- Does the NGISA say the size line and ask on a borderline task?
- Does a plan-mode worker finish without merge or push, and report a `ledger:` path that exists?
- Token cost of plan mode against direct mode for the same task.
