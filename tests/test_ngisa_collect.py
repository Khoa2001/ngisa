import os
import subprocess
import tempfile
import unittest

BIN = os.environ.get("NGISA_COLLECT_BIN") or os.path.expanduser("~/bin/ngisa-collect")

FAKES = {
    "ngisa-report": '#!/bin/sh\necho "ngisa-report $*" >> "$FAKE_LOG"\n[ "$1" = "set" ] && echo "BOARD"\nexit 0\n',
    "agent-wall.sh": '#!/bin/sh\necho "agent-wall.sh $*" >> "$FAKE_LOG"\n',
}


class NgisaCollectTest(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        root = self._tmp.name
        self.repo = os.path.join(root, "demo")
        os.mkdir(self.repo)
        self.git("init", "-q", "-b", "main")
        self.git("commit", "-q", "--allow-empty", "-m", "base")
        self.base = self.git("rev-parse", "HEAD").strip()
        self.wt = os.path.join(self.repo, ".claude", "worktrees", "warm-1")
        self.git("worktree", "add", "-q", self.wt, "-b", "warm/1", "HEAD")
        fakebin = os.path.join(root, "fakebin")
        os.mkdir(fakebin)
        for name, body in FAKES.items():
            p = os.path.join(fakebin, name)
            with open(p, "w") as f:
                f.write(body)
            os.chmod(p, 0o755)
        self.log = os.path.join(root, "log")
        self.env = dict(os.environ, PATH=fakebin + os.pathsep + os.environ["PATH"], FAKE_LOG=self.log)

    def git(self, *args, cwd=None):
        env = dict(os.environ, GIT_AUTHOR_NAME="t", GIT_AUTHOR_EMAIL="t@t", GIT_COMMITTER_NAME="t", GIT_COMMITTER_EMAIL="t@t")
        return subprocess.run(["git", *args], cwd=cwd or self.repo, env=env, check=True, capture_output=True, text=True).stdout

    def commit(self, body, branch="feat/x", cwd=None):
        wt = cwd or self.wt
        self.git("checkout", "-q", "-B", branch, self.base, cwd=wt)
        with open(os.path.join(wt, "a.txt"), "w") as f:
            f.write("work")
        self.git("add", "a.txt", cwd=wt)
        self.git("commit", "-q", "-m", "test: thing\n\n" + body, cwd=wt)

    def run_cli(self, session="demo-warm-1", branch="feat/x"):
        return subprocess.run([BIN, "slug", session, self.base, branch], cwd=self.repo, env=self.env,
                              capture_output=True, text=True)

    def logged(self):
        if not os.path.exists(self.log):
            return []
        with open(self.log) as f:
            return f.read().splitlines()

    def state_of(self, r):
        return next(l for l in r.stdout.splitlines() if l.startswith("state: ")).split(": ")[1]

    def check(self, checks, asks="none", want="ok", closes=None):
        self.commit(f"checks: {checks}\nunverified: none\nasks: {asks}\n")
        r = self.run_cli()
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertEqual(self.state_of(r), want, r.stdout)
        closed = "agent-wall.sh --close demo-warm-1" in self.logged()
        self.assertEqual(closed, want == "ok" if closes is None else closes)
        self.assertIn("ngisa-report set slug --base %s --branch feat/x --state %s" % (self.base, want), self.logged())
        return r

    def test_trailer_after_asks_none_is_still_ok(self):
        self.commit("checks: fvm flutter test x -> 18 pass; analyze -> no issues\nunverified: none\nasks: none\n\nCo-Authored-By: Claude Sonnet 5.5 <noreply@anthropic.com>\n")
        r = self.run_cli()
        self.assertEqual(self.state_of(r), "ok", r.stdout)

    def test_trailer_after_checks_does_not_leak_into_checks(self):
        self.commit("checks: all green\nunverified: none\nasks: none\n\nCo-Authored-By: Claude failed <noreply@anthropic.com>\n")
        self.assertEqual(self.state_of(self.run_cli()), "ok")

    def test_ok_closes_pane(self):
        r = self.check("fvm flutter test x -> 7 pass; analyze clean")
        self.assertIn("commits: 1", r.stdout)
        self.assertIn("BOARD", r.stdout)
        self.assertEqual(self.logged()[0], "ngisa-report mark slug report")

    def test_zero_failures_is_ok(self):
        self.check("tests: 12 passed, 0 failures; analyze: no errors")

    def test_failures_colon_zero_is_ok(self):
        self.check("tests passed, failures: 0, errors: 0")

    def test_exit_code_in_checks_is_fail(self):
        self.check("fvm flutter test x, exit=1", want="fail")
        self.check("test exit 2", want="fail")

    def test_partial_pass_is_fail(self):
        self.check("tests: 12/13 pass", want="fail")

    def test_not_green_timeout_broke_are_fail(self):
        for text in ("tests not green", "analyze clean, tests timed out", "build broke"):
            self.check(text, want="fail")

    def test_could_not_run_is_fail(self):
        self.check("cannot run: fvm not found", want="fail")

    def test_no_positive_evidence_is_fail(self):
        self.check("ran the tests", want="fail")

    def test_empty_checks_with_continuation_is_read(self):
        self.commit("checks:\n- fvm flutter test: 2 failed\nunverified: none\nasks: none\n")
        self.assertEqual(self.state_of(self.run_cli()), "fail")

    def test_continuation_clean_is_ok(self):
        self.commit("checks:\n- fvm flutter test: 7 pass\n- analyze: clean\nunverified: none\nasks: none\n")
        self.assertEqual(self.state_of(self.run_cli()), "ok")

    def test_asks_on_next_lines_is_blocked(self):
        self.commit("checks: all green\nunverified: none\nasks:\n- use X or Y? rec X\n")
        self.assertEqual(self.state_of(self.run_cli()), "blocked")

    def test_missing_asks_line_is_blocked(self):
        self.commit("checks: all green\nunverified: none\n")
        self.assertEqual(self.state_of(self.run_cli()), "blocked")

    def test_dirty_worktree_is_blocked(self):
        self.commit("checks: all green\nunverified: none\nasks: none\n")
        with open(os.path.join(self.wt, "left.txt"), "w") as f:
            f.write("x")
        r = self.run_cli()
        self.assertEqual(self.state_of(r), "blocked")
        self.assertNotIn("agent-wall.sh --close demo-warm-1", self.logged())

    def test_wrong_branch_is_blocked(self):
        self.commit("checks: all green\nunverified: none\nasks: none\n", branch="warm/1")
        r = self.run_cli(branch="feat/x")
        self.assertEqual(self.state_of(r), "blocked")

    def test_two_errors_is_fail_keeps_pane(self):
        self.check("analyze: 2 errors", want="fail")

    def test_tests_failed_is_fail(self):
        self.check("fvm flutter test x -> 3 FAILED", want="fail")

    def test_red_word_is_fail(self):
        self.check("checks red", want="fail")

    def test_no_checks_line_is_blocked(self):
        self.commit("unverified: none\nasks: none\n")
        r = self.run_cli()
        self.assertEqual(self.state_of(r), "blocked")
        self.assertNotIn("agent-wall.sh --close demo-warm-1", self.logged())

    def test_zero_commits_is_blocked(self):
        r = self.run_cli()
        self.assertEqual(self.state_of(r), "blocked")

    def test_asks_not_none_is_blocked_keeps_pane(self):
        self.check("all green", asks="use X or Y? rec X", want="blocked")

    def test_asks_none_with_period_is_ok(self):
        self.check("all green", asks="None.")

    def test_cold_worker_found_by_branch(self):
        cold = os.path.join(self.repo, ".claude", "worktrees", "cold-1")
        self.git("worktree", "add", "-q", cold, "-b", "feat/cold", "HEAD")
        self.commit("checks: all green\nunverified: none\nasks: none\n", branch="feat/cold", cwd=cold)
        r = subprocess.run([BIN, "slug", "demo-slug", self.base, "feat/cold"], cwd=self.repo, env=self.env,
                           capture_output=True, text=True)
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertEqual(self.state_of(r), "ok")
        self.assertIn("agent-wall.sh --close demo-slug", self.logged())

    def test_missing_worktree_counts_failure_and_blocks(self):
        r = subprocess.run([BIN, "slug", "demo-warm-9", self.base, "feat/none"], cwd=self.repo, env=self.env,
                           capture_output=True, text=True)
        self.assertGreaterEqual(r.returncode, 1)
        self.assertEqual(self.state_of(r), "blocked")


if __name__ == "__main__":
    unittest.main()
