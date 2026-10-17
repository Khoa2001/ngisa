# NGISA speed parity with plain Claude

## Context
NGISA adds handoff stages plain Claude does not have: NGISA plans, worker runs, report, merge/PR. The user felt the wait in all four. Goal: NGISA not slower than plain Claude on tiny, small, parallel and big tasks, at the same quality. Run logs under `docs/runs/` have almost no per-stage timing and no plain-Claude baseline, so cuts would be blind. Branch: `feat/speed-parity`, never main.

## Agreed (user)
- Measure first, then cut.
- Test bed: busy-bees. One tiny fix plus two independent test tasks (a parallel pair). Each runs once on plain Claude and once on NGISA.
- "Equal" means not slower at all. The parallel pair must beat plain Claude outright.
- Fast lane for tiny and small: the worker runs at once, no plan-OK wait, no long report. Worktree and guards stay.

## My calls (flagged)
- Per task, measure wall-clock per stage (plan, worker, report, merge/PR), user interventions and cost.
- Quality: the user reviews both diffs blind.
- NGISA stamps stage events through `ngisa-report`; plain Claude is timed by hand. Nothing else in the kit changes in this step.
- The fast lane keeps one handoff (NGISA to worker), so tiny and small can get close, not provably "not slower". The baseline shows the real gap; if it stays above zero, revisit "NGISA edits tiny tasks directly".

## Phases
1. Instrument: stage stamps and a timing view in `ngisa-report`, a run-log protocol.
2. Baseline: run the three tasks both ways, log to `docs/runs/`.
3. Cut: from the numbers. Candidates: skip plan-OK for tiny and small (`orchestrating.md` Size), pre-allow `agent-pr` approvals, the worker's first `tool/setup.sh` failure (exit 127), worker re-research (richer task text), the report shape.
4. Re-measure the same tasks.

Phases 2 to 4 need real runs and the user's task picks; they are not in the first plan.

## Out of scope
Global `~/.claude`, a new framework, bringing back the reviewer stage.
