# Example: the reviewer that never approves

The canonical multi-agent failure. Two agents in a loop, polite, productive-looking, and quietly burning thousands of dollars.

## The setup

You build a content pipeline with two LLMs:

1. A `generator` that drafts a piece of content.
2. A `reviewer` that reads the draft and either approves it or sends back feedback.

Standard pattern. Looks like this:

```python
state = "initial draft"
while True:
    draft   = generator.run(state)
    review  = reviewer.run(draft)
    if "APPROVED" in review:
        break
    state = review
```

## Why it goes wrong

The reviewer is doing its job too well. Every revision it receives, it finds something else to flag. New typo. Tone could be tighter. Missing citation. Could be more concise. Could be more detailed. The feedback is genuinely substantive each time. It also never converges.

This isn't theoretical. We've reproduced it on natural prompts with Claude Sonnet 4 and Opus 4.6. Smarter models make it worse, not better, because a more capable reviewer finds more subtle issues to flag on every pass.

## What you'll see in your bill

Conservative numbers, GPT-4-class pricing:

- Each rotation: roughly 2K input + 1.5K output tokens per agent, two agents per rotation.
- Cost per rotation: about $0.05 to $0.15 depending on model.
- 1,000 rotations overnight: $50 to $150.
- 10,000 rotations over a weekend: $500 to $1,500.
- A bug that loops a hosted batch job for several days: well into four figures.

The bill is convincingly distributed across many small calls. There's no single line that screams "stuck loop." That's the whole problem.

## What AgentSonar shows

Wire in the Custom Python adapter:

```python
from agentsonar import monitor_orchestrator

sonar = monitor_orchestrator()

state = "initial draft"
for _ in range(50):
    sonar.delegation(source="reviewer", target="generator")
    draft  = generator.run(state)

    sonar.delegation(source="generator", target="reviewer")
    review = reviewer.run(draft)
    if "APPROVED" in review:
        break
    state = review

sonar.shutdown()
```

After 5 rotations, AgentSonar fires:

```
[SONAR ...] WARNING cyclic_delegation: [reviewer -> generator -> reviewer] (5 rotations)
```

After 15:

```
[SONAR ...] CRITICAL cyclic_delegation: [reviewer -> generator -> reviewer] (15 rotations)
```

The HTML report card shows:

- Severity: CRITICAL
- Cycle path: `reviewer -> generator -> reviewer`
- Rotations observed: 15+
- Recommendation: inspect the agent at the start of the cycle (here, the reviewer) for an exit condition.

## How to stop it before the next call

Turn on Prevent Mode:

```python
from agentsonar import monitor_orchestrator, PreventError

sonar = monitor_orchestrator(config={
    "prevent": {"cyclic_delegation": True}
})

try:
    state = "initial draft"
    while True:
        sonar.delegation(source="reviewer", target="generator")
        draft  = generator.run(state)

        sonar.delegation(source="generator", target="reviewer")
        review = reviewer.run(draft)
        if "APPROVED" in review:
            break
        state = review

except PreventError as e:
    print(f"Stopped: {e.reason}")
    print(f"Cycle:   {' -> '.join(e.cycle_path)}")
    print(f"After:   {e.rotations} rotations")
    # ...escalate to a human, write to your incident channel, etc.

sonar.shutdown()
```

With default thresholds, the loop stops at rotation 15. With `prevent={"cyclic_delegation": {"max_rotations": 5}}`, it stops at rotation 5.

## How to actually fix it (so you don't need to keep tripping)

Three options, in order of how often they help:

1. **Add a hard rotation cap.** Most reviewer-never-approves loops have no business running more than 3 to 5 rotations. Hardcode that as a `for` loop, not a `while True`.
2. **Make the reviewer's exit condition explicit.** "If the draft is at least as good as the previous one, approve." Vague approval criteria leak into infinite review.
3. **Score, don't review.** Have the reviewer return a numeric score (0-10) and approve at >=8. Numeric thresholds converge; freeform "is this good enough?" doesn't.

AgentSonar catching the loop tells you the structural problem exists. The fix lives in your prompt or your control flow.

## Related

- [Prevent Mode walkthrough](../prevent-mode.md): all the trip thresholds and escape hatches.
- [Concepts](../concepts.md): why this is a "silent loop" between agents and not just "agent A is wrong."
- [Custom Python adapter](../adapters/custom-python.md): the universal way to wire AgentSonar into any Python loop.
