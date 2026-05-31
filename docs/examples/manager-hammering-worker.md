# Example: the manager that won't stop reassigning

The subtle failure. One agent keeps sending work to the same target. The wording differs every round, so a string-matcher would never spot it. Only a structural watcher counting traffic on a specific edge can see it.

## The setup

You build a planner-executor system:

1. A `planner` that breaks a goal into subtasks.
2. An `executor` that runs each subtask.

The planner sees the executor's output, decides whether to revise the plan, and re-issues. Standard pattern.

```python
goal = "Write a sales plan for Q2"
plan = planner.run(goal)
for _ in range(20):
    result = executor.run(plan)
    feedback = planner.run(f"Did this work? {result}")
    if "good" in feedback:
        break
    plan = planner.run(f"Revise: {feedback}")
```

## Why it goes wrong

The planner is in a slow-motion loop with itself, mediated by the executor. Each revision is genuinely different prose. None of the revisions actually changes the executor's behavior. The planner re-plans, the executor re-executes the same thing in a slightly different shape, the planner re-plans again.

A traditional logging tool sees 50 distinct prompts and 50 distinct completions. It looks like productive work.

AgentSonar sees the same pair (`planner -> executor`) talking 50 times in a window where it normally talks 3 to 5 times. That's the kind of shift it flags.

## What you'll see in your bill

Less explosive than the cyclic case, but worse for chronic spend:

- 50 calls per "task" instead of 5. Quietly multiplies your daily cost by 10x.
- Doesn't trigger any alarms because each individual call looks fine.
- Often invisible until your monthly bill hits.

We've seen this pattern cost a 3-person team $3,000 in a month before anyone noticed.

## What AgentSonar shows

```python
from agentsonar import monitor_orchestrator

sonar = monitor_orchestrator()

goal = "Write a sales plan for Q2"
plan = planner.run(goal)

for _ in range(20):
    sonar.delegation(source="planner", target="executor")
    result = executor.run(plan)

    sonar.delegation(source="executor", target="planner")
    feedback = planner.run(f"Did this work? {result}")

    if "good" in feedback:
        break

    plan = planner.run(f"Revise: {feedback}")
    sonar.delegation(source="planner", target="planner")  # the planner re-thinking is itself a delegation

sonar.shutdown()
```

When the `planner -> executor` traffic looks unusual compared to the rest of the system, you'll see a repeated-call alert:

```
[SONAR ...] WARNING repeated calls: planner -> executor (firing well above baseline)
```

The HTML report card shows:

- Failure: repeated tool calls
- Pair: `planner -> executor`
- Frequency: actual rate vs. baseline rate
- Recommendation: the source agent needs an explicit exit condition or a different decomposition strategy.

## Why this isn't covered by Prevent Mode (yet)

The repeated-call signal can also auto-stop: add `prevent={"repetitive_delegation": {"max_events": N}}` and AgentSonar raises `PreventError` once the same edge fires N times. (Prevent Mode now spans every shipped failure class, not just silent loops.)

In the meantime, you can poll between iterations and break the loop yourself:

```python
for _ in range(20):
    sonar.delegation(source="planner", target="executor")
    result = executor.run(plan)
    # ...

    # Check for any active repeated-call alert before continuing
    events = sonar.engine.get_recent_events()
    if any(e.failure_class.value == "repetitive_delegation" for e in events):
        print("Bailing: planner is hammering executor.")
        break
```

## How to actually fix it

The pattern almost always indicates that the planner's exit criterion is too vague. Two fixes that usually work:

1. **Cap planner-executor handoffs explicitly.** If three rounds of planning haven't converged, the goal is wrong, not the plan.
2. **Force the planner to write the exit criterion before the first executor call.** "I will accept the executor's output if X." Then evaluate that condition in code, not in the planner.

If neither fix is feasible, lower `z_score_threshold` to fire alerts earlier:

```python
sonar = monitor_orchestrator(config={
    "z_score_threshold": 2.0,  # raise sensitivity
})
```

## Related

- [Concepts](../concepts.md): why watching the shape of agent traffic catches what string-matching can't.
- [Configuration reference](../configuration.md): the repeated-call sensitivity knobs.
- [Reviewer never approves example](reviewer-never-approves.md): the silent-loop cousin of this failure, where two agents share the loop instead of one being the obvious culprit.
