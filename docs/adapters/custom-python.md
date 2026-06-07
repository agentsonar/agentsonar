# Python adapter: works with any framework

The `monitor_orchestrator()` adapter is AgentSonar's universal Python
integration. If you can write Python, you can wire it in, regardless
of which agent framework (or none) you're using.

This is the adapter to use when:

- You're writing your own agent loops by calling `openai.ChatCompletion` or `anthropic.Messages` directly
- You're using a framework AgentSonar doesn't have a native adapter for yet (OpenAI Agents SDK, AutoGen, Pydantic AI, …)
- Your "orchestrator" is a Celery DAG, a FastAPI endpoint, a subprocess pipeline, or anything else that doesn't look like CrewAI / LangGraph
- You want full control over what counts as a "delegation" event

**There is no functionality difference** between this adapter and the
framework-specific ones. Detection, Prevent Mode, the HTML report, the
JSONL timeline, all identical. The only difference is YOU explicitly
tell AgentSonar when one agent hands work to another, instead of it
auto-detecting from a framework's event bus.

## Install

```bash
pip install agentsonar
```

No extras needed, this adapter has zero framework dependencies.

## The whole API in one example

```python
from agentsonar import monitor_orchestrator

sonar = monitor_orchestrator()

# Each time one agent hands work to another, tell AgentSonar:
sonar.delegation(source="planner",    target="researcher")
# ... your researcher agent runs ...

sonar.delegation(source="researcher", target="writer")
# ... your writer agent runs ...

sonar.delegation(source="writer",     target="reviewer")
# ... your reviewer agent runs ...

# When your run is finished:
sonar.shutdown()
```

That's it. Three functions:

| Function | What it does |
|---|---|
| `monitor_orchestrator(config=None)` | Constructor. Returns an adapter object. Optional `config` dict for tuning, see the [configuration reference](../configuration.md). |
| `sonar.delegation(source, target, metadata=None, timestamp=None)` | Tell AgentSonar one agent handed work to another. |
| `sonar.shutdown()` | Finalize the run. Writes JSON + HTML reports. |

Every call is fire-and-forget, `delegation()` and `shutdown()` never raise
into your code (the only exception: `PreventError` when Prevent Mode
explicitly trips, which IS the point).

## Runnable example

Two minimal scripts you can copy and run (zero LLM credits required):

- [`examples/custom-python/detect.py`](../../examples/custom-python/detect.py): detection-only setup.
- [`examples/custom-python/prevent.py`](../../examples/custom-python/prevent.py): same flow, with Prevent Mode opted in.

## Two-line minimum example

For a simple two-agent loop:

```python
from agentsonar import monitor_orchestrator
from openai import OpenAI

client = OpenAI()
sonar = monitor_orchestrator()

state = "initial draft"
for _ in range(20):
    sonar.delegation(source="reviewer", target="generator")
    state = client.chat.completions.create(...).choices[0].message.content

    sonar.delegation(source="generator", target="reviewer")
    review = client.chat.completions.create(...).choices[0].message.content

sonar.shutdown()
```

If `reviewer` and `generator` ping-pong long enough to form a coordination
problem, AgentSonar fires alerts, same as if you were on CrewAI or
LangGraph.

## Context manager (recommended for production)

`shutdown()` runs even if your loop raises:

```python
with monitor_orchestrator() as sonar:
    for _ in range(20):
        sonar.delegation("planner", "researcher")
        # ...
        sonar.delegation("researcher", "writer")
        # ...
# shutdown() called automatically on exit, even if an exception escaped
```

## What counts as a "delegation"?

AgentSonar treats every `delegation(source, target)` call as one directed
edge in the agent graph. Anything that represents "agent A handed work to
agent B" qualifies:

| Your code does this | Call this |
|---|---|
| Agent A's LLM produces output, you pass it to Agent B's LLM as input | `sonar.delegation("a", "b")` |
| A subprocess spawns a sub-agent worker | `sonar.delegation("manager", "worker")` |
| A Celery task pushes a message to another agent's queue | `sonar.delegation("upstream", "downstream")` |
| An HTTP webhook from agent A triggers agent B | `sonar.delegation("a", "b")` |
| OpenAI Agents SDK `delegate_to_agent` tool fires | `sonar.delegation(source_agent_role, target_agent_role)` |

The agent names are arbitrary strings, use whatever your code already
uses (function names, role names, queue names, container names).
AgentSonar treats them as opaque identifiers. Just be consistent: the
same agent should always have the same name, otherwise the cycle
detection won't connect related delegations.

## Configuration

The two-line example above uses zero config. To tune detection:

