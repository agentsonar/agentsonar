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

A graph-aware tool sees one edge (`planner -> executor`) firing 50 times in a window where it normally fires 3 to 5 times. That's a structural anomaly.

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

When the `planner -> executor` edge fires more often than the engine's exponentially-decayed baseline expects (roughly: more than `z_score_threshold=3.0` standard deviations above the running mean, with at least `min_total_events=20` events recorded), you'll see:

```
[SONAR ...] WARNING repetitive_delegation: planner -> executor (firing 4.2 sigma above baseline)
```

The HTML report card shows:

- Failure class: `repetitive_delegation`
- Edge: `planner -> executor`
- Frequency: actual rate vs. baseline rate
- Recommendation: the source agent needs an explicit exit condition or a different decomposition strategy.

## Why this isn't covered by Prevent Mode (yet)

`repetitive_delegation` fires alerts but does not currently raise `PreventError`. Today, only `cyclic_delegation` is in scope for Prevent Mode. Repetitive and resource-exhaustion auto-stop are on the roadmap.

In the meantime, you can poll `sonar.engine.get_recent_events()` between iterations and break the loop yourself:

```python
for _ in range(20):
    sonar.delegation(source="planner", target="executor")
    result = executor.run(plan)
    # ...

    # Check for any active repetitive_delegation alert before continuing
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
    "z_score_threshold": 2.0,  # fire at 2 sigma instead of 3
})
```

## Related

- [Concepts](../concepts.md): why "edge frequency over a sliding window" catches what string-matching can't.
- [Configuration reference](../configuration.md): the repetitive detector's tuning knobs (`half_life_seconds`, `z_score_threshold`, etc.).
- [Reviewer never approves example](reviewer-never-approves.md): the cyclic cousin of this failure, where two agents share the loop instead of one being the obvious culprit.
