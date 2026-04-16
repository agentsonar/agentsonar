# Validation: coordination failures on frontier models

> *"But top-tier models like Claude Opus 4.6 or Gemini never end up
> in loops."*

They do. And smarter models actually make this **worse**, not
better.

A more capable reviewer finds more subtle issues to flag, so the
reject-and-retry cycle runs longer before the orchestrator gives
up. More capable planners break tasks into more sub-tasks, which
grows the pending queue exponentially. More capable coders fix
issue A in a way that reveals issue B, so each round's feedback
is genuinely different — something string-matching can't detect
but a graph-topology watcher can.

**Capability doesn't prevent emergent coordination failures. The
failure lives in the graph topology, not in any one agent's
reasoning.**

This document walks through three real failure modes we
reproduced on Claude Sonnet 4 and Claude Opus 4.6, running inside
production LangGraph workloads with natural, non-rigged prompts.

## The three validated scenarios

### Scenario 1 — Cyclic delegation

**Workload:** a 3-node LangGraph writing a technical blog post
comparing AI agent frameworks.

```
researcher → writer → reviewer ─┬→ researcher (cycle)
                                └→ END        (never reached)
```

**Why it fails on frontier models:** review is inherently
open-ended. A rigorous reviewer checking technical accuracy,
missing perspectives, clarity, and examples will *always* find
something to improve. The more capable the model, the more
subtle issues it finds. The reviewer is not buggy — it's doing
its job well. The problem is that "doing its job well" means
never sending the END signal.

**The paradox:** the better the model, the worse this failure
gets.

**What AgentSonar flagged (Claude Opus 4.6 run):**

- ⚠ `WARNING cyclic_delegation` at rotation 5
- Cycle path: `reviewer → researcher → writer → reviewer`
- Agents involved: `{researcher, writer, reviewer}`
- Per-edge frequency: 5 on every edge in the cycle
- Fingerprint stable across re-runs (same failure → same ID)

### Scenario 2 — Repetitive delegation (the subtle one)

**Workload:** a 3-node LangGraph implementing a Python rate
limiter with sliding-window, token-bucket, and leaky-bucket
variants.

```
planner → coder → qa_reviewer ─┬→ planner (needs revision)
                                └→ END     (never ships)
```

**Why it fails:** QA checks 6 dimensions. Fixing issue A reveals
issue B. Each round's feedback is **genuinely different** — this
is not the same error repeated. The system IS making progress on
each specific issue. But the space of possible improvements is
effectively infinite, and no single agent has a global view of
"we've been at this for 20 rounds."

**Why this is hard to detect without graph topology:**
string-matching on error messages won't catch it. Each round's
feedback is novel prose. Only structural watchers — counting
edge frequencies over a sliding window — can spot "the planner
and coder have handed work back and forth 15 times in 60
seconds, something is wrong at the coordination layer."

**What AgentSonar flagged (Claude Opus 4.6 run):**

- ⚠ `WARNING repetitive_delegation` on `planner → coder`
- 🚨 `CRITICAL repetitive_delegation` as the edge continued to
  fire
- Per-window event count crossed both WARNING (event 11) and
  CRITICAL (event 15) thresholds

### Scenario 3 — Spawn explosion (resource exhaustion)

**Workload:** a LangGraph researching quantum computing
comprehensively.

```
coordinator → researcher → coordinator (loop, queue grows)
           └→ synthesizer → END         (never reached)
```

**Why it fails:** each researcher identifies sub-subtopics and
pushes them onto the coordinator's pending queue. The
coordinator never says "done" because there are always pending
subtopics to dispatch. Each individual agent is doing its job
perfectly — the failure is that no agent has a global view of
resource consumption.

**What AgentSonar flagged:**

- 🚨 `CRITICAL resource_exhaustion` on the hottest edge
- Circuit-breaker severity fires when the sliding-window event
  rate crosses the per-edge limit — before the bill arrives

## Why this works on any frontier model

**AgentSonar detects the structure of the failure, not the
content of the messages.**

Sonnet 4, Opus 4.6, Gemini 2.5 Pro, or any future frontier
model — the detection layer doesn't care. It's watching the
delegation graph, not the prose. That's why it still works when
your agents are smart enough to produce genuinely different,
genuinely thoughtful feedback on every pass.

None of the demo prompts were engineered to fail. Every agent
behaves reasonably. The failures are **emergent** — they only
exist in the interaction pattern, not in any single agent's
behavior. This is why graph-level detection beats
smarter-prompting as a mitigation strategy: you can't prompt
your way out of an emergent property.

## How we validated

All three scenarios were executed end-to-end against live
Anthropic APIs — Claude Sonnet 4 and Claude Opus 4.6 — inside
real LangGraph workloads. Every alert shown above came from a
real run, not synthetic test data. AgentSonar caught each
failure mode in real time, at the rotation counts and severity
levels documented.

## Takeaways

1. **Coordination failures are real even on frontier models.**
   Capability is not a mitigation. If anything, it extends the
   length of each failure loop.
2. **Graph topology is the right detection surface.** String
   matching on error messages fails on genuinely-different
   feedback every round. Counting edges in the interaction
   graph does not.
3. **The failure is emergent.** Every individual agent is
   rational. The bug is the conversation between them. That's
   why you need a watcher outside the agents, not smarter
   agents.

---

Back to the [main README](../README.md).
