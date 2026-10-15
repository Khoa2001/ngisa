# Remove review stage Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Drop the reviewer agent, review panes and APPROVE/BLOCK loop from the NGISA kit, and replace the reviewer's gate-integrity role with a non-LLM `gate-check` script.

**Architecture:** `lab-quickstart.md` heredocs are the source of the kit files and `~/bin` scripts, so every script change is made in the doc first, then installed with an `extract` helper and diffed. The reviewer's only unique job (catching tampering with the gate files and lint config) becomes `gate-check <branch> [base]`, which the NGISA runs on each worker report. Everything else the reviewer did is now the user's job at the final diff.

**Tech Stack:** bash, python3 (`agent-view`), WezTerm CLI, static HTML/SVG, headless Chrome + ffmpeg + Node 22 (GIF render).

**Spec:** `docs/superpowers/specs/2026-10-15-remove-review-stage-design.md`

## Global Constraints

- Branch `feat/remove-review-stage`. Never work on main. Do NOT commit or push: the user has not said so. Each task ends with a checkpoint, not a commit.
- No em dash anywhere (use a plain dash). Never hand-edit `CHANGELOG.md` or generated files.
- Scripts call `fvm flutter` / `fvm dart`, never bare `flutter`.
- Do not touch `~/.claude` or the global CLAUDE.md. `~/bin` and `~/lab` are fine.
- Every doc has a Vietnamese copy (`*.vi.md`, `*.vi.html`): change both in the same task. Code, commands and config stay English in both.
- Keep `docs/runs/2026-10-15-*.md` logs untouched (research data). Only add a new log.
- Kit and docs change together (CLAUDE.md rule): `agents/`, `orchestrating.md`, `settings.local.json` must match their `lab-quickstart.md` heredocs byte for byte.
- Caveman style in messages to the user.

## Review Focus

- `gate-check` run for a branch that has no worktree (worker committed in the main checkout): must not crash, skips the file diff, still checks config files. Test in Task 1.
- `gate-check` with a gate file present only in the main checkout or only in the worktree: counts as a difference. Test in Task 1.
- `gate-check` given a branch that does not exist: exit 2 with a message, not a stack trace or a false "clean". Test in Task 1.
- `agent-view` with the reviewer code removed: no leftover reference to `reviewer`, `verdict`, `steps`, `reviewed` (NameError at runtime). Checked with pyflakes-style compile plus grep in Task 3.
- `agent-wall.sh` with the review layout removed: a 4th agent still gets "tab full", the first pane still splits right of the NGISA. Checked by `bash -n` and reading the diff in Task 3.
- Demo and diagrams still have 9 steps, so `index.html` `MAP=[0,1,1,2,3,4,4,4,5]` still lines up. Checked in Task 7.

## File Structure

| File | Responsibility after change |
|---|---|
| `~/bin/gate-check` (source: heredoc in `docs/orchestration/lab-quickstart.md`) | New. Compare gate files and lint/CI config for one branch |
| `agents/implementer.md` | Unchanged |
| `agents/reviewer.md` | Deleted |
| `orchestrating.md`, `settings.local.json` | NGISA rules and permissions, gate-check instead of reviewer |
| `docs/orchestration/lab-quickstart.md` | Source of truth for kit + scripts |
| `docs/orchestration/one-terminal-orchestrator(.vi).md`, `lab-setup.md` | Design doc and lab setup, reviewer removed |
| `CLAUDE.md`, `CONTEXT.md`, `PRODUCT.md`, `README(.vi).md`, `docs/README.md`, `docs/verification/cut-verification-time(.vi).md` | Wording and decision log |
| `docs/diagrams/*`, `docs/index(.vi).html`, `docs/assets/site.css`, `docs/assets/*.gif` | Diagram, site, demo and GIFs |
| `docs/runs/2026-10-15-remove-review-stage.md` | New run log |

## Helper used in several tasks

Run once per shell (shell state does not persist between Bash calls, so paste it at the top of any command that uses it):

```bash
KIT=/Users/khoamai/Projects/my_proj/ngisa
extract() { # extract <name>: print the heredoc body of ~/bin/<name> or $KIT/<name> from lab-quickstart.md
  awk -v a="cat > ~/bin/$1 <<'EOF'" -v b="cat > \$KIT/$1 <<'EOF'" '$0==a||$0==b{f=1;next} f&&$0=="EOF"{exit} f' "$KIT/docs/orchestration/lab-quickstart.md"
}
```

---

### Task 0: Baseline

**Files:** none changed.

- [ ] **Step 1: Confirm branch and clean tree**

Run: `cd /Users/khoamai/Projects/my_proj/ngisa && git branch --show-current && git status --short`
Expected: `feat/remove-review-stage`; only `?? docs/superpowers/` untracked.

- [ ] **Step 2: Confirm docs and installed scripts agree today**

```bash
KIT=/Users/khoamai/Projects/my_proj/ngisa
extract() { awk -v a="cat > ~/bin/$1 <<'EOF'" -v b="cat > \$KIT/$1 <<'EOF'" '$0==a||$0==b{f=1;next} f&&$0=="EOF"{exit} f' "$KIT/docs/orchestration/lab-quickstart.md"; }
for n in agent-wall.sh agent-view ngisa-statusline caveman-ultra-hook repo-tab make-lab; do extract $n | diff -q - ~/bin/$n >/dev/null && echo "same  $n" || echo "DRIFT $n"; done
for n in orchestrating.md settings.local.json agents/implementer.md agents/reviewer.md; do extract $n | diff -q - "$KIT/$n" >/dev/null && echo "same  $n" || echo "DRIFT $n"; done
```
Expected: all `same`. If any `DRIFT`: STOP and report to the user which one; the docs and the install disagree before we start, so we cannot tell what is intended.

---

### Task 1: `gate-check` script (TDD)

**Files:**
- Modify: `docs/orchestration/lab-quickstart.md` (add heredoc in Step 3 next to the other `~/bin` scripts; update the `chmod +x` line near 1271; the "nine scripts" wording wherever it appears)
- Create (install): `~/bin/gate-check`

**Interfaces:**
- Produces: `gate-check <branch> [base-branch]`, run from any directory inside the repo. Exit 0 = clean, 1 = findings printed to stdout, 2 = usage or git error (message on stderr). Task 2 calls it from `orchestrating.md`.

- [ ] **Step 1: Write the failing test script**

Create `/private/tmp/claude-501/-Users-khoamai-Projects-my-proj-ngisa/243d4a1e-65a6-4262-8da2-7bc921cc6428/scratchpad/gate-check-test.sh` (scratchpad, not the repo):

