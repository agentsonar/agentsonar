# Before: no AgentSonar

A LangGraph state graph with a node that loops back to itself. No monitoring.

Run:

    pip install langgraph
    python pipeline.py

You'll see:

    30 rotations completed.
    Mocked cost: $14.50
    All done.

No alerts. No warnings. Nothing tells you the reviewer never approved.

The mocked cost cites Claude Sonnet 4.6 pricing as of 2026-05-09 ($3 / 1M input tokens, $15 / 1M output tokens). See [anthropic.com/pricing](https://www.anthropic.com/pricing).

Now compare with [`../after/`](../after/).
