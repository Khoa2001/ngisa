# NGISA and implementer report output Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Give the NGISA a fixed, scannable report (shape B, glyph dashboard) shown as a coloured read-only pane and as identical plain text in chat, fixed ask blocks (G2) and a fixed implementer report (J).

**Architecture:** A new Python 3 script `~/bin/ngisa-report` stores one JSON row per task under `~/.cache/ngisa/report/ngisa-<repo>.json`. `set` merges a row and prints the plain board (the NGISA pastes it into chat), `ask` prints a G2 block, `view` is the coloured refresh loop for a pane. `agent-wall.sh` opens that pane once as a strip under the NGISA pane, outside the worker slot count. `orchestrating.md` and `agents/implementer.md` carry the fixed skeletons. Every kit change lands in the docs in the same change.

**Tech Stack:** Python 3 standard library (script and `unittest`), bash + jq (`agent-wall.sh`, fake `wezterm` for tests), Markdown docs.

**Spec:** `docs/superpowers/specs/2026-10-16-report-output-design.md`

## Global Constraints
- Python 3 standard library only; scripts never call bare `flutter` (use `fvm flutter` / `fvm dart`, not needed here).
- macOS bash 3.2: no `mapfile`, no negative array indexes in `agent-wall.sh`.
- Palette is exactly the one in `~/bin/agent-view`: TEAL `38;2;60;196;178`, AMBER `38;2;231;164;71`, GREEN `38;2;76;198;138`, RED `38;2;255;107;95`, everything else dim (`2`) or plain. Every state also has a symbol: `✓ ✗ ▶ ? !`.
- No em dash anywhere; use a plain dash. Code, commands and config stay English.
- The kit is generated from the docs: the same change updates both. Script blocks in `docs/orchestration/lab-quickstart.md` must equal the files in `~/bin` and the kit (checked in Task 4).
- Do not touch `~/.claude` or the global CLAUDE.md. Test in `~/lab` only.
- Do NOT commit or push at any step (global rule: the user says when). Leave all changes in the working tree on branch `feat/report-output`.
- Never write to `CHANGELOG.md` or other generated files.
- Test scratch dirs live under `${TMPDIR:-/tmp}`.

## Review Focus
- Pane narrower than any column (width 10, even 1): no crash, no line wider than the pane.
- Report file corrupt or half-written (NGISA killed): `view` shows `no report yet`, `set` starts a clean report instead of a traceback.
- A worker re-run after a fix: `set` with the same slug replaces the row in place (order kept, old findings and asks gone), never duplicates it.
- A report pane that was closed or whose id is stale: `agent-wall.sh` drops the stale id and opens a new strip; the strip never counts toward "tab full" or the equal-height resize.
- Two repos at once: each repo has its own report file, no cross-talk.

Each line has a test in the task that owns the code (Task 1: narrow, corrupt, re-run, two repos; Task 2: stale pane).

---

### Task 1: `ngisa-report` script with unit tests

**Files:**
- Create: `~/bin/ngisa-report`
- Create (scratch test): `${TMPDIR:-/tmp}/ngisa-report-test/test_ngisa_report.py`

**Interfaces:**
- Produces (CLI, used by Tasks 2-4):
  - `ngisa-report set <slug> --state ok|fail|working|blocked [--base B] [--branch X] [--gate G] [--tests T] [--diff FILES ADD DEL] [--finding F]... [--ask "text|why|rec"]... [--unverified U]...` - replaces the row for `<slug>`, prints the plain board.
  - `ngisa-report show [--color]` - prints the board (exit 1 `no report` if none).
  - `ngisa-report ask <slug>` - prints the G2 block for each ask of `<slug>` (exit 1 if the slug or its asks are missing).
  - `ngisa-report view [--once]` - read-only refresh loop (2 s), full colour, width from the terminal (`COLUMNS` honoured). `--once` prints one frame.
  - `ngisa-report clear` - deletes this repo's report.
- Env: `NGISA_REPO` overrides the repo name (tests), `XDG_CACHE_HOME` the cache root, `NO_COLOR` turns colour off in `view`.
- Python module API used by tests: `board(data, width, color) -> list[str]`, `ask_block(task, color) -> list[str]`.

- [ ] **Step 1: Write the failing tests**

```bash
T=${TMPDIR:-/tmp}/ngisa-report-test; mkdir -p "$T"
```

Create `$T/test_ngisa_report.py`:

