# AgentSonar

**Coordination intelligence for AI.**

Catch the multi-agent failure modes that tracing tools miss — silent loops between agents, the same agent being called over and over with the same task, and sudden traffic spikes between agents.

**Today, AgentSonar supports multi-agent systems** — any setup where two or more agents talk to each other and pass work along. Use it with **CrewAI, LangGraph, custom Python orchestrators, or Node / Electron orchestrators**. If your framework isn't directly supported yet, the custom-orchestrator path works with anything you've wired together yourself.

**Coming soon (other AI system shapes):**

- 🛣 Single agent with tools (function-calling, retrieval, code execution)
- 🛣 Single agent wired to MCP servers
- 🛣 RAG pipelines (retriever → re-ranker → generator)
- 🛣 Custom buses between agents

One install. No accounts. No remote dashboard.

[Website](https://www.agent-sonar.com) · [Discord](https://discord.gg/cPPD4xHe) · [PyPI](https://pypi.org/project/agentsonar/) · [npm](https://www.npmjs.com/package/agentsonar) · [Issues](https://github.com/agentsonar/agentsonar/issues)

---

## A scenario you've probably hit

You wire up three agents:

- A **Researcher** gathers source material.
- A **Writer** turns the research into a draft.
- A **Reviewer** checks the draft. If the Reviewer isn't happy, the draft goes back to the Researcher for another pass.

It's a classic multi-agent setup. But there's a hidden failure mode: **what if the Reviewer is never satisfied?**

The three agents keep handing work to each other. Forever. Your trace viewer shows hundreds of clean LLM calls — each one looks fine on its own. Tokens burn. The bill climbs. No one in the chain is checking whether the loop is actually making progress.

AgentSonar watches the *shape* of the traffic between your agents. The moment the Researcher → Writer → Reviewer → Researcher loop crosses the threshold you set, AgentSonar fires an alert. Open the HTML report and you see the loop drawn as a graph, the rotation count, and the exact moment it tripped. Turn on **Prevent Mode** and the run halts automatically before the next LLM call.

![AgentSonar HTML report showing a silent loop caught and stopped by Prevent Mode](docs/images/prevent-error.png)

---

## What it catches

### Detect (shipped)

- ✅ **Silent loops** — your Researcher gathers material and sends it to the Writer, the Writer drafts something and sends it to the Reviewer, the Reviewer flags an issue and sends it back to the Researcher. Round and round, forever. The Reviewer never approves. Tokens burn, no output ever ships.
- ✅ **Repeated agent calls** — your Writer asks the Researcher for the same thing 47 times in a row ("find competitor pricing", "find competitor pricing", "find competitor pricing"…). The Researcher returns the same answer each time. The Writer never moves on.
- ✅ **Traffic spikes between agents** — a sudden burst of agent-to-agent calls (the Writer fires off work to the Researcher 200 times in 30 seconds) that's wildly out of pattern with normal traffic, even if no single pair is repeating.

### Prevent (shipped, opt-in)

- ✅ **Auto-stop silent loops** — when a cycle between agents crosses the threshold you set, AgentSonar raises a typed `PreventError` exception. Your code catches it and stops the run before the next LLM call. (Today, Prevent Mode covers silent loops only — repeated calls and traffic spikes alert you, but won't auto-stop.)

→ Full walkthrough: [`docs/prevent-mode.md`](docs/prevent-mode.md)

### Coming soon

- 🛣 **Deadlocks** — two agents wait on each other and neither can move. The Researcher is waiting for the Writer's brief; the Writer is waiting for the Researcher to confirm scope. Both sit there forever.
- 🛣 **Agent stalling** — an agent goes quiet mid-task and never times out. The pipeline hangs and no error ever surfaces.
- 🛣 **Groundless response** — agent answers customer questions without consulting any tool.
- 🛣 **Retrieval thrash** — agentic RAG re-fetching the same content 20+ times.
- 🛣 **MCP retry loop** — agent retries a failing MCP server forever, ignoring errors.
- 🛣 **Cost runaway** — real-time projection: *"this cycle will cost $X if not stopped."*

…and many more coordination and silent failures we're tracking. If you want a specific failure mode added, [request a feature](https://github.com/agentsonar/agentsonar/issues/new?template=feature_request.yml) or [open an issue](https://github.com/agentsonar/agentsonar/issues/new/choose).

---

## Framework support

| Framework | Status |
|---|---|
| **Custom Python** (any framework, no orchestrator) | ✅ Shipped |
| **Custom Node / TypeScript** (any framework, no orchestrator) | ✅ Shipped |
| **LangGraph** | ✅ Shipped |
| **CrewAI** | ✅ Shipped (detect-only; auto-stop on the way) |
| **Electron / Node bus** (OMA sidecar) | ✅ Shipped |
| **OpenAI Agents SDK** | 🛣 Coming soon |
| **Anthropic Claude Agent SDK** | 🛣 Coming soon |
| **AutoGen** | 🛣 Coming soon |

If your framework isn't listed here, use the **Custom Python** or **Custom Node / TypeScript** path in the Quick Start below — both work with anything you've wired together yourself.

---

## Quick start

Pick the setup that matches your framework. Each card has the install command, the minimal wire-in, and a link to the full guide.

### LangGraph

```bash
pip install agentsonar[langgraph]
```

```python
from agentsonar import monitor

graph = monitor(your_graph.compile())   # one line — that's the whole change
graph.invoke({"input": "..."})
```

→ Full guide: [`docs/adapters/langgraph.md`](docs/adapters/langgraph.md)

### CrewAI

```bash
pip install agentsonar[crewai]
```

```python
from agentsonar import AgentSonarListener

listener = AgentSonarListener()       # auto-attaches to CrewAI's event bus
crew.kickoff()
listener.shutdown()
```

→ Full guide: [`docs/adapters/crewai.md`](docs/adapters/crewai.md)

### Custom Python (no framework, or any framework not listed)

```bash
pip install agentsonar
```

```python
from agentsonar import monitor_orchestrator

sonar = monitor_orchestrator()
# ...your code... whenever one agent hands off to another:
sonar.delegation(source="researcher", target="writer")
sonar.shutdown()
```

→ Full guide: [`docs/adapters/custom-python.md`](docs/adapters/custom-python.md)

### Node / Electron

```bash
npm install agentsonar
```

```javascript
import { AgentSonar } from 'agentsonar'

const sonar = new AgentSonar({})
sonar.delegation('researcher', 'writer')
await sonar.shutdown()
```

→ Full guide: [`docs/adapters/`](docs/adapters/) (Node-side adapter docs)

### After your run

```bash
open agentsonar_logs/run-<latest>/report.html
```

That's it. No API keys. No setup beyond the install.

---

## How AgentSonar is different from tracing

AgentSonar is a *failure detector*, not a *trace viewer*. Tracing tools show you what happened. AgentSonar tells you when something is going wrong, while it's still going wrong — and optionally stops it.

---

## Install

### Python

```bash
pip install agentsonar               # works with any Python framework
pip install agentsonar[crewai]       # CrewAI
pip install agentsonar[langgraph]    # LangGraph / LangChain
pip install agentsonar[all]          # all of the above
```

### Node / Electron

```bash
npm install agentsonar
```

> **Heads up:** AgentSonar sends one anonymous session-start event per run (install ID, version, OS, adapter, no agent content). On by default, opt-out with `AGENTSONAR_TELEMETRY=off` or `DO_NOT_TRACK=1`. [What's collected and why](https://www.agent-sonar.com/telemetry).

---

## Examples (5 minutes, no API key)

Three runnable before/after examples in this repo. Each one is a complete folder with its own `README.md` that walks you through the run step by step. **Open the folder's README first — it has the exact commands.**

### How to get them

**Option 1 — clone the whole repo (recommended):**

```bash
git clone https://github.com/agentsonar/agentsonar-public.git
cd agentsonar-public/examples/custom-python   # or langgraph / node
# then follow that folder's README.md
```

**Option 2 — copy individual files from GitHub:** open the folder link below, click any file, hit the "Raw" button, and copy the contents into your own project.

### The three examples

| Example | Stack | What it shows | Folder README |
|---|---|---|---|
| **Custom Python** | Plain Python, no framework | Researcher → Writer → Reviewer silent loop. Run `before/pipeline.py`, see no signal. Run `after/detect.py`, see the loop caught. Run `after/prevent.py`, see it stopped. | [`examples/custom-python/README.md`](examples/custom-python/README.md) |
| **LangGraph** | Python + LangGraph | Same scenario, expressed as a LangGraph state graph. | [`examples/langgraph/README.md`](examples/langgraph/README.md) |
| **Node / TypeScript** | Node + tsx | Same scenario in TypeScript. `npm run before` (silent burn), `npm run detect` (loop caught), `npm run prevent` (auto-stopped). | [`examples/node/README.md`](examples/node/README.md) |

Every folder also includes a one-page `what-changed.md` showing the literal one-line diff that adds AgentSonar — handy for reviewing what actually changes in your own code.

---

## Using the OMA sidecar?

The `@agentsonar/oma` adapter still works. Its repo lives at [`agentsonar-oma`](https://github.com/agentsonar/agentsonar-oma). The native `agentsonar` package covers most use cases directly; if you're starting fresh, use `agentsonar`.

---

## Documentation

| Topic | Where |
|---|---|
| **Start here**: full docs index | [`docs/README.md`](docs/README.md) |
| **Adapters**: per-framework setup | [`docs/adapters/`](docs/adapters/) |
| **Prevent Mode**: opt-in auto-stop | [`docs/prevent-mode.md`](docs/prevent-mode.md) |
| **Configuration**: every config knob | [`docs/configuration.md`](docs/configuration.md) |
| **Concepts**: what AgentSonar catches, in plain English | [`docs/concepts.md`](docs/concepts.md) |
| **Validation**: how the engine is tested | [`docs/VALIDATION.md`](docs/VALIDATION.md) |
| **FAQ** | [`docs/faq.md`](docs/faq.md) |

Release notes: [`CHANGELOG.md`](CHANGELOG.md).

---

## Status

**Closed beta, expanding.** Apache-2.0 licensed.

This public repo exists for:

- **Issues**: bug reports, feature requests, questions ([templates](https://github.com/agentsonar/agentsonar/issues/new/choose))
- **Discussions**: feedback, integration questions, show-and-tell

If you'd like to be considered as a design partner, open an issue describing your multi-agent workload and we'll follow up.

---

## Contact

- **Open an issue**: fastest, public, searchable: [bug](https://github.com/agentsonar/agentsonar/issues/new?template=bug_report.yml) · [feature request](https://github.com/agentsonar/agentsonar/issues/new?template=feature_request.yml) · [feedback](https://github.com/agentsonar/agentsonar/issues/new?template=feedback.yml)
- **Email**: [agentsonarai@gmail.com](mailto:agentsonarai@gmail.com) for private feedback, design partner inquiries, security reports
- **Discord**: [discord.gg/cPPD4xHe](https://discord.gg/cPPD4xHe)

## License

Apache-2.0
