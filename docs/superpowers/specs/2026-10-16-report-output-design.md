# NGISA and implementer report output

> Superseded in part (2026-10-16): the coloured report pane (`ngisa-report view`, the strip in `agent-wall.sh`) was removed after the first real run; the board stays in the chat and asks are length-limited. See `docs/runs/2026-10-16-report-output.md`.

## Context
The developer reads every result and has to scan and decide fast. Today the NGISA final report is free text and its caveman style slips on long text (findings, decisions; logged twice in `docs/runs/2026-10-15-pane-view-and-caveman.md`). The implementer's final message is a free list. Goal: fixed, scannable shapes, real colour, drift visible as a deviation. Path: architectural (kit + new script + docs en/vi). Branch: `feat/report-output`, never main.

## Agreed
- Final report shape **B** (glyph dashboard): one line per task, asks and findings inline under their row, legend line.
- Colour: a read-only report pane in the existing palette (teal working, amber needs you, green done, red error, rest dim), plus the same report as plain text in chat. The NGISA reply is model text rendered as markdown, so it cannot carry its own ANSI colour; only a script can.
- Mid-run ask **G2**: `✗ task  gate FAIL`, a `!` finding, a one-line why, then `?` with keys (`y · n · d diff`) and `rec`.
- Implementer report **J**: fixed keys `branch / files / gate / scope / unverified / asks` (`asks: none` when empty).
- Caveman drift: templates only, no post-check hook. Fixed skeletons replace prose rules.
- Pane data: the NGISA writes JSON through a script; the pane renders it.

## Data flow
```
worker --J block--> NGISA --ngisa-report set--> ~/.cache/ngisa/report/ngisa-<repo>.json
                      |                                  |
                      | chat: B + G2 (template)          v
                      v                         ngisa-report view (pane)
                    user
```
- `~/bin/ngisa-report`: Python 3, standard library only, like `agent-view`.
  - `set <slug> ...` merges one task row into the session JSON, then prints the plain-text B for all rows. The NGISA pastes that text into chat, so chat and pane have one source.
  - `view` is the read-only refresh loop (about 2 s), full palette, no input.
- `Bash(ngisa-report:*)` goes in `settings.local.json` allow. The JSON lives in the cache dir: no git noise, no code-dir edit.
- The pane is opened by `agent-wall.sh` as a `report` pane: a short strip under the NGISA pane in the left column. It does not count toward the 3 worker slots, the "tab full" check or the equal-height resize of the worker column.

## Schemas
JSON row per task:
```
slug, branch, state (ok|fail|working|blocked), gate, tests,
diff {files, add, del}, findings[], asks[{text, why, rec}], unverified[]
```
Templates (literal skeletons in `orchestrating.md`): B, G2 and a one-line status. The NGISA fills slots; no free prose. Every state has a symbol (`✓ ✗ ? !`) so meaning never depends on colour alone.

## Changes (kit and docs in the same commit; every doc has a .vi copy)
| Area | Change |
|---|---|
| `agents/implementer.md` | final message becomes the J block |
| `orchestrating.md` | step 7 report and ask rules become the B, G2 and status skeletons; call `ngisa-report set` per worker report |
| `settings.local.json` | allow `Bash(ngisa-report:*)` |
| `~/bin/ngisa-report` (new) | `set`, `view`; script block in `docs/orchestration/lab-quickstart.md` |
| `agent-wall.sh`, `repo-tab` | open the report pane; exclude it from slot counts and equalize |
| `docs/orchestration/*` (en+vi), `CONTEXT.md`, `README(.vi).md`, `PRODUCT.md` | document the report pane, J, B, G2; record decision and rationale |
| `docs/diagrams/*`, demo GIFs | add the report pane only if the pane layout appears there |

## Verification
- Replay `ngisa-report view` on fixture JSON at widths 40, 80 and 140: no line wider than the terminal, glyphs and colours match the approved mock.
- `set` merge test: two tasks, one update, one re-run of the same slug.
- `agent-wall.sh` with fake `wezterm`: report pane opens under the NGISA, worker slot counts and "tab full" unchanged.
- One real headless `claude -p` NGISA run in `~/lab`: does it fill the skeleton and paste the `set` output; count drift.
- Quickstart script blocks equal `~/bin`; `bash -n` on shell scripts.
- Log the run under `docs/runs/` with the drift count.
- Not tested until run in WezTerm: pane placement and live refresh.

## Out of scope
- A post-check caveman hook.
- Changing `agent-view` (worker panes stay status-only).
- Moving the kit into `~/.claude`.