```python
import importlib.machinery, importlib.util, json, os, re, subprocess, sys, tempfile, unittest

BIN = os.path.expanduser("~/bin/ngisa-report")
ANSI = re.compile(r"\x1b\[[0-9;?]*[A-Za-z]")
GREEN, RED = "38;2;76;198;138", "38;2;255;107;95"


def load_module():
    loader = importlib.machinery.SourceFileLoader("ngisa_report", BIN)
    spec = importlib.util.spec_from_loader("ngisa_report", loader)
    mod = importlib.util.module_from_spec(spec)
    loader.exec_module(mod)
    return mod


DATA = {
    "repo": "demo", "base": "feat/health-utils",
    "tasks": [
        {"slug": "util-media", "branch": "feat/util-media", "state": "ok", "gate": "exit 0", "tests": "12 pass",
         "diff": {"files": 1, "add": 69, "del": 0}, "findings": [], "asks": [], "unverified": ["no device run"]},
        {"slug": "util-text", "branch": "feat/util-text", "state": "ok", "gate": "exit 0", "tests": "9 pass",
         "diff": {"files": 1, "add": 114, "del": 0}, "findings": [],
         "asks": [{"text": "dart:45-47 untested. add test?", "why": "age bug could ship", "rec": "y"}], "unverified": []},
        {"slug": "util-color", "branch": "feat/util-color", "state": "fail", "gate": "gate FAIL", "tests": "",
         "diff": {"files": 2, "add": 40, "del": 3}, "findings": ["analysis_options.yaml changed"],
         "asks": [{"text": "revert?", "why": "lint rule loosened", "rec": "y"}], "unverified": []},
    ],
}

EXPECTED_BOARD = "\n".join([
    "NGISA  demo  feat/health-utils",
    " ✓ util-media  feat/util-media  12 pass  +69 −0",
    " ✓ util-text   feat/util-text   9 pass  +114 −0",
    "     ? dart:45-47 untested. add test? [rec y]",
    " ✗ util-color  feat/util-color  gate FAIL  +40 −3",
    "     ! analysis_options.yaml changed",
    "     ? revert? [rec y]",
    "",
    " unverified: util-media no device run",
    " ✓ ok  ✗ fail  ▶ working  ? asks you  ! finding",
])


def vis(s):
    return len(ANSI.sub("", s))


class BoardTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.m = load_module()

    def test_plain_board_matches_mock(self):
        self.assertEqual("\n".join(self.m.board(DATA, None, False)), EXPECTED_BOARD)

    def test_colour_board_uses_palette(self):
        out = "\n".join(self.m.board(DATA, None, True))
        self.assertIn(f"\033[{GREEN}m✓", out)
        self.assertIn(f"\033[{RED}m✗", out)
        self.assertEqual(ANSI.sub("", out), EXPECTED_BOARD)

    def test_width_never_exceeded(self):
        for width in (1, 5, 10, 40, 80, 140):
            for color in (False, True):
                for ln in self.m.board(DATA, width, color):
                    self.assertLessEqual(vis(ln), width, (width, ln))

    def test_branch_column_dropped_when_narrow(self):
        self.assertNotIn("feat/util-media", "\n".join(self.m.board(DATA, 40, False)))
        self.assertIn("feat/util-media", "\n".join(self.m.board(DATA, 80, False)))

    def test_empty_report(self):
        self.assertEqual(self.m.board({"repo": "demo", "tasks": []}, None, False), ["NGISA  demo", " no tasks yet"])

    def test_ask_block_plain(self):
        t = DATA["tasks"][2]
        self.assertEqual("\n".join(self.m.ask_block(t, False)), "\n".join([
            "✗ util-color  gate FAIL",
            "  ! analysis_options.yaml changed",
            "  why: lint rule loosened",
            "  ? revert?   y · n · d diff   rec y",
        ]))


class CliTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.env = dict(os.environ, XDG_CACHE_HOME=self.tmp, NGISA_REPO="demo", COLUMNS="80", NO_COLOR="1")

    def run_cli(self, *args, repo=None):
        env = dict(self.env)
        if repo:
            env["NGISA_REPO"] = repo
        return subprocess.run([sys.executable, BIN, *args], capture_output=True, text=True, env=env)

    def report_file(self, repo="demo"):
        return os.path.join(self.tmp, "ngisa", "report", f"ngisa-{repo}.json")

    def test_set_merges_and_replaces_in_place(self):
        self.run_cli("set", "a", "--state", "ok", "--branch", "feat/a", "--tests", "3 pass")
        self.run_cli("set", "b", "--state", "fail", "--branch", "feat/b", "--gate", "gate FAIL",
                     "--finding", "cfg changed", "--ask", "revert?|why|y")
        r = self.run_cli("set", "a", "--state", "fail", "--branch", "feat/a", "--gate", "gate FAIL")
        slugs = [t["slug"] for t in json.load(open(self.report_file()))["tasks"]]
        self.assertEqual(slugs, ["a", "b"])
        row_a = json.load(open(self.report_file()))["tasks"][0]
        self.assertEqual(row_a["state"], "fail")
        self.assertEqual(row_a["tests"], "")
        self.assertIn("✗ a", r.stdout)
        self.assertEqual(r.returncode, 0)

    def test_set_prints_plain_board_with_base(self):
        r = self.run_cli("set", "a", "--base", "main", "--state", "ok", "--branch", "feat/a", "--tests", "3 pass",
                         "--diff", "1", "5", "2", "--unverified", "no device")
        self.assertIn("NGISA  demo  main", r.stdout)
        self.assertIn(" ✓ a  feat/a  3 pass  +5 −2", r.stdout)
        self.assertIn(" unverified: a no device", r.stdout)
        self.assertNotIn("\033", r.stdout)

    def test_ask_parse_and_missing(self):
        self.run_cli("set", "a", "--state", "blocked", "--ask", "keep?|it is old|n", "--ask", "plain ask")
        r = self.run_cli("ask", "a")
        self.assertIn("  why: it is old", r.stdout)
        self.assertIn("  ? keep?   y · n · d diff   rec n", r.stdout)
        self.assertIn("  ? plain ask   y · n · d diff", r.stdout)
        self.assertEqual(self.run_cli("ask", "zzz").returncode, 1)
        self.run_cli("set", "c", "--state", "ok")
        self.assertEqual(self.run_cli("ask", "c").returncode, 1)

    def test_corrupt_report_is_survivable(self):
        os.makedirs(os.path.dirname(self.report_file()))
        open(self.report_file(), "w").write('{"tasks": [{"slug": "a", ')
        self.assertIn("no report yet", self.run_cli("view", "--once").stdout)
        r = self.run_cli("set", "x", "--state", "ok")
        self.assertEqual(r.returncode, 0)
        self.assertEqual([t["slug"] for t in json.load(open(self.report_file()))["tasks"]], ["x"])

    def test_two_repos_do_not_share_a_report(self):
        self.run_cli("set", "a", "--state", "ok", repo="one")
        self.run_cli("set", "b", "--state", "ok", repo="two")
        self.assertEqual([t["slug"] for t in json.load(open(self.report_file("one")))["tasks"]], ["a"])
        self.assertEqual([t["slug"] for t in json.load(open(self.report_file("two")))["tasks"]], ["b"])

    def test_view_once_and_clear(self):
        self.assertIn("no report yet", self.run_cli("view", "--once").stdout)
        self.run_cli("set", "a", "--state", "working", "--branch", "feat/a")
        out = self.run_cli("view", "--once").stdout
        self.assertIn("▶ a", out)
        self.assertTrue(all(vis(ln) <= 80 for ln in out.splitlines()))
        self.run_cli("clear")
        self.assertFalse(os.path.exists(self.report_file()))
        self.assertEqual(self.run_cli("show").returncode, 1)


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `python3 -I ${TMPDIR:-/tmp}/ngisa-report-test/test_ngisa_report.py 2>&1 | tail -8`
Expected: FAIL / ERROR with `FileNotFoundError` for `~/bin/ngisa-report` (the script does not exist yet).

- [ ] **Step 3: Write the script**

Create `~/bin/ngisa-report`:

```python
#!/usr/bin/env python3
"""Report board for the NGISA: one row per worker task, asks and findings inline.

  ngisa-report set <slug> --state ok|fail|working|blocked [--base B] [--branch X] [--gate G] [--tests T]
                  [--diff FILES ADD DEL] [--finding F]... [--ask "text|why|rec"]... [--unverified U]...
      replace the row for <slug>, then print the plain-text board (paste it into chat unchanged)
  ngisa-report show [--color]   print the board
  ngisa-report ask <slug>       print the ask block (G2) for each ask of <slug>
  ngisa-report view [--once]    read-only refresh loop for a pane, full colour
  ngisa-report clear            delete this repo's report

One report per repo: ~/.cache/ngisa/report/ngisa-<repo>.json (XDG_CACHE_HOME respected). Python 3 standard library only.
"""
import argparse, json, os, shutil, subprocess, sys, tempfile, time

