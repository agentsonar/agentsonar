# FAQ

The questions we get most often, with concrete answers.

## Does it slow down my agents?

The detection engine work per delegation event is microseconds. Three operations: append to a graph, walk for cycle, increment a counter. The slowest part of any AgentSonar setup is whatever your existing logger does (writing a JSONL line to disk).

In benchmarks on a single delegation:
- Engine ingest path: under 100 microseconds.
- Logger flush (default): under 500 microseconds.

For comparison, a single LLM API call is typically 500 to 5000 milliseconds. AgentSonar adds well under 0.1% to your run time.

## Does it phone home? What data leaves my machine?

**Starting in 0.4.0, AgentSonar sends one anonymous session-start event per run.** The first time you run it on a machine, you'll see a one-time message in stderr explaining what's collected and how to disable it.

**What we send (per session):**

- `install_id`: a random UUID stored at `~/.agentsonar/state.json`, regenerated if missing
- `session_id`: a fresh UUID per session
- `version`: e.g. `0.4.0`
- `python`: e.g. `3.12`
- `os`: e.g. `darwin`, `linux`, `win32`
- `arch`: e.g. `arm64`, `x86_64`
- `adapter`: which integration is active (`custom_python`, `crewai`, `langgraph`)
- `timestamp`: epoch seconds

**What we never send:**

