"""
AFTER: same pipeline + AgentSonar (detection only).

Run:
    pip install agentsonar
    python detect.py

What you'll see:
    - WARNING fires at rotation 5, CRITICAL at rotation 15
      (streamed to stderr).
    - A run directory under agentsonar_logs/ containing timeline.jsonl,
      alerts.log, report.json, and report.html.
    - The same mocked cost as before/pipeline.py, but now you also know
      something went wrong.

This script needs zero LLM credits. We hardcode the agent handoffs to
show exactly what AgentSonar would record during a real run. In production
code, you'd call sonar.delegation() right next to your actual LLM calls.
"""
from agentsonar import monitor_orchestrator

ROTATIONS = 30
INPUT_TOKENS_PER_CALL = 3_000
OUTPUT_TOKENS_PER_CALL = 1_500
INPUT_PRICE_PER_M = 3.00
OUTPUT_PRICE_PER_M = 15.00

sonar = monitor_orchestrator()

# Three agents in a silent loop: researcher -> writer -> reviewer -> researcher.
for _ in range(ROTATIONS):
    sonar.delegation(source="researcher", target="writer")
    # ...your writer agent runs here...

    sonar.delegation(source="writer", target="reviewer")
    # ...your reviewer agent runs here...

    sonar.delegation(source="reviewer", target="researcher")
    # ...your researcher agent runs here...

sonar.shutdown()

calls = ROTATIONS * 3
input_cost = calls * INPUT_TOKENS_PER_CALL * INPUT_PRICE_PER_M / 1_000_000
output_cost = calls * OUTPUT_TOKENS_PER_CALL * OUTPUT_PRICE_PER_M / 1_000_000
total = input_cost + output_cost
print(f"{ROTATIONS} rotations completed.")
print(f"Mocked cost: ${total:,.2f}")
print("Done. Open agentsonar_logs/run-<latest>/report.html in a browser.")
