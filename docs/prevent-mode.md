# Prevent Mode

Detection alone tells you what happened. **Prevent Mode raises a typed
exception the moment a tracked failure crosses the trip threshold**,
letting your code stop a runaway loop before the next LLM call.

It's the difference between "alerting on the $47K loop" and "killing it
at $38."

![Prevent Mode tripped: cyclic_delegation stopped at 15 rotations](images/prevent-error.png)

## When to use it

| Mode | What it does | When to use |
|---|---|---|
| **Detection only** (default) | Fires alerts (WARNING / CRITICAL) but never stops your loop | When you want visibility but full manual control over termination |
| **Prevent Mode** (opt-in) | Same alerts AS WELL AS raising `PreventError` to stop the loop | When the cost of letting a known-bad loop continue is real money |

If you're running real LLM workloads with real cost, Prevent Mode is the
safer default. The opt-in is one line of config.

## Quick start

The whole API in one example:

```python
from agentsonar import monitor_orchestrator, PreventError

sonar = monitor_orchestrator(config={
    "prevent": {"cyclic_delegation": True}   # ← this is the opt-in
})

try:
    while True:
        sonar.delegation("reviewer", "generator")
        # ...your agents run...
        sonar.delegation("generator", "reviewer")
        # ...
except PreventError as e:
    print(f"Stopped: {e.reason}")
    print(f"Cycle:   {' -> '.join(e.cycle_path)}")
    print(f"After:   {e.rotations} rotations (severity {e.severity})")

sonar.shutdown()
```

That's it. Two changes to a regular AgentSonar setup:

1. Add `"prevent": {"cyclic_delegation": True}` to your config dict
2. Wrap your loop in `try / except PreventError`

## What gets covered

Today, Prevent Mode handles **`cyclic_delegation`**: agents stuck in a
loop. The other two failure classes (`repetitive_delegation`,
`resource_exhaustion`) are detection-only for now; they're on the
roadmap for a follow-up release.

## Adapter support

| Adapter | Prevent Mode | How |
|---|---|---|
| **Custom Python** (`monitor_orchestrator`) | ✅ Auto-raise on `delegation()` calls | Pass `prevent={...}` in config |
| **LangGraph** (`monitor()` / `AgentSonarCallback`) | ✅ Auto-raise out of `graph.invoke()` | Pass `prevent={...}` in config |
| **OMA** (TypeScript via sidecar) | ✅ Auto-raise on `emitDelegations()` | Start sidecar with `--prevent-cyclic-delegation` |
| **CrewAI** (`AgentSonarListener`) | ⏸️ Deferred, CrewAI's event bus swallows listener exceptions and the framework has no native stop API. Detection-only mode works as before. |

For non-CrewAI users: it just works. For CrewAI users: detection still
fires; auto-stop requires a CrewAI framework change we're tracking
upstream.

## The three opt-in shapes

### 1. Trip on CRITICAL severity (default)

```python
"prevent": {"cyclic_delegation": True}
```

AgentSonar fires `PreventError` when the cycle alert reaches CRITICAL
severity (the default `critical_threshold` is 15 rotations). Best for
production: gives the cycle a chance to resolve naturally before
forcing a stop.

### 2. Trip at exactly N rotations

```python
"prevent": {"cyclic_delegation": {"max_rotations": 5}}
```

Trip at exactly 5 rotations regardless of WARNING/CRITICAL severity.
Useful for tight test loops or when you want a hard cap below the
default CRITICAL threshold.

### 3. Don't auto-raise: return the result instead

```python
"prevent": {"cyclic_delegation": True, "raise": False}
```

The trip is detected, but no exception is thrown. Instead, you poll
`sonar.engine.should_prevent()` yourself between operations and decide
how to react. Useful for batch workflows where catching an exception
mid-iteration is awkward.

```python
result = sonar.engine.should_prevent()
if result is not None:
    print(f"Should stop: {result.reason}")
    # ... your own decision logic ...
```

## What `PreventError` carries

