# LangGraph / LangChain adapter

The LangGraph adapter watches every node transition in your graph as a delegation event. Detection runs in real time during `graph.invoke()`, and Prevent Mode raises `PreventError` straight out of the invoke call.

## Install

```bash
pip install agentsonar[langgraph]
```

The `[langgraph]` extra brings in `langchain-core`, which is the only LangChain dependency required (the callback infrastructure lives there). If you already have LangChain or LangGraph installed, plain `pip install agentsonar` works too.

## Quick start

Two ways to wire it in. Pick the one that fits your code.

### Option 1: `monitor()` wrapper (recommended)

Wrap your compiled graph once. Every `.invoke()`, `.stream()`, `.ainvoke()`, or `.astream()` afterward is monitored automatically.

```python
from agentsonar import monitor
from langgraph.graph import StateGraph

graph = StateGraph(MyState)
# ...add nodes and edges...
graph = graph.compile()
graph = monitor(graph)               # one line, then run as usual

result = graph.invoke({"input": "hello"})
```

If you're already using other LangChain callbacks, they keep working. `monitor()` adds AgentSonar alongside your existing callbacks, it doesn't replace them.

To read the AgentSonar summary later:

```python
print(graph.sonar.get_summary())
```

### Option 2: Direct callback in invoke config

If you'd rather not wrap the graph, pass the callback directly:

```python
from agentsonar import AgentSonarCallback
from langgraph.graph import StateGraph

graph = StateGraph(MyState)
# ...add nodes and edges...
graph = graph.compile()

sonar = AgentSonarCallback()
result = graph.invoke(
    {"input": "hello"},
    config={"callbacks": [sonar]},
)

sonar.shutdown()
```

Functionally identical to `monitor()`, just more explicit.

## Runnable example

Two minimal scripts you can copy and run:

- [`examples/langgraph/detect.py`](../../examples/langgraph/detect.py): detection-only setup.
- [`examples/langgraph/prevent.py`](../../examples/langgraph/prevent.py): same graph, with Prevent Mode opted in.

## What gets detected

Every node transition in your graph becomes a delegation edge. AgentSonar's full alert surface applies: silent loops, repeated tool calls, and runaway token / tool spend.

Each new `graph.invoke()` starts a fresh detection session. Sequential invokes don't share loop history with each other.

## Config

The same config dict as every other adapter:

```python
from agentsonar import monitor

graph = monitor(graph, config={
    "warning_threshold":  3,
    "critical_threshold": 8,
    "log_dir":            "./logs",
})
```

Or with `AgentSonarCallback()`:

```python
sonar = AgentSonarCallback(config={
    "warning_threshold": 3,
})
```

Full reference: [`../configuration.md`](../configuration.md).

## Prevent Mode

LangGraph supports the full Prevent Mode story. When you opt in, `PreventError` raises out of `graph.invoke()`:

```python
from agentsonar import monitor, PreventError

graph = monitor(graph, config={
    "prevent": {"cyclic_delegation": True}
})

try:
    result = graph.invoke({"input": "hello"})
except PreventError as e:
    print(f"Stopped: {e.reason}")
    print(f"Cycle:   {' -> '.join(e.cycle_path)}")
    print(f"After:   {e.rotations} rotations")
```

If you'd rather see the trip without an exception, use the return-style mode:

```python
graph = monitor(graph, config={
    "prevent": {"cyclic_delegation": True, "raise": False}
})

result = graph.invoke({"input": "hello"})
trip = graph.sonar.engine.should_prevent()
if trip is not None:
    print(f"Should stop: {trip.reason}")
```

## Streaming and async

The same `monitor()` wrapper handles `.stream()`, `.ainvoke()`, and `.astream()`. AgentSonar's callback is forwarded to all of them:

```python
graph = monitor(graph)

# Sync invoke
graph.invoke({"input": "hello"})

# Sync stream
for chunk in graph.stream({"input": "hello"}):
    print(chunk)

# Async invoke
result = await graph.ainvoke({"input": "hello"})

# Async stream
async for chunk in graph.astream({"input": "hello"}):
    print(chunk)
```

If Prevent Mode is enabled, `PreventError` raises out of every variant when a trip occurs.

## Multi-graph projects

If you have multiple graphs in the same process, give each its own `monitor()` instance. They'll write to separate run directories under `agentsonar_logs/` and have independent detection state.

```python
research_graph = monitor(research_graph)
review_graph = monitor(review_graph, config={"warning_threshold": 2})

result1 = research_graph.invoke(...)
result2 = review_graph.invoke(...)
```

If you want a single combined view across two graphs, run them inside the same callback:

```python
sonar = AgentSonarCallback()

result1 = graph_a.invoke(input, config={"callbacks": [sonar]})
result2 = graph_b.invoke(input, config={"callbacks": [sonar]})

sonar.shutdown()
```

## Limitations

- **Sub-graphs**: nested LangGraph calls are flattened from AgentSonar's perspective. The parent and child graph nodes show up as edges in the same graph. If you want them separated, pass distinct callbacks.
- **Tools-as-agents**: if your tools call out to LLMs that you'd think of as agents, those don't currently surface as delegation events (LangChain doesn't emit `langgraph_node` for tool execution). For tool-level delegation tracking, use the [Custom Python adapter](custom-python.md) and call `engine.ingest()` from your tool wrapper.

## Output

Same as every other adapter:

```
agentsonar_logs/
└── run-2026-04-29_05-12-34-amber-fox/
    ├── timeline.jsonl
    ├── alerts.log
    ├── report.json
    └── report.html
```

## See also

- [Concepts](../concepts.md): what counts as a coordination failure.
- [Configuration](../configuration.md): every config knob.
- [Prevent Mode](../prevent-mode.md): the full auto-stop walkthrough, including LangGraph-specific details.
- [Custom Python adapter](custom-python.md): the manual fallback for cases where the auto-tracking misses an event.