# same four semantic colours as agent-view; everything else is dim or plain. Every state also has a symbol.
TEAL, AMBER, GREEN, RED = "38;2;60;196;178", "38;2;231;164;71", "38;2;76;198;138", "38;2;255;107;95"
DIM, BOLD = "2", "1"
STATES = {"ok": ("✓", GREEN), "fail": ("✗", RED), "working": ("▶", TEAL), "blocked": ("?", AMBER)}
LEGEND = "✓ ok  ✗ fail  ▶ working  ? asks you  ! finding"


def paint(code, text, color):
    return f"\033[{code}m{text}\033[0m" if color and code else text


def repo_name():
    env = os.environ.get("NGISA_REPO")
    if env:
        return env
    try:
        out = subprocess.run(["git", "rev-parse", "--path-format=absolute", "--git-common-dir"],
                             capture_output=True, text=True, check=True).stdout.strip()
        return os.path.basename(os.path.dirname(out.rstrip("/")))
    except Exception:
        return os.path.basename(os.getcwd())


def report_path(repo):
    base = os.environ.get("XDG_CACHE_HOME") or os.path.expanduser("~/.cache")
    return os.path.join(base, "ngisa", "report", f"ngisa-{repo}.json")


def load(path):
    try:
        with open(path) as f:
            data = json.load(f)
        return data if isinstance(data, dict) and isinstance(data.get("tasks"), list) else None
    except (OSError, ValueError):
        return None


def save(path, data):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=os.path.dirname(path), suffix=".tmp")
    with os.fdopen(fd, "w") as f:
        json.dump(data, f, ensure_ascii=False, indent=1)
    os.replace(tmp, path)


def detail(t):
    if t.get("state") == "fail":
        return t.get("gate") or t.get("tests") or ""
    return t.get("tests") or t.get("gate") or ""


def diff_text(t):
    d = t.get("diff")
    return f"+{d['add']} −{d['del']}" if d else ""


def line(parts, width, color):
    """Join (colour code, text) parts; cut at `width` visible characters with an ellipsis. width None = no cut."""
    out, used = [], 0
    for code, text in parts:
        if width is not None:
            room = width - used
            if room <= 0:
                break
            if len(text) > room:
                text = text[: room - 1] + "…"
        out.append(paint(code, text, color))
        used += len(text)
    s = "".join(out)
    return s if color else s.rstrip()


def board(data, width, color):
    tasks = data.get("tasks") or []
    head = [(BOLD + ";" + TEAL, "NGISA"), (None, "  " + data.get("repo", ""))]
    if data.get("base"):
        head.append((DIM, "  " + data["base"]))
    lines = [line(head, width, color)]
    if not tasks:
        lines.append(line([(DIM, " no tasks yet")], width, color))
        return lines
    sw = max(len(t["slug"]) for t in tasks)
    bw = max(len(t.get("branch", "")) for t in tasks)
    show_branch = width is None or width >= 60
    for t in tasks:
        glyph, code = STATES.get(t.get("state"), ("·", DIM))
        parts = [(None, " "), (code, glyph), (None, " "), (BOLD, t["slug"].ljust(sw))]
        if show_branch:
            parts.append((DIM, "  " + t.get("branch", "").ljust(bw)))
        if detail(t):
            parts.append((None, "  " + detail(t)))
        if diff_text(t):
            parts.append((DIM, "  " + diff_text(t)))
        lines.append(line(parts, width, color))
        for f in t.get("findings", []):
            lines.append(line([(None, "     "), (RED, "! "), (None, f)], width, color))
        for a in t.get("asks", []):
            p = [(None, "     "), (AMBER, "? "), (None, a["text"])]
            if a.get("rec"):
                p.append((GREEN, f" [rec {a['rec']}]"))
            lines.append(line(p, width, color))
    lines.append("")
    for t in tasks:
        for u in t.get("unverified", []):
            lines.append(line([(DIM, f" unverified: {t['slug']} {u}")], width, color))
    lines.append(line([(DIM, " " + LEGEND)], width, color))
    return lines