```python
except PreventError as e:
    e.failure_class    # 'cyclic_delegation'
    e.severity         # 'CRITICAL' (or 'WARNING' if max_rotations triggered before CRITICAL)
    e.rotations        # actual rotation count at trip
    e.cycle_path       # list[str], the cycle of agents
    e.reason           # human-readable summary
    e.timestamp        # epoch seconds at trip
    e.prevention       # full PreventionResult object (frozen dataclass)
```

The exception is picklable, so it round-trips through Sentry / structured
logs / `multiprocessing` cleanly.

## What you'll see in the report

After a trip, the HTML report shows a single deduped card with a
**🛑 PREVENTED** badge prefixed before the standard CRITICAL badge:

![Prevent Mode tripped: cyclic_delegation stopped at 15 rotations](images/prevent-error.png)

The Topology block shows the actual rotation count at trip time (not
the stale alert count) and the full cycle path. The `alerts.log` file
gets a matching line:

```
[SONAR ...] 🛑 PREVENTED cyclic_delegation: [reviewer -> researcher -> writer] stopped at 15 rotations
```

So whether you're reading the report visually or grepping the chronological
log, the trip is the same single, unmistakable signal.

## Re-raise behavior: once tripped, stays tripped

Once `PreventError` raises, the same alert remains in the engine's
recent-alerts buffer. Any subsequent `delegation()` call will re-raise
the same error. **This is intentional**: Prevent Mode's contract is
"stop the loop." If you catch and continue calling `delegation()`,
every next call re-raises.

To resume detection in a clean state, call `sonar.shutdown()` and
construct a fresh `monitor_orchestrator()`.

## Configuration interaction

If you set `max_rotations` lower than `warning_threshold`, AgentSonar
auto-lowers `warning_threshold` to match. This ensures alerts emit
early enough for the prevent check to actually see them.

```python
"prevent": {"cyclic_delegation": {"max_rotations": 3}}
# warning_threshold (default 5) is auto-lowered to 3: prevent intent wins
```

## Troubleshooting

**Q: (OMA / TypeScript users only) I started the sidecar with `--prevent-cyclic-delegation` but nothing trips.**

This question is specific to the OMA adapter, Python users won't see
this CLI flag.

Check that the cycle is actually crossing CRITICAL severity. Default mode
trips on CRITICAL only. With default thresholds (warning=5, critical=15),
your cycle needs to reach 15 rotations before the trip fires.

For tighter tests, restart the sidecar with `--prevent-max-rotations 1`
to bypass the severity gate.

> Python equivalent: pass `{"prevent": {"cyclic_delegation": {"max_rotations": 1}}}` in the config dict.

**Q: I see WARNING + CRITICAL in alerts.log but no PREVENTED line.**

Make sure you're on `agentsonar==0.3.3` or later, earlier versions
emitted the PREVENTED card in the HTML report but not the alerts.log
line. `pip install --upgrade agentsonar`.

**Q: Two cards in the HTML report, a normal CRITICAL one and a phantom "unknown" PREVENTED one.**

You're on `agentsonar==0.3.1` or earlier. Upgrade to 0.3.2+, there
was a fingerprint-mismatch bug between the SCC analyzer and the
prevention event that's been fixed.

**Q: How do I test Prevent Mode locally without burning real LLM credits?**

Use the Python adapter and call `delegation()` manually with hardcoded
agent names, no LLM needed. The detection engine is identical whether
LLMs are involved or not. Example:

```python
sonar = monitor_orchestrator(config={
    "prevent": {"cyclic_delegation": {"max_rotations": 3}}
})
try:
    for _ in range(20):
        sonar.delegation("a", "b")
        sonar.delegation("b", "c")
        sonar.delegation("c", "a")
except PreventError as e:
    print(f"Tripped at rotation {e.rotations}")
sonar.shutdown()
```

This runs in milliseconds with zero cost.

## See also

- [Custom Python adapter](adapters/custom-python.md): the universal way to wire AgentSonar in
- [LangGraph adapter](adapters/langgraph.md), Prevent Mode through `graph.invoke()`
- [OMA (TypeScript)](adapters/oma.md), Prevent Mode across the HTTP sidecar
- [Configuration reference](configuration.md): all config knobs
