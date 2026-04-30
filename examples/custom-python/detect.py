"""
AgentSonar custom-python adapter, detection only.

Run:
    pip install agentsonar
    python detect.py

What you'll see:
    - WARNING fires at rotation 5, CRITICAL at rotation 15
      (streamed to stderr).
    - A run directory under agentsonar_logs/ containing timeline.jsonl,
      alerts.log, report.json, and report.html.

This script needs zero LLM credits. We hardcode delegations to show
exactly what AgentSonar would record during a real reviewer-generator
loop. In production code, you'd call sonar.delegation() right next to
your actual LLM calls.
"""
from agentsonar import monitor_orchestrator

sonar = monitor_orchestrator()

# Simulate a 30-rotation reviewer-generator cycle.
for _ in range(30):
    sonar.delegation(source="reviewer", target="generator")
    # ...your generator agent runs here...

    sonar.delegation(source="generator", target="reviewer")
    # ...your reviewer agent runs here...

sonar.shutdown()
print("Done. Open agentsonar_logs/run-<latest>/report.html in a browser.")
