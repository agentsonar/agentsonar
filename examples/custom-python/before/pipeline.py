"""
BEFORE: a Researcher / Writer / Reviewer pipeline with no monitoring.

Run:
    python pipeline.py

What you'll see:
    - 30 rotations finish with no errors and no warnings.
    - A printed "all done" line and a mocked cost number.
    - Nothing tells you the Reviewer never approved.

This is the silent failure: agents stuck in a loop, work bouncing
between them, and your only signal is a token bill that arrives later.

The mocked cost is based on Claude Sonnet 4.6 input pricing as of
2026-05-09 ($3 / 1M input tokens). See:
    https://www.anthropic.com/pricing
We assume ~3,000 input tokens per agent call, two agents per rotation,
30 rotations -> 30 * 2 * 3000 = 180,000 tokens -> ~$0.54 per run on
input alone. Output tokens at $15 / 1M with ~1,500 output tokens per
call push the total to roughly $14.50 per run.
"""

ROTATIONS = 30
INPUT_TOKENS_PER_CALL = 3_000
OUTPUT_TOKENS_PER_CALL = 1_500
INPUT_PRICE_PER_M = 3.00     # Claude Sonnet 4.6 input ($/1M tokens)
OUTPUT_PRICE_PER_M = 15.00   # Claude Sonnet 4.6 output ($/1M tokens)


def researcher(state):
    return state + " research."


def writer(state):
    return state + " draft."


def reviewer(state):
    # The reviewer never approves. It always asks for another revision.
    return state + " needs more work."


state = "topic: rate limiters"
for _ in range(ROTATIONS):
    state = researcher(state)
    state = writer(state)
    state = reviewer(state)

calls = ROTATIONS * 3
input_cost = calls * INPUT_TOKENS_PER_CALL * INPUT_PRICE_PER_M / 1_000_000
output_cost = calls * OUTPUT_TOKENS_PER_CALL * OUTPUT_PRICE_PER_M / 1_000_000
total = input_cost + output_cost

print(f"{ROTATIONS} rotations completed.")
print(f"Mocked cost: ${total:,.2f}")
print("All done.")
