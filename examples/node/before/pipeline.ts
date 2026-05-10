/**
 * BEFORE: a Researcher / Writer / Reviewer pipeline with no monitoring.
 *
 * Run:
 *     npm run before
 *
 * What you'll see:
 *     - 30 rotations finish with no errors and no warnings.
 *     - A printed "all done" line and a mocked cost number.
 *     - Nothing tells you the Reviewer never approved.
 *
 * This is the silent failure: agents stuck in a loop, work bouncing
 * between them, and your only signal is a token bill that arrives later.
 *
 * The mocked cost is based on Claude Sonnet 4.6 input pricing as of
 * 2026-05-09 ($3 / 1M input tokens, $15 / 1M output tokens). See:
 *     https://www.anthropic.com/pricing
 * We assume ~3,000 input + ~1,500 output tokens per agent call, three
 * agents per rotation, 30 rotations -> roughly $14.50 per run.
 */
const ROTATIONS = 30
const INPUT_TOKENS_PER_CALL = 3_000
const OUTPUT_TOKENS_PER_CALL = 1_500
const INPUT_PRICE_PER_M = 3.0    // Claude Sonnet 4.6 input ($/1M tokens)
const OUTPUT_PRICE_PER_M = 15.0  // Claude Sonnet 4.6 output ($/1M tokens)

function researcher(state: string): string {
  return state + ' research.'
}

function writer(state: string): string {
  return state + ' draft.'
}

function reviewer(state: string): string {
  // The reviewer never approves. It always asks for another revision.
  return state + ' needs more work.'
}

let state = 'topic: rate limiters'
for (let i = 0; i < ROTATIONS; i++) {
  state = researcher(state)
  state = writer(state)
  state = reviewer(state)
}

const calls = ROTATIONS * 3
const inputCost = (calls * INPUT_TOKENS_PER_CALL * INPUT_PRICE_PER_M) / 1_000_000
const outputCost = (calls * OUTPUT_TOKENS_PER_CALL * OUTPUT_PRICE_PER_M) / 1_000_000
const total = inputCost + outputCost

console.log(`${ROTATIONS} rotations completed.`)
console.log(`Mocked cost: $${total.toFixed(2)}`)
console.log('All done.')
