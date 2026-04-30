# Example: the agent spawn that ran away

The fast failure. One agent decides to spawn many child agents. Each child decides to spawn more. Within a minute, you have a thousand LLM calls in flight and nobody driving.

## The setup

You build a manager-worker pattern with a tool that lets the manager spawn workers:

```python
@tool
def spawn_worker(task: str, role: str) -> str:
    """Create a new worker agent to handle this task."""
    worker = Agent(name=role)
    return worker.run(task)

manager = Agent(name="manager", tools=[spawn_worker])
manager.run("Process all customer feedback from last quarter")
```

Looks reasonable. The manager will spawn one worker per chunk of feedback, and each worker reports back. Bounded fan-out.

## Why it goes wrong

A few real ways this blows up:

1. **The manager hallucinates a delegation strategy.** Instead of "spawn 10 workers, one per chunk," it decides "spawn one worker, and tell that worker to spawn 100 sub-workers, and each sub-worker spawns 10 of its own." Now you have 1,000 workers from one manager.

2. **A worker is also given the spawn tool.** Now any worker can spawn its own children. A bug or hallucination in any of them turns linear fan-out into exponential.

3. **Loop + spawn.** A retry mechanism around the spawn tool sees a transient failure, retries, succeeds, but the original spawn also succeeded. You get duplicate workers per retry. With three levels of retry-on-failure, that's 8x the intended count.

The trace looks "busy but normal." Each spawn is one valid call. There's no exception, no error log. Token counts climb, response times climb, and your provider eventually rate-limits you, which can mask the underlying issue.

## What you'll see in your bill

This is the failure that causes bills like "we spent $4,000 in 11 minutes." The math is straightforward:

- 1,000 worker LLM calls at ~3K tokens average = 3M tokens.
- At GPT-4-class pricing (~$30 / M output, ~$10 / M input), that's $40 to $90 per minute of runaway.
- Modern frontier models with extended-thinking and big context: easily 5 to 10x that.

We've validated this against real LangGraph workloads with frontier models. The detection fires correctly. The bill, if you don't catch it, is real.

## What AgentSonar shows

You don't need to record every single sub-spawn manually. The framework adapter (CrewAI, LangGraph) does it for you. For the Custom Python adapter, you call `delegation()` once per spawn:

```python
from agentsonar import monitor_orchestrator

sonar = monitor_orchestrator()

@tool
def spawn_worker(task: str, role: str) -> str:
    sonar.delegation(source="manager", target=role)
    worker = Agent(name=role)
    return worker.run(task)

manager = Agent(name="manager", tools=[spawn_worker])
manager.run("Process all customer feedback from last quarter")

sonar.shutdown()
```

When the rate of `manager -> worker` events crosses `per_edge_limit=10` events in any 180-second window (defaults), AgentSonar fires:

```
[SONAR ...] CRITICAL resource_exhaustion: manager -> worker (12 events in 180s, limit 10)
```

When the global event rate crosses `global_limit=200` in any 180-second window, AgentSonar fires:

```
[SONAR ...] CRITICAL resource_exhaustion: global (215 events in 180s, limit 200)
```

The HTML report card shows the actual rate, the limit, and the time window. You see "the manager spawned 12 workers in 60 seconds, normal is 3" without having to manually read the timeline.

## Tuning the rate limiter for your workload

Defaults are conservative. If your normal pattern is 50 child agents per minute and that's healthy for your use case, the defaults will fire false positives. Tune like so:

```python
sonar = monitor_orchestrator(config={
    "per_edge_limit": 100,    # was 10
    "global_limit":   2000,   # was 200
    "window_size":    60.0,   # was 180 seconds
})
```

The right values are workload-specific. Run a known-healthy job once with the defaults, look at the alerts you got, and raise the limit just above your healthy peak.

## Why Prevent Mode doesn't auto-stop spawn explosions yet

Same as repetitive_delegation: today, only `cyclic_delegation` raises `PreventError`. `resource_exhaustion` fires alerts but doesn't auto-interrupt the spawn loop. On the roadmap.

If you want auto-stop today, poll between iterations:

```python
@tool
def spawn_worker(task: str, role: str) -> str:
    sonar.delegation(source="manager", target=role)

    events = sonar.engine.get_recent_events()
    if any(e.failure_class.value == "resource_exhaustion" for e in events):
        raise RuntimeError("Spawn rate exceeded. Cooling off.")

    worker = Agent(name=role)
    return worker.run(task)
```

## How to actually fix it

The structural fix is to bound fan-out in code, not in prompts:

1. **Cap children per parent in the spawn tool itself.** A counter on `Agent` that errors out if the same agent has spawned more than N children.
2. **Disallow recursive spawning.** Workers should not have the spawn tool. Only the manager.
3. **Write a backpressure check before each spawn.** "If there are already 50 workers running, queue this one."
4. **Use a worker pool, not unbounded spawning.** A fixed pool of N workers consuming from a queue.

The detection layer flags the pattern; the fix lives in your tool definition or your agent control flow.

## Related

- [Concepts](../concepts.md): "resource exhaustion" as the third failure class.
- [Configuration reference](../configuration.md): the rate limiter's tuning knobs (`per_edge_limit`, `global_limit`, `window_size`).
- [Reviewer never approves example](reviewer-never-approves.md): a cyclic failure that does have Prevent Mode coverage.