def ask_block(t, color):
    glyph, code = STATES.get(t.get("state"), ("·", DIM))
    out = [line([(code, f"{glyph} {t['slug']}"), (None, "  " + detail(t))], None, color)]
    for f in t.get("findings", []):
        out.append(line([(None, "  "), (RED, "! "), (None, f)], None, color))
    for a in t.get("asks", []):
        if a.get("why"):
            out.append(line([(DIM, f"  why: {a['why']}")], None, color))
        p = [(None, "  "), (AMBER, "? "), (None, a["text"]), (DIM, "   y · n · d diff")]
        if a.get("rec"):
            p.append((GREEN, f"   rec {a['rec']}"))
        out.append(line(p, None, color))
    return out


def parse_ask(raw):
    text, why, rec = (raw.split("|", 2) + ["", ""])[:3]
    return {"text": text.strip(), "why": why.strip(), "rec": rec.strip()}


def cmd_set(a):
    repo = repo_name()
    path = report_path(repo)
    data = load(path) or {"repo": repo, "tasks": []}
    data["repo"] = repo
    if a.base:
        data["base"] = a.base
    row = {"slug": a.slug, "branch": a.branch or "", "state": a.state, "gate": a.gate or "", "tests": a.tests or "",
           "diff": {"files": a.diff[0], "add": a.diff[1], "del": a.diff[2]} if a.diff else None,
           "findings": a.finding or [], "asks": [parse_ask(x) for x in a.ask or []], "unverified": a.unverified or []}
    for i, t in enumerate(data["tasks"]):
        if t.get("slug") == a.slug:
            data["tasks"][i] = row
            break
    else:
        data["tasks"].append(row)
    data["updated"] = int(time.time())
    save(path, data)
    print("\n".join(board(data, None, False)))


def cmd_show(a):
    data = load(report_path(repo_name()))
    if not data:
        print("ngisa-report: no report", file=sys.stderr)
        return 1
    print("\n".join(board(data, None, a.color)))


def cmd_ask(a):
    data = load(report_path(repo_name()))
    rows = [t for t in (data or {}).get("tasks", []) if t.get("slug") == a.slug]
    if not rows or not rows[0].get("asks"):
        print(f"ngisa-report: no asks for {a.slug}", file=sys.stderr)
        return 1
    print("\n".join(ask_block(rows[0], False)))


def cmd_clear(a):
    try:
        os.remove(report_path(repo_name()))
    except OSError:
        pass


def cmd_view(a):
    path = report_path(repo_name())
    color = not os.environ.get("NO_COLOR")

    def frame():
        data = load(path)
        if not data:
            return [paint(DIM, "no report yet", color)]
        return board(data, shutil.get_terminal_size((80, 24)).columns, color)

    if a.once:
        print("\n".join(frame()))
        return 0
    out = sys.stdout
    out.write("\033[?25l\033[2J")
    try:
        while True:
            out.write("\033[H" + "".join(l + "\033[K\n" for l in frame()) + "\033[J")
            out.flush()
            time.sleep(2)
    except KeyboardInterrupt:
        pass
    finally:
        out.write("\033[?25h")
        out.flush()
    return 0


def main():
    p = argparse.ArgumentParser(prog="ngisa-report")
    sub = p.add_subparsers(dest="cmd", required=True)
    s = sub.add_parser("set")
    s.add_argument("slug")
    s.add_argument("--state", required=True, choices=sorted(STATES))
    s.add_argument("--base")
    s.add_argument("--branch")
    s.add_argument("--gate")
    s.add_argument("--tests")
    s.add_argument("--diff", nargs=3, type=int, metavar=("FILES", "ADD", "DEL"))
    s.add_argument("--finding", action="append")
    s.add_argument("--ask", action="append")
    s.add_argument("--unverified", action="append")
    s.set_defaults(fn=cmd_set)
    sh = sub.add_parser("show")
    sh.add_argument("--color", action="store_true")
    sh.set_defaults(fn=cmd_show)
    k = sub.add_parser("ask")
    k.add_argument("slug")
    k.set_defaults(fn=cmd_ask)
    v = sub.add_parser("view")
    v.add_argument("--once", action="store_true")
    v.set_defaults(fn=cmd_view)
    c = sub.add_parser("clear")
    c.set_defaults(fn=cmd_clear)
    a = p.parse_args()
    return a.fn(a) or 0


if __name__ == "__main__":
    sys.exit(main())