```bash
#!/usr/bin/env bash
set -u
GC=${GC:-$HOME/bin/gate-check}
T=$(mktemp -d); trap 'rm -rf "$T"' EXIT
pass=0; failn=0
expect() { # expect <exit> <grep-pattern-or-empty> <label> -- run gate-check "$@"
  local want=$1 pat=$2 label=$3; shift 3
  out=$("$GC" "$@" 2>&1); rc=$?
  if [[ $rc == "$want" ]] && { [[ -z $pat ]] || grep -q -- "$pat" <<<"$out"; }; then pass=$((pass+1)); echo "ok   $label"
  else failn=$((failn+1)); echo "FAIL $label (rc=$rc want=$want)"; echo "$out" | sed 's/^/     /'; fi
}
cd "$T" && git init -q -b main main && cd main
mkdir tool && printf 'echo ok\n' > tool/ci_local.sh && printf 'echo setup\n' > tool/setup.sh
printf 'a\n' > analysis_options.yaml && printf 'x\n' > lib.txt
git add analysis_options.yaml lib.txt && git commit -qm init          # tool/ stays untracked, like a lab
git worktree add -q ../wt -b feat/x && cp -R tool ../wt/

expect 0 'clean'              "clean worktree"                       feat/x main
echo 'echo hacked' >> ../wt/tool/ci_local.sh
expect 1 'tool/ci_local.sh'   "edited ci_local.sh"                   feat/x main
cp tool/ci_local.sh ../wt/tool/ci_local.sh
printf 'test_a\n' > ../wt/tool/known_failures.txt
expect 1 'known_failures.txt' "known_failures only in worktree"      feat/x main
rm ../wt/tool/known_failures.txt
rm ../wt/tool/setup.sh
expect 1 'tool/setup.sh'      "setup.sh missing in worktree"         feat/x main
cp tool/setup.sh ../wt/tool/setup.sh
( cd ../wt && echo 'x: y' >> analysis_options.yaml && git commit -qam 'loosen lint' )
expect 1 'analysis_options'   "lint config changed on branch"        feat/x main
git worktree add -q ../wt2 -b feat/y && ( cd ../wt2 && echo more >> lib.txt && git commit -qam 'code only' )
cp -R tool ../wt2/
expect 0 'clean'              "code-only change is clean"            feat/y main
git checkout -q -b feat/z && echo z >> lib.txt && git commit -qam z && git checkout -q main
expect 0 'clean'              "branch without a worktree"            feat/z main
expect 2 'no local branch'    "missing branch"                       feat/nope main
expect 2 'usage'              "no args"
echo "$pass passed, $failn failed"; [[ $failn == 0 ]]
```

- [ ] **Step 2: Run it to verify it fails**

Run: `bash /private/tmp/claude-501/-Users-khoamai-Projects-my-proj-ngisa/243d4a1e-65a6-4262-8da2-7bc921cc6428/scratchpad/gate-check-test.sh`
Expected: every case `FAIL` (`~/bin/gate-check` does not exist).

- [ ] **Step 3: Add the script to the doc**

In `lab-quickstart.md` Step 3, add this block right after the `agent-wall.sh` heredoc (before `cat > ~/bin/agent-view`):

````
cat > ~/bin/gate-check <<'EOF'
#!/usr/bin/env bash
# gate-check <branch> [base-branch]
# Did the worker on <branch> touch the gate? The NGISA runs this on each worker report, from the main checkout.
#  1. tool/ci_local.sh, tool/setup.sh, tool/known_failures.txt: the branch's worktree copy must equal the main checkout's copy
#     (in a lab these files are untracked, so git diff would not show a change).
#  2. Lint, analyzer, test and CI config must not differ between the base branch and <branch>.
# Exit 0 clean, 1 findings (printed), 2 usage or git error. It never edits anything.
set -uo pipefail
branch=${1:-}
[[ -n $branch ]] || { echo "usage: gate-check <branch> [base-branch]" >&2; exit 2; }
common=$(git rev-parse --path-format=absolute --git-common-dir 2>/dev/null) || { echo "gate-check: not in a git repo" >&2; exit 2; }
main=$(cd "$common/.." && pwd -P)
git -C "$main" rev-parse --verify -q "refs/heads/$branch" >/dev/null || { echo "gate-check: no local branch '$branch'" >&2; exit 2; }
base=${2:-$(git -C "$main" branch --show-current)}
[[ -n $base ]] || { echo "gate-check: main checkout is detached, pass a base branch" >&2; exit 2; }
mb=$(git -C "$main" merge-base "$base" "$branch") || { echo "gate-check: no merge base for $base and $branch" >&2; exit 2; }
wt=$(git -C "$main" worktree list --porcelain | awk -v b="refs/heads/$branch" '/^worktree /{p=substr($0,10)} $0=="branch " b{print p; exit}')
fail=0
if [[ -n $wt && $(cd "$wt" && pwd -P) != "$main" ]]; then
  for f in tool/ci_local.sh tool/setup.sh tool/known_failures.txt; do
    a=$main/$f; b=$wt/$f
    [[ -e $a || -e $b ]] || continue
    [[ -e $a ]] || a=/dev/null
    [[ -e $b ]] || b=/dev/null
    if ! d=$(diff -u --label "main/$f" --label "worktree/$f" "$a" "$b"); then
      echo "FAIL gate file differs: $f"; printf '%s\n' "$d"; fail=1
    fi
  done
fi
cfg='(^|/)(analysis_options\.yaml|phpstan\.neon(\.dist)?|phpunit\.xml(\.dist)?|pint\.json|\.php-cs-fixer(\.dist)?\.php|\.gitlab-ci\.yml)$|^\.github/workflows/'
changed=$(git -C "$main" diff --name-only "$mb" "$branch" | grep -E "$cfg" || true)
if [[ -n $changed ]]; then
  echo "FAIL lint/test/CI config changed on $branch:"; printf '%s\n' "$changed" | sed 's/^/  /'; fail=1
fi
(( fail )) && exit 1
echo "gate-check: clean ($branch vs $base)"
EOF

````

Then in the same Step 3: add `~/bin/gate-check` to the `chmod +x ...` line, and change any "nine scripts" or script list to include `gate-check` (also in `docs/README.md`, done in Task 6).

- [ ] **Step 4: Install from the doc and run the test**

