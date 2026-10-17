import json
import os
import subprocess
import tempfile
import unittest

BIN = os.environ.get("AGENT_WALL_BIN") or os.path.expanduser("~/bin/agent-wall.sh")

FAKE_CLAUDE = """#!/bin/sh
if [ "$1" = "agents" ]; then
  cat "$FAKE_AGENTS"
else
  echo "claude $*" >> "$FAKE_LOG"
fi
"""

FAKE_WEZTERM = """#!/bin/sh
if [ "$2" = "list" ]; then
  cat "$FAKE_PANES"
elif [ "$2" = "split-pane" ]; then
  echo "split-pane $*" >> "$FAKE_LOG"
  echo 99
fi
exit 0
"""


def pane(pid, tab=1, top=0, rows=20):
    return {"pane_id": pid, "tab_id": tab, "top_row": top, "size": {"rows": rows}}


class AgentWallAttachTest(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        root = self._tmp.name
        self.repo = os.path.join(root, "demo")
        os.mkdir(self.repo)
        subprocess.run(["git", "init", "-q"], cwd=self.repo, check=True)
        fakebin = os.path.join(root, "fakebin")
        os.mkdir(fakebin)
        for name, body in (("claude", FAKE_CLAUDE), ("wezterm", FAKE_WEZTERM)):
            p = os.path.join(fakebin, name)
            with open(p, "w") as f:
                f.write(body)
            os.chmod(p, 0o755)
        self.log = os.path.join(root, "log")
        self.agents = os.path.join(root, "agents.json")
        self.panes = os.path.join(root, "panes.json")
        self.set_agents([])
        self.set_panes([pane(1)])
        self.env = dict(
            os.environ,
            PATH=fakebin + os.pathsep + os.environ["PATH"],
            FAKE_LOG=self.log,
            FAKE_AGENTS=self.agents,
            FAKE_PANES=self.panes,
            WEZTERM_PANE="1",
            XDG_CACHE_HOME=os.path.join(root, "cache"),
        )
        self.env.pop("AGENT_VIEW", None)

    def set_agents(self, names):
        with open(self.agents, "w") as f:
            json.dump([{"name": n, "state": "idle"} for n in names], f)

    def set_panes(self, panes):
        with open(self.panes, "w") as f:
            json.dump(panes, f)

    def run_cli(self, *args):
        return subprocess.run([BIN, *args], cwd=self.repo, env=self.env, capture_output=True, text=True)

    def logged(self, needle):
        if not os.path.exists(self.log):
            return []
        with open(self.log) as f:
            return [l for l in f.read().splitlines() if needle in l]

    def test_attach_opens_pane_only(self):
        self.set_agents(["demo-warm1"])
        r = self.run_cli("s", "--attach", "demo-warm1")
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertEqual(self.logged("--bg"), [])
        splits = self.logged("split-pane")
        self.assertEqual(len(splits), 1, splits)
        self.assertTrue(splits[0].endswith("-- claude attach demo-warm1"), splits[0])
        state = os.path.join(self.env["XDG_CACHE_HOME"], "ngisa", "panes", "demo-warm1")
        self.assertTrue(os.path.exists(state))

    def headless(self):
        d = os.path.join(self.env["XDG_CACHE_HOME"], "ngisa")
        os.makedirs(d, exist_ok=True)
        open(os.path.join(d, "headless"), "w").close()
        self.env.pop("WEZTERM_PANE", None)

    def test_headless_attach_opens_no_pane(self):
        self.headless()
        self.set_agents(["demo-warm1"])
        r = self.run_cli("s", "--attach", "demo-warm1")
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertEqual(self.logged("split-pane"), [])

    def test_headless_attach_missing_session_still_exits_1(self):
        self.headless()
        r = self.run_cli("s", "--attach", "demo-warm1")
        self.assertEqual(r.returncode, 1)
        self.assertIn("no session demo-warm1", r.stderr)

    def test_headless_cold_start_runs_bg_without_pane(self):
        self.headless()
        r = self.run_cli("s", "implementer", "sonnet", "do x")
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertEqual(len(self.logged("--bg")), 1)
        self.assertEqual(self.logged("split-pane"), [])

    def test_attach_twice_does_not_open_a_second_pane(self):
        self.set_agents(["demo-warm1"])
        self.set_panes([pane(1), pane(99, top=0)])
        state = os.path.join(self.env["XDG_CACHE_HOME"], "ngisa", "panes")
        os.makedirs(state, exist_ok=True)
        with open(os.path.join(state, "demo-warm1"), "w") as f:
            f.write("99\n")
        r = self.run_cli("s", "--attach", "demo-warm1")
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertEqual(self.logged("split-pane"), [])

    def test_attach_missing_session_exits_1(self):
        r = self.run_cli("s", "--attach", "demo-warm1")
        self.assertEqual(r.returncode, 1)
        self.assertIn("agent-wall.sh: no session demo-warm1", r.stderr)
        self.assertEqual(self.logged("split-pane"), [])

    def test_cold_start_has_no_report_suffix(self):
        r = self.run_cli("s", "implementer", "sonnet", "do x")
        self.assertEqual(r.returncode, 0, r.stderr)
        bg = self.logged("--bg")
        self.assertEqual(len(bg), 1, bg)
        self.assertIn("do x", bg[0])
        self.assertNotIn("SendMessage", bg[0])

    def test_cold_start_quick_is_lean_with_prompt_first(self):
        r = self.run_cli("s", "implementer", "sonnet", "Branch: b. Base: x. mode: quick. do x")
        self.assertEqual(r.returncode, 0, r.stderr)
        line = self.logged("--bg")[0]
        self.assertTrue(line.endswith("--strict-mcp-config --disable-slash-commands --setting-sources project,local --tools Bash,Edit,Write,Read,Glob,Grep"), line)
        self.assertLess(line.index("do x"), line.index("--tools"))

    def test_cold_start_plan_mode_is_full(self):
        r = self.run_cli("s", "implementer", "sonnet", "Branch: b. Base: x. mode: plan /p/plan.md. do x")
        self.assertEqual(r.returncode, 0, r.stderr)
        line = self.logged("--bg")[0]
        for flag in ("--tools", "--setting-sources", "--strict-mcp-config", "--disable-slash-commands"):
            self.assertNotIn(flag, line)

    def test_cold_start_env_full_profile(self):
        self.env["AGENT_PROFILE"] = "full"
        r = self.run_cli("s", "implementer", "sonnet", "Branch: b. Base: x. mode: quick. do x")
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertNotIn("--tools", self.logged("--bg")[0])

    def test_headless_cold_start_is_lean_too(self):
        self.headless()
        r = self.run_cli("s", "implementer", "sonnet", "do x")
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertIn("--tools", self.logged("--bg")[0])

    def test_tab_full_still_refuses(self):
        self.set_panes([pane(1), pane(2, top=0), pane(3, top=20), pane(4, top=40)])
        self.set_agents(["demo-warm1"])
        r = self.run_cli("s", "--attach", "demo-warm1")
        self.assertEqual(r.returncode, 1)
        self.assertIn("tab full", r.stderr)
        self.assertEqual(self.logged("split-pane"), [])


if __name__ == "__main__":
    unittest.main()
