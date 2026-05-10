# CrewAI adapter

The `AgentSonarListener` plugs into CrewAI's event bus and detects coordination failures automatically. No code changes inside your crew. Two lines at startup.

## Install

```bash
pip install agentsonar[crewai]
```

The `[crewai]` extra brings in CrewAI as a dependency. If you already have CrewAI installed, plain `pip install agentsonar` plus your existing CrewAI works too. The listener will raise a clear `RuntimeError` at instantiation if CrewAI's event bus isn't importable.

## Quick start

```python
from agentsonar import AgentSonarListener
from crewai import Agent, Crew, Task

# Wire AgentSonar in. That's it.
sonar = AgentSonarListener()

# Build and run your crew normally.
crew = Crew(
    agents=[planner, researcher, writer, reviewer],
    tasks=[plan_task, research_task, write_task, review_task],
)
result = crew.kickoff()
```

Detection runs as your crew runs. Alerts stream to stderr; the HTML report and JSONL timeline are written when CrewAI emits the kickoff-completed event.

## Runnable example

Two minimal scripts you can copy and run:

- [`examples/crewai/detect.py`](../../examples/crewai/detect.py): detection-only setup.
- [`examples/crewai/prevent.py`](../../examples/crewai/prevent.py): same flow, plus the polling workaround for the deferred Prevent Mode (see below).

## What gets detected

Every agent-to-agent delegation in your crew is recorded automatically. AgentSonar can fire three kinds of alerts:

- **Silent loops** (`cyclic_delegation`): when delegation paths form a circle (reviewer -> planner -> reviewer).
- **Repeated tool calls** (`repetitive_delegation`): when one agent keeps hammering another past its baseline.
- **Runaway token / tool spend** (`resource_exhaustion`): when total or per-pair traffic crosses the rate limit.

## Config

The listener accepts the same config dict as every other adapter:

```python
sonar = AgentSonarListener(config={
    "warning_threshold":  3,
    "critical_threshold": 8,
    "log_dir":            "./logs",
})
```

Full reference: [`../configuration.md`](../configuration.md).

## Custom delegation events

If your crew has a tool that performs delegation but doesn't have "delegate" in its name (rare but valid), AgentSonar won't auto-detect it. Two options:

1. **Rename the tool.** The cleanest fix; helps every other observability tool too.
2. **Manually call `engine.ingest()`.** The listener exposes the underlying engine via `sonar.engine`. Build an `InteractionEvent` and pass it in:

```python
from agentsonar._core.models import InteractionEvent
import time

# Inside your tool's execution path:
sonar.engine.ingest(InteractionEvent(
    source="manager",
    target="worker",
    timestamp=time.time(),
))
```

This is the same path the listener uses internally, so detection results are identical to the auto-tracked case.

## Lifecycle

The listener is fire-and-forget. As long as `sonar` is alive in your Python process and CrewAI's event bus is up, alerts fire automatically. When CrewAI emits the kickoff-completed event, the listener calls `engine.shutdown()` for you, which writes the final reports.

If you have multiple sequential crew kickoffs in the same process, the second `kickoff()` will start a fresh detection session. The first run's reports are already on disk; no work to clean up.

To explicitly close out (e.g., long-running workers that don't naturally hit kickoff_completed), call:

```python
sonar.shutdown()
```

It's safe to call multiple times. Subsequent calls are no-ops.

## Prevent Mode (deferred for CrewAI)

Prevent Mode auto-stop is currently deferred for CrewAI. Detection still works as expected: you'll see WARNING and CRITICAL alerts in stderr, in `alerts.log`, and on the HTML report card.

If you need auto-stop today, poll the engine between tasks and abort if a cycle was flagged:

```python
from agentsonar import AgentSonarListener

sonar = AgentSonarListener()

# Run task 1
crew.kickoff(tasks=[task1])

# Check before running task 2
events = sonar.engine.get_recent_events()
if any(e.failure_class.value == "cyclic_delegation" for e in events):
    raise RuntimeError("Stopping: cycle detected during task 1.")

# Run task 2
crew.kickoff(tasks=[task2])
```

## Limitations

- **Self-loops are tracked.** If an agent delegates to itself (rare but possible in CrewAI), it counts as an edge. Filter at the tool level if you don't want this.
- **The listener requires CrewAI 0.55+.** Older CrewAI versions used a different event bus shape. If you're on something older, upgrade or fall back to the [Custom Python adapter](custom-python.md).
- **Tool-name detection is fuzzy.** If your custom tool happens to contain "delegate" in its name but isn't actually a delegation (e.g., `delegate_state_check`), AgentSonar will treat its calls as delegations. Rename or use the manual `engine.ingest()` path to be precise.

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

Same output as every other adapter. Open `report.html` in any browser.

## See also

- [Concepts](../concepts.md): what counts as a coordination failure.
- [Configuration](../configuration.md): every config knob.
- [Custom Python adapter](custom-python.md): the universal fallback if you outgrow the auto-tracking.
- [Prevent Mode](../prevent-mode.md): the auto-stop story (currently CrewAI-deferred).
