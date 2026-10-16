# Run log: NGISA fixed a bug inline (2026-10-16)

## What happened
- Session pane `ngisa-busy-bees`, branch `fix/moment-edit-load-lock`, Opus 5.5, auto mode. User pasted a bug report (staff/teacher moment edit: saving before the data loads can save empty images/video).
- The NGISA did the work itself: wrote a repro test through a shell redirect (`grep -v isFormLocked ... > test/.../zz_repro_test.dart`), ran `fvm flutter test`, then "Applying provider fix". No plan, no implementer, no gate-check.

## Cause (checked)
- Most likely the session ran in the real `~/Projects/dotb/busy-bees`, not `~/lab/busy-bees`: the real repo has no `CLAUDE.local.md`, no `.claude/agents/implementer.md`, no `ngisa-settings.json`, so the NGISA was plain Opus with the caveman prompt. The lab copy is complete and its `CLAUDE.local.md` equals `orchestrating.md`. The pane name is `ngisa-<basename>`, the same for both.
- Even in a lab the shell redirect would pass: the edit deny covers `Edit(lib/**)`, not Bash. Known gap, `CONTEXT.md`.
- A bug report is not a "quick" task, and the rules never said who repros it.

## Intervention
- 1 intervention: user stopped and asked why. Counted as an NGISA edit.

## Fix
- `real-init`, `ngisa-guard`, rule changes: see `CONTEXT.md` section "Real repos".

## To check in the next real run
- NGISA spawns an implementer for the same bug report; `ngisa-guard` blocks `sed -i lib/x.dart`, `echo x > test/a.dart`, `fvm flutter test`.
