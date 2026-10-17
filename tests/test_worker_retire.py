import json
import os
import subprocess
import tempfile
import unittest

BIN = os.environ.get("WORKER_RETIRE_BIN") or os.path.expanduser("~/bin/worker-retire")

FAKE_CLAUDE = """#!/bin/sh
if [ "$1" = "agents" ]; then
  cat "$FAKE_AGENTS"
else
  echo "claude $*" >> "$FAKE_LOG"
fi
"""

FAKE_WALL = """#!/bin/sh
echo "agent-wall.sh $*" >> "$FAKE_LOG"
"""


class WorkerRetireTest(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        root = self._tmp.name
        self.repo = os.path.join(root, "demo")
        os.mkdir(self.repo)
        self.git("init", "-q", "-b", "main")
        self.git("commit", "-q", "--allow-empty", "-m", "base")
        self.wt = os.path.join(self.repo, ".claude", "worktrees", "warm-1")
        self.git("worktree", "add", "-q", self.wt, "-b", "warm/1", "HEAD")
        fakebin = os.path.join(root, "fakebin")
        os.mkdir(fakebin)
        for name, body in (("claude", FAKE_CLAUDE), ("agent-wall.sh", FAKE_WALL)):
            p = os.path.join(fakebin, name)
            with open(p, "w") as f:
                f.write(body)
            os.chmod(p, 0o755)
        self.log = os.path.join(root, "log")
        self.agents = os.path.join(root, "agents.json")
        self.set_agent("done")
        self.env = dict(
            os.environ,
            PATH=fakebin + os.pathsep + os.environ["PATH"],
            FAKE_LOG=self.log,
            FAKE_AGENTS=self.agents,
            GIT_AUTHOR_NAME="t", GIT_AUTHOR_EMAIL="t@t", GIT_COMMITTER_NAME="t", GIT_COMMITTER_EMAIL="t@t",
        )

    def git(self, *args, cwd=None):
        env = dict(os.environ, GIT_AUTHOR_NAME="t", GIT_AUTHOR_EMAIL="t@t",
                   GIT_COMMITTER_NAME="t", GIT_COMMITTER_EMAIL="t@t")
        return subprocess.run(["git", *args], cwd=cwd or self.repo, env=env, check=True,
                              capture_output=True, text=True).stdout

    def set_agent(self, state, name="demo-warm-1"):
        with open(self.agents, "w") as f:
            json.dump([{"name": name, "id": "abc123", "state": state}], f)

    def run_cli(self, name="demo-warm-1"):
        return subprocess.run([BIN, name], cwd=self.repo, env=self.env, capture_output=True, text=True)

    def logged(self):
        if not os.path.exists(self.log):
            return []
        with open(self.log) as f:
            return f.read().splitlines()

    def test_refuses_non_warm_name(self):
        self.set_agent("done", name="demo-feature")
        r = self.run_cli("demo-feature")
        self.assertEqual(r.returncode, 2)
        self.assertIn("worker-retire: not a warm worker: demo-feature", r.stderr)
        self.assertEqual(self.logged(), [])

    def test_refuses_busy_worker(self):
        self.set_agent("working")
        r = self.run_cli()
        self.assertEqual(r.returncode, 1)
        self.assertIn("worker-retire: demo-warm-1 is working", r.stderr)
        self.assertEqual(self.logged(), [])
        self.assertTrue(os.path.isdir(self.wt))

    def test_refuses_dirty_worktree(self):
        with open(os.path.join(self.wt, "scratch.txt"), "w") as f:
            f.write("x")
        r = self.run_cli()
        self.assertEqual(r.returncode, 1)
        self.assertIn("worker-retire: dirty worktree", r.stderr)
        self.assertEqual(self.logged(), [])
        self.assertTrue(os.path.isdir(self.wt))

    def test_happy_path_order(self):
        r = self.run_cli()
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertEqual(r.stdout.strip(), "retired demo-warm-1")
        self.assertEqual(self.logged(), ["claude stop abc123", "claude rm abc123",
                                         "agent-wall.sh --close demo-warm-1"])
        self.assertFalse(os.path.exists(self.wt))
        self.assertEqual(self.git("branch", "--list", "warm/1").strip(), "")

    def test_task_branch_and_commits_survive(self):
        self.git("checkout", "-q", "-B", "feat/x", "HEAD", cwd=self.wt)
        with open(os.path.join(self.wt, "a.txt"), "w") as f:
            f.write("work")
        self.git("add", "a.txt", cwd=self.wt)
        self.git("commit", "-q", "-m", "task work", cwd=self.wt)
        r = self.run_cli()
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertFalse(os.path.exists(self.wt))
        self.assertEqual(self.git("branch", "--list", "feat/x").strip(), "feat/x")
        self.assertIn("task work", self.git("log", "--format=%s", "feat/x"))

    def test_refuses_detached_head(self):
        self.git("checkout", "-q", "--detach", cwd=self.wt)
        with open(os.path.join(self.wt, "a.txt"), "w") as f:
            f.write("work")
        self.git("add", "a.txt", cwd=self.wt)
        self.git("commit", "-q", "-m", "detached work", cwd=self.wt)
        r = self.run_cli()
        self.assertEqual(r.returncode, 1)
        self.assertIn("worker-retire: detached HEAD", r.stderr)
        self.assertEqual(self.logged(), [])
        self.assertTrue(os.path.isdir(self.wt))

    def test_unknown_session(self):
        self.set_agent("done", name="demo-warm-2")
        r = self.run_cli()
        self.assertEqual(r.returncode, 1)
        self.assertIn("worker-retire: no session demo-warm-1", r.stderr)
        self.assertEqual(self.logged(), [])


if __name__ == "__main__":
    unittest.main()
