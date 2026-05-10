# The only change you made

Compared to `before/pipeline.py`, the `after/` scripts add **one import and one line**.

## detect.py

```diff
+ from agentsonar import monitor_orchestrator
+ sonar = monitor_orchestrator()

  for _ in range(ROTATIONS):
+     sonar.delegation(source="researcher", target="writer")
      ...
+     sonar.delegation(source="writer", target="reviewer")
      ...
+     sonar.delegation(source="reviewer", target="researcher")
      ...

+ sonar.shutdown()
```

That's the whole integration. Each `delegation()` call records one agent handing work to another. Everything else (alerts, report.html, the timeline) is automatic.

## prevent.py

Same as detect.py, plus three more lines:

```diff
- sonar = monitor_orchestrator()
+ sonar = monitor_orchestrator(config={
+     "prevent": {"cyclic_delegation": {"max_rotations": 10}},
+ })

+ try:
      while True:
          ...
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