```

```bash
chmod +x ~/bin/ngisa-report
```

- [ ] **Step 4: Run the tests to verify they pass**

Run: `python3 -I ${TMPDIR:-/tmp}/ngisa-report-test/test_ngisa_report.py 2>&1 | tail -8`
Expected: `Ran 12 tests ... OK`. If `test_plain_board_matches_mock` fails only on spacing, diff actual against the mock in the spec section "Agreed" and fix the script, not the mock.

- [ ] **Step 5: Look at it in a real terminal width**

```bash
export XDG_CACHE_HOME=${TMPDIR:-/tmp}/ngisa-report-demo NGISA_REPO=demo
ngisa-report set util-media --base feat/health-utils --state ok --branch feat/util-media --tests "12 pass" --diff 1 69 0 --unverified "no device run"
ngisa-report set util-color --state fail --branch feat/util-color --gate "gate FAIL" --diff 2 40 3 --finding "analysis_options.yaml changed" --ask "revert?|lint rule loosened|y"
COLUMNS=80 ngisa-report view --once
ngisa-report ask util-color
unset XDG_CACHE_HOME NGISA_REPO
```
Expected: coloured board identical in layout to the approved mock (green `✓`, red `✗`/`!`, amber `?`, green `[rec y]`, rest dim), then the plain G2 block. Do not commit.

---

### Task 2: report pane in `agent-wall.sh`

**Files:**
- Modify: `~/bin/agent-wall.sh` (add report-pane state after the cleanup loop; exclude it from `impl`; open it after the worker pane)
- Create (scratch test): `${TMPDIR:-/tmp}/ngisa-wall-test/run.sh`

**Interfaces:**
- Consumes: `~/bin/ngisa-report view` (Task 1).
- Produces: state file `~/.cache/ngisa/panes/<repo>.report` holding the report pane id. The pane is a strip under the NGISA pane (`--bottom --percent 20` on `$WEZTERM_PANE`), opened once, after the first worker pane. It is excluded from `impl` (slot count, "tab full", equal heights).

- [ ] **Step 1: Write the failing test**

```bash
T=${TMPDIR:-/tmp}/ngisa-wall-test; mkdir -p "$T"
```

Create `$T/run.sh`:

```bash
#!/usr/bin/env bash
set -euo pipefail
T=${TMPDIR:-/tmp}/ngisa-wall-test
rm -rf "$T/fake" "$T/cache" "$T/demo"; mkdir -p "$T/fake" "$T/cache" "$T/demo"
cat > "$T/fake/wezterm" <<'EOF'
#!/usr/bin/env bash
d=${FAKE_DIR:?}
echo "$*" >> "$d/log"
[[ $1 == cli ]] || exit 1
case $2 in
  list) cat "$d/panes.json";;
  split-pane)
    new=$(jq 'map(.pane_id) | max + 1' "$d/panes.json")
    jq --argjson n "$new" '. + [{pane_id:$n, tab_id:1, size:{rows:10}, top_row:(length*10)}]' "$d/panes.json" > "$d/p.tmp" && mv "$d/p.tmp" "$d/panes.json"
    echo "$new";;
  *) ;;
esac
EOF
for n in claude agent-view ngisa-report; do
  printf '#!/usr/bin/env bash\necho "%s $*" >> "$FAKE_DIR/log"\n' "$n" > "$T/fake/$n"
done
chmod +x "$T/fake/"*
export FAKE_DIR="$T/fake" XDG_CACHE_HOME="$T/cache" WEZTERM_PANE=1 PATH="$T/fake:$PATH"
(cd "$T/demo" && git init -q)
wall() { (cd "$T/demo" && bash ~/bin/agent-wall.sh "$@"); }
has() { grep -q -- "$1" "$FAKE_DIR/log" || { echo "FAIL: log has no '$1'"; cat "$FAKE_DIR/log"; exit 1; }; }
panes="$T/cache/ngisa/panes"

echo '[{"pane_id":1,"tab_id":1,"size":{"rows":40},"top_row":0}]' > "$FAKE_DIR/panes.json"
wall one implementer sonnet "x"
has 'split-pane --pane-id 1 --right --percent 55'
has 'split-pane --pane-id 1 --bottom --percent 20'
[[ -f $panes/demo.report ]] || { echo "FAIL: no report state file"; exit 1; }
wall two implementer sonnet "x"
has 'split-pane --pane-id 2 --bottom --percent 50'
wall three implementer sonnet "x"
has 'split-pane --pane-id 4 --bottom --percent 66'
if wall four implementer sonnet "x" 2> "$T/err"; then echo "FAIL: fourth worker was allowed"; exit 1; fi
grep -q "tab full" "$T/err" || { echo "FAIL: no 'tab full' message"; exit 1; }
[[ $(grep -c -- '--bottom --percent 20' "$FAKE_DIR/log") == 1 ]] || { echo "FAIL: report pane opened more than once"; exit 1; }

