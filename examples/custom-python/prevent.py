"""
AgentSonar custom-python adapter, with Prevent Mode.

Run:
    pip install agentsonar
    python prevent.py

What you'll see:
    - WARNING fires at rotation 5.
    - At rotation 15, PreventError raises and the loop stops.
    - The except block prints the cycle path and rotation count.

Compare this to detect.py: only difference is the prevent={...} config
and the try/except around the loop.
"""
from agentsonar import monitor_orchestrator, PreventError

sonar = monitor_orchestrator(config={
    "prevent": {"cyclic_delegation": True}  # opt in
})

try:
    while True:
        sonar.delegation(source="reviewer", target="generator")
        # ...your generator agent runs here...

        sonar.delegation(source="generator", target="reviewer")
        # ...your reviewer agent runs here...

except PreventError as e:
    print(f"Stopped: {e.reason}")
    print(f"Cycle:   {' -> '.join(e.cycle_path)}")
    print(f"After:   {e.rotations} rotations (severity {e.severity})")

sonar.shutdown()
