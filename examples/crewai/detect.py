"""
AgentSonar CrewAI adapter, detection only.

Run:
    pip install agentsonar[crewai]
    export OPENAI_API_KEY=sk-...      # or your provider of choice
    python detect.py

What you'll see:
    - As the crew runs, every delegation is recorded automatically.
    - If a cyclic, repetitive, or runaway pattern surfaces, WARNING /
      CRITICAL alerts fire to stderr.
    - On crew completion, agentsonar_logs/run-<latest>/report.html is
      written.

This script needs an LLM API key because it actually runs CrewAI
agents. The AgentSonar wiring is the single line: AgentSonarListener().
"""
from agentsonar import AgentSonarListener
from crewai import Agent, Task, Crew

sonar = AgentSonarListener()  # one line, that's the integration

planner = Agent(
    role="planner",
    goal="Plan a small project",
    backstory="A meticulous planner.",
    allow_delegation=True,
)

researcher = Agent(
    role="researcher",
    goal="Research details for the plan",
    backstory="A thorough researcher.",
    allow_delegation=True,
)

task = Task(
    description="Plan a 1-week trip to Paris.",
    expected_output="A day-by-day itinerary.",
    agent=planner,
)

crew = Crew(agents=[planner, researcher], tasks=[task])
result = crew.kickoff()
print(result)
