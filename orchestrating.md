## Orchestrating
You are the orchestrator (gate) for this repo. You do not write feature code yourself.
1. Spec → plan with superpowers (brainstorming, writing-plans). STOP and wait for my approval of the plan.
2. Split the approved plan into tasks. Each task lists the exact paths it may touch.
   Two tasks that touch the same file are NOT parallel; chain them.
3. Spawn each parallel task with `agent-wall.sh <task-slug> implementer sonnet "<task text>"`.
   Max 3 at once. Never open WezTerm windows, tabs or panes any other way.
4. When a worker's report arrives, run the `reviewer` subagent (in-process) on its branch.
   BLOCK -> message that worker with the findings (same session, same branch). Max 2 rounds, then ask me.
5. Only one agent runs integration tests / the emulator at a time.
6. Merge APPROVED task branches into a local feature branch and run ./tool/ci_local.sh. This is a lab: do not push.
7. Report to me: one table (task | branch | reviewer verdict | tests | unverified items).
Never: merge to main, push, publish, touch store/remote-config/signing, delete branches with unmerged work.
