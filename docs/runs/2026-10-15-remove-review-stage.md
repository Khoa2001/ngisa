# Run: remove the review stage (2026-10-15)

Spec: `docs/superpowers/specs/2026-10-15-remove-review-stage-design.md`. Plan: `docs/superpowers/plans/2026-10-15-remove-review-stage.md`.

## What changed
- Reviewer agent, `-review` panes, APPROVE/BLOCK loop and the reviewer UI in `agent-view` are gone.
- New `gate-check <branch> [base]` script (heredoc in `lab-quickstart.md`, installed to `~/bin`). The NGISA runs it on each worker report and stops on exit 1.
- Docs en + vi, diagrams, site, demo and both GIFs updated. Older run logs untouched.

## Verified (seen in this session)
- Docs and installed scripts matched before the change (drift check on 6 scripts and 4 kit files).
- `gate-check`: 17 cases pass after the final-review fixes (renamed lint config, committed gate file with the worktree removed, weakened `composer.json` test script, new eslint config, branch named like a file, missing base; dependency-only `composer.json` change stays clean). Base 10 cases pass in a throwaway repo (clean, edited `ci_local.sh`, `known_failures.txt` only in worktree, `setup.sh` missing, lint config changed on branch, code-only change, branch without a worktree, stale worktree registration, missing branch, no args). Each was run red first.
- Found by running it on the real lab: a branch whose worktree was deleted by hand gave a false FAIL. Added the stale-worktree case, fixed, re-ran. Lab branches `test/format-type`, `test/form-data-ex`, `fix/moment-edit-save-during-load` now report clean.
- Kit files equal their `lab-quickstart.md` heredocs (diff). `settings.local.json` is valid JSON.
- `bash -n` on the changed shell scripts, `py_compile` on `agent-view` and `ngisa-statusline`.
- `agent-view` `draw()` ran in simple and detail mode on 6 real sessions without error.
- GIFs re-rendered; frames for step 6, 8, 9 (en) and 8 (vi) and the English diagram page inspected.
- `~/lab/busy-bees` synced: `reviewer.md` removed, `implementer.md`, `settings.local.json`, `CLAUDE.local.md` refreshed.

## Final review (fresh Opus-class reviewer)
- 5 Important fixed with tests red first: rename bypass, committed `tool/*` invisible without a worktree, config list too short, exit 2 not handled by the NGISA rule, no re-run after a relay. One Minor re-graded Important and fixed (git errors reported as clean).
- Deferred minors: base equal to branch passes silently; missing-file message wording (fixed anyway with the above); diagram mock shows a gate-check FAIL on a worker pane and a draft PR in the same chat; stale wording in `CONTEXT.md` lines 51, 108, 109 and the index "Yours" promise; demo step 7 maps to flow item 4.

## Not exercised
- A live NGISA run in WezTerm (panes, queue, `tab full` for a 4th agent, `gate-check` called by the NGISA, a forced FAIL on `tool/known_failures.txt`).
- Index pages at mobile width, `index.vi.html` and the Vietnamese diagram page by eye.

## Interventions, FAILs, cost
- Interventions: user chose gate-check (script) over dropping the checks, and chose native execution. No gate-check FAILs in real runs yet.
- Cost: not measured.