# stale report pane: its id is not in the pane list any more
: > "$FAKE_DIR/log"; rm -f "$panes"/*
echo '[{"pane_id":1,"tab_id":1,"size":{"rows":40},"top_row":0},{"pane_id":2,"tab_id":1,"size":{"rows":20},"top_row":0}]' > "$FAKE_DIR/panes.json"
echo 9 > "$panes/demo.report"
wall five implementer sonnet "x"
has 'split-pane --pane-id 2 --bottom --percent 50'
has 'split-pane --pane-id 1 --bottom --percent 20'
[[ $(cat "$panes/demo.report") != 9 ]] || { echo "FAIL: stale report id kept"; exit 1; }
echo "agent-wall report pane: OK"
```

- [ ] **Step 2: Run the test to verify it fails**

Run: `bash ${TMPDIR:-/tmp}/ngisa-wall-test/run.sh`
Expected: `FAIL: log has no 'split-pane --pane-id 1 --bottom --percent 20'` (current script has no report pane).

- [ ] **Step 3: Edit `~/bin/agent-wall.sh`**

Edit 1. Replace the line

```bash
for f in "$state/$repo"-*; do [[ -f $f ]] && ! alive "$(cat "$f")" && rm -f "$f"; done
# the right-hand column holds the worker panes, one per agent
impl=(${others[@]+"${others[@]}"})
```

with

```bash
for f in "$state/$repo"-*; do [[ -f $f ]] && ! alive "$(cat "$f")" && rm -f "$f"; done
# the report board (ngisa-report view) is a strip under the NGISA pane. It is not a worker pane: left out of the slot count and the equal heights.
report_file="$state/$repo.report"
report_id=$(cat "$report_file" 2>/dev/null || true)
if [[ -n $report_id ]] && ! alive "$report_id"; then rm -f "$report_file"; report_id=; fi
# the right-hand column holds the worker panes, one per agent
impl=()
for id in ${others[@]+"${others[@]}"}; do [[ $id == "$report_id" ]] || impl+=("$id"); done
```

Edit 2. Replace the last line block

```bash
equalize_column ${impl[@]+"${impl[@]}"} "$new"
wezterm cli activate-pane --pane-id "$me" >/dev/null 2>&1 || true
```

with

```bash
equalize_column ${impl[@]+"${impl[@]}"} "$new"
# open the report board once, with the first worker, under the NGISA pane; it stays until its pane is closed
if [[ -z $report_id ]] && command -v ngisa-report >/dev/null 2>&1; then
  rep=$(wezterm cli split-pane --pane-id "$me" --bottom --percent 20 -- "$(command -v ngisa-report)" view) && echo "$rep" > "$report_file" || true
fi
wezterm cli activate-pane --pane-id "$me" >/dev/null 2>&1 || true
```

- [ ] **Step 4: Run the test to verify it passes**

Run: `bash ${TMPDIR:-/tmp}/ngisa-wall-test/run.sh && bash -n ~/bin/agent-wall.sh && echo SYNTAX-OK`
Expected: `agent-wall report pane: OK` then `SYNTAX-OK`.

- [ ] **Step 5: Leave uncommitted**

Run: `git -C /Users/khoamai/Projects/my_proj/ngisa status --short` (kit repo is untouched by Tasks 1-2: the scripts live in `~/bin` until Task 4 copies them into the docs). Do not commit.

---

### Task 3: kit files (implementer J, orchestrating, settings, repo-tab) synced to the lab

**Files:**
- Modify: `agents/implementer.md` (step 5)
- Modify: `orchestrating.md` (steps 4 and 7, ask rule, style)
- Modify: `settings.local.json` (allow `ngisa-report`)
- Modify: `~/bin/repo-tab` (system-prompt sentence)

**Interfaces:**
- Consumes: the `ngisa-report set|ask` CLI (Task 1).
- Produces: the J block keys `branch / files / gate / scope / unverified / asks` that the NGISA maps to `--branch --gate --unverified --ask`.

- [ ] **Step 1: Implementer final message becomes the J block**

In `agents/implementer.md` replace

```
5. Final message, exactly: branch name, files changed, test command + result, anything you could NOT verify and why. Write it in caveman ultra (no articles or filler, fragments OK); branch, paths, commands and errors stay exact.
```

with

```
5. Final message: exactly these six lines, nothing before or after, in caveman ultra (no articles or filler, fragments OK); branch, paths, commands and errors stay exact.
   branch: <branch name>
   files: <paths changed, comma separated>
   gate: <./tool/ci_local.sh exit code and test count, or the exact error>
   scope: in paths | outside: <paths>
   unverified: <what you could NOT verify and why, or none>
   asks: <decisions you deferred, each with your recommendation, separated by ";", or none>
```

- [ ] **Step 2: Orchestrating steps 4 and 7, ask rule, style**

In `orchestrating.md`, replace step 4's last sentence block

```
   Exit 0: go on. Exit 1 (findings) or 2 (error, e.g. wrong branch name): stop, show me its output, do not merge that branch until I decide. It only compares the gate files and the
   lint/analyzer/CI config; I read the diff myself, so do not add your own review.
```

with

```
   Exit 0: go on. Exit 1 (findings) or 2 (error, e.g. wrong branch name): stop, show me its output, do not merge that branch until I decide. It only compares the gate files and the
   lint/analyzer/CI config; I read the diff myself, so do not add your own review.
   Then record the row: `ngisa-report set <slug> --base <base branch> --branch <branch> --state ok|fail|blocked --gate "<gate line>" --tests "<n pass>" --diff <files> <added> <removed>`
   plus `--finding "<text>"` per gate-check finding, `--ask "<text>|<why>|<rec>"` per item in the worker's `asks:`, `--unverified "<text>"` per item in its `unverified:`.
   `fail` when gate-check exited 1 or the gate was red, `blocked` when it waits on me, else `ok`; a worker still running is `--state working`.
   Diff counts: `git diff --shortstat <base>...<branch>`.
```

Replace step 7

```
7. Report to me: one table (task | branch | gate-check | tests | unverified items).
```

with

```
7. Report to me: paste the output of the last `ngisa-report set` unchanged (the board), then the PR link if any. Never retype or reword it: the report pane shows the same data.
Ask: when you need a decision, run `ngisa-report ask <slug>` and send only its output, one ask per message, then wait. Never put an ask in prose.
```

In the `Style:` paragraph, after the `Long text too (findings, decisions): numbered fragments, never prose paragraphs.` line and its example, add a new line

```
  Boards and asks are templates: paste them, do not rewrite them.
```

- [ ] **Step 3: Allow the script**

In `settings.local.json` change `"Bash(gate-check:*)"` to `"Bash(gate-check:*)", "Bash(ngisa-report:*)"`. Then validate: `jq -e . settings.local.json >/dev/null && echo JSON-OK`.

- [ ] **Step 4: Tell the system prompt**

In `~/bin/repo-tab`, at the end of the `style='...'` string, before the closing `'`, append (single line, no apostrophes):

```
 Reports and asks are templates: paste the output of ngisa-report set (the board) or ngisa-report ask unchanged; do not reword them.
```

Check: `bash -n ~/bin/repo-tab && echo SYNTAX-OK`.

- [ ] **Step 5: Sync into the lab and check**

```bash
KIT=/Users/khoamai/Projects/my_proj/ngisa
ls ~/lab/busy-bees >/dev/null   # if the lab is missing: make-lab <repo> first, then skip the cp lines
cp $KIT/agents/implementer.md ~/lab/busy-bees/.claude/agents/implementer.md
cp $KIT/orchestrating.md ~/lab/busy-bees/CLAUDE.local.md
cp $KIT/settings.local.json ~/lab/busy-bees/.claude/settings.local.json
diff $KIT/orchestrating.md ~/lab/busy-bees/CLAUDE.local.md && echo LAB-IN-SYNC
grep -n "ngisa-report" ~/lab/busy-bees/CLAUDE.local.md | head
```
Expected: `LAB-IN-SYNC` and the `ngisa-report` lines in step 4, step 7 and the ask rule. Do not commit.

---

### Task 4: docs, quickstart script blocks, spec fixes

**Files:**
- Create (scratch): `${TMPDIR:-/tmp}/ngisa-sync/sync_quickstart.py`
- Modify: `docs/orchestration/lab-quickstart.md` (heredocs for implementer, orchestrating, settings, `repo-tab`, `agent-wall.sh`; new `ngisa-report` heredoc; chmod/which/Step 1 lines)
- Modify: `docs/orchestration/one-terminal-orchestrator.md` and `.vi.md` (sections for the implementer prompt and the NGISA rules)
- Modify: `CONTEXT.md`, `PRODUCT.md`, `docs/README.md`
- Modify: `docs/superpowers/specs/2026-10-16-report-output-design.md` (two small fixes)
- Check: `README.md`, `README.vi.md`, `docs/diagrams/*`

**Interfaces:**
- Consumes: final files from Tasks 1-3.

- [ ] **Step 1: Write the sync-and-check helper**

Create `${TMPDIR:-/tmp}/ngisa-sync/sync_quickstart.py` (`mkdir -p` the dir first):

```python
import os, re, sys

KIT = "/Users/khoamai/Projects/my_proj/ngisa"
QS = os.path.join(KIT, "docs/orchestration/lab-quickstart.md")
HOME = os.path.expanduser("~")
BLOCKS = [
    ("cat > $KIT/agents/implementer.md <<'EOF'", f"{KIT}/agents/implementer.md"),
    ("cat > $KIT/orchestrating.md <<'EOF'", f"{KIT}/orchestrating.md"),
    ("cat > $KIT/settings.local.json <<'EOF'", f"{KIT}/settings.local.json"),
    ("cat > ~/bin/repo-tab <<'EOF'", f"{HOME}/bin/repo-tab"),
    ("cat > ~/bin/agent-wall.sh <<'EOF'", f"{HOME}/bin/agent-wall.sh"),
    ("cat > ~/bin/ngisa-report <<'EOF'", f"{HOME}/bin/ngisa-report"),
]
ANCHOR_FOR_NEW = "cat > ~/bin/ngisa-statusline <<'EOF'"
check = "--check" in sys.argv
text = open(QS).read()
bad = 0
for header, path in BLOCKS:
    body = open(path).read().rstrip("\n")
    pat = re.compile(re.escape(header) + r"\n(.*?)\nEOF\n", re.S)
    m = pat.search(text)
    if check:
        ok = bool(m) and m.group(1) == body
        print(("OK   " if ok else "DIFF ") + header)
        bad += 0 if ok else 1
    elif m:
        text = text[: m.start(1)] + body + text[m.end(1):]
    else:
        assert ANCHOR_FOR_NEW in text, "anchor missing"
        text = text.replace(ANCHOR_FOR_NEW, f"{header}\n{body}\nEOF\n\n{ANCHOR_FOR_NEW}", 1)
if not check:
    open(QS, "w").write(text)
sys.exit(1 if bad else 0)
```

- [ ] **Step 2: Sync the blocks and fix the surrounding lines**

```bash
mkdir -p ${TMPDIR:-/tmp}/ngisa-sync
python3 ${TMPDIR:-/tmp}/ngisa-sync/sync_quickstart.py
```

Then edit `docs/orchestration/lab-quickstart.md`:
- Step 1 comment: `# agent-view and ngisa-statusline are Python 3 scripts (standard library only)` becomes `# agent-view, ngisa-statusline and ngisa-report are Python 3 scripts (standard library only)`.
- The `chmod +x ...` line: append ` ~/bin/ngisa-report`.
- The `which ...` line: append ` ngisa-report` and change `# all nine must print a path` to `# all ten must print a path`.
- Directly after the `(macOS ships bash 3.2 ...)` note add one sentence: `ngisa-report is the report board: the NGISA runs ngisa-report set per worker report and pastes its output; agent-wall.sh opens ngisa-report view as a strip under the NGISA pane.`

- [ ] **Step 3: Verify the quickstart equals the files**

Run: `python3 ${TMPDIR:-/tmp}/ngisa-sync/sync_quickstart.py --check`
Expected: six `OK` lines, exit 0.

- [ ] **Step 4: Update `one-terminal-orchestrator.md` and `.vi.md`**

Open `docs/orchestration/one-terminal-orchestrator.md`. Make the same wording changes as in `orchestrating.md` (Task 3 Step 2) in the section that mirrors the NGISA rules (the numbered list around "4. For each finished task, run `gate-check ...`" through "7. Report to me:", plus the style paragraph), and in the implementer section replace the final-message item with the six J lines (find it with `grep -n "final message\|Final message" docs/orchestration/one-terminal-orchestrator.md`). Add one short paragraph after the NGISA rules, in the doc's existing voice: what `ngisa-report` is, that `agent-wall.sh` opens the report strip under the NGISA pane (not counted in the 3 slots), and the B legend `✓ ok  ✗ fail  ▶ working  ? asks you  ! finding`.

Open `one-terminal-orchestrator.vi.md` and apply the same changes in Vietnamese at the matching sections (`grep -n "gate-check\|báo cáo\|bảng" docs/orchestration/one-terminal-orchestrator.vi.md`). Commands, paths, keys (`branch / files / gate / scope / unverified / asks`) and the legend stay in English.

- [ ] **Step 5: CONTEXT, PRODUCT, docs README, spec, other docs**

- `CONTEXT.md`: add a decisions section `### Report output (2026-10-16)` after `### Review stage removed`: B final report, coloured report pane plus identical plain chat (one source: `ngisa-report set` output), G2 asks, J worker report, templates instead of more prose rules for caveman drift (it slipped twice, see `docs/runs/2026-10-15-pane-view-and-caveman.md`), JSON in `~/.cache/ngisa/report/ngisa-<repo>.json`. Add `~/bin/ngisa-report` to the kit map script list and a row `agents/implementer.md` / `orchestrating.md` note about the J and B skeletons. In `### Orchestrator` roles line, change `` `gate-check` (a script) runs on each worker report`` to add `; the NGISA records each report with `ngisa-report set``. Add an open item: `Exercise the report pane in a real WezTerm tab: placement under the NGISA pane, live refresh.`
- `PRODUCT.md` line 19 (`Surfaces:`): add `the report board (`ngisa-report view`, a strip under the NGISA pane)`.
- `docs/README.md` line 10: update the script count/list the line gives for `lab-quickstart.md` (read the line, add `ngisa-report`).
- Spec `docs/superpowers/specs/2026-10-16-report-output-design.md`: change `<session>.json` to `ngisa-<repo>.json` (one NGISA per repo) and `Bash(ngisa-report *)` to `Bash(ngisa-report:*)` (matches the other allow entries).
- Check, change only if they show the old final table: `grep -n "table\|gate-check" README.md README.vi.md` and `grep -ln "unverified items\|gate-check" docs/diagrams/*.html docs/index*.html`. If a README or diagram describes the final report as a table, reword it to the board and mirror the change in the `.vi` copy; if none do, leave them.

- [ ] **Step 6: Final doc checks**

```bash
cd /Users/khoamai/Projects/my_proj/ngisa
python3 ${TMPDIR:-/tmp}/ngisa-sync/sync_quickstart.py --check
grep -rn $'\xe2\x80\x94' CONTEXT.md PRODUCT.md orchestrating.md agents/implementer.md docs/superpowers/specs/2026-10-16-report-output-design.md docs/superpowers/plans/2026-10-16-report-output.md | head   # em dash: expect no output
grep -c "ngisa-report" docs/orchestration/one-terminal-orchestrator.md docs/orchestration/one-terminal-orchestrator.vi.md
git status --short
```
Expected: six `OK`, no em dash lines, a non-zero `ngisa-report` count in both orchestrator docs, only intended files modified. Do not commit.

---

### Task 5: headless NGISA run and run log

**Files:**
- Create: `docs/runs/2026-10-16-report-output.md`

**Interfaces:**
- Consumes: everything above, synced into `~/lab/busy-bees` (Task 3 Step 5).

- [ ] **Step 1: One real headless NGISA turn**

```bash
export T=${TMPDIR:-/tmp}/ngisa-run; mkdir -p $T/cache
cd ~/lab/busy-bees
style=$(sed -n "s/^style='\(.*\)'$/\1/p" ~/bin/repo-tab)
XDG_CACHE_HOME=$T/cache claude -p --model opus --output-format json --append-system-prompt "$style" \
  'Pretend: gate-check feat/x main exited 0 and tests passed. Worker report arrived:
branch: feat/x
files: test/x_test.dart
gate: exit 0, 9 pass
scope: in paths
unverified: no device run
asks: add test for dart:45-47 branch (rec yes)
Do step 4 recording and step 7 report. Diff is 1 file, +40 -0.' > $T/out.json
jq -r '.result' $T/out.json; jq '.total_cost_usd' $T/out.json
cat $T/cache/ngisa/report/ngisa-busy-bees.json | jq '.tasks[0] | {slug, state, asks, unverified}'
```
Expected: the result text contains the board returned by `ngisa-report set` unchanged (header `NGISA  busy-bees`, row ` ✓ x ...`, the `? ... [rec ...]` line, `unverified:` line, legend), no prose paragraph around it; the JSON row has the ask and the unverified item. Record in the run log: board pasted unchanged yes/no, any prose outside the skeleton (drift count), cost. If the NGISA reworded the board, tighten the wording of step 7 in `orchestrating.md` (and its docs copy and the quickstart block, re-run the Task 4 Step 3 check) and repeat once.

- [ ] **Step 2: Write the run log**

Create `docs/runs/2026-10-16-report-output.md` in the style of `docs/runs/2026-10-15-pane-view-and-caveman.md`: a title line with the date, `## Changes` (J block, B and G2 skeletons, `ngisa-report`, report pane in `agent-wall.sh`, repo-tab sentence, allow entry), `### Checked` (Task 1 unit tests count and pass, Task 2 fake-wezterm scenarios incl. stale pane, quickstart equality check, the headless run result with drift count and cost, the width replay at 40/80/140), `### Not tested` (a real WezTerm tab: strip placement under the NGISA pane, live refresh, the pane opening when all workers were closed; a whole real task with three workers). Include interventions (none expected) and the cost number from Step 1.

- [ ] **Step 3: Clean up and report**

```bash
rm -rf ${TMPDIR:-/tmp}/ngisa-run ${TMPDIR:-/tmp}/ngisa-report-demo
git -C /Users/khoamai/Projects/my_proj/ngisa status --short
```
Expected: modified kit and docs files plus the new spec, plan and run log; nothing committed. Tell the user the branch (`feat/report-output`) is ready for them to review and commit (suggest `/carve`), and list what was not tested.
