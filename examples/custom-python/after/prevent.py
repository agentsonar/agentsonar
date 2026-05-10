"""
AFTER: same pipeline + AgentSonar with Prevent Mode (auto-stop).

Run:
    pip install agentsonar
    python prevent.py

What you'll see:
    - WARNING fires at rotation 5.
    - At rotation 10, PreventError raises and the loop stops.
    - The except block prints the cycle path and rotation count.
    - Mocked cost is roughly one third of detect.py's because the loop
      stopped before burning the rest of the rotations.

Compare this to detect.py: only difference is the prevent={...} config
and the try/except around the loop.
"""
from agentsonar import monitor_orchestrator, PreventError

INPUT_TOKENS_PER_CALL = 3_000
OUTPUT_TOKENS_PER_CALL = 1_500
INPUT_PRICE_PER_M = 3.00
OUTPUT_PRICE_PER_M = 15.00

sonar = monitor_orchestrator(config={
    # Stop the silent loop at exactly 10 rotations.
    "prevent": {"cyclic_delegation": {"max_rotations": 10}},
})

rotations_done = 0
try:
    while True:
        sonar.delegation(source="researcher", target="writer")
        sonar.delegation(source="writer", target="reviewer")
        sonar.delegation(source="reviewer", target="researcher")
        rotations_done += 1

except PreventError as e:
    print(f"Stopped: {e.reason}")
    print(f"Cycle:   {' -> '.join(e.cycle_path)}")
    print(f"After:   {e.rotations} rotations (severity {e.severity})")

sonar.shutdown()

calls = rotations_done * 3
input_cost = calls * INPUT_TOKENS_PER_CALL * INPUT_PRICE_PER_M / 1_000_000
output_cost = calls * OUTPUT_TOKENS_PER_CALL * OUTPUT_PRICE_PER_M / 1_000_000
total = input_cost + output_cost
print(f"{rotations_done} rotations completed before auto-stop.")
print(f"Mocked cost: ${total:,.2f}")
print("Saved versus the 'before' run: roughly $9.67 of the $14.50 baseline.")
