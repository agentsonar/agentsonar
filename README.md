# AgentSonar

**The coordination intelligence layer for multi-agent AI.**
*Detect, prevent, and optimize coordination across any framework — in real time.*

When agents get stuck in infinite loops, spam each other with
redundant delegations, or blow through a rate limit, standard
tracing tools show you a timeline AFTER the fact. AgentSonar
watches the conversation BETWEEN agents and surfaces the failure
as it's happening — in milliseconds, while your crew or graph is
still running.

Think **Sentry, but for multi-agent AI systems**.

**Detection today. Prevention, FinOps, and governance on the same graph
substrate — next up.** See [What's next](#whats-next).

---

## Install

```bash
pip install agentsonar               # custom orchestrators — no extras needed
pip install agentsonar[crewai]       # for CrewAI
pip install agentsonar[langgraph]    # for LangGraph / LangChain
pip install agentsonar[all]          # crewai + langgraph
# OpenAI Agents SDK native adapter: shipping next (see What's next below)
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

**Custom orchestrator** (hand-rolled Python, subprocess pipelines, Celery DAGs):

```python
from agentsonar import monitor_orchestrator
sonar = monitor_orchestrator()
sonar.delegation(source="planner", target="researcher")
# ...run your agents normally...
sonar.shutdown()
```

That's the whole API. No accounts, no API keys, zero config required.

## What's detected today

Three coordination failure classes currently supported:

- **Cyclic delegation** — agents stuck in a loop (reviewer never
  approves, planner always says "revise", etc.)
- **Repetitive delegation** — one agent hammering another without
  making progress
- **Resource exhaustion** — runaway event throughput that would
  burn through your token budget if left unchecked

All three fire as structured alerts in real-time via stderr, a
JSONL timeline, a human-readable alerts log, and a standalone HTML
report you can email or attach to a bug ticket.

<a id="whats-next"></a>
## What's next

AgentSonar today ships **Detection**. The substrate it runs on — a
first-class coordination graph with stable cross-run fingerprints and
framework-agnostic adapters — was built so the same primitive powers a
handful of adjacent products. The sequencing:

| Next | Rough timing | What it unlocks |
|---|---|---|
| **OpenAI Agents SDK** native adapter | ~2–3 weeks | Same one-import integration you already get on CrewAI / LangGraph. For OpenAI SDK users today, the [custom-orchestrator adapter](https://pypi.org/project/agentsonar/) works as a bridge. |
| **Prevent Mode** | ~4 weeks | Circuit breakers on detected cycles, per-edge budget caps. The difference between *"alerting on the $47K loop"* and *"killing it at $38."* Moves AgentSonar from debugger to runtime control plane. |
| **Cost attribution** (FinOps) | ~6 weeks | Token cost per agent AND per delegation edge. Answers *"which coordination pattern burned the most this week?"* without leaving the tool. |
| **Dynamic-delegation tracking** | ~8 weeks | Instrument runtime handoff patterns (e.g. OpenAI Agents SDK handoffs, `delegate_to_agent` tools) that static adapters under-capture today. |
| **Governance / audit trails** | longer | EU AI Act Article 12 logs, SOC 2 decision lineage — the compliance tier enterprises will need once the August 2026 EU enforcement date hits. |

Same graph, different products. The goal is closer to what **Datadog**
did with metrics+tags (20+ products on one data model) or **Sentry**
did with its event schema than to what a one-trick loop detector would
look like.

If there's a specific detector, integration, or expansion area on
this list you'd want moved up, [open an
issue](https://github.com/agentsonar/agentsonar/issues/new?template=feature_request.yml)
— feature priority is driven by real user requests, not a roadmap
committee.

## Validated against frontier models

Skeptical that top-tier models like Claude Opus 4.6 or Gemini
actually get stuck in loops? They do — and smarter models make it
*worse*, not better, because a more capable reviewer finds more
subtle issues to flag on every pass. We reproduced three
coordination-failure scenarios (cyclic delegation, repetitive
delegation, spawn explosion) on real LangGraph workloads running
Sonnet 4 and Opus 4.6 with natural non-rigged prompts. AgentSonar
flagged each one in real time.

→ Full scenarios and alert output:
**[`docs/VALIDATION.md`](docs/VALIDATION.md)**

## What the output looks like

Every run produces a self-contained HTML report — no external CSS
or JavaScript, no network requests, dark mode that respects your
system preference. Two top-level tabs organize the view:

**1. Coordination Failures** — the primary signal. One card per
detected failure with severity badge, failure class (hover for a
definition), fingerprint, and expandable topology / thresholds /
provider-error / downstream-impact blocks. Filter chips at the top
let you narrow to Critical or Warning with one click.

![Coordination Failures tab — the primary signal, Sentry-style](docs/images/coordination-failures.png)

**2. Session Activity** — INFO-level context, always one click away.
Two sub-tabs switch between lenses on the same run:

- **Edge Activity** — every delegation edge the graph saw, with fire
  count and severity attribution. Red border = edge involved in a
  critical alert, no border = clean. Scans in seconds, even on
  hundred-event sessions.
- **Chronological Log** — raw event stream with timestamps. Rows
  color-coded where an alert fired: light red for critical, light
  orange for warning. Lets you see *when* coordination broke relative
  to surrounding traffic.

![Session Activity tab — Edge Activity view](docs/images/session-activity.png)

The "Coordination Failures — Raw JSON" drop-down at the bottom of
every report carries the same payload as `report.json` — copy it
straight into a dashboard or CI gate without opening a second file.

All four output files land in a per-run session directory under
`agentsonar_logs/`:

| File | Written | Purpose |
|---|---|---|
| `timeline.jsonl` | **Live — flushed on every event** | Every event, one JSON object per line. Tail with `tail -f` to watch what's happening as your crew runs. |
| `alerts.log` | **Live — flushed on every alert** | Signal-only, human-readable. The "just show me the problems" view. |
| `report.json` | On `shutdown()` | Structured summary report, deduped + inhibited. Pipe into your dashboard. |
| `report.html` | On `shutdown()` | The standalone two-tab HTML report shown above. |

The two `.jsonl` / `.log` files mean you don't have to wait for
your crew to finish to see what went wrong. Open a second terminal
and `tail -f agentsonar_logs/<latest>/timeline.jsonl` — coordination
failures surface the moment they happen.

## TypeScript / Open Multi-Agent

For [Open Multi-Agent (OMA)](https://github.com/JackChen-me/open-multi-agent) — a TypeScript multi-agent framework by Jack Chen — there's a sibling package `@agentsonar/oma` that bridges OMA's task graph and trace events to a local AgentSonar Python sidecar. Same detection engine, same HTML report, TypeScript-idiomatic install.

```bash
npm install @agentsonar/oma
pip install agentsonar
```

→ Full docs: [`github.com/agentsonar/agentsonar-oma`](https://github.com/agentsonar/agentsonar-oma)

## Current status

**Closed beta, expanding.** Deployed across six design partners spanning
CrewAI, LangGraph, custom Python orchestrators, and Open Multi-Agent
(TypeScript). Python SDK shipping on PyPI, Apache-2.0 licensed. OpenAI
Agents SDK native adapter in active development; see
[What's next](#whats-next) for the full sequence.

Source repository is currently private during the beta. This public
repo exists for:

- **Issues tab** — file bug reports, feature requests, and
  questions. Maintainers respond here.
- **Discussions** — general feedback, integration questions,
  show-and-tell.
- **Release notes** — see [`CHANGELOG.md`](CHANGELOG.md).

If you'd like to be considered as a design partner, open an issue
describing your multi-agent workload and we'll follow up.

## Contact / feedback

We read everything. Reach out whichever way fits your question:

- **Open an issue** — fastest, public, searchable by other users who
  may hit the same thing. Structured templates for
  [bug reports](https://github.com/agentsonar/agentsonar/issues/new?template=bug_report.yml),
  [feature requests](https://github.com/agentsonar/agentsonar/issues/new?template=feature_request.yml),
  and [general feedback or questions](https://github.com/agentsonar/agentsonar/issues/new?template=feedback.yml).
  Maintainers respond here.
- **Email** — <agentsonarai@gmail.com> for private feedback, design
  partner inquiries, security reports, or anything that doesn't fit
  a public issue.

## Links

- **PyPI:** <https://pypi.org/project/agentsonar/>
- **Validation on frontier models:** [`docs/VALIDATION.md`](docs/VALIDATION.md)
- **Changelog:** [`CHANGELOG.md`](CHANGELOG.md)

## License

Apache-2.0
