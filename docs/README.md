# AgentSonar Documentation

This folder is the deep-dive companion to the project [README](../README.md).
The README answers *"is this for me + how do I start?"*, these docs answer
*"how do I actually use it?"*

## Start here

New to AgentSonar? Read these in order:

1. [**Concepts**](concepts.md): what's a coordination failure, in plain English. Read this if you're not sure what AgentSonar even detects.
2. [**Quick start by adapter**](#adapters-by-framework): pick the adapter for your stack and follow its setup.
3. [**Prevent Mode**](prevent-mode.md): turn on auto-stop for runaway loops.

## Adapters by framework

| Framework | Adapter | Doc |
|---|---|---|
| Your own Python code / any framework | `monitor_orchestrator()` | [adapters/custom-python.md](adapters/custom-python.md) |
| CrewAI | `AgentSonarListener` | [adapters/crewai.md](adapters/crewai.md) |
| LangGraph / LangChain | `monitor()` | [adapters/langgraph.md](adapters/langgraph.md) |
| Open Multi-Agent (OMA, TypeScript) | `@agentsonar/oma` | [adapters/oma.md](adapters/oma.md) |

If your framework isn't listed, the [Python adapter](adapters/custom-python.md)
covers it, works with any orchestrator that runs in Python.

## Reference

- [**Configuration**](configuration.md): every config knob, organized by group, with defaults
- [**Prevent Mode**](prevent-mode.md): opt-in auto-stop: how it works, the three opt-in shapes, troubleshooting
- [**Validation**](VALIDATION.md): alert output on real frontier-model workloads
- [**FAQ**](faq.md): common questions, including "why am I seeing X but not Y?"

## Examples

Real scenarios with concrete dollar pain, copy-paste runnable:

- [Reviewer never approves](examples/reviewer-never-approves.md): the canonical $50→$47K loop
- [Manager hammering one worker](examples/manager-hammering-worker.md): repetitive_delegation
- [Runaway agent spawn](examples/runaway-agent-spawn.md): resource_exhaustion

## Contributing to docs

Spotted a mistake or have a clearer phrasing? Issues and PRs welcome on
[the public repo](https://github.com/agentsonar/agentsonar). Docs PRs
are reviewed quickly, small wording fixes often merge same-day.
