# Concepts: what AgentSonar actually detects

This page is for anyone who saw "coordination intelligence for multi-agent AI" and thought: *what does that even mean?*

If you've ever built an agent loop and watched your OpenAI bill keep climbing while nothing useful seemed to be happening, this page will tell you exactly what AgentSonar catches and why your existing logs probably missed it.

## What is "multi-agent" in the first place?

A multi-agent system is any setup where two or more LLM calls hand work off to each other. That's it. Some examples:

- A `planner` LLM that writes a plan, then a `researcher` LLM that fills in the plan, then a `writer` LLM that drafts the final output.
- A `reviewer` LLM that reads what a `generator` LLM wrote, sends back feedback, and the generator tries again.
- A `manager` agent that splits one task into 10 subtasks and fires them off to 10 worker LLMs.

You don't need a framework to have a multi-agent system. A `for` loop with two `client.chat.completions.create()` calls inside is a multi-agent system. Frameworks like CrewAI, LangGraph, AutoGen, and the OpenAI Agents SDK just add scaffolding around the same basic idea.

## What is "coordination"?

Coordination is the part where one agent hands its work to another. Every time agent A's output becomes agent B's input, that's a coordination event. AgentSonar calls this a **delegation**.

If you draw arrows between the agents in your system, those arrows are the delegations. The whole thing is a graph: nodes are agents, edges are who-talks-to-whom.

```
planner -> researcher -> writer -> reviewer
                           ^          |
                           +----------+   <- this is the loop
```

When agents talk in a loop like the one above, the system can keep running long after the actual useful work is done. That's a coordination failure.

## The three failure modes AgentSonar catches today

### 1. Cyclic delegation (the loop that won't end)

**Plain English:** two or more agents are passing the same work back and forth without making progress.

**Everyday analogy:** two coworkers stuck in a "you take it" / "no, you take it" exchange about a hot potato. The hot potato never gets eaten.

**Real example:** a `reviewer` agent that always finds something to nitpick, and a `generator` agent that always tries to fix the nitpick. The reviewer never approves. The generator never gets to ship. They burn tokens forever.

**Why it's expensive:** every loop iteration is two LLM calls. At Sonnet pricing (~$15 / million output tokens, ~$3 / million input), 200 rounds of a reviewer-generator loop with ~3K tokens per round is around $4. 2,000 rounds is around $40. Overnight unattended, you can rack up a four-figure bill on a single stuck loop.

**What AgentSonar shows:** a CRITICAL alert with the exact cycle path (`reviewer -> generator -> reviewer`), a rotation count, and a recommendation telling you which agent to inspect first.

### 2. Repetitive delegation (one agent hammering another)

**Plain English:** one agent keeps calling the same target agent over and over, even though the calls aren't making forward progress.

**Everyday analogy:** a manager who keeps reassigning the same task to the same employee with slightly different wording each time. Each version sounds like progress. None of it ships.

**Real example:** a `planner` that decomposes a task into subtasks, sends them all to a single `executor`, the executor fails or returns something the planner wants to revise, and the planner re-sends. The wording differs every round (so a string-match check would fail to spot it), but the structure is the same: planner -> executor, planner -> executor, planner -> executor.

**Why it's subtle:** there's no exact-string repetition. The text content keeps changing. Only a structural watcher counting traffic on a specific edge over time can spot it.

**What AgentSonar shows:** an alert tagged `repetitive_delegation` with the source and target agent, the firing frequency, and the time window over which the spike happened.

### 3. Resource exhaustion (the runaway throughput)

**Plain English:** the total volume of agent-to-agent calls suddenly spikes far past what your system normally produces.

**Everyday analogy:** one fire alarm misfires and triggers ten others, which trigger fifty more, and now the whole building is screaming.

**Real example:** a `manager` agent with a tool that lets it spawn child agents. A bug in the tool, or a hallucinated decision, causes it to spawn 50 children where it should have spawned 2. Each child spawns more. Within a minute the system is firing thousands of LLM calls.

**Why standard tracing misses it:** most tracing tools record events one at a time. They don't model rate. By the time a human notices the trace volume, the bill is already in the hundreds.

**What AgentSonar shows:** a `resource_exhaustion` alert when either a single edge or the whole graph crosses a configurable rate limit (default: 10 events per edge or 200 events total in any 180-second window).

## Why standard logging and tracing miss this

Standard tools (LangSmith, OpenLLMetry, Sentry, Helicone, raw OpenAI logs) are great at recording **what happened**. They show you a timeline of LLM calls, with prompts, completions, tokens, and timestamps.

What they do not do, by default:

1. **Detect cycles in the call graph in real time.** Cycles only become visible if you visualize the trace after the run ends. By then, the run cost what it cost.
2. **Spot structurally repetitive traffic where the prompts differ.** A repetitive-delegation pattern looks like 200 unrelated calls to a string-matcher. To a graph watcher, it's one edge firing 200 times.
3. **Stop a run mid-flight.** Tracing tools observe. They don't intervene. If you want to stop a runaway loop before the next API call, you need a tool that participates in your runtime.

That's the gap AgentSonar fills. It watches the same agent traffic, but with three structural detectors that fire as the run is happening, plus an opt-in `PreventError` that can interrupt the run when a known-bad pattern crosses a threshold.

## Next steps

- **Quick start by adapter:** [`adapters/`](adapters/)
- **Turn on auto-stop:** [`prevent-mode.md`](prevent-mode.md)
- **Tune detection thresholds:** [`configuration.md`](configuration.md)
- **See real frontier-model alert output:** [`VALIDATION.md`](VALIDATION.md)
