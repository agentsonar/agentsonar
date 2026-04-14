# AgentSonar

**Detect coordination failures in multi-agent AI systems — in real time.**

When agents get stuck in infinite loops, spam each other with
redundant delegations, or blow through a rate limit, standard
tracing tools show you a timeline AFTER the fact. AgentSonar
watches the conversation BETWEEN agents and surfaces the failure
as it's happening — in milliseconds, while your crew or graph is
still running.

Think **Sentry, but for multi-agent AI systems**.

---

## Install

```bash
pip install agentsonar[crewai]      # for CrewAI
pip install agentsonar[langgraph]   # for LangGraph / LangChain
pip install agentsonar[all]         # both
```

Available on PyPI: **[pypi.org/project/agentsonar](https://pypi.org/project/agentsonar/)**

## Two-line integration

**CrewAI:**

```python
from agentsonar import AgentSonarListener
sonar = AgentSonarListener()
# ...run your crew normally. Detection happens automatically.
```

**LangGraph / LangChain:**

```python
from agentsonar import monitor
graph = monitor(graph)
result = graph.invoke(input)
```

That's the whole API. No accounts, no API keys, zero config required.

## What gets detected

Three coordination failure classes currently supported:

- **Cyclic delegation** — agents stuck in a loop (reviewer never
  approves, planner always says "revise", etc.)
- **Repetitive delegation** — one agent hammering another without
  making progress
- **Resource exhaustion** — runaway event throughput that would
  burn through your token budget if left unchecked

All three fire as structured alerts in real-time via stderr, JSONL
timeline, and a standalone HTML report that you can email or attach
to a bug ticket.

## Current status

**Closed beta.** Actively deployed in the environments of six design
partners. Python SDK only, Apache-2.0 licensed, published to PyPI.

Source repository is currently private during the beta. This public
repo exists for:

- **Issues tab** — file bug reports, feature requests, and
  questions. Maintainers respond here.
- **Discussions** — general feedback, integration questions,
  show-and-tell.
- **Release notes** — see [`CHANGELOG.md`](CHANGELOG.md).

If you'd like to be considered as a design partner, open an issue
describing your multi-agent workload and we'll follow up.

## Links

- **PyPI:** <https://pypi.org/project/agentsonar/>
- **Issues:** [github.com/agentsonar/agentsonar/issues](https://github.com/agentsonar/agentsonar/issues)
- **Changelog:** [`CHANGELOG.md`](CHANGELOG.md)

## License

Apache-2.0
