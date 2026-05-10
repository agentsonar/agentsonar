# Validation

AgentSonar's detection engine is validated via 663 unit tests, property-based fuzzing, and a 10,000-case differential fuzz suite against a reference implementation. Test code is open under `agentsonar-sdk/tests/` and `agentsonar-npm/tests/`.

## Validated against frontier models

We reproduced the failure modes AgentSonar catches on real LangGraph workloads running Claude Sonnet 4 and Claude Opus 4.6 with natural, non-rigged prompts. AgentSonar flagged each one in real time:

- **Silent loops:** a 3-node `researcher → writer → reviewer` graph that never reaches END. Caught at rotation 5 (WARNING) and rotation 15 (CRITICAL).
- **Repeated tool calls:** a `planner → coder → qa_reviewer → planner` workflow where each round's feedback is genuinely different but the system never converges. Caught when the repeated-call signal crossed sensitivity thresholds.
- **Runaway token / tool spend:** a coordinator that pushes new sub-tasks onto its own queue forever. Caught the moment traffic crossed the rate limit.

## Why this works on any frontier model

AgentSonar detects the *shape* of a failure, not the content of any message. That's why it still works when your agents are smart enough to produce genuinely different, thoughtful feedback on every pass — and why a more capable model can actually make these failures *worse*, since a more capable reviewer finds more subtle issues to flag.

None of the demo prompts were engineered to fail. The failures are emergent: they only exist in the interaction pattern, not in any single agent's behavior.

---

Back to the [main README](../README.md).
