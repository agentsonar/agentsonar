# Concepts: what AgentSonar actually detects

This page is for anyone who saw "coordination intelligence for AI" and thought: *what does that even mean?*

If you've ever shipped a multi-agent system and seen tokens burn for minutes with no useful output — agents passing work back and forth, the same tool called over and over, no error, no signal — this page explains what AgentSonar catches and why a normal trace viewer didn't show you the problem.

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

## The failure modes AgentSonar catches today

### 1. Silent loops (the loop that won't end)

**Plain English:** two or more agents are passing the same work back and forth without making progress.

**Everyday analogy:** two coworkers stuck in a "you take it" / "no, you take it" exchange about a hot potato. The hot potato never gets eaten.

**Real example:** a `reviewer` agent that always finds something to nitpick, and a `generator` agent that always tries to fix the nitpick. The reviewer never approves. The generator never gets to ship. They burn tokens forever.

**Why it's expensive:** every loop iteration is two LLM calls. At Sonnet pricing (~$15 / million output tokens, ~$3 / million input), 200 rounds of a reviewer-generator loop with ~3K tokens per round is around $4. 2,000 rounds is around $40. Overnight unattended, you can rack up a four-figure bill on a single stuck loop.

**What AgentSonar shows:** a CRITICAL alert with the exact cycle path (`reviewer -> generator -> reviewer`), a rotation count, and a recommendation telling you which agent to inspect first.

### 2. Repeated tool calls (one agent hammering another)

**Plain English:** one agent keeps calling the same target agent over and over, even though the calls aren't making forward progress.

**Everyday analogy:** a manager who keeps reassigning the same task to the same employee with slightly different wording each time. Each version sounds like progress. None of it ships.

**Real example:** a `planner` that decomposes a task into subtasks, sends them all to a single `executor`, the executor fails or returns something the planner wants to revise, and the planner re-sends. The wording differs every round (so a string-match check would fail to spot it), but the structure is the same: planner -> executor, planner -> executor, planner -> executor.

**Why it's subtle:** there's no exact-string repetition. The text content keeps changing. Only a watcher that tracks the *shape* of agent traffic over time can spot it.

**What AgentSonar shows:** a repeated-call alert with the source and target agent, the firing frequency, and the time window over which the spike happened.

### 3. Runaway token / tool spend (the throughput spiral)

**Plain English:** the total volume of agent-to-agent calls suddenly spikes far past what your system normally produces.

**Everyday analogy:** one fire alarm misfires and triggers ten others, which trigger fifty more, and now the whole building is screaming.

**Real example:** a `manager` agent with a tool that lets it spawn child agents. A bug in the tool, or a hallucinated decision, causes it to spawn 50 children where it should have spawned 2. Each child spawns more. Within a minute the system is firing thousands of LLM calls.

**Why standard tracing misses it:** most tracing tools record events one at a time. They don't model rate. By the time a human notices the trace volume, the bill is already in the hundreds.

**What AgentSonar shows:** a runaway-spend alert when either a single agent-to-agent pair or the whole system crosses a configurable rate limit (default: 10 calls per pair or 200 calls total in any 180-second window).

The next five reach past agent-to-agent traffic into a single agent's *own* tool use and its session. Same idea, watch the shape: the "edge" is now a tool or the session, not another agent.

### 4. Redundant work (the same call, again and again)

**Plain English:** an agent calls the same tool with the exact same arguments over and over, getting nothing new back.

**Real example:** a coding agent re-reads the same file four times in one task, or re-runs the identical `grep` it ran a minute ago. Nothing changed in between, so every call returns the same bytes — pure wasted tokens and latency.

**What AgentSonar shows:** a `redundant_work` alert naming the tool and the repeat count. A write that changes the target resets the count, so a normal read → edit → read cycle never trips it.

### 5. Stuck or hung tool calls (the call that never returns)

**Plain English:** a tool starts and never finishes, and no error is ever raised.

**Everyday analogy:** dialing a number that just rings forever. You're not on hold, you're not rejected — you're stuck.

**Real example:** a hung MCP server, an HTTP request with no timeout, a stuck shell subprocess. The agent is blocked waiting on a result that will never arrive, and the session silently hangs.

**What AgentSonar shows:** an `agent_stall` alert for any tool call still pending past your timeout (default: warning at 120s, critical at 300s), with the tool name and how long it has been hanging.

### 6. Subagent explosion (the runaway fan-out)

**Plain English:** an agent spawns a swarm of subagents all at once.

**Real example:** a coordinator that should delegate to two researchers instead launches ten in parallel. Each is reasonable alone, but together they multiply the token bill and can stampede shared resources or rate limits.

**What AgentSonar shows:** a `subagent_explosion` alert when concurrent or bursty spawns cross your limit (default: 8 alive at once, or 10 spawned in 30s), with the count and the subagent types involved.

### 7. Failed-tool retry storms (hammering a dead path)

**Plain English:** a tool keeps failing and the agent keeps retrying it instead of stopping or routing around it.

**Real example:** an API that's down, or a command that errors on every run. The agent retries the identical call again and again, burning budget on a path that was never going to succeed.

**What AgentSonar shows:** a `cascade_failure` alert after N consecutive failures on the same tool (default: warning at 2, critical at 3), with the tool and the error streak.

### 8. Context-window cliff (the session that fills up)

**Plain English:** a long session fills the model's context window, and answer quality quietly degrades before the next autocompact.

**Real example:** hours into a session, the model starts forgetting decisions made earlier, repeating itself, or contradicting its own plan — not because it got dumber, but because the relevant context scrolled out of the window. Long-context research ("context rot") shows accuracy drops well before the window is technically full.

**What AgentSonar shows:** a `token_velocity_anomaly` alert as the session crosses a fraction of the model's window (default: warning at 50%, critical at 75%), read from the real token counts the model reports — so you can wrap up or start fresh before the cliff.

## Why standard logging and tracing miss this

Standard tools (LangSmith, OpenLLMetry, Sentry, Helicone, raw OpenAI logs) are great at recording **what happened**. They show you a timeline of LLM calls, with prompts, completions, tokens, and timestamps.

What they do not do, by default:

1. **Spot silent loops in real time.** Loops only become visible if you visualize the trace after the run ends. By then, the run cost what it cost.
2. **Spot repeated calls when the prompts differ.** A repeated-call pattern looks like 200 unrelated calls to a string-matcher. To AgentSonar, it's one pair of agents talking 200 times.
3. **Stop a run mid-flight.** Tracing tools observe. They don't intervene. If you want to stop a runaway loop before the next API call, you need a tool that participates in your runtime.

That's the gap AgentSonar fills. It watches the *shape* of your agent traffic as the run is happening, and offers an opt-in `PreventError` that can interrupt the run when a known-bad pattern crosses a threshold.

## Next steps

- **Quick start by adapter:** [`adapters/`](adapters/)
- **Turn on auto-stop:** [`prevent-mode.md`](prevent-mode.md)
- **Tune detection thresholds:** [`configuration.md`](configuration.md)
- **See real frontier-model alert output:** [`VALIDATION.md`](VALIDATION.md)
