# Before: no AgentSonar

This is what you have today. Three agents, a silent loop, no signal.

Run:

    python pipeline.py

You'll see:

    30 rotations completed.
    Mocked cost: $14.50
    All done.

No alerts. No warnings. Nothing tells you the Reviewer never approved. The only signal is the token bill that arrives later.

The mocked cost cites Claude Sonnet 4.6 pricing as of 2026-05-09 ($3 / 1M input tokens, $15 / 1M output tokens). See [anthropic.com/pricing](https://www.anthropic.com/pricing).

Now compare with [`../after/`](../after/).
