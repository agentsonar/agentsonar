# The only change you made

Compared to `before/pipeline.py`, the `after/` scripts add **one import and one line**.

## detect.py

```diff
+ from agentsonar import monitor

  graph = builder.compile()
+ graph = monitor(graph)

  result = graph.invoke({"text": "", "rounds": 0})
```

That's the whole integration. Every node transition becomes a delegation edge. Alerts, `report.html`, and the timeline are automatic.

## prevent.py

Same as detect.py, plus the prevent config and a try/except:

```diff
- graph = monitor(graph)
+ graph = monitor(graph, config={
+     "prevent": {"cyclic_delegation": {"max_rotations": 10}},
+ })

+ try:
      result = graph.invoke({"text": "", "rounds": 0})
+ except PreventError as e:
+     print(f"Stopped: {e.reason}")
```

## Cost saved

| Run | Rotations | Mocked cost |
|---|---|---|
| `before/pipeline.py` | 30 (loop runs to completion) | $14.50 |
| `after/detect.py` | 30 (loop runs, alerts fire) | $14.50 |
| `after/prevent.py` | 10 (auto-stop kicks in) | $4.83 |

Savings on `prevent.py` versus `before/pipeline.py`: roughly **$9.67 per run**.

Pricing source: Claude Sonnet 4.6 input/output rates as of 2026-05-09 from [anthropic.com/pricing](https://www.anthropic.com/pricing).
