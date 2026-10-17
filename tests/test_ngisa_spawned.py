import os
import subprocess
import tempfile
import time
import unittest

BIN = os.environ.get("NGISA_SPAWNED_BIN") or os.path.expanduser("~/bin/ngisa-spawned")

FAKES = {
    "ngisa-report": '#!/bin/sh\necho "ngisa-report $*" >> "$FAKE_LOG"\n',
    "agent-wall.sh": '#!/bin/sh\necho "agent-wall.sh $*" >> "$FAKE_LOG"\n[ "$3" = "$FAKE_WALL_FAIL" ] && exit 1\nexit 0\n',
    "agent-warm": '#!/bin/sh\necho "agent-warm $*" >> "$FAKE_LOG"\n',
}


class NgisaSpawnedTest(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        root = self._tmp.name
        fakebin = os.path.join(root, "fakebin")
        os.mkdir(fakebin)
        for name, body in FAKES.items():
            p = os.path.join(fakebin, name)
            with open(p, "w") as f:
                f.write(body)
            os.chmod(p, 0o755)
        self.log = os.path.join(root, "log")
        self.env = dict(os.environ, PATH=fakebin + os.pathsep + os.environ["PATH"], FAKE_LOG=self.log)
        self.env.pop("NGISA_WARM", None)
        self.env.pop("FAKE_WALL_FAIL", None)
        self.root = root

    def run_cli(self, *args, **extra):
        return subprocess.run([BIN, *args], cwd=self.root, env=dict(self.env, **extra), capture_output=True, text=True)

    def logged(self, want_refill=True):
        for _ in range(30):
            lines = []
            if os.path.exists(self.log):
                with open(self.log) as f:
                    lines = f.read().splitlines()
            if not want_refill or any(l.startswith("agent-warm") for l in lines):
                return lines
            time.sleep(0.1)
        return lines

    def test_two_pairs_in_order(self):
        r = self.run_cli("a=demo-warm-1", "b=demo-warm-2")
        self.assertEqual(r.returncode, 0, r.stderr)
        lines = self.logged()
        self.assertEqual(lines[:4], [
            "ngisa-report mark a spawn", "agent-wall.sh a --attach demo-warm-1",
            "ngisa-report mark b spawn", "agent-wall.sh b --attach demo-warm-2"])
        self.assertEqual(r.stdout.splitlines(), ["ok a", "ok b"])

    def test_failed_attach_continues_and_exit_count(self):
        r = self.run_cli("a=demo-warm-1", "b=demo-warm-2", FAKE_WALL_FAIL="demo-warm-1")
        self.assertEqual(r.returncode, 1)
        self.assertEqual(r.stdout.splitlines(), ["FAIL a attach", "ok b"])
        self.assertIn("agent-wall.sh b --attach demo-warm-2", self.logged())

    def test_refill_uses_ngisa_warm_default_1(self):
        self.run_cli("a=demo-warm-1")
        self.assertIn("agent-warm 1", self.logged())

    def test_refill_env_override(self):
        self.run_cli("a=demo-warm-1", NGISA_WARM="2")
        self.assertIn("agent-warm 2", self.logged())

    def test_bad_argument_exit_2(self):
        r = self.run_cli("nopair")
        self.assertEqual(r.returncode, 2)
        self.assertIn("usage: ngisa-spawned", r.stderr)
        self.assertEqual(self.logged(want_refill=False), [])


if __name__ == "__main__":
    unittest.main()
