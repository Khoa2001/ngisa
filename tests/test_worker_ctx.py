import json
import os
import subprocess
import tempfile
import unittest

BIN = os.environ.get("WORKER_CTX_BIN") or os.path.expanduser("~/bin/worker-ctx")

FAKE_CLAUDE = """#!/bin/sh
if [ "$1" = "agents" ]; then
  cat "$FAKE_AGENTS"
fi
"""

NOW = "2026-10-17T12:00:00Z"


def assistant(ts, inp, read, create):
    return {
        "type": "assistant",
        "timestamp": ts,
        "message": {"usage": {"input_tokens": inp, "cache_read_input_tokens": read,
                              "cache_creation_input_tokens": create}},
    }


def user(text, ts="2026-10-17T11:00:00.000Z", parts=False):
    content = [{"type": "text", "text": text}] if parts else text
    return {"type": "user", "timestamp": ts, "message": {"content": content}}


class WorkerCtxTest(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        root = self._tmp.name
        self.repo = os.path.join(root, "demo")
        os.mkdir(self.repo)
        subprocess.run(["git", "init", "-q"], cwd=self.repo, check=True)
        fakebin = os.path.join(root, "fakebin")
        os.mkdir(fakebin)
        fake = os.path.join(fakebin, "claude")
        with open(fake, "w") as f:
            f.write(FAKE_CLAUDE)
        os.chmod(fake, 0o755)
        self.agents = os.path.join(root, "agents.json")
        self.projects = os.path.join(root, "projects")
        os.makedirs(os.path.join(self.projects, "-some-project"))
        self.env = dict(
            os.environ,
            PATH=fakebin + os.pathsep + os.environ["PATH"],
            FAKE_AGENTS=self.agents,
            CLAUDE_PROJECTS_DIR=self.projects,
            WORKER_CTX_NOW=NOW,
        )
        with open(self.agents, "w") as f:
            json.dump([{"name": "demo-warm-1", "sessionId": "sid-1", "state": "done"}], f)

    def transcript(self, lines, sid="sid-1"):
        path = os.path.join(self.projects, "-some-project", sid + ".jsonl")
        with open(path, "w") as f:
            for line in lines:
                f.write(json.dumps(line) + "\n")
        return path

    def run_cli(self, name="demo-warm-1"):
        return subprocess.run([BIN, name], cwd=self.repo, env=self.env, capture_output=True, text=True)

    def test_sums_last_assistant_usage(self):
        self.transcript([
            assistant("2026-10-17T11:00:00.000Z", 10, 20000, 5000),
            assistant("2026-10-17T11:30:00.000Z", 2, 49000, 1000),
        ])
        r = self.run_cli()
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertEqual(r.stdout.splitlines()[0], "ctx: 50k")

    def test_context_drop_after_compaction(self):
        self.transcript([
            assistant("2026-10-17T11:00:00.000Z", 2, 100000, 84000),
            assistant("2026-10-17T11:30:00.000Z", 2, 0, 12000),
        ])
        r = self.run_cli()
        self.assertEqual(r.stdout.splitlines()[0], "ctx: 12k")

    def test_idle_minutes_from_last_assistant(self):
        self.transcript([
            assistant("2026-10-17T11:48:00.000Z", 1, 1000, 1000),
            user("later user line", ts="2026-10-17T11:59:00.000Z"),
        ])
        r = self.run_cli()
        self.assertEqual(r.stdout.splitlines()[1], "idle: 12m")

    def test_tasks_counts_branch_messages(self):
        self.transcript([
            user("Branch: a. Base: x. do it"),
            assistant("2026-10-17T11:10:00.000Z", 1, 1000, 1000),
            user("Branch: b. Base: y. do it", parts=True),
            user("Branch: c. Base: z. do it"),
            user("thanks, now relax"),
        ])
        r = self.run_cli()
        self.assertEqual(r.stdout.splitlines()[2], "tasks: 3")

    def test_tasks_counts_cross_session_wrapper(self):
        wrapped = ("Another Claude session sent a message:\n"
                   '<cross-session-message from="uds:/tmp/x.sock" from-name="ngisa-demo">\n'
                   "Branch: feat/a. Base: abc. do it\n</cross-session-message>")
        self.transcript([
            user(wrapped),
            assistant("2026-10-17T11:10:00.000Z", 1, 1000, 1000),
            user(wrapped.replace("feat/a", "feat/b"), parts=True),
            user("Another Claude session sent a message:\n<cross-session-message from=\"x\">\nhello there\n</cross-session-message>"),
        ])
        r = self.run_cli()
        self.assertEqual(r.stdout.splitlines()[2], "tasks: 2")

    def test_synthetic_assistant_entry_ignored(self):
        synth = assistant("2026-10-17T11:59:00.000Z", 0, 0, 0)
        synth["message"]["model"] = "<synthetic>"
        self.transcript([
            assistant("2026-10-17T11:30:00.000Z", 2, 100000, 50000),
            synth,
        ])
        r = self.run_cli()
        self.assertEqual(r.stdout.splitlines()[:2], ["ctx: 150k", "idle: 30m"])

    def test_no_assistant_message(self):
        path = self.transcript([user("Branch: a. Base: x. do it")])
        os.utime(path, (1792238400 - 600, 1792238400 - 600))  # mtime 2026-10-17T11:50:00Z
        r = self.run_cli()
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertEqual(r.stdout.splitlines(), ["ctx: 0k", "idle: 10m", "tasks: 1"])

    def test_unknown_session(self):
        r = self.run_cli("demo-warm-9")
        self.assertEqual(r.returncode, 1)
        self.assertIn("worker-ctx: no session", r.stderr)

    def test_missing_transcript(self):
        r = self.run_cli()
        self.assertEqual(r.returncode, 1)
        self.assertIn("worker-ctx: no transcript", r.stderr)


if __name__ == "__main__":
    unittest.main()
