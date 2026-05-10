/**
 * AFTER: same pipeline + AgentSonar with Prevent Mode (auto-stop).
 *
 * Run:
 *     npm install
 *     npm run prevent
 *
 * What you'll see:
 *     - WARNING fires at rotation 5.
 *     - At rotation 10, PreventError throws and the loop stops.
 *     - The catch block prints the cycle path and rotation count.
 *     - Mocked cost is roughly one third of detect.ts's because the loop
 *       stopped before burning the rest of the rotations.
 *
 * Compare this to detect.ts: only difference is the prevent={...} config
 * and the try/catch around the loop.
 */
import { AgentSonar, PreventError } from 'agentsonar'

const INPUT_TOKENS_PER_CALL = 3_000
const OUTPUT_TOKENS_PER_CALL = 1_500
const INPUT_PRICE_PER_M = 3.0
const OUTPUT_PRICE_PER_M = 15.0

const sonar = new AgentSonar(
  {
    // Stop the silent loop at exactly 10 rotations.
    prevent: { cyclicDelegation: { maxRotations: 10 } },
  },
  'researcher-writer-reviewer',
)

let rotationsDone = 0
try {
  while (true) {
    sonar.delegation('researcher', 'writer')
    sonar.delegation('writer', 'reviewer')
    sonar.delegation('reviewer', 'researcher')
    rotationsDone += 1
  }
} catch (err) {
  if (err instanceof PreventError) {
    console.log(`Stopped: ${err.reason}`)
    console.log(`Cycle:   ${err.cyclePath.join(' -> ')}`)
    console.log(`After:   ${err.rotations} rotations (severity ${err.severity})`)
  } else {
    throw err
  }
}

sonar.shutdown()

const calls = rotationsDone * 3
const inputCost = (calls * INPUT_TOKENS_PER_CALL * INPUT_PRICE_PER_M) / 1_000_000
const outputCost = (calls * OUTPUT_TOKENS_PER_CALL * OUTPUT_PRICE_PER_M) / 1_000_000
const total = inputCost + outputCost
console.log(`${rotationsDone} rotations completed before auto-stop.`)
console.log(`Mocked cost: $${total.toFixed(2)}`)
console.log("Saved versus the 'before' run: roughly $9.67 of the $14.50 baseline.")
