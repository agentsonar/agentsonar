# LangGraph example: silent loops

A two-node LangGraph (`generator` / `reviewer`) where the reviewer never approves and work loops back to the generator forever. Tokens burn quietly.

5 minutes. Clone, install, run.

## Before (without AgentSonar)

    pip install langgraph
    cd before && python pipeline.py
    # silent burn. No alerts. ~$14.50 in mocked tokens.

## After (with AgentSonar — detect)

    pip install agentsonar[langgraph]
    cd after && python detect.py
    # alert fires at rotation 5, escalates at 15. report.html on disk.

## After + Prevent Mode (auto-stop)

    cd after && python prevent.py
    # graph.invoke() halts at rotation 10. ~$4.83 mocked cost. Saved $9.67.

## The only change you made

See [`what-changed.md`](what-changed.md) for the literal diff.

## Cost numbers

Mocked, based on Claude Sonnet 4.6 pricing as of 2026-05-09 ($3 / 1M input tokens, $15 / 1M output tokens). Source: [anthropic.com/pricing](https://www.anthropic.com/pricing).
