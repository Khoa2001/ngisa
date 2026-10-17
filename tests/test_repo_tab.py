import os
import subprocess
import tempfile
import time
import unittest

BIN = os.environ.get("REPO_TAB_BIN") or os.path.expanduser("~/bin/repo-tab")

FAKE_AGENT_WARM = """#!/bin/sh
echo "agent-warm $* cwd=$(pwd -P)" >> "$FAKE_LOG"
"""

FAKE_CLAUDE = """#!/bin/sh
echo "claude $*" >> "$FAKE_LOG"
"""

FAKE_WEZTERM = """#!/bin/sh
# wezterm cli <sub> ...
if [ "$2" = "spawn" ]; then
  echo "spawn $*" >> "$FAKE_LOG"
  echo 99
fi
exit 0
"""


class RepoTabTest(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        root = os.path.realpath(self._tmp.name)
        self.repo = os.path.join(root, "demo")
        os.mkdir(self.repo)
        subprocess.run(["git", "init", "-q"], cwd=self.repo, check=True)
        fakebin = os.path.join(root, "fakebin")
        os.mkdir(fakebin)
        for name, body in (
            ("agent-warm", FAKE_AGENT_WARM),
            ("claude", FAKE_CLAUDE),
            ("wezterm", FAKE_WEZTERM),
        ):
            p = os.path.join(fakebin, name)
            with open(p, "w") as f:
                f.write(body)
            os.chmod(p, 0o755)
        self.log = os.path.join(root, "log")
        self.env = dict(
            os.environ,
            PATH=fakebin + os.pathsep + os.environ["PATH"],
            FAKE_LOG=self.log,
            TMPDIR=root,
        )
        for k in ("WEZTERM_PANE", "NGISA_WARM", "NGISA_ROSTER"):
            self.env.pop(k, None)

    def run_tab(self, **extra):
        env = dict(self.env, **extra)
        return subprocess.run([BIN, self.repo], env=env, capture_output=True, text=True)

    def logged(self, needle):
        if not os.path.exists(self.log):
            return []
        with open(self.log) as f:
            return [l for l in f.read().splitlines() if l.startswith(needle)]

    def wait_for(self, needle, timeout=3.0):
        end = time.time() + timeout
        while time.time() < end:
            got = self.logged(needle)
            if got:
                return got
            time.sleep(0.05)
        return self.logged(needle)

    def test_static_text(self):
        with open(BIN) as f:
            text = f.read()
        self.assertIn("--model sonnet", text)
        self.assertNotIn("--model opus", text)
        self.assertIn("agent-warm", text)
        self.assertIn("NGISA_WARM", text)

    def test_bash_syntax(self):
        r = subprocess.run(["bash", "-n", BIN], capture_output=True, text=True)
        self.assertEqual(r.returncode, 0, r.stderr)

    def test_spawn_uses_sonnet_and_starts_warm_pool(self):
        r = self.run_tab()
        self.assertEqual(r.returncode, 0, r.stderr)
        warm = self.wait_for("agent-warm")
        self.assertEqual(len(warm), 1, warm)
        self.assertEqual(warm[0], "agent-warm 2 cwd=" + self.repo)
        spawn = self.logged("spawn")
        self.assertEqual(len(spawn), 1, spawn)
        self.assertIn("--model sonnet", spawn[0])
        self.assertNotIn("--model opus", spawn[0])

    def test_warm_zero_skips_pool(self):
        r = self.run_tab(NGISA_WARM="0")
        self.assertEqual(r.returncode, 0, r.stderr)
        time.sleep(0.5)
        self.assertEqual(self.logged("agent-warm"), [])
        self.assertEqual(len(self.logged("spawn")), 1)

    def test_warm_count_override(self):
        r = self.run_tab(NGISA_WARM="3")
        self.assertEqual(r.returncode, 0, r.stderr)
        warm = self.wait_for("agent-warm")
        self.assertEqual(warm, ["agent-warm 3 cwd=" + self.repo])


if __name__ == "__main__":
    unittest.main()
