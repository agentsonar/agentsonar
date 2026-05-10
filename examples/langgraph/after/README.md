# After: with AgentSonar

Two scripts. Same LangGraph as `before/`, plus AgentSonar.

## `detect.py` — see the loop

    pip install agentsonar[langgraph]
    python detect.py

You'll see:

    [SONAR ...] WARNING ... 5 rotations
    [SONAR ...] CRITICAL ... 15 rotations
    Final rounds: 30
    Mocked cost: $14.50

A run directory lands under `agentsonar_logs/run-<latest>/` with `timeline.jsonl`, `alerts.log`, `report.json`, and `report.html`.

## `prevent.py` — stop the loop

    python prevent.py

You'll see:

    [SONAR ...] WARNING ... 5 rotations
    Stopped: <silent-loop reason>
    Cycle:   generator -> reviewer -> generator
    After:   10 rotations
    Mocked cost: $4.83
    Saved versus the 'before' run: roughly $9.67 of the $14.50 baseline.

`graph.invoke()` raises `PreventError` at rotation 10. No more node calls fire.

The mocked cost cites Claude Sonnet 4.6 pricing as of 2026-05-09 ($3 / 1M input, $15 / 1M output). See [anthropic.com/pricing](https://www.anthropic.com/pricing).
