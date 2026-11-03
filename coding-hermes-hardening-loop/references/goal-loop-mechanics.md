# Goal-loop mechanics — the concrete persistence surface

Depth for SKILL.md §"Goals, subgoals, and the feeder". That section states the rule (a terminal
evaluation the loop cannot WRITE is prose). This file names the surface, so an evaluation pass has
somewhere to actually append.

## Where standing goals live

Not a slash command, not a cron job, not a file: **rows in `state.db` → `state_meta`, key
`goal:<session_id>`**, value = a JSON object (`GoalState`). Confirm the surface is what you think
before explaining why a loop is quiet — a chat can hold several goal sessions, and only ONE of them
is the live loop.

Read it with a staged script file, not an inline heredoc (a command guard can refuse the heredoc and
the refusal reads like a crash):

```python
# goal-state.py   ->  run the FILE
import sqlite3, json, datetime
c = sqlite3.connect('file:' + DB + '?mode=ro', uri=True)
for k, v in c.execute("select key, value from state_meta where key like 'goal:%' order by rowid desc"):
    d = json.loads(v)
    print(k, d.get('status'), d.get('turns_used'), '/', d.get('max_turns'),
          d.get('last_verdict'), len(d.get('subgoals') or []), d.get('last_turn_at'))
```

Fields that decide the diagnosis: `status` (active|paused|done|cleared), `turns_used`,
`last_turn_at`, `last_verdict` (continue|wait|blocked|done), `last_reason`, `subgoals`,
`consecutive_parse_failures`, `consecutive_transport_failures`, `waiting_on_delegations`.

**Epochs are UTC; gateway log timestamps are LOCAL.** A log window derived from `created_at` misses
by the machine's offset and returns nothing, which reads as "no activity" when the real cause is a
window hours off.

## Arm and append from inside the agent

When the owner says "run it as a goal with subgoals", you can arm it: reuse the code that owns
`/goal` grammar instead of hand-writing the JSON, or the row drifts from the schema and the judge
reads fields nobody populated.

```python
from hermes_cli.goals import GoalManager, load_goal
from hermes_cli.goal_command import dispatch_goal_command
mgr = GoalManager("<this session id>")
dispatch_goal_command(mgr, GOAL_TEXT, authorize_gate=lambda: None)   # returns a rendered line
for sg in SUBGOALS:
    mgr.add_subgoal(sg)
state = load_goal("<this session id>")      # READ BACK: status, max_turns, len(subgoals)
```

- **A rendered return value is not proof.** Confirm with `load_goal()`: `active`, the expected
  `max_turns`, the expected subgoal count.
- **Arming is not doing.** Dispatch the first worker in the SAME turn, or the first continuation
  re-derives the plan you just wrote and burns a turn.
- **Every subgoal names an ARTIFACT** — a file that must exist, a screen that renders, a command
  that must be green. A subgoal that restates the goal or the loop's own name is unjudgeable and the
  loop spins on it; a list of bare repeated phrases is the decay signature.
- **A goal armed mid-turn starts looping only after the turn ends**, and dispatching subagents parks
  it (`waiting_on_delegations`) until they finish — a goal at zero turns while your own workers run
  is behaving correctly.

## Diagnose a quiet loop in one pass

1. Read the state row. `active` with `turns_used: 0` and `last_turn_at: 0` = the judge has **never**
   run for that session: registered, not paused, not out of budget, nothing feeding it.
2. Read the newest message timestamp for that session — a long turn legitimately looks quiet.
3. Grep the FEEDER's prompt for the re-append clause. The needles are cheap and decisive:
   `subgoal`, `re-eval`, `terminal`, `feeds itself`. A feeder that finishes iterations and never
   adds the next one produces the *same* outward silence as a disabled feeder.
4. Check the feeder is enabled AND that its board is the goal's board. A feeder pointed at a sibling
   project is busy and irrelevant, which also looks like progress in its own logs.

A goal sitting at one turn, days stale, with a single subgoal that restates the loop contract, is the
signature of a feeder that stopped — report which of the three deaths it was (disabled / no re-append
clause / wrong board) and do not re-enable a feeder whose prompt lacks the clause.

## What the mechanism actually does (probed, not inferred)

`GoalManager` in `hermes_cli/goals.py` is the engine, and
`gateway/run_goals.py::_post_turn_goal_continuation` is the only feeder. Three behaviours decide
whether a loop turns, and none of them is visible in the skill's prose:

1. **Barrier expiry is LAZY.** `is_waiting()` clears a satisfied barrier *when it is called*;
   nothing schedules a wake at `waiting_until`. A goal parked on a delegation or a timer that
   expired days ago still reads `active` with a stale `last_turn_at`, because the only thing that
   would re-judge it is a new turn and the park is what prevented one. Treat
   `status=active AND waiting_until < now`, or a `waiting_on_delegations` count with no live
   delegations, as a FROZEN loop rather than patience: re-judge it explicitly or bury it with the
   real reason. `wait` is the quietest death because it looks like correct restraint.
2. **`add_subgoal` does not dedupe.** Three identical strings store three subgoals. The judge's
   input is a render of that list, so duplicates dilute the criteria with unjudgeable repeats —
   the decay signature SKILL.md warns about has a mechanical cause. Audit it as
   `len(subgoals) != len(set(subgoals))` before concluding a loop is being judged on its real
   criteria.
3. **There is no repeat/oscillation detector.** `last_reason` is written every turn and never
   compared to its predecessor, so a judge returning the same finding N turns running yields
   `continue` N times. Escalate it yourself: the second identical reason is a cue to re-scope or
   pause, not to spend another turn on the same wall.

**Probe the machinery on a throwaway session, never a live one.** This exercises the real class
in-process, calls no model, and cannot disturb a running loop:

```python
import sys, time; sys.path.insert(0, '<hermes repo>')
from hermes_cli.goals import GoalManager, load_goal
from hermes_cli.goal_command import dispatch_goal_command
SID = 'probe_%d' % int(time.time())
m = GoalManager(session_id=SID, default_max_turns=50)
dispatch_goal_command(m, '<probe goal>', authorize_gate=lambda: None)   # ARM FIRST
for _ in range(3):
    m.add_subgoal('artifact A exists')          # duplicate-acceptance probe
m.wait_for_seconds(2, reason='probe')
time.sleep(3)
print(load_goal(SID).status, m.is_waiting())    # expiry probe: False == barrier lifted
m.clear()                                        # always clean up the probe session
```

- `add_subgoal` raises `RuntimeError: no active goal` until the goal is armed — arm before you
  assert anything about subgoals.
- `dispatch_goal_command` lives in `hermes_cli.goal_command`, NOT `hermes_cli.goals`. Importing it
  from the wrong module is an ImportError that reads like a missing feature.
- `wait_for_seconds(n, on_delegations=k)` releases the moment live delegations drop below `k`, so
  a park made with a delegation count that never existed lifts immediately. Verify a barrier with
  the same call shape production uses, not a simplified one.
- A rendered `GoalCommandResult.output` is a display string. `load_goal(SID)` is the assertion.

## One continuing cost to state out loud

The judge is an auxiliary-model call per turn: a goal loop is a recurring spend, and its input is a
RENDER of the subgoal list that can truncate. Treat the board rows as the durable contract and the
goal as cadence.
