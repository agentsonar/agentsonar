"""
AgentSonar CrewAI adapter, with the Prevent-Mode workaround.

Prevent Mode auto-stop is currently deferred for CrewAI. This script
shows the workaround: between tasks, poll the engine for any active
cycle alert and abort if one fired.

Run:
    pip install agentsonar[crewai]
    export OPENAI_API_KEY=sk-...
    python prevent.py
"""
from agentsonar import AgentSonarListener
from crewai import Agent, Task, Crew

sonar = AgentSonarListener()

planner = Agent(
    role="planner",
    goal="Plan a small project",
    backstory="A meticulous planner.",
    allow_delegation=True,
)
researcher = Agent(
    role="researcher",
    goal="Research details",
    backstory="A thorough researcher.",
    allow_delegation=True,
)

# Task 1
task1 = Task(
    description="Plan part 1.",
    expected_output="A short list.",
    agent=planner,
)
Crew(agents=[planner, researcher], tasks=[task1]).kickoff()

# Check between tasks. If a cycle was flagged, stop before launching task 2.
events = sonar.engine.get_recent_events()
for e in events:
    if e.failure_class.value == "cyclic_delegation":
        raise RuntimeError(f"Stopping: cycle detected. {e.summary}")

# Task 2 only runs if the check passed.
task2 = Task(
    description="Plan part 2.",
    expected_output="A short list.",
    agent=planner,
)
Crew(agents=[planner, researcher], tasks=[task2]).kickoff()
