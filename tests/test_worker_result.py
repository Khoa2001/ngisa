import os
import subprocess
import tempfile
import unittest

BIN = os.environ.get("WORKER_RESULT_BIN") or os.path.expanduser("~/bin/worker-result")

BODY = "feat: thing\n\nchecks: analyze ok\nunverified: none\nasks: none\n"


class WorkerResultTest(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.repo = os.path.join(self._tmp.name, "wt")
        os.mkdir(self.repo)
        self.git("init", "-q", "-b", "work")
        self.write("a.txt", "one\n")
        self.git("add", "-A")
        self.git("commit", "-q", "-m", "base")
        self.base = self.git("rev-parse", "HEAD").stdout.strip()

    def git(self, *args):
        return subprocess.run(
            ["git", "-c", "user.name=t", "-c", "user.email=t@example.com", *args],
            cwd=self.repo, capture_output=True, text=True, check=True,
        )

    def write(self, name, text):
        with open(os.path.join(self.repo, name), "w") as f:
            f.write(text)

    def worker_commit(self):
        self.write("b.txt", "two\n")
        self.git("add", "-A")
        self.git("commit", "-q", "-m", BODY)

    def run_cli(self, *args):
        return subprocess.run([BIN, *args], capture_output=True, text=True)

    def test_prints_commit_body_and_stat(self):
        self.worker_commit()
        r = self.run_cli(self.repo, self.base)
        self.assertEqual(r.returncode, 0, r.stderr)
        lines = r.stdout.splitlines()
        self.assertEqual(lines[0], "commits: 1")
        self.assertEqual(lines[1], "branch: work")
        self.assertEqual(lines[2], "--- body")
        for want in ("checks: analyze ok", "unverified: none", "asks: none"):
            self.assertIn(want, lines)
        self.assertIn("--- stat", lines)
        self.assertIn("b.txt", r.stdout.split("--- stat")[1])

    def test_zero_commits(self):
        r = self.run_cli(self.repo, self.base)
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertEqual(r.stdout, "commits: 0\nbranch: work\n")

    def test_missing_args_exit_2(self):
        for args in ((), (self.repo,)):
            r = self.run_cli(*args)
            self.assertEqual(r.returncode, 2)
            self.assertIn("usage: worker-result <worktree-path> <base>", r.stderr)

    def test_not_a_worktree_exit_1(self):
        plain = os.path.join(self._tmp.name, "plain")
        os.mkdir(plain)
        r = self.run_cli(plain, "HEAD")
        self.assertEqual(r.returncode, 1)
        self.assertIn("worker-result: not a git worktree: " + plain, r.stderr)

    def test_bad_base_exit_1(self):
        r = self.run_cli(self.repo, "nope")
        self.assertEqual(r.returncode, 1)
        self.assertIn("worker-result: bad base: nope", r.stderr)

    def test_option_like_base_rejected_no_file(self):
        self.worker_commit()
        r = self.run_cli(self.repo, "--output=x")
        self.assertEqual(r.returncode, 1)
        self.assertFalse(os.path.exists(os.path.join(self.repo, "x")))
        self.assertFalse(os.path.exists("x"))

    def test_does_not_modify_repo(self):
        self.worker_commit()
        self.write("c.txt", "dirty\n")
        before = (self.git("rev-parse", "HEAD").stdout, self.git("status", "--porcelain").stdout)
        self.run_cli(self.repo, self.base)
        after = (self.git("rev-parse", "HEAD").stdout, self.git("status", "--porcelain").stdout)
        self.assertEqual(before, after)


if __name__ == "__main__":
    unittest.main()