- Agent names
- Prompts or LLM responses
- Log content
- Project paths or filenames
- IP addresses (the collector doesn't log them)

**To disable**, set either env var (both work):

```bash
export AGENTSONAR_TELEMETRY=off
# or the universal opt-out:
export DO_NOT_TRACK=1
```

Or in code, via the config dict:

```python
sonar = monitor_orchestrator(config={"telemetry": False})
```

The code-disable persists across runs (stored in `~/.agentsonar/state.json`), so you only need to set it once.

**Why we added it**: at closed beta we genuinely had no idea how many people were using AgentSonar (PyPI download counts are dominated by CI traffic). Session-event telemetry gives us minimal, honest signal so we can prioritize the adapters and Python versions our actual users care about. Full rationale and exact wire format documented at [agent-sonar.com/telemetry](https://www.agent-sonar.com/telemetry).

**Other than this one event**, nothing else leaves your machine. The HTML report is a self-contained file. The OMA adapter talks to a local Python sidecar on `localhost:8787` (you start it yourself). No accounts, no API keys, no remote dashboard.

## Does it need an LLM API key?

No. AgentSonar watches your agent traffic; it never makes its own LLM calls. You can develop and test against AgentSonar with hardcoded delegation calls and zero LLM credits spent.

## Why am I seeing WARNING but not CRITICAL?

Default thresholds are `warning_threshold=5` and `critical_threshold=15` rotations. WARNING fires when a cycle hits 5 rotations; CRITICAL fires when it hits 15. If your cycle resolves between 5 and 15 rotations, you'll see a WARNING but no CRITICAL.

If you want CRITICAL to fire earlier, lower `critical_threshold`:

```python
sonar = monitor_orchestrator(config={
    "critical_threshold": 8,  # was 15
})
```

See [`configuration.md`](configuration.md) for the full threshold semantics.

## Why am I seeing CRITICAL but no PREVENTED line?

You enabled Prevent Mode but the trip threshold is being met during your loop, not because of bad config. Two common gotchas:

1. **You're on `agentsonar` 0.3.2 or earlier.** The PREVENTED line in `alerts.log` was added in 0.3.3. Upgrade with `pip install --upgrade agentsonar`.
2. **You set `"raise": False`.** That config key disables the exception path. The trip is detected internally and exposed via `sonar.engine.should_prevent()` instead of being raised. See [`prevent-mode.md`](prevent-mode.md) section "Don't auto-raise".

## Can I use it in production?

Yes. Specifically:

- **Detection mode (default)**: zero risk. The engine is read-only on your runtime; it only emits alerts to stderr / files. If AgentSonar itself crashes (it shouldn't, but in principle), the worst case is that detection silently stops; your agents keep running.
- **Prevent Mode (opt-in)**: raises `PreventError` from the call that would have continued the loop. Your code wraps the loop in `try / except PreventError` to handle it cleanly. We've shipped this across three adapters and validated against real LLM workloads with frontier models.

If you're nervous about the exception path in production, run with `prevent={"cyclic_delegation": True, "raise": False}` first. That mode logs trips without raising, so you can verify the alerts are correct before flipping the switch on auto-stop.

## What if the same cycle gets detected over and over?

The engine deduplicates alerts by a fingerprint (the failure class plus the sorted set of agents involved). The same cycle won't generate 50 cards in your HTML report; it generates one card with the highest-severity status it reached.

In `alerts.log`, you'll see the WARNING and CRITICAL transitions for the same cycle, plus a PREVENTED line if Prevent Mode tripped. The HTML report shows the deduped result.

## What happens to detection if my agents talk to themselves (A -> A)?

AgentSonar treats self-loops as valid edges (some frameworks legitimately have an agent that re-invokes itself). They count toward edge frequency for repetitive_delegation detection. They don't form a cycle on their own (a cycle requires at least two agents).

If you don't want self-loops counted, filter them at the call site before passing to `delegation()`.

## Can I use AgentSonar with the OpenAI Agents SDK / AutoGen / Pydantic AI?

Yes, via the [Custom Python adapter](adapters/custom-python.md). Native adapters for the OpenAI Agents SDK and Claude Agent SDK are on the near-term roadmap (~2-3 weeks). In the meantime, calling `sonar.delegation(source, target)` from inside your handoff hook gives you the same detection as a native adapter.

If your framework isn't covered and you'd like a native adapter, [open a feature request](https://github.com/agentsonar/agentsonar/issues/new?template=feature_request.yml). We genuinely want to add new framework support; past adapters have shipped in days, not weeks.

## How do I share the report with my team?

The `report.html` file is fully self-contained. No external CSS, JS, or image dependencies. Email it, drop it into Slack, attach it to a Linear ticket, or commit it to your repo. It renders in any modern browser.

## Why do I see so many INFO log lines in the timeline?

The JSONL timeline (`timeline.jsonl`) is the comprehensive event stream. Every delegation, every state transition, every threshold crossing is recorded. It's meant for `tail -f` during a run, programmatic processing, or post-mortem grepping.

The `alerts.log` file is the signal-only view: it only contains WARNING, CRITICAL, and PREVENTED lines. If you just want "show me the problems," read `alerts.log`. If you want full context, read `timeline.jsonl`.

## Can I disable file output?

Yes. Set `file_output=False` in the config:

```python
sonar = monitor_orchestrator(config={
    "file_output": False,
    "console_output": True,  # still see alerts in stderr
})
```

This skips `agentsonar_logs/` entirely. Useful for ephemeral CI runs where you only want stderr alerts and no leftover log files.

## How do I clean up old run directories?

Set `keep_runs` in config or the environment variable `AGENTSONAR_KEEP_RUNS`:

```python
sonar = monitor_orchestrator(config={
    "keep_runs": 20,  # keep the 20 most recent runs, prune older
})
```

By default, AgentSonar keeps a sensible number of recent runs and deletes older ones at session start. Set `keep_runs=None` to disable cleanup entirely (you'll keep every run forever).

## I'm running on Windows. Anything different?

Mostly no. The Python adapter is pure Python and works identically on Windows, Linux, and macOS. The OMA TypeScript adapter starts a Python sidecar; on Windows, you may need to use `python` instead of `python3` and adjust path separators in `--log-dir`. Otherwise identical.

## Is there a hosted / cloud version?

Not today. AgentSonar is a local Python library with a self-contained HTML report. We're focused on shipping more detectors and adapters first. If a hosted control plane (multi-run aggregation, team dashboards, alerting integrations) would unblock something for you, [tell us](https://github.com/agentsonar/agentsonar/issues/new?template=feature_request.yml) so we can prioritize.

## What's the license?

Apache 2.0. Use it commercially, modify it, redistribute it, build on it. We just ask that you don't sue us if it doesn't work (standard Apache 2.0 disclaimer).

## My question isn't here.

[Open an issue](https://github.com/agentsonar/agentsonar/issues/new?template=feedback.yml) or email [agentsonarai@gmail.com](mailto:agentsonarai@gmail.com). We try to answer the same day on weekdays.
