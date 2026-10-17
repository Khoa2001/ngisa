import os
import subprocess
import sys
import tempfile
import unittest

BIN = os.environ.get("NGISA_REPORT_BIN") or os.path.expanduser("~/bin/ngisa-report")


class TimingTest(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.cache = self._tmp.name
        self.env = dict(os.environ, XDG_CACHE_HOME=self.cache, NGISA_REPO="demo")

    def run_cli(self, *args):
        return subprocess.run([sys.executable, BIN, *args], env=self.env, capture_output=True, text=True)

    def report_file(self):
        return os.path.join(self.cache, "ngisa", "report", "ngisa-demo.json")

    def test_mark_then_timing(self):
        for args in (["-", "request", "--at", "1000"], ["a", "spawn", "--at", "1060"],
                     ["a", "report", "--at", "1360"], ["a", "decided", "--at", "1420"],
                     ["a", "pr", "--at", "1480"]):
            r = self.run_cli("mark", *args)
            self.assertEqual(r.returncode, 0, r.stderr)
            self.assertEqual(r.stdout, "")
        r = self.run_cli("timing", "a")
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertEqual(r.stdout, "a  plan 1m00s  worker 5m00s  report 1m00s  merge 1m00s  total 8m00s\n")

    def test_missing_event_prints_dash(self):
        self.run_cli("mark", "a", "spawn", "--at", "100")
        self.run_cli("mark", "a", "report", "--at", "105")
        r = self.run_cli("timing", "a")
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertIn("plan -", r.stdout)
        self.assertIn("merge -", r.stdout)
        self.assertIn("worker 0m05s", r.stdout)

    def test_unknown_event_rejected(self):
        r = self.run_cli("mark", "a", "nope")
        self.assertEqual(r.returncode, 2)
        self.assertIn("unknown event", r.stderr)
        self.assertEqual(self.run_cli("timing").returncode, 1)

    def test_total_falls_back_to_last_mark_without_pr(self):
        for args in (["-", "request", "--at", "1000"], ["a", "spawn", "--at", "1060"],
                     ["a", "report", "--at", "1360"]):
            self.assertEqual(self.run_cli("mark", *args).returncode, 0)
        r = self.run_cli("timing", "a")
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertIn("total 6m00s", r.stdout)

    def test_set_keeps_marks(self):
        self.run_cli("mark", "a", "spawn", "--at", "1")
        self.assertEqual(self.run_cli("set", "a", "--state", "ok").returncode, 0)
        r = self.run_cli("timing", "a")
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertTrue(r.stdout.startswith("a  "))

    def test_negative_gap_is_dash(self):
        self.run_cli("mark", "a", "report", "--at", "10")
        self.run_cli("mark", "a", "spawn", "--at", "20")
        r = self.run_cli("timing", "a")
        self.assertIn("worker -", r.stdout)

    def test_corrupt_json_mark_starts_fresh(self):
        os.makedirs(os.path.dirname(self.report_file()))
        with open(self.report_file(), "w") as f:
            f.write('{"x": 1}')
        r = self.run_cli("mark", "a", "spawn")
        self.assertEqual(r.returncode, 0, r.stderr)

    def test_no_marks_exit_1(self):
        r = self.run_cli("timing")
        self.assertEqual(r.returncode, 1)
        self.assertIn("no marks", r.stderr)


if __name__ == "__main__":
    unittest.main()
