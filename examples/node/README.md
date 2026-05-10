# Node example: silent loops

A Researcher, a Writer, and a Reviewer hand work back and forth. The Reviewer never approves. Tokens burn forever.

5 minutes. Clone, install, run.

## Before (without AgentSonar)

    npm install
    npm run before
    # silent burn. No alerts. ~$14.50 in mocked tokens.

## After (with AgentSonar — detect)

    npm run detect
    # alert fires at rotation 5, escalates at 15. report.html on disk.

## After + Prevent Mode (auto-stop)

    npm run prevent
    # pipeline halts at rotation 10. ~$4.83 mocked cost. Saved $9.67.

## The only change you made

See [`what-changed.md`](what-changed.md) for the literal diff.

## Cost numbers

Mocked, based on Claude Sonnet 4.6 pricing as of 2026-05-09 ($3 / 1M input tokens, $15 / 1M output tokens). Source: [anthropic.com/pricing](https://www.anthropic.com/pricing).
