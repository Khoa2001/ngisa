# Report board, asks and worker report (2026-10-16)

Goal: make the NGISA's final report and decision asks fast to scan, show them in colour, and stop caveman drift on long NGISA text. Spec: `docs/superpowers/specs/2026-10-16-report-output-design.md`. Plan: `docs/superpowers/plans/2026-10-16-report-output.md`. Run natively, no commits (the user commits).

## Changes
- `~/bin/ngisa-report` (new, Python 3 stdlib): `set` replaces one task row in `~/.cache/ngisa/report/ngisa-<repo>.json` and prints the plain board; `ask <slug>` prints the ask block (finding, why, `y · n · d diff`, rec); `view` is the read-only coloured refresh loop; `show`, `clear`.
- Board shape B: one line per task (`✓ ✗ ▶ ?`), findings `!` and asks `?` inline, unverified items, legend. Colours are the agent-view palette; every state also has a symbol. Under 60 columns the branch column drops; no line is wider than the pane.
- `agent-wall.sh`: opens `ngisa-report view` once as a strip (`--bottom --percent 20`) under the NGISA pane, after the first worker pane. The strip id is kept in `~/.cache/ngisa/panes/report.<repo>` (a name the worker cleanup glob `<repo>-*` cannot match), dropped when its pane is gone, and left out of the worker list (slot count, "tab full", equal heights).
- `agents/implementer.md`: the final message is six fixed lines, `branch / files / gate / scope / unverified / asks`.
- `orchestrating.md`: step 4 records each report with `ngisa-report set`; step 7 pastes its output unchanged; asks come from `ngisa-report ask`; boards and asks are templates. `settings.local.json` allows `ngisa-report`; `repo-tab` adds one sentence to the system prompt.
- Docs: quickstart script blocks, both orchestrator docs (en, vi), `CONTEXT.md`, `PRODUCT.md`, `docs/README.md`.

## Checked
- `test_ngisa_report.py`: 12 tests (board equals the approved mock, colour palette, widths 1 to 140, narrow branch drop, empty report, ask block, same-slug re-run keeps order and drops old data, corrupt report file, two repos, view and clear), watched failing first, then passing.
- `agent-wall.sh` with a fake `wezterm`: worker 1 opens right of the NGISA (55%), the strip opens once under the NGISA, worker 2 at 50%, worker 3 at 66% of the last worker pane (not the strip), a fourth stops with "tab full", and a stale report id (9) is replaced.
- Quickstart script blocks equal the files (6 of 6, helper in scratch). `bash -n` on `agent-wall.sh`, `repo-tab`; `jq` on `settings.local.json`; lab copies refreshed.
- One real headless Opus NGISA turn in the busy-bees lab (cost 0.24 USD): it ran `ngisa-report set` with the right flags and pasted the board unchanged. Drift: 1 (it invented an ask reason the worker never gave, and added a short numbered note after the board). Fixed by a "never invent a why" clause in step 4. The clause was not re-run, nor were the three later prompt rules.
- Interventions: none by the user.
- Whole-branch review by a fresh Opus reviewer: 0 Critical, 7 Important, 10 Minor. All 7 Important fixed, each with a test that failed first where code was involved: the strip state file was deleted by a worker of a repo whose name is a prefix of another (`demo` vs `demo-web`); `view` ignored the pane height and scrolled on every redraw (now `fit_rows` with `+N more`, no newline after the last row); a red gate without a worker ask had no ask block (default `merge anyway?`, rec `n`); the strip found its repo from the pane cwd (now `env NGISA_REPO`). Prompt rules added to `orchestrating.md`: single-quote text values (`$` and backticks in worker text), `ngisa-report clear` before a new plan, `ngisa-report set --state working` after each spawn or relay. Suite 16/16, wall test OK.
- Minors deferred: wrong-shape JSON crashes `view`; `set` on a corrupt file drops other rows silently; no lock on parallel `set`; wide characters; same-basename repos share a board; the English orchestrator doc still says "one table" at one place and its non-lab allow line lacks `ngisa-report`; diagrams do not show the strip; no one-line status template.

## Not tested
- A real WezTerm tab: the strip under the NGISA pane, live refresh, equal worker heights after the strip opens, the strip when all workers were closed before a new one.
- A whole task with three real workers and the new J report; whether Sonnet keeps to the six lines.
- Whether the NGISA keeps pasting the board unchanged over a long session (count drift in the next real run).
