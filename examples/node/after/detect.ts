/**
 * AFTER: same pipeline + AgentSonar (detection only).
 *
 * Run:
 *     npm install
 *     npm run detect
 *
 * What you'll see:
 *     - WARNING fires at rotation 5, CRITICAL at rotation 15
 *       (streamed to stderr).
 *     - A run directory under agentsonar_logs/ containing timeline.jsonl,
 *       alerts.log, report.json, and report.html.
 *     - The same mocked cost as before/pipeline.ts, but now you also know
 *       something went wrong.
 *
 * This script needs zero LLM credits. We hardcode the agent handoffs to
 * show exactly what AgentSonar would record during a real run. In your
 * production code, you'd call sonar.delegation() right next to your
 * actual LLM calls.
 */
import { AgentSonar } from 'agentsonar'

const ROTATIONS = 30
const INPUT_TOKENS_PER_CALL = 3_000
const OUTPUT_TOKENS_PER_CALL = 1_500
const INPUT_PRICE_PER_M = 3.0
const OUTPUT_PRICE_PER_M = 15.0

const sonar = new AgentSonar({}, 'researcher-writer-reviewer')

// Three agents in a silent loop: researcher -> writer -> reviewer -> researcher.
for (let i = 0; i < ROTATIONS; i++) {
  sonar.delegation('researcher', 'writer')
  // ...your writer agent runs here...

  sonar.delegation('writer', 'reviewer')
  // ...your reviewer agent runs here...

  sonar.delegation('reviewer', 'researcher')
  // ...your researcher agent runs here...
}

sonar.shutdown()

const calls = ROTATIONS * 3
const inputCost = (calls * INPUT_TOKENS_PER_CALL * INPUT_PRICE_PER_M) / 1_000_000
const outputCost = (calls * OUTPUT_TOKENS_PER_CALL * OUTPUT_PRICE_PER_M) / 1_000_000
const total = inputCost + outputCost
console.log(`${ROTATIONS} rotations completed.`)
console.log(`Mocked cost: $${total.toFixed(2)}`)
console.log('Done. Open agentsonar_logs/run-<latest>/report.html in a browser.')
