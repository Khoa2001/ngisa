import os
import subprocess
import tempfile
import unittest

BIN = os.environ.get("AGENT_WALL_BIN") or os.path.expanduser("~/bin/agent-wall.sh")

FAKE_WEZTERM = """#!/bin/sh
if [ "$2" = "kill-pane" ]; then
  echo "kill-pane $*" >> "$FAKE_LOG"
  [ -n "$FAKE_KILL_FAIL" ] && exit 1
fi
exit 0
"""


class AgentWallCloseTest(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        root = self._tmp.name
        fakebin = os.path.join(root, "fakebin")
        os.mkdir(fakebin)
        p = os.path.join(fakebin, "wezterm")
        with open(p, "w") as f:
            f.write(FAKE_WEZTERM)
        os.chmod(p, 0o755)
        self.log = os.path.join(root, "log")
        self.cache = os.path.join(root, "cache")
        self.panes = os.path.join(self.cache, "ngisa", "panes")
        os.makedirs(self.panes)
        self.env = dict(
            os.environ,
            PATH=fakebin + os.pathsep + os.environ["PATH"],
            FAKE_LOG=self.log,
            XDG_CACHE_HOME=self.cache,
        )
        self.env.pop("WEZTERM_PANE", None)
        self.env.pop("FAKE_KILL_FAIL", None)
        self.root = root

    def pane_file(self, name, pane_id):
        path = os.path.join(self.panes, name)
        with open(path, "w") as f:
            f.write(str(pane_id) + "\n")
        return path

    def run_cli(self, *args, **extra):
        env = dict(self.env, **extra)
        return subprocess.run([BIN, *args], cwd=self.root, env=env, capture_output=True, text=True)

    def logged(self):
        if not os.path.exists(self.log):
            return []
        with open(self.log) as f:
            return f.read().splitlines()

    def test_close_kills_recorded_pane_and_removes_file(self):
        path = self.pane_file("demo-warm-1", 99)
        r = self.run_cli("--close", "demo-warm-1")
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertEqual(r.stdout, "")
        self.assertEqual(self.logged(), ["kill-pane cli kill-pane --pane-id 99"])
        self.assertFalse(os.path.exists(path))

    def test_close_missing_file_is_silent_ok(self):
        r = self.run_cli("--close", "demo-warm-1")
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertEqual(r.stdout + r.stderr, "")
        self.assertEqual(self.logged(), [])

    def test_close_survives_wezterm_failure(self):
        path = self.pane_file("demo-warm-1", 99)
        r = self.run_cli("--close", "demo-warm-1", FAKE_KILL_FAIL="1")
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertFalse(os.path.exists(path))

    def test_close_leaves_other_pane_files(self):
        self.pane_file("demo-warm-1", 99)
        other = self.pane_file("demo-warm-2", 77)
        self.run_cli("--close", "demo-warm-1")
        self.assertTrue(os.path.exists(other))
        self.assertEqual(self.logged(), ["kill-pane cli kill-pane --pane-id 99"])

    def test_close_rejects_path_names(self):
        victim = os.path.join(self.root, "victim.txt")
        with open(victim, "w") as f:
            f.write("5\n")
        for bad in ("../../../victim.txt", "a/b", "..", "x..y/z"):
            r = self.run_cli("--close", bad)
            self.assertEqual(r.returncode, 2, bad)
            self.assertIn("bad session name", r.stderr)
        self.assertTrue(os.path.exists(victim))
        self.assertEqual(self.logged(), [])

    def test_close_without_name_exits_2(self):
        r = self.run_cli("--close")
        self.assertEqual(r.returncode, 2)
        self.assertIn("usage", r.stderr)


if __name__ == "__main__":
    unittest.main()
