# README rewrite and GIF (2026-10-15)

Not an agent run. Records how the README animation was made, so it can be redone.

- `docs/diagrams/ngisa-demo.html` draws one frame per `?step=N&lang=en|vi`. Step durations live in `DURATIONS` in that file.
- `docs/diagrams/render-demo-gif.sh` screenshots each step with headless Chrome (960x540), then `ffmpeg` builds a looping GIF (800 px wide, 128-colour palette). Output: `docs/assets/ngisa-demo.gif` (74 KB) and `ngisa-demo.vi.gif` (75 KB), 19 s loop.
- First try used a 64-colour palette and turned the red "Approve?" / "Your merge." text amber. Fixed with 128 colours and `stats_mode=full`.
- It is a mock-up, labelled "illustrative" in both READMEs. The commands and statuses (`./tool/ci_local.sh`, APPROVE, BLOCK) match the real kit.
- `docs/assets/gate-run-busy-bees.png` is no longer used by the README; `CONTEXT.md` still cites it as run 1 evidence.