```python
sonar = monitor_orchestrator(config={
    # Detection thresholds, when alerts fire
    "warning_threshold":   5,    # rotation count for first WARNING (default 5)
    "critical_threshold":  15,   # rotation count to escalate to CRITICAL (default 15)

    # Rate limiter, when does runaway throughput fire `resource_exhaustion`?
    "per_edge_limit":  10,       # max events per edge in window (default 10)
    "global_limit":    200,      # max total events in window  (default 200)
    "window_size":     180.0,    # time window in seconds      (default 180)

    # Prevent Mode (opt-in)
    "prevent": {"cyclic_delegation": True},

    # Output
    "log_dir":        ".",       # where agentsonar_logs/ goes
    "console_output": True,      # stream alerts to stderr
    "file_output":    True,      # write timeline.jsonl + alerts.log + report.*
})
```

Full configuration reference: [`../configuration.md`](../configuration.md).

## Prevent Mode

Stop the loop the moment AgentSonar detects it crosses a threshold.

```python
from agentsonar import monitor_orchestrator, PreventError

sonar = monitor_orchestrator(config={
    "prevent": {"cyclic_delegation": True}
})

try:
    while True:
        sonar.delegation("reviewer", "generator")
        # ...your agents run...
        sonar.delegation("generator", "reviewer")
        # ...
except PreventError as e:
    print(f"Stopped: {e.reason}")
    print(f"Cycle:   {' -> '.join(e.cycle_path)}")

sonar.shutdown()
```

→ Full Prevent Mode walkthrough: [`../prevent-mode.md`](../prevent-mode.md).

## Output

After `shutdown()`:

```
agentsonar_logs/
└── run-2026-04-29_05-12-34-amber-fox/
    ├── timeline.jsonl   # every event, machine-readable
    ├── alerts.log       # signal-only, human-readable
    ├── report.json      # deduped summary
    └── report.html      # standalone visual report
```

Open `report.html` in any browser, no external CSS / JS / network calls.

## Common scenarios

### OpenAI Agents SDK (until the native adapter ships)

The OpenAI Agents SDK uses `Agent.run()` and a `delegate_to_agent` tool.
You can bridge it through the Python adapter by recording each
delegation as the tool fires:

```python
from agents import Agent
from agentsonar import monitor_orchestrator

sonar = monitor_orchestrator()

planner = Agent(name="planner", tools=[delegate_to_agent_tool])
researcher = Agent(name="researcher", ...)

# Wrap delegate_to_agent so we record each handoff
original_delegate = delegate_to_agent_tool.func
def tracked_delegate(source_role: str, target_role: str, payload):
    sonar.delegation(source=source_role, target=target_role)
    return original_delegate(source_role, target_role, payload)
delegate_to_agent_tool.func = tracked_delegate

result = planner.run("…")
sonar.shutdown()
```

When the native OpenAI Agents SDK adapter ships, this bridge becomes a
one-line `from agentsonar import monitor_openai_agent` swap.

### Celery agent pipeline

```python
from agentsonar import monitor_orchestrator
import celery

sonar = monitor_orchestrator()

@celery.shared_task
def planner_task(input):
    output = run_planner(input)
    sonar.delegation(source="planner", target="researcher")
    researcher_task.delay(output)
    return output

@celery.shared_task
def researcher_task(input):
    output = run_researcher(input)
    sonar.delegation(source="researcher", target="writer")
    writer_task.delay(output)
    return output

# ...etc
```

Heads up: `monitor_orchestrator()` keeps state per-process. If your
Celery workers run in separate processes, each gets its own AgentSonar
session. For cross-process aggregation, use the [OMA-style sidecar](oma.md)
pattern, one Python process holds the engine, all workers post
delegations to it over HTTP.

### Subprocess pipeline

```python
import subprocess
from agentsonar import monitor_orchestrator

sonar = monitor_orchestrator()

planner_output = subprocess.check_output(["python", "planner.py", input])
sonar.delegation(source="planner", target="researcher")

researcher_output = subprocess.check_output(["python", "researcher.py", planner_output])
sonar.delegation(source="researcher", target="writer")

# ...
sonar.shutdown()
```

## What if my framework isn't covered?

**We're genuinely happy to add support for new frameworks, just ask.**

Open an [issue](https://github.com/agentsonar/agentsonar/issues/new?template=feature_request.yml)
or [email us](mailto:founders@agent-sonar.com), tell us what you're using,
and we'll wire it up. The bar for new adapters is intentionally low,
any framework with a callback hook or event bus can plug in, and past
adapters have shipped in days, not weeks. If your framework is blocking
you, we'll prioritize it.

In the meantime, the `monitor_orchestrator()` adapter shown above gives
you everything a native adapter would, with one extra line per
delegation handoff.
