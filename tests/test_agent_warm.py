import json
import os
import subprocess
import tempfile
import time
import unittest

BIN = os.environ.get("AGENT_WARM_BIN") or os.path.expanduser("~/bin/agent-warm")

FAKE_CLAUDE = """#!/bin/sh
if [ "$1" = "agents" ]; then
  cat "$FAKE_AGENTS"
else
  echo "$*" >> "$FAKE_LOG"
fi
"""


class AgentWarmTest(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        root = self._tmp.name
        self.repo = os.path.join(root, "demo")
        os.mkdir(self.repo)
        self.git("init", "-q", "-b", "main")
        self.git("commit", "-q", "--allow-empty", "-m", "base")
        self.plain = os.path.join(root, "plain")
        os.mkdir(self.plain)
        fakebin = os.path.join(root, "fakebin")
        os.mkdir(fakebin)
        fake = os.path.join(fakebin, "claude")
        with open(fake, "w") as f:
            f.write(FAKE_CLAUDE)
        os.chmod(fake, 0o755)
        self.log = os.path.join(root, "log")
        self.agents = os.path.join(root, "agents.json")
        self.set_agents([])
        self.env = dict(
            os.environ,
            PATH=fakebin + os.pathsep + os.environ["PATH"],
            FAKE_LOG=self.log,
            FAKE_AGENTS=self.agents,
        )

    def git(self, *args, cwd=None):
        return subprocess.run(
            ["git", "-c", "user.name=t", "-c", "user.email=t@example.com", *args],
            cwd=cwd or self.repo, capture_output=True, text=True, check=True,
        )

    def set_agents(self, rows):
        """rows: names (state done) or (name, state) pairs"""
        out = [{"name": r, "state": "done"} if isinstance(r, str) else {"name": r[0], "state": r[1]} for r in rows]
        with open(self.agents, "w") as f:
            json.dump(out, f)

    def make_warm(self, i, used=False):
        path = os.path.join(self.repo, ".claude", "worktrees", f"warm-{i}")
        self.git("worktree", "add", path, "-b", f"warm/{i}", "HEAD")
        if used:
            self.git("checkout", "-q", "-B", f"feat/task{i}", cwd=path)

    def run_cli(self, *args, cwd=None):
        return subprocess.run([BIN, *args], cwd=cwd or self.repo, env=self.env, capture_output=True, text=True)

    def starts(self):
        if not os.path.exists(self.log):
            return []
        with open(self.log) as f:
            return [l for l in f.read().splitlines() if "--bg" in l]

    def test_default_starts_two(self):
        r = self.run_cli()
        self.assertEqual(r.returncode, 0, r.stderr)
        lines = self.starts()
        self.assertEqual(len(lines), 2)
        for i, line in enumerate(lines, 1):
            self.assertIn(f"--name demo-warm-{i}", line)
            self.assertIn("--agent implementer --model sonnet", line)
            self.assertIn(f"warm/{i}", line)
            self.assertIn(f"warm demo-warm-{i} started", r.stdout)
            self.assertIn("warm free: 0", r.stdout)

    def test_cap_at_three(self):
        r = self.run_cli("9")
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertEqual(len(self.starts()), 3)

    def test_bad_n_exit_2(self):
        for bad in ("0", "x", "-1"):
            r = self.run_cli(bad)
            self.assertEqual(r.returncode, 2, bad)
            self.assertIn("agent-warm: n must be 1..3", r.stderr)
        self.assertEqual(self.starts(), [])

    def started_names(self):
        return [l.split("--name ")[1].split()[0] for l in self.starts()]

    def test_free_worker_counts_and_tops_up(self):
        self.make_warm(1)
        self.set_agents(["demo-warm-1"])
        r = self.run_cli()
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertIn("warm free: 1", r.stdout)
        self.assertEqual(self.started_names(), ["demo-warm-2"])
        self.assertIn("warm demo-warm-2 started", r.stdout)

    def test_used_worker_not_free_new_index_above_highest(self):
        self.make_warm(1, used=True)
        self.set_agents(["demo-warm-1"])
        r = self.run_cli("1")
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertIn("warm free: 0", r.stdout)
        self.assertEqual(self.started_names(), ["demo-warm-2"])

    def test_exited_ignored_but_index_not_reused(self):
        self.make_warm(1)
        self.make_warm(2)
        self.set_agents([("demo-warm-1", "exited"), ("demo-warm-2", "stopped")])
        r = self.run_cli("2")
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertIn("warm free: 0", r.stdout)
        self.assertEqual(self.started_names(), ["demo-warm-3", "demo-warm-4"])

    def test_blocked_and_working_not_free(self):
        self.make_warm(1)
        self.make_warm(2)
        self.set_agents([("demo-warm-1", "blocked"), ("demo-warm-2", "working")])
        r = self.run_cli("1")
        self.assertIn("warm free: 0", r.stdout)
        self.assertEqual(self.started_names(), ["demo-warm-3"])

    def test_idle_state_counts_as_free(self):
        self.make_warm(1)
        self.set_agents([("demo-warm-1", "idle")])
        r = self.run_cli("1")
        self.assertIn("warm free: 1", r.stdout)
        self.assertEqual(self.starts(), [])

    def test_enough_free_starts_nothing(self):
        for i in (1, 2):
            self.make_warm(i)
        self.set_agents(["demo-warm-1", "demo-warm-2"])
        r = self.run_cli("2")
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertIn("warm free: 2", r.stdout)
        self.assertEqual(self.starts(), [])

    def test_cap_three_free(self):
        for i in (1, 2, 3):
            self.make_warm(i)
        self.set_agents(["demo-warm-1", "demo-warm-2", "demo-warm-3"])
        r = self.run_cli("9")
        self.assertEqual(self.starts(), [])
        self.set_agents(["demo-warm-1", "demo-warm-2"])
        r = self.run_cli("9")
        self.assertEqual(self.started_names(), ["demo-warm-3"])

    def test_other_repo_sessions_ignored(self):
        self.set_agents([("other-warm-7", "done"), ("demo-warm-x", "done")])
        r = self.run_cli("1")
        self.assertEqual(self.started_names(), ["demo-warm-1"])

    def test_prompt_contract(self):
        r = self.run_cli("1")
        line = self.starts()[0]
        self.assertIn("warm path taken", line)
        self.assertIn("Base: <ref>", line)
        self.assertIn("git checkout -B <name> <ref>", line)

    def _assert_aborts(self, content):
        with open(self.agents, "w") as f:
            f.write(content)
        r = self.run_cli()
        self.assertNotEqual(r.returncode, 0)
        self.assertIn("agent list", r.stderr)
        self.assertEqual(self.starts(), [])

    def test_garbage_agent_list_aborts_without_starting(self):
        self._assert_aborts("not json at all")

    def test_empty_agent_list_output_aborts_without_starting(self):
        self._assert_aborts("")

    def test_object_agent_list_aborts_without_starting(self):
        self._assert_aborts('{"name": "demo-warm-1"}')

    def test_outside_repo_fails(self):
        r = self.run_cli(cwd=self.plain)
        self.assertEqual(r.returncode, 1)
        self.assertEqual(self.starts(), [])

    # ---- lock ----
    def lock_path(self):
        return os.path.join(self.repo, ".git", "agent-warm.lock")

    def spawn_cli(self, *args, env=None):
        return subprocess.Popen([BIN, *args], cwd=self.repo, env=env or self.env,
                                stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)

    def test_lock_serialises_concurrent_runs(self):
        fake = os.path.join(self._tmp.name, "fakebin", "claude")
        with open(fake, "w") as f:
            f.write("""#!/bin/sh
if [ "$1" = "agents" ]; then
  cat "$FAKE_AGENTS"
else
  echo "$*" >> "$FAKE_LOG"
  sleep 0.5
  name=$(echo "$*" | sed 's/.*--name \\([^ ]*\\).*/\\1/')
  python3 -c 'import json,sys; p=sys.argv[1]; d=json.load(open(p)); d.append({"name":sys.argv[2],"state":"done"}); json.dump(d,open(p,"w"))' "$FAKE_AGENTS" "$name"
  git worktree add ".claude/worktrees/warm-${name##*-}" -b "warm/${name##*-}" HEAD >/dev/null 2>&1
fi
""")
        a = self.spawn_cli("1")
        b = self.spawn_cli("1")
        for p in (a, b):
            p.communicate(timeout=30)
            self.assertEqual(p.returncode, 0)
        names = self.started_names()
        self.assertEqual(len(names), 1, names)
        self.assertEqual(len(set(names)), len(names))

    def test_waits_for_fresh_lock_then_succeeds(self):
        os.mkdir(self.lock_path())
        p = self.spawn_cli("1")
        time.sleep(1)
        self.assertIsNone(p.poll())
        os.rmdir(self.lock_path())
        out, err = p.communicate(timeout=20)
        self.assertEqual(p.returncode, 0, err)
        self.assertEqual(len(self.starts()), 1)

    def test_stale_lock_is_removed(self):
        os.mkdir(self.lock_path())
        old = time.time() - 300
        os.utime(self.lock_path(), (old, old))
        t0 = time.time()
        r = self.run_cli("1")
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertLess(time.time() - t0, 5)
        self.assertEqual(len(self.starts()), 1)
        self.assertFalse(os.path.exists(self.lock_path()))

    def test_lock_timeout_exit_1_and_keeps_foreign_lock(self):
        os.mkdir(self.lock_path())
        env = dict(self.env, AGENT_WARM_LOCK_TIMEOUT="1")
        p = self.spawn_cli("1", env=env)
        out, err = p.communicate(timeout=20)
        self.assertEqual(p.returncode, 1)
        self.assertIn("agent-warm: busy", err)
        self.assertTrue(os.path.isdir(self.lock_path()))
        self.assertEqual(self.starts(), [])

    def test_lock_released_after_run(self):
        r = self.run_cli("1")
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertFalse(os.path.exists(self.lock_path()))

    def test_lock_works_from_linked_worktree(self):
        wt = os.path.join(self._tmp.name, "linked")
        self.git("worktree", "add", wt, "-b", "side", "HEAD")
        os.mkdir(self.lock_path())
        env = dict(self.env, AGENT_WARM_LOCK_TIMEOUT="1")
        p = subprocess.Popen([BIN, "1"], cwd=wt, env=env, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        out, err = p.communicate(timeout=20)
        self.assertEqual(p.returncode, 1)
        self.assertIn("busy", err)


if __name__ == "__main__":
    unittest.main()