```bash
KIT=/Users/khoamai/Projects/my_proj/ngisa
extract() { awk -v a="cat > ~/bin/$1 <<'EOF'" -v b="cat > \$KIT/$1 <<'EOF'" '$0==a||$0==b{f=1;next} f&&$0=="EOF"{exit} f' "$KIT/docs/orchestration/lab-quickstart.md"; }
extract gate-check > ~/bin/gate-check && chmod +x ~/bin/gate-check && bash -n ~/bin/gate-check
bash /private/tmp/claude-501/-Users-khoamai-Projects-my-proj-ngisa/243d4a1e-65a6-4262-8da2-7bc921cc6428/scratchpad/gate-check-test.sh
```
Expected: `9 passed, 0 failed` (9 `expect` lines). Fix the script, not the test, on any `FAIL`.

- [ ] **Step 5: Checkpoint**

Report to the user: gate-check installed, 9/9 cases pass. Do not commit.

---

### Task 2: Kit core - remove reviewer, wire gate-check

**Files:**
- Delete: `agents/reviewer.md`
- Modify: `orchestrating.md`, `settings.local.json`
- Modify: `docs/orchestration/lab-quickstart.md` (heredocs at the old lines 40-56 reviewer, 58-93 orchestrating, 95-119 settings, and the `ls -R` comment at 135)

**Interfaces:**
- Consumes: `gate-check <branch> [base-branch]` (Task 1).

- [ ] **Step 1: Edit the kit files**

`agents/reviewer.md`: `git rm -q agents/reviewer.md` is staging-only and fine, but do not commit. Use `rm agents/reviewer.md` instead to keep the index untouched.

`orchestrating.md`, replace step 4 (the 4 lines starting "4. When a worker's report arrives, start its reviewer") with:

```
4. When a worker's report arrives, run `gate-check <branch> <base branch>` (branch from the report; base is the branch the plan was cut from).
   Exit 1: stop, show me its output, do not merge that branch until I decide. Exit 0: go on. It only compares the gate files and the
   lint/analyzer/CI config; I read the diff myself, so do not add your own review.
```

Replace step 6 with:
`6. Merge task branches that passed gate-check (or that I allowed) into a local feature branch and run ./tool/ci_local.sh. This is a lab: never push on your own.`

Replace step 7 with:
`7. Report to me: one table (task | branch | gate-check | tests | unverified items).`

Replace the Quick task second line with:
`  Spawn ONE implementer with exactly those paths, then run gate-check as usual. Anything bigger: say it needs a plan.`

In the Style block: `Running. Reviewer next.` becomes `Running. Gate-check next.` and `Long text too (reviewer verdicts, findings, decisions)` becomes `Long text too (findings, decisions)`.

`settings.local.json`: add `"Bash(gate-check:*)"` to the end of the second allow row group, i.e. change
`"Bash(git merge:*)", "Bash(git checkout:*)", "Bash(agent-wall.sh:*)", "Bash(worktree-include)"` to
`"Bash(git merge:*)", "Bash(git checkout:*)", "Bash(agent-wall.sh:*)", "Bash(worktree-include)", "Bash(gate-check:*)"`.
Leave `Bash(diff:*)` in place (harmless, also used by workers).

- [ ] **Step 2: Mirror into `lab-quickstart.md`**

Delete the `cat > $KIT/agents/reviewer.md <<'EOF' ... EOF` block and its blank line. Make the identical edits inside the `orchestrating.md` and `settings.local.json` heredocs. Change the comment `# expect: agents/implementer.md agents/reviewer.md orchestrating.md ...` to `# expect: agents/implementer.md orchestrating.md settings.local.json ngisa-settings.json`.

- [ ] **Step 3: Verify kit equals heredocs and is valid**

```bash
KIT=/Users/khoamai/Projects/my_proj/ngisa
extract() { awk -v a="cat > ~/bin/$1 <<'EOF'" -v b="cat > \$KIT/$1 <<'EOF'" '$0==a||$0==b{f=1;next} f&&$0=="EOF"{exit} f' "$KIT/docs/orchestration/lab-quickstart.md"; }
for n in orchestrating.md settings.local.json agents/implementer.md; do extract $n | diff - "$KIT/$n" && echo "same $n"; done
test ! -e "$KIT/agents/reviewer.md" && echo "reviewer gone"
python3 -m json.tool "$KIT/settings.local.json" >/dev/null && echo "json ok"
grep -n -i "review" "$KIT/orchestrating.md" "$KIT/settings.local.json"
```
Expected: three `same`, `reviewer gone`, `json ok`, and the last grep prints only the line `I read the diff myself, so do not add your own review.` (the one intended mention).

- [ ] **Step 4: Checkpoint** (no commit)

---

### Task 3: Scripts - `agent-wall.sh`, `agent-view`, text cleanups

**Files:**
- Modify: `docs/orchestration/lab-quickstart.md` heredocs for `agent-wall.sh`, `agent-view`, `ngisa-statusline`, `caveman-ultra-hook`, `repo-tab`
- Install: `~/bin/agent-wall.sh`, `~/bin/agent-view`, `~/bin/ngisa-statusline`, `~/bin/caveman-ultra-hook`, `~/bin/repo-tab`

- [ ] **Step 1: `agent-wall.sh` - remove the review layout**

In the heredoc, replace everything from the line `# the right-hand column holds the implementer panes; reviewer panes ...` through the `claude --bg ...` call's preceding `fi` (that is: the `impl=()` loop, the `target=""` block with the `if [[ $task =~ ^(.+)-review...` branch and the `elif (( ${#impl[@]} >= 3 ))` branch) with:

```bash
# the right-hand column holds the worker panes, one per agent
impl=(${others[@]+"${others[@]}"})
if (( ${#impl[@]} >= 3 )); then
  echo "tab full: 3 agents already shown for $repo" >&2; exit 1
fi
```

Then replace the split section (from `if [[ -n $target ]]; then` to the final `fi` after `wezterm cli activate-pane --pane-id "$me"`) with:

```bash
if (( ${#impl[@]} == 0 )); then
  new=$(wezterm cli split-pane --pane-id "$me" --right --percent 55 -- "${viewer[@]}")
else
  # first guess at equal heights; equalize_column below fixes what the split leaves uneven
  n=${#impl[@]}
  new=$(wezterm cli split-pane --pane-id "${impl[n-1]}" --bottom --percent $(( 100 * n / (n + 1) )) -- "${viewer[@]}")
fi
echo "$new" > "$state/$name"
equalize_column ${impl[@]+"${impl[@]}"} "$new"
wezterm cli activate-pane --pane-id "$me" >/dev/null 2>&1 || true
```

Keep the `claude --bg ...` call and the `viewer=` lines between the two blocks exactly as they are.

