import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


class ImplementerTextTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.text = (ROOT / "agents" / "implementer.md").read_text()

    def test_warm_start_and_commit_body_fields(self):
        for needle in ("Branch:", "checks:", "unverified:", "asks:",
                       "git checkout -B", "warm-"):
            self.assertIn(needle, self.text)

    def test_last_commit_carries_lines(self):
        self.assertIn("LAST commit", self.text)
        self.assertIn("git commit --allow-empty", self.text)

    def test_base_and_cold_start(self):
        for needle in ("Branch: <name>. Base: <ref>.", "git checkout -B <name> <ref>",
                       "never origin/HEAD", "is not a message", "final line `no branch given`",
                       "final line = the exact error", "warm start: as the Warm start line says"):
            self.assertIn(needle, self.text)
        self.assertNotIn("stop and report now", self.text)
        self.assertIn("In a `warm-*` worktree, a task message with no `Branch:` line", self.text)

    def test_no_seven_line_report_or_sendmessage(self):
        self.assertNotIn("exactly these seven lines", self.text)
        self.assertNotIn("SendMessage", self.text)

    def test_cold_start_isolation_check(self):
        for needle in ("git worktree add .claude/worktrees/<last path segment of Branch> -b <name> <ref>",
                       "git worktree list --porcelain", "git rev-parse --show-toplevel",
                       "NEVER run `git checkout`, `git switch`, `git reset` or commit in the main checkout",
                       "Never change the branch, index or files of the main checkout",
                       "Already in a linked worktree (path under `.claude/worktrees/`): run `git checkout -B <name> <ref>` there",
                       "run `worktree-include`, and work ONLY there"):
            self.assertIn(needle, self.text)
        self.assertNotIn("your isolation worktree is new", self.text)

    def test_several_numbered_steps(self):
        self.assertEqual(self.text.count("Task text may hold several numbered steps: do them in order in this worktree, one commit per step, the LAST commit carries the `checks:`/`unverified:`/`asks:` lines for all steps."), 2)

    def test_front_matter(self):
        m = re.match(r"---\n(.*?)\n---\n", self.text, re.S)
        self.assertIsNotNone(m)
        self.assertIn("isolation: worktree", m.group(1))
        self.assertIn("model: sonnet", m.group(1))

    def test_no_em_dash(self):
        self.assertNotIn("—", self.text)

    def test_quick_mode(self):
        for needle in ("mode: quick", "no extra test cases", "mode: direct", "mode: plan"):
            self.assertIn(needle, self.text)

    def test_no_reformat_rule(self):
        self.assertEqual(self.text.count("Do not reformat code you did not change: if a formatter rewrites other lines, undo those hunks before committing."), 2)

    def test_call_pattern_and_output_trimming(self):
        for needle in ("Call pattern for quick mode (target 5 to 6 requests; direct mode keeps red first and then uses steps 3 and 4; a multi-step task runs it once per numbered step):",
                       "1) Warm start: ONE Bash call `git checkout -B <name> <ref>` first. Read the files you need only after it, never before",
                       "2) ONE turn, parallel Write/Edit calls for all listed files.",
                       "3) ONE Bash call for all listed checks: `log=$(mktemp); rc=0; { <check 1> || rc=1; <check 2> || rc=1; } > \"$log\" 2>&1; echo \"exit=$rc\"; tail -n 40 \"$log\"`.",
                       "A red result: also run `grep -n -m 20 -E 'FAIL|Error|error:' \"$log\"`, fix, re-run the chain.",
                       "4) ONE Bash call to commit: `git add` the listed paths, `git commit` with the body lines.",
                       "Plan mode keeps its own procedure."):
            self.assertIn(needle, self.text)
        self.assertNotIn("(<check 1>; <check 2>)", self.text)

    def test_reused_worker_rule(self):
        self.assertIn("A reused worker (it already did an earlier task): start from this Base ref, ignore the earlier task's scope, touch only this task's listed paths.", self.text)

    def test_no_stack_tools(self):
        low = self.text.lower()
        for word in ("flutter", "fvm", "phpunit"):
            self.assertNotIn(word, low)


class OrchestratingTextTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.text = (ROOT / "orchestrating.md").read_text()
        cls.quick = (ROOT / "docs" / "orchestration" / "lab-quickstart.md").read_text()

    def test_dependent_tasks_one_worker(self):
        self.assertIn("go to ONE worker as a single task text, tasks in order", self.text)
        self.assertIn("Only independent tasks get separate workers.", self.text)
        self.assertIn("numbered steps in order", self.text)
        self.assertNotIn("chain them", self.text)

    def test_required(self):
        for needle in ("notify_when_idle", "ngisa-spawned", "--need N",
                       "Branch:", "ngisa-collect", "ngisa-start"):
            self.assertIn(needle, self.text)
        self.assertNotIn("git -C", self.text)

    def test_new_rules(self):
        t = self.text
        self.assertIn('message: "Branch: <name>. Base: <base>. <task text>"', t)
        self.assertIn("`base: <sha>`", t)
        self.assertNotIn("git log -1 --format=%H", t)
        self.assertIn("state `done` or `idle`", t)
        self.assertIn("`branch=warm/N`", t)
        self.assertIn("git worktree list --porcelain", t)
        self.assertIn("no `checks:` line", t)
        self.assertIn("never `ok`", t)
        self.assertIn("carries `notify_when_idle: true`", t)
        self.assertNotIn("claude agents --cwd", t)
        self.assertNotRegex(t, r"claude agents(?! --json)")

    def test_reuse_and_retire_rules(self):
        t = self.text
        for needle in ("worker-ctx", "worker-retire", "closes the pane only for `ok`", "# Compact instructions",
                       "`ctx` under 100k", "`idle` under 55 min", "`tasks` under 3",
                       
                       "Unknown last paths: not reusable.",
                       "end a worker only with `worker-retire`"):
            self.assertIn(needle, t)
        for raw in ("claude stop", "claude rm"):
            for line in t.splitlines():
                if raw in line:
                    self.assertTrue(line.startswith("Never:") or line.lstrip().startswith("delete branches"), line)
        self.assertTrue(t.rstrip().endswith("unknown last paths mean: not reusable."))
        # review fixes: no contradiction on name reuse, dirty check through worker-result, dependent Base for reuse
        self.assertIn("never give a NEW assignment a name already on it", t)
        self.assertNotIn("never reuse a name on it this run", t)
        self.assertIn("its `dirty=no`", t)
        self.assertNotIn("shows a clean tree", t)
        self.assertIn("A task that depends on a worker's earlier task gets `Base:` = that task's branch name, for a reused or a fresh worker.", t)


    def test_cost_cut_rules(self):
        t = self.text
        for needle in ("`ngisa-start`", "`ngisa-spawned", "`ngisa-collect", "one task: run it in plain Claude",
                       "Plan-mode tasks take the cold path and never reuse a worker.",
                       "all in one turn",
                       "N = number of quick/direct tasks (max 3)",
                       "do not start cold meanwhile",
                       "In the same turn as `ngisa-start`, run `ToolSearch` `select:SendMessage`",
                       "do not re-run `ngisa-report set` or `agent-wall.sh --close`",
                       "not a relay or follow-up to a running worker",
                       "size it in one line first",
                       "After an ask is answered, an override to `ok`, or a merge: `agent-wall.sh --close <session>`",
                       "lean workers have no skills"):
            self.assertIn(needle, t)
        self.assertLessEqual(len(t.encode()), 10800)  # ruling: the 80% target was dropped (the file is ~1% of the tokens); it must not grow past the pre-cost-cut 10.7 KB
        for old in ("`ngisa-report mark <slug> report` at the worker's idle notice.",
                    "agent-warm 1 >/dev/null 2>&1 &"):
            self.assertNotIn(old, t)

    def test_removed(self):
        for needle in ("When a worker's report arrives",
                       "send your final report", "gate:"):
            self.assertNotIn(needle, self.text)

    def test_no_em_dash(self):
        self.assertNotIn("\u2014", self.text)

    def test_structure(self):
        for n in range(1, 8):
            self.assertRegex(self.text, r"(?m)^%d\. " % n)
        for h in ("Quiet:", "Ask:", "Size:"):
            self.assertRegex(self.text, r"(?m)^%s" % re.escape(h))

    def test_size_lines_use_quick(self):
        lines = self.text.splitlines()
        for prefix in ("  tiny = ", "  small = "):
            line = next(l for l in lines if l.startswith(prefix))
            self.assertIn("mode: quick", line)
            self.assertNotIn("mode: direct", line)
        self.assertIn("mode: quick|direct|plan <path>", self.text)

    def test_doc_copies(self):
        docs = ROOT / "docs" / "orchestration"
        for name in ("one-terminal-orchestrator.md", "one-terminal-orchestrator.vi.md"):
            doc = {l.strip() for l in (docs / name).read_text().splitlines()}
            for kit in (ROOT / "orchestrating.md", ROOT / "agents" / "implementer.md"):
                for l in kit.read_text().splitlines():
                    if l.strip():
                        self.assertIn(l.strip(), doc, (name, kit.name))
        quick = {l.strip() for l in (docs / "lab-quickstart.md").read_text().splitlines()}
        for l in (ROOT / "agents" / "implementer.md").read_text().splitlines():
            if l.strip():
                self.assertIn(l.strip(), quick)

    def test_quickstart_copy(self):
        quick = {l.strip() for l in self.quick.splitlines()}
        for l in self.text.splitlines():
            t = l.strip()
            if t:
                self.assertIn(t, quick)


class SettingsTextTest(unittest.TestCase):
    def test_allow_and_deny(self):
        import json
        perms = json.loads((ROOT / "settings.local.json").read_text())["permissions"]
        for e in ("Bash(claude agents --json:*)", "Bash(worker-result:*)", "Bash(agent-warm:*)",
                  "Bash(git worktree list:*)", "Bash(git rev-parse HEAD)"):
            self.assertIn(e, perms["allow"])
        self.assertNotIn("Bash(claude agents:*)", perms["allow"])
        for e in perms["allow"]:
            self.assertFalse(e.startswith("Bash(git -C"))
        self.assertIn("Bash(git push:*)", perms["deny"])
        for e in ("Bash(worker-ctx:*)", "Bash(worker-retire:*)", "Bash(ngisa-start:*)", "Bash(ngisa-spawned:*)", "Bash(ngisa-collect:*)"):
            self.assertIn(e, perms["allow"])
        for e in perms["allow"]:
            for raw in ("Bash(claude stop", "Bash(claude rm", "Bash(git worktree remove"):
                self.assertFalse(e.startswith(raw), e)


if __name__ == "__main__":
    unittest.main()
