import json
import os
import subprocess
import tempfile
import unittest

BIN = os.environ.get("NGISA_START_BIN") or os.path.expanduser("~/bin/ngisa-start")

FAKE_CLAUDE = """#!/bin/sh
if [ "$1" = "agents" ]; then cat "$FAKE_AGENTS"; fi
"""
FAKE_REPORT = """#!/bin/sh
echo "ngisa-report $*" >> "$FAKE_LOG"
"""
FAKE_WARM = """#!/bin/sh
echo "agent-warm $*" >> "$FAKE_LOG"
if [ -n "$FAKE_WARM_MAKES" ]; then
  git worktree add -q .claude/worktrees/warm-9 -b warm/9 HEAD
  python3 - "$FAKE_AGENTS" <<'PY'
import json, sys
rows = json.load(open(sys.argv[1]))
rows.append({"name": "demo-warm-9", "state": "done"})
json.dump(rows, open(sys.argv[1], "w"))
PY
fi
"""
FAKE_CTX = """#!/bin/sh
if [ "$1" = "demo-warm-3" ]; then echo "worker-ctx: no transcript" >&2; exit 1; fi
echo "ctx: 40k"; echo "idle: 5m"; echo "tasks: 1"
"""


class NgisaStartTest(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        root = self._tmp.name
        self.repo = os.path.join(root, "demo")
        os.mkdir(self.repo)
        self.git("init", "-q", "-b", "main")
        self.git("commit", "-q", "--allow-empty", "-m", "base")
        self.base = self.git("rev-parse", "HEAD").strip()
        for i, branch in ((1, "warm/1"), (2, "feat/x"), (3, "warm/3")):
            wt = os.path.join(self.repo, ".claude", "worktrees", f"warm-{i}")
            self.git("worktree", "add", "-q", wt, "-b", branch, "HEAD")
        with open(os.path.join(self.repo, ".claude", "worktrees", "warm-2", "dirty.txt"), "w") as f:
            f.write("x")
        fakebin = os.path.join(root, "fakebin")
        os.mkdir(fakebin)
        for name, body in (("claude", FAKE_CLAUDE), ("ngisa-report", FAKE_REPORT), ("worker-ctx", FAKE_CTX), ("agent-warm", FAKE_WARM)):
            p = os.path.join(fakebin, name)
            with open(p, "w") as f:
                f.write(body)
            os.chmod(p, 0o755)
        self.log = os.path.join(root, "log")
        self.agents = os.path.join(root, "agents.json")
        self.set_agents([("demo-warm-1", "done"), ("demo-warm-2", "idle"), ("demo-warm-3", "done"), ("demo-warm-4", "working")])
        self.env = dict(os.environ, PATH=fakebin + os.pathsep + os.environ["PATH"],
                        FAKE_LOG=self.log, FAKE_AGENTS=self.agents)

    def git(self, *args):
        env = dict(os.environ, GIT_AUTHOR_NAME="t", GIT_AUTHOR_EMAIL="t@t", GIT_COMMITTER_NAME="t", GIT_COMMITTER_EMAIL="t@t")
        return subprocess.run(["git", *args], cwd=self.repo, env=env, check=True, capture_output=True, text=True).stdout

    def set_agents(self, rows):
        with open(self.agents, "w") as f:
            json.dump([{"name": n, "state": s} for n, s in rows], f)

    def run_cli(self, *args):
        return subprocess.run([BIN, *args], cwd=self.repo, env=self.env, capture_output=True, text=True)

    def logged(self):
        if not os.path.exists(self.log):
            return []
        with open(self.log) as f:
            return f.read().splitlines()

    def test_new_plan_clears_then_marks(self):
        r = self.run_cli("--new-plan")
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertEqual(self.logged(), ["ngisa-report clear", "ngisa-report mark - request"])

    def test_without_flag_only_marks(self):
        self.run_cli()
        self.assertEqual(self.logged(), ["ngisa-report mark - request"])

    def test_prints_base_and_free_count(self):
        r = self.run_cli()
        lines = r.stdout.splitlines()
        self.assertEqual(lines[0], "base: " + self.base)
        self.assertEqual(lines[-1], "free: 2")  # warm-1 and warm-3 still on warm/N

    def test_dirty_and_branch_per_worker(self):
        r = self.run_cli()
        self.assertIn("warm-1 branch=warm/1 dirty=no ctx=40k idle=5m tasks=1", r.stdout.splitlines())
        self.assertIn("warm-2 branch=feat/x dirty=yes ctx=40k idle=5m tasks=1", r.stdout.splitlines())

    def test_unreadable_worker_prints_dash(self):
        r = self.run_cli()
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertIn("warm-3 branch=warm/3 dirty=no ctx=- idle=- tasks=-", r.stdout.splitlines())

    def test_run_from_linked_worktree_reports_main_checkout(self):
        wt = os.path.join(self.repo, ".claude", "worktrees", "integration")
        self.git("worktree", "add", "-q", wt, "-b", "integ", "HEAD")
        r = subprocess.run([BIN], cwd=wt, env=self.env, capture_output=True, text=True)
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertEqual(r.stdout.splitlines()[0], "base: " + self.base)
        self.assertIn("warm-1 branch=warm/1 dirty=no ctx=40k idle=5m tasks=1", r.stdout.splitlines())

    def test_need_tops_up_and_waits_until_ready(self):
        self.env["FAKE_WARM_MAKES"] = "1"
        self.env["NGISA_START_POLL"] = "0.2"
        r = self.run_cli("--need", "3")
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertIn("agent-warm 3", self.logged())
        self.assertEqual(r.stdout.splitlines()[-2], "free: 3")
        self.assertTrue(r.stdout.splitlines()[-1].startswith("waited: "))
        self.assertIn("warm-9 branch=warm/9 dirty=no ctx=40k idle=5m tasks=1", r.stdout.splitlines())

    def test_need_already_met_starts_nothing(self):
        r = self.run_cli("--need", "2")
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertNotIn("agent-warm 2", self.logged())
        self.assertNotIn("waited:", r.stdout)

    def test_need_times_out_quietly(self):
        self.env["NGISA_START_WAIT"] = "1"
        self.env["NGISA_START_POLL"] = "0.2"
        r = self.run_cli("--need", "3")
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertEqual(r.stdout.splitlines()[-2], "free: 2")
        self.assertEqual(r.stdout.splitlines()[-1], "waited: 1s")

    def test_new_plan_and_need_together(self):
        self.run_cli("--new-plan", "--need", "1")
        self.assertEqual(self.logged()[:2], ["ngisa-report clear", "ngisa-report mark - request"])

    def test_bad_need_exits_2(self):
        r = self.run_cli("--need", "x")
        self.assertEqual(r.returncode, 2)
        self.assertIn("usage: ngisa-start", r.stderr)

    def test_busy_worker_not_listed(self):
        r = self.run_cli()
        self.assertNotIn("warm-4", r.stdout)


if __name__ == "__main__":
    unittest.main()