- [ ] **Step 2: `agent-view` - remove all reviewer code**

In the heredoc:
1. `FAIL_RE`: remove `|\bBLOCK` so it reads `re.compile(r"fail|error|exit [1-9]|not clean|FAILED", re.I)`.
2. Delete `REVIEW_PHASES`, `VERDICT_RE` and the whole `review_phase` function (from `REVIEW_PHASES = [...]` through that function's `return None`, plus the blank lines around it).
3. Replace `simple_view` with:

```python
def simple_view(name, w, state, elapsed, branch, commit, subject, report, pending, last_text, last_activity):
    """Status only: working, needs you or done. Nothing about what the worker is doing."""
    if state == "blocked":
        chip = c(AMBER, "needs you")
    elif state == "done":
        chip = c(GREEN, "done")
    elif state in ("working", "running", "busy"):
        chip = c(TEAL, "working")
    else:
        chip = dim(state)
    right = chip + dim(f" · {elapsed}")
    repo = os.path.basename(git(".", "rev-parse", "--show-toplevel"))
    short = name[len(repo) + 1:] if repo and name.startswith(repo + "-") else name  # the repo prefix says nothing in a pane
    lines = [split(bold(clip(short, w - vis(right) - 2)), right, w)]
    if branch:
        lines.append(dim(clip(branch, w)))
    lines.append("")
    if state == "blocked":
        text = pending["doing"] if pending else (last_text.splitlines()[0] if last_text else "waiting for you")
        lines.append(c(AMBER, "waiting  ") + clip(text, w - 9))
        lines.append(dim("answer with: ") + f"claude attach {name}")
    elif state == "done":
        lines.append(clip(f'{commit} "{subject}"', w) if commit else dim("no commit"))
    elif last_activity and time.time() - last_activity >= 120:
        lines.append(dim(f"quiet for {fmt_dur(time.time() - last_activity)}"))
    if report == "failed":
        lines.append(c(RED, "the NGISA did not get the result"))
    while lines and lines[-1] == "":
        lines.pop()
    return [fit(l, w) for l in lines]
```

4. In `draw`: delete `reviewer = bool(re.search(...))`; change `verdict, verdict_text, steps, reviewed = "", "", 0, ""` by deleting that line; delete the whole `if reviewer:` block inside the event loop (from `if reviewer:` through `verdict_text = re.sub(...)`); delete the `steps += 1` line.
5. `working = "reviewing" if reviewer else "working"` and the `chip = {...}` dict: replace with `chip = {"working": c(TEAL, "working"), "running": c(TEAL, "working"), "busy": c(TEAL, "working"), "blocked": c(AMBER, "needs you"), "done": c(GREEN, "done"), "idle": dim("idle")}.get(state, dim(state))`.
6. The `simple_view(...)` call becomes `return simple_view(name, w, state, elapsed, branch if in_own else "", commit, subject, report, pending, last_text, last_activity)`.
7. Replace the `if reviewer: lines.append(dim(...reviewing...)) else: ...` pair with the single line `lines.append(dim(clip(f"{branch} · {shown}" if in_own else f"{branch if branch != '?' else 'no branch'} · in the main checkout", w)))`.
8. Delete the `if verdict == "BLOCK": bad.add("verdict")` and `if verdict: hit.add("verdict")` lines (keep `bad = set()`).
9. Delete the whole `elif state == "done" and reviewer:` branch (4 lines).
10. Replace `lines.append(strip(hit, cur, state, bad, REVIEW_PHASES if reviewer else PHASES))` with `lines.append(strip(hit, cur, state, bad))`, and the `if reviewer: ctr = [...] else:` block with its `else` body un-indented:

```python
    ctr = ["preparing worktree"] if preparing else [f"{len(changed)} file{'s' if len(changed) != 1 else ''}"]
    if changed:
        ctr.append(f"+{add} −{rem}")
    ctr.append({"running": "gate running", "failed": "gate failed", "passed": "gate passed", "ran": "gate ran"}.get(gate, "gate not run"))
```

11. Read the rest of `draw` and the file after the strip/counter lines for any other use of `reviewer`, `verdict`, `steps`, `reviewed`, `REVIEW_PHASES`, and remove it the same way.

- [ ] **Step 3: Comment and text cleanups**

- `ngisa-statusline` docstring: delete the sentence `The reviewer is also a background worker (a `-review` pane) and is listed like the others.`
- `caveman-ultra-hook` (both `msg=` strings) and `repo-tab` (`style=` string): `Running. Reviewer next.` becomes `Running. Gate-check next.`; `Long text too (reviewer verdicts, findings, decisions)` becomes `Long text too (findings, decisions)`.

- [ ] **Step 4: Install and verify**

```bash
KIT=/Users/khoamai/Projects/my_proj/ngisa
extract() { awk -v a="cat > ~/bin/$1 <<'EOF'" -v b="cat > \$KIT/$1 <<'EOF'" '$0==a||$0==b{f=1;next} f&&$0=="EOF"{exit} f' "$KIT/docs/orchestration/lab-quickstart.md"; }
for n in agent-wall.sh agent-view ngisa-statusline caveman-ultra-hook repo-tab; do extract $n > ~/bin/$n; chmod +x ~/bin/$n; done
bash -n ~/bin/agent-wall.sh && bash -n ~/bin/caveman-ultra-hook && bash -n ~/bin/repo-tab && echo bash-ok
python3 -I -m py_compile ~/bin/agent-view ~/bin/ngisa-statusline && echo py-ok
python3 -I -m pyflakes ~/bin/agent-view 2>/dev/null || echo "(pyflakes not installed; rely on grep below)"
grep -n -i "reviewer\|review_phase\|REVIEW_PHASES\|VERDICT\|verdict\|reviewed\|\bsteps\b\|-review" ~/bin/agent-wall.sh ~/bin/agent-view ~/bin/ngisa-statusline ~/bin/caveman-ultra-hook ~/bin/repo-tab
~/bin/agent-view no-such-session | head -3
echo '{}' | ~/bin/caveman-ultra-hook | head -c 300
```
Expected: `bash-ok`, `py-ok`, the big grep prints nothing (a hit on `steps` in an unrelated sense must be inspected and is fine only if unrelated to review), `agent-view` prints `no-such-session: no such background session (yet)`, the hook prints JSON without the word "Reviewer".

- [ ] **Step 5: Live check of pane layout (needs WezTerm)**

In a throwaway lab (Task 8 sets one up), spawn 3 dummy workers and a 4th: the 4th must print `tab full: 3 agents already shown`. If WezTerm is not available in this session, say so in the checkpoint; do not claim it works.

- [ ] **Step 6: Checkpoint** (no commit)

---

### Task 4: `lab-quickstart.md` prose

**Files:**
- Modify: `docs/orchestration/lab-quickstart.md`

- [ ] **Step 1: Edit the prose around the heredocs**

1. Step 4 "Gate integrity" bullet becomes: `- Gate integrity: `settings.local.json` denies Edit on `tool/setup.sh`, `tool/ci_local.sh` and `tool/known_failures.txt` (change them by hand). On each worker report the NGISA runs `gate-check <branch>`, which fails if a worktree's copy of those files differs from the main checkout, or if lint, analyzer, test or CI config changed on the branch. It checks nothing else: you read the diff. Known gap: it runs after the worker is done, it does not stop a shell edit like `sed -i`, it reports it.`
2. Step 5 "You should see" list: in the first bullet, change `one result line (the commit for an implementer, `N findings` for a reviewer). A reviewer's status reads `reviewing`, then `APPROVED` or `BLOCK`. A worker that ...` to `one result line (the commit). A worker that ...`. Delete the bullet `a reviewer pane opens ...`. Replace `the NGISA collects the verdicts and shows you one table` with `the NGISA runs `gate-check` on each branch, merges the clean ones into a feature branch, runs `ci_local.sh`, and shows you one table (task | branch | gate-check | tests | unverified items)`. Change `2 panes open ... one per agent` unchanged.
3. Troubleshooting row `no workers line ...`: delete `(reviewers too, since they are workers)`.
4. Add a troubleshooting row: `| `gate-check: no local branch 'x'` | the branch name in the worker's report is not a local branch of the main checkout; ask the worker for its real branch (`git branch --show-current` in its worktree) |`
5. Anywhere the doc lists the scripts or counts them (search `nine`, `agent-wall.sh, agent-view`), add `gate-check`.

- [ ] **Step 2: Verify**

Run: `grep -n -i "review" docs/orchestration/lab-quickstart.md`
Expected: only these remain: Step 4 `review them against the repo's real CI` (generated files, unrelated), `review tool/setup.sh ...` (agent-init text, unrelated), `NGISA ... carve`-style text not mentioning reviewers, and `read the diff`. Every remaining line must be one that does not refer to a reviewer agent, pane or verdict. Also: `grep -n "BLOCK\|APPROVE" docs/orchestration/lab-quickstart.md` prints nothing.

- [ ] **Step 3: Checkpoint** (no commit)

---

### Task 5: Design doc (en + vi) and `lab-setup.md`

**Files:**
- Modify: `docs/orchestration/one-terminal-orchestrator.md`, `docs/orchestration/one-terminal-orchestrator.vi.md`, `docs/orchestration/lab-setup.md`

- [ ] **Step 1: Edit the English design doc**

Read each region first (line numbers from before this change, may have shifted): 5, 42, 100-130, 140-165, 184-190, 223, 285-286, 298-301, 317, 322, 328, 346, 352.

- Line 5: `and an **Opus reviewer** on each result` becomes `and a `gate-check` script on each result (you review the diff yourself)`.
- Line 42 table row `| `implementer.md`, `reviewer.md` | ...` becomes `| `implementer.md` | `~/.claude/agents/` | once, all repos |`.
- Section 2a: delete the `~/.claude/agents/reviewer.md` heading and its code block (about lines 105-125). Keep a one-line note under 2a: `There is no reviewer agent. The user reads the diff; `gate-check` (see lab-quickstart.md) only guards the gate files and lint config.`
- Section 2c rules and the copies at 150-162 and 298-301: apply the exact same text as `orchestrating.md` steps 4, 6, 7, the quick-task line and the Style edits from Task 2. The embedded 2c block must equal the new `orchestrating.md`.
- Line 186 `reviewer checks each one` becomes `gate-check runs on each one`; line 188 `reviewer APPROVE on all tasks` becomes `gate-check clean on all tasks`.
- Line 223 `reviewer verdicts` becomes `findings`.
- Lines 285-286: delete the `Reviewer panes: ...` bullet; in the `agent-view shows status only ...` bullet remove `, `N findings` for a reviewer, ...` clauses and the reviewer status sentence.
- Line 317 (`3. **Reviewer vs implementer disagreement after 2 rounds.** You decide.`): replace with `3. **A failed `gate-check`.** You decide: keep the change (it was asked for) or send the worker back.` and update the "human gates" count text if it says how many there are.
- Line 322 `per-task review` becomes `gate-check`. Line 328 `Opus only for orchestrator + reviewer` becomes `Opus only for the orchestrator`. Line 346 metric `reviewer BLOCKs` becomes `gate-check FAILs`. Line 352 `implementer.md + reviewer.md + ...` becomes `implementer.md + ...`.
- Lines 171 and 318 claim a PreToolUse hook blocks merges to main, which the shipped `settings.local.json` does not have. Out of scope: leave as is, and list it in the final report to the user.

- [ ] **Step 2: Mirror into the Vietnamese doc**

Apply the same edits at the equivalent places (the agent report put them around lines 8, 23, 37, 84, 89, 99-116, 131-153, 183-184, 190, 250-297). Translate prose; keep code blocks, commands, filenames in English. Use this wording where a new sentence is needed:
- 2a note: `Không có reviewer agent. Người dùng tự đọc diff; `gate-check` (xem lab-quickstart.md) chỉ bảo vệ các file gate và cấu hình lint.`
- Human gate 3: `3. **`gate-check` báo lỗi.** Bạn quyết định: giữ thay đổi (vì task có yêu cầu) hoặc trả lại cho worker.`

- [ ] **Step 3: `lab-setup.md`**

Line 13: `implementer.md, reviewer.md` becomes `implementer.md`. Line 27: `ngisa/agents/implementer.md, ngisa/agents/reviewer.md` becomes `ngisa/agents/implementer.md`. Leave lines 14, 29, 75 (the "block hook" claims) alone, same reason as above.

- [ ] **Step 4: Verify**

Run: `grep -n -i "reviewer\|APPROVE\|BLOCK" docs/orchestration/one-terminal-orchestrator.md docs/orchestration/one-terminal-orchestrator.vi.md docs/orchestration/lab-setup.md`
Expected: only the hits the "block hook" claims produce (`block hook` is a different word: match `BLOCK` case-sensitively: `grep -n "BLOCK\|APPROVE\|[Rr]eviewer"`). Expected: no output. Also diff the embedded 2c block against `orchestrating.md` by eye or with `diff <(sed -n '<start>,<end>p' docs/orchestration/one-terminal-orchestrator.md) orchestrating.md`.

- [ ] **Step 5: Checkpoint** (no commit)

---

### Task 6: Top-level docs and decision log

**Files:**
- Modify: `CLAUDE.md`, `CONTEXT.md`, `PRODUCT.md`, `README.md`, `README.vi.md`, `docs/README.md`, `docs/verification/cut-verification-time.md`, `docs/verification/cut-verification-time.vi.md`

- [ ] **Step 1: `CLAUDE.md`**

Line 3: `(NGISA, implementer and reviewer agents, hooks, scripts)` becomes `(NGISA, implementer agent, hooks, scripts)`. Rules bullet: `Log each run (time, interventions and why, BLOCKs, cost)` becomes `Log each run (time, interventions and why, gate-check FAILs, cost)`.

- [ ] **Step 2: `README.md` and `README.vi.md`**

English:
- Tagline: `They write, test and review. Only you merge.` becomes `They write and test. You review and merge.`
- Intro: `has every branch reviewed, and stops at a draft PR for you` becomes `checks that the gate was not touched, and stops at a draft PR for you`.
- GIF alt text: `a reviewer approves, you merge` becomes `a gate check passes, you merge`.
- Gate bullet: `A reviewer checks that the gate files were not touched.` becomes ``gate-check`, a script, checks that the gate files and lint config were not touched.`
- Last section: `(time, interventions, BLOCKs, cost)` becomes `(time, interventions, gate-check FAILs, cost)`. Also `You stay in charge` bullet: add `You review the diff.` after `You approve the plan.`

Vietnamese: make the equivalent edits (same lines, 5, 7, 9, 16). Keep `NGISA`, `gate-check`, filenames in English.

- [ ] **Step 3: `PRODUCT.md` lines 10 and 13**

Read both lines, drop `reviewer` from the worker list and `reviewed` from the outcome phrase (`a reviewed branch comes out` becomes `a branch that passed its gate comes out`).

- [ ] **Step 4: `docs/README.md`**

Line 8: `implementer and reviewer agents` becomes `implementer agents`. Line 13 script list: add `gate-check` and change the count (`nine` to `ten`). Line 27 `CI as second reviewer` stays (concept doc). Repo-files table row `agents/implementer.md`, `agents/reviewer.md` becomes `agents/implementer.md`.

- [ ] **Step 5: `cut-verification-time.md` and `.vi.md`**

Leave the research body alone. Directly under the title add:
- en: `> Kit note (2026-10-15): the NGISA kit no longer runs a reviewer agent. You review the diff yourself, and `gate-check` only compares gate files and lint config. The review-agent advice below is kept as research.`
- vi: `> Ghi chú về kit (2026-10-15): kit NGISA không còn chạy reviewer agent. Bạn tự xem diff, `gate-check` chỉ so sánh file gate và cấu hình lint. Phần tư vấn về review agent bên dưới được giữ lại như tài liệu nghiên cứu.`

- [ ] **Step 6: `CONTEXT.md` - decision log**

1. Orchestrator "Roles" bullet: replace `Reviewer = Opus, answers APPROVE or BLOCK. A BLOCK goes back to the same implementer, for 2 rounds at most, and after that the human decides.` with `No reviewer agent (removed 2026-10-15): the user reviews the final diff. `gate-check` (a script) runs on each worker report.`
2. NGISA section: in the quick-task bullet `reviewer still runs` becomes `gate-check still runs`; in the caveman bullet drop `and reviewer` from `the NGISA, implementers and reviewer all get it`.
3. Stack-agnostic bullet `the reviewer BLOCKs a worktree whose copy differs ...` becomes `gate-check fails a worktree whose copy of the gate files differs from the main checkout, or a branch that changed lint, analyzer, test or CI config. Known gap: it runs after the worker is done and only reports a shell edit.`
4. Max plan limits: `Opus only for the NGISA and the reviewer` becomes `Opus only for the NGISA`.
5. Verification section: keep `Opus for plans and reviews` (research), no change.
6. Add a new decision section after "Stack-agnostic workers":

```
### Review stage removed (2026-10-15)
- Why: the user reviews every result anyway, so the Opus reviewer and its BLOCK loop (2 rounds) only added latency and quota use.
- What stays: `gate-check <branch> [base]` (a script in `~/bin`, no LLM) fails on a differing `tool/ci_local.sh`, `tool/setup.sh` or `tool/known_failures.txt`, or on changed lint, analyzer, test or CI config. The NGISA runs it on each report and stops on exit 1.
- What is lost: the reviewer's checks for secrets or PII in the diff, edits outside the task's paths, and tests that would pass without the change. The user covers them at the final diff.
- Old runs under `docs/runs/` still describe the reviewer; they are research data and were not rewritten.
```

7. Kit map: first row becomes `| `agents/implementer.md` | one-terminal-orchestrator.md section 2a |`; last row add `gate-check` to the `~/bin` list.
8. Run 1 note `so check that the reviewer reads the branch actually used` and the `BLOCK count` in "Still to log": leave (historical run record). Open items: `a shell edit of `tool/ci_local.sh` is only caught by the reviewer's diff` becomes `... is only caught by `gate-check`, after the fact`.

- [ ] **Step 7: Verify**

Run: `grep -rn "[Rr]eviewer\|BLOCK\|APPROVE" CLAUDE.md PRODUCT.md README.md README.vi.md docs/README.md`
Expected: no output. `grep -n -i "reviewer" CONTEXT.md` must show only: the new decision section, Run 1 historical lines, and the Verification section's research bullets. Check `grep -c "—" CLAUDE.md CONTEXT.md README.md` is 0 for any em dash you added.

- [ ] **Step 8: Checkpoint** (no commit)

---

### Task 7: Diagrams, site, demo and GIFs

**Files:**
- Modify: `docs/diagrams/ngisa-and-agent-wall.html`, `docs/diagrams/ngisa-and-agent-wall.vi.html`, `docs/diagrams/ngisa-demo.html`, `docs/index.html`, `docs/index.vi.html`, `docs/assets/site.css`
- Regenerate: `docs/assets/ngisa-demo.gif`, `docs/assets/ngisa-demo.vi.gif`

- [ ] **Step 1: `ngisa-and-agent-wall.html` (and `.vi.html`, same geometry, translated text)**

1. Chat mock (`.chat` block): `<div class="cl">cache APPROVE · sync BLOCK (round 1)</div>` becomes `<div class="cl">cache gate-check ok · sync gate-check <span class="hl">FAIL</span></div>`. The third pane text `fixing reviewer findings` becomes `waiting for your call`.
2. Key: delete the `<span style="color:var(--review)">...Reviewer · Opus</span>`.
3. SVG `aria-label`: replace `each reports to the reviewer, blocked work goes back to the same agent, approved work is merged` with `each reports to the NGISA, which runs gate-check; a failed check stops for you; clean work is merged`.
4. SVG reviewer group: the `<rect class="box rv" ...>` becomes `<rect class="box g" x="215" y="480" width="215" height="52" rx="8"/>`; its two texts become `gate-check` and `gate files, lint config`. Delete the two `BLOCK: same agent fixes` / `max 2 rounds` labels. Keep the dashed arrow `M405 480V376H475` out: delete it (a failed check does not go back to the agent automatically). The "Break the tie" box texts become `Your call` and `if gate-check fails`; keep its dashed arrow from the gate-check box. The `APPROVE` label under the box becomes `clean`.
5. Steps list: `<li data-o="review"><div><b>Reviewer</b>...` becomes `<li data-o="gate"><div><b>gate-check</b><span>A script compares the gate files and lint config. A difference stops the merge and waits for you.</span></div></li>`.
6. "What only you do": `<li><b>Reviewer deadlock</b><span>After 2 BLOCK rounds</span></li>` becomes `<li><b>Reading the diff</b><span>You are the reviewer; there is no review agent</span></li>`. "Max plan limits": `Opus only for the NGISA and the reviewer.` becomes `Opus only for the NGISA.`
7. Vietnamese file: same changes, translated (`gate-check` and filenames stay).

- [ ] **Step 2: `site.css` and `index(.vi).html`**

- `site.css`: remove `--review:#e7a447;` from `:root`, remove `.fig-steps li[data-o=review] b{color:var(--review)}` (keep the `data-o=human` rule on the same line), remove `svg .rv{stroke:var(--review)}`. Check the dark/light token blocks for a second `--review` and remove it too.
- `index.html` and `index.vi.html`: remove the two `.flow li[data-o=review]` rules (lines 47, 52), keeping the `human` rules. `<meta description>` and `.sub`: `They write, test and review. Only you merge.` becomes `They write and test. You review and merge.`; `has every branch reviewed, and stops at a draft PR for you` becomes `checks that the gate was not touched, and stops at a draft PR for you`. Promises `Gated` bullet: `A reviewer checks that the gate files were not touched.` becomes `A script (<code>gate-check</code>) checks that the gate files and lint config were not touched.` Flow item 5: `<li data-o="review"><div><b>Review</b><span>APPROVE, or BLOCK back to the same worker. 2 rounds max.</span></div></li>` becomes `<li data-o="gate"><div><b>Check</b><span><code>gate-check</code> confirms the gate was not touched, then the branches merge.</span></div></li>`. Demo `title`/`alt`: `built by two workers, reviewed and left for you to merge` becomes `built by two workers, checked and left for you to merge`. `MAP=[0,1,1,2,3,4,4,4,5]` stays (9 demo steps, 6 flow items). Vietnamese file: same, translated.

- [ ] **Step 3: `ngisa-demo.html`**

In `<style>`: delete `--review:#e7a447;` from `:root`, `.bad{color:var(--review)}` (keep `.ok{...}`), and `.st.r{background:var(--review);color:#10141b}`. Change `.stack{...grid-template-rows:repeat(3,1fr)...}` to `repeat(2,1fr)` and, in the `@media (max-width:640px)` block, `repeat(3,minmax(84px,auto))` to `repeat(2,minmax(84px,auto))`.

In `T.en` (and the vi equivalents): delete `syncBlock`, `fixing`, `review`, `reviewing`, `gatefiles`, `revCache`, `revSync1`, `revSync2`. Set:

```js
    cacheOk: "cache gate-check <span class=ok>ok</span>",
    syncOk: "sync gate-check <span class=ok>ok</span>",
    merged: "Merged cache, sync into a feature branch",
    done: "Draft PR ready. <span class=hl>Your merge.</span>",
    working: "Working", done_: "Done",
```
(vi: `cacheOk: "cache gate-check <span class=ok>ok</span>"`, `syncOk: "sync gate-check <span class=ok>ok</span>"`, `merged: "Đã gộp cache, sync vào nhánh feature"`, `done: "Draft PR sẵn sàng. <span class=hl>Bạn merge.</span>"`, `working: "Đang chạy", done_: "Xong"`.)

Captions (9, same count so `DURATIONS` and `index.html` MAP still fit):

```js
    caps: [
      "You give NGISA a task",
      "NGISA plans and splits it",
      "You approve the plan",
      "Workers start, each in its own git worktree",
      "Each worker must pass the repo's tool/ci_local.sh",
      "NGISA runs gate-check: gate files untouched",
      "Clean branches merge into a feature branch",
      "ci_local.sh runs again, draft PR ready",
      "Only you merge to main"
    ],
```
vi: `"Bạn giao việc cho NGISA"`, `"NGISA lên plan và chia task"`, `"Bạn duyệt plan"`, `"Worker khởi động, mỗi worker một git worktree"`, `"Mỗi worker phải qua tool/ci_local.sh của repo"`, `"NGISA chạy gate-check: file gate không bị đụng"`, `"Nhánh sạch được gộp vào nhánh feature"`, `"ci_local.sh chạy lại, draft PR sẵn sàng"`, `"Chỉ bạn được merge vào main"`.

In `model()`: remove the `bad`/`ok` helper constants that become unused (keep `dim`), then:

```js
  const ngisa = [
    {id:"task",   cls:"you", at:250,   rate:38, html:t.task},
    {id:"plan",   cls:"cl",  at:1750,  rate:16, html:t.plan},
    {id:"go",     cls:"you", at:3500,  rate:90, html:t.go},
    {id:"spawn",  cls:"cl",  at:4800,  rate:0,  html:t.spawned},
    {id:"cacheOk",cls:"cl",  at:9500,  rate:0,  html:t.cacheOk},
    {id:"syncOk", cls:"cl",  at:10300, rate:0,  html:t.syncOk},
    {id:"merged", cls:"cl",  at:11300, rate:16, html:t.merged},
    {id:"ci",     cls:"cl",  at:13500, rate:0,  html:t.gateOk},
    {id:"done",   cls:"cl",  at:15700, rate:14, html:t.done}
  ];
  const slot = (id, list) => list.map((e, i) => Object.assign({id: id + i}, e));
  const panes = [
    {name:"shelfie-cache", at:4800,
     status:[{at:4800, txt:t.working, c:"w"}, {at:9300, txt:t.done_, c:"d"}],
     l1: slot("c1", [{at:4950, rate:0, html:dim(t.wt)}, {at:9300, rate:30, html:t.gateOk}]),
     l2: slot("c2", [{at:5200, rate:22, html:t.tests}, {at:6900, rate:30, html:t.gateRun}, {at:9300, rate:0, html:""}])},
    {name:"shelfie-sync", at:4800,
     status:[{at:4800, txt:t.working, c:"w"}, {at:10100, txt:t.done_, c:"d"}],
     l1: slot("s1", [{at:4950, rate:0, html:dim(t.wt)}, {at:10100, rate:30, html:t.gateOk}]),
     l2: slot("s2", [{at:5200, rate:22, html:t.tests}, {at:6900, rate:30, html:t.gateRun}, {at:10100, rate:0, html:""}])}
  ];
```

The `.ngisa` pane has room for 9 lines at 13px/1.6 in the 456px window: check frame 7 visually (Step 5); if the last line clips, shorten `merged` or drop the `ci` line and move its caption to `done`.

- [ ] **Step 4: Render GIFs**

Run: `cd /Users/khoamai/Projects/my_proj/ngisa/docs/diagrams && ./render-demo-gif.sh`
Expected: prints `ngisa-demo.gif <n> bytes` and `ngisa-demo.vi.gif <n> bytes`. If Node 22, Chrome or ffmpeg is missing, stop and tell the user; do not hand-edit the GIFs.

- [ ] **Step 5: Pixel check (user standard: picky)**

Open each in a browser or headless Chrome screenshot at 960x540: `ngisa-demo.html?step=0..8&lang=en` and `lang=vi`; the two diagram pages; `index.html` and `index.vi.html` at 1280 and 390 wide. Check: no leftover reviewer pane or empty gap in the stack (2 rows fill the height), caption text not clipped, the SVG gate-check box and the "Your call" box are aligned with their arrows, no orphan arrow (the removed `M405 480V376H475`), flow highlight in `index.html` follows steps (steps 5-7 highlight item 5 "Check"). View the new GIFs frame by frame (a few frames via ffmpeg `-vf fps=1`).

- [ ] **Step 6: Verify strings**

Run: `grep -rn -i "review\|BLOCK\|APPROVE\|--review\|data-o=review\|\.rv" docs/diagrams docs/index.html docs/index.vi.html docs/assets/site.css`
Expected: only `render-demo-frames.mjs`-style unrelated hits (none expected), and the intended `You review and merge`, `You are the reviewer` strings, plus `CI + Claude review` (remote second reviewer, stays).

- [ ] **Step 7: Checkpoint** (no commit)

---

### Task 8: Lab sync, end-to-end run, run log

**Files:**
- Modify (outside repo): `~/lab/busy-bees/.claude/agents/`, `~/lab/busy-bees/CLAUDE.local.md`, `~/lab/busy-bees/.claude/settings.local.json`
- Create: `docs/runs/2026-10-15-remove-review-stage.md`

- [ ] **Step 1: Sync the existing lab by hand**

`make-lab` refuses an existing lab, so replicate its three kit-copy lines for `~/lab/busy-bees`:

```bash
KIT=/Users/khoamai/Projects/my_proj/ngisa; LAB=~/lab/busy-bees
git -C "$KIT" show HEAD:agents/reviewer.md | diff -q - "$LAB/.claude/agents/reviewer.md" && rm "$LAB/.claude/agents/reviewer.md"
cp "$KIT/agents/implementer.md" "$LAB/.claude/agents/implementer.md"
cp "$KIT/settings.local.json" "$LAB/.claude/settings.local.json"
cp "$KIT/orchestrating.md" "$LAB/CLAUDE.local.md"
ls "$LAB/.claude/agents"
```
Expected: `implementer.md` only. If the `diff -q` reports a difference the lab copy was customised: stop and ask.

- [ ] **Step 2: End-to-end run (needs the user's WezTerm)**

Tell the user to run `repo-tab ~/lab/busy-bees`, give the NGISA a small 2-part task, approve the plan, and say `go`. Expected: 2 worker panes only; after each report the NGISA runs `gate-check`; clean branches merge and `ci_local.sh` runs; the table has a `gate-check` column and no reviewer. Then force a failure: have a worker (or you by hand in its worktree) append a line to `tool/known_failures.txt` before its report and confirm the NGISA stops with the diff. A 4th `agent-wall.sh` call must print `tab full`. Do not claim success for anything not observed; if the user cannot run it now, record it as not exercised.

- [ ] **Step 3: Write the run log**

Create `docs/runs/2026-10-15-remove-review-stage.md` with: date, what changed (link to spec), the verification commands run and their output, what was observed live vs not exercised, interventions and why, gate-check FAILs, cost if known.

- [ ] **Step 4: Final sweep**

```bash
cd /Users/khoamai/Projects/my_proj/ngisa
grep -rIn "[Rr]eviewer" --exclude-dir=.git --exclude-dir=runs --exclude-dir=superpowers . | grep -v "second reviewer"
git status --short
```
Expected: the grep shows only the intended leftovers (CONTEXT.md Run 1 history and the new decision section, the cut-verification research body, `You are the reviewer`). `git status` shows only the files named in this plan. Report the list to the user and ask whether to run `/carve` to commit. Do not commit before they say so.

---

## Self-review

- **Spec coverage:** reviewer agent deletion (Task 2), NGISA flow + gate-check step (Tasks 1, 2), pane code and `agent-view` (Task 3), docs en+vi (Tasks 4-6), diagrams, demo, GIFs (Task 7), lab sync, e2e, run log (Task 8), keep `docs/runs/*` (Global Constraints, Task 8). The spec's "PII/secrets, outside-paths, tests-pass-without-change" are explicitly listed as lost in CONTEXT.md (Task 6).
- **Placeholders:** none; doc-prose tasks give exact replacement text or the exact rule plus a grep that proves completion.
- **Type consistency:** `gate-check <branch> [base-branch]` and exit codes 0/1/2 are the same in Tasks 1, 2, 4, 6. Table header `task | branch | gate-check | tests | unverified items` is the same in Tasks 2, 4, 5.
- **Deviations from the spec worth the user's attention:** `gate-check` takes a branch name (it finds the worktree itself), so the implementer's report format does not change. The demo drops the BLOCK drama and shows two clean branches. Lint-config check includes `.gitlab-ci.yml` and `.github/workflows/`.
