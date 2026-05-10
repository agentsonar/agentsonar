# Configuration reference

Every config knob AgentSonar accepts, grouped by what each one controls. Each setting is described in plain English by what it does for you, not by how it works inside.

All four adapters take the same config dict. Pass it to whichever entry point you're using:

```python
# Custom Python
sonar = monitor_orchestrator(config={...})

# CrewAI
sonar = AgentSonarListener(config={...})

# LangGraph
sonar = AgentSonarCallback(config={...})
graph = monitor(graph, config={...})
```

For the OMA sidecar, the same knobs are exposed as CLI flags (`agentsonar-sidecar --warning-threshold 3 --critical-threshold 10 ...`). See [`adapters/oma.md`](adapters/oma.md) for the full flag mapping.

## Three common shapes

Most users fall into one of three configs. Pick whichever matches what you want today; you can always tune later.

### 1. The default — zero config

You don't have to set anything. Pass no config and you get sensible defaults for every knob:

```python
sonar = monitor_orchestrator()   # that's it
```

Defaults you get:

- WARNING fires after 5 loop rotations, CRITICAL after 15
- Traffic-spike alerts fire after 10 calls between the same two agents in 180 seconds
- Reports written to `agentsonar_logs/run-<timestamp>/`
- Prevent Mode is **off** (alerts only — your code keeps running)

This is the right starting point. Run your workload, open `report.html`, and only come back to this page if you want to change something.

### 2. Detect only (custom thresholds, no auto-stop)

You want alerts and an HTML report, but you don't want AgentSonar to ever interrupt your run. Just tune the sensitivity:

```python
sonar = monitor_orchestrator(config={
    "warning_threshold": 3,        # alert sooner — after 3 loop rotations
    "critical_threshold": 10,      # escalate after 10 rotations
    "log_dir": "./logs/agentsonar" # custom report location
})
```

Use this when you're still learning your workload's normal patterns. Watch the alerts for a week, then decide whether to turn Prevent Mode on.

### 3. Detect + Prevent Mode (auto-stop silent loops)

You want AgentSonar to actually stop the run when a silent loop crosses the line. Add the `prevent` block:

```python
sonar = monitor_orchestrator(config={
    "warning_threshold": 3,
    "critical_threshold": 10,
    "prevent": {
        "cyclic_delegation": {
            "max_rotations": 10   # raise PreventError at rotation 10
        }
    }
})
```

When the loop hits 10 rotations, your next `sonar.delegation(...)` call raises a typed `PreventError`. Wrap your code in a `try / except PreventError` and your pipeline halts cleanly before the next LLM call.

→ Full Prevent Mode walkthrough: [`prevent-mode.md`](prevent-mode.md)

## At a glance

| Group | Keys | What it controls |
|---|---|---|
| **Silent-loop alerts** | `warning_threshold`, `critical_threshold`, `re_alert_interval`, `resolve_after_seconds` | When the silent-loop detector raises a warning, when it escalates, and when it resolves |
| **Runaway-spend alerts** | `window_size`, `per_edge_limit`, `global_limit` | When AgentSonar flags a sudden spike in agent traffic |
| **Repeated-call alerts** | `half_life_seconds`, `z_score_threshold`, `hard_weight_limit`, `min_edges_for_zscore`, `min_total_events` | Sensitivity for the repeated-call detector |
| **Periodic re-check** | `scc_interval_seconds`, `scc_interval_events` | How often AgentSonar runs a backup pass over the full agent graph |
| **Output** | `log_dir`, `console_output`, `file_output`, `log_level`, `keep_runs`, `report_title`, `auto_export_on_shutdown` | Where alerts and reports go |
| **Prevent Mode** | `prevent` | Auto-stop on detected silent loops (opt-in) |

## Silent-loop alert thresholds

Sensitivity for the silent-loop detector. Raise a threshold to silence alerts; lower it to alert sooner.

### `warning_threshold` (int, default `5`)

How many times agents go around in a loop before AgentSonar fires a WARNING. A "rotation" is one full lap of the loop.

Lower this if you want earlier visibility on short loops. Raise it if your workflow legitimately repeats a few times before settling.

### `critical_threshold` (int, default `15`)

How many laps of a loop before the alert escalates from WARNING to CRITICAL.

The default Prevent Mode trip happens at CRITICAL severity, so this is also where auto-stop fires by default.

### `re_alert_interval` (float, default `30`)

Seconds to wait before re-firing the same CRITICAL alert. Stops AgentSonar from spamming the same line every microsecond when a runaway loop keeps going.

### `resolve_after_seconds` (float, default `60.0`)

Seconds of quiet on a tracked failure before AgentSonar marks it as resolved. Useful for the HTML report's "did this fix itself?" view.

## Runaway-spend alert thresholds

Sensitivity for the runaway-spend detector — the one that catches sudden traffic spikes between agents.

### `window_size` (float, default `180.0`)

Length of the time window AgentSonar uses to count traffic, in seconds.

Shrink it (e.g., 60.0) to detect faster spikes. Enlarge it (e.g., 600.0) to smooth over short bursts.

### `per_edge_limit` (int, default `10`)

How many calls between two specific agents (`A -> B`) inside the time window before AgentSonar flags it.

Raise it if your healthy workflow has high one-to-one traffic between two agents. The default suits most "manager spawns N workers" patterns where N is small.

### `global_limit` (int, default `200`)

How many total agent-to-agent calls across the whole system inside the window before AgentSonar flags it. Catches "the whole system went berserk" patterns where no single pair stands out but the total is wrong.

## Repeated-call alert thresholds

Sensitivity for the repeated-call detector — the one that catches one agent hammering another with the same kind of work over and over.

### `half_life_seconds` (float, default `180.0`)

How long old activity stays relevant. Older activity gradually counts for less when AgentSonar judges whether a current spike is unusual.

Shrink it for faster reactivity to recent activity. Enlarge it to weigh more history.

### `z_score_threshold` (float, default `3.0`)

How unusual recent traffic must look before AgentSonar fires an alert. Raise it (e.g., 4.0) for fewer false positives. Lower it (e.g., 2.0) for earlier alerts.

### `hard_weight_limit` (float, default `10.0`)

A safety cap that keeps AgentSonar's per-pair tracking memory bounded, even on extremely hot edges. You almost never need to change this.

### `min_edges_for_zscore` (int, default `10`)

Minimum number of distinct agent pairs AgentSonar needs to see before it starts judging what counts as unusual. Prevents noisy alerts when there isn't enough data yet.

### `min_total_events` (int, default `20`)

Minimum total agent-to-agent calls AgentSonar needs to see before it starts judging unusualness. Pairs with `min_edges_for_zscore` as a startup guard.

## Periodic re-check

A backup pass that walks the full agent graph from time to time, just in case the live detector missed a multi-agent loop.

### `scc_interval_seconds` (float, default `10.0`)

How often the backup pass runs (in seconds since the last run).

### `scc_interval_events` (int, default `50`)

Minimum number of new events between backup passes. Both conditions must be met (enough time AND enough new events) before the pass runs.

If your run is short, lower the event interval so the pass runs at all. If your run is firehose-busy, raise the event interval to keep the pass cheap.

## Output

Where alerts, the timeline, and reports go.

### `log_dir` (str, default `"."`)

Directory where `agentsonar_logs/` is created. Per-run session directories land inside it (`agentsonar_logs/run-<timestamp>-<slug>/`).

Override per run via the env var `AGENTSONAR_LOG_DIR` if you want CI to write to a fixed path without code changes.

### `console_output` (bool, default `True`)

Whether to stream WARNING / CRITICAL / PREVENTED alert lines to stderr in real time.

### `file_output` (bool, default `True`)

Whether to write `timeline.jsonl`, `alerts.log`, `report.json`, `report.html` to the run directory.

Set to `False` for ephemeral CI runs where you only want stderr alerts.

### `log_level` (str, default `"INFO"`)

Logging verbosity. Set to `"DEBUG"` to see more detail. Set to `"WARNING"` to suppress informational lines and only see alerts.

### `keep_runs` (int | None, default `None`)

Number of recent run directories to keep on disk. Older runs are pruned at session start. `None` reads from the env var `AGENTSONAR_KEEP_RUNS`, falling back to a built-in default.

Set to a fixed integer (e.g., `keep_runs=20`) to keep the 20 most recent runs and delete older ones. Set to `0` to delete every run except the current one. Disable cleanup entirely with `keep_runs=10**9` (effectively unlimited).

### `report_title` (str, default `"AgentSonar Report"`)

Title string used in the HTML report header. Customize per project (`"Acme Order Pipeline AgentSonar"`).

### `auto_export_on_shutdown` (bool, default same as `file_output`)

Whether to write `report.json` and `report.html` automatically when `shutdown()` is called. Set to `False` if you want to manage report generation yourself.

## Prevent Mode

Opt-in auto-stop on detected silent loops. The full walkthrough lives in [`prevent-mode.md`](prevent-mode.md); this section is the config reference only.

### `prevent` (dict | None, default `None`)

Enables Prevent Mode. Three valid shapes:

#### Trip on CRITICAL (default)

```python
"prevent": {"cyclic_delegation": True}
```

`PreventError` raises when the silent-loop alert reaches CRITICAL severity (using `critical_threshold`).

#### Trip at exactly N rotations

```python
"prevent": {"cyclic_delegation": {"max_rotations": 5}}
```

`PreventError` raises at exactly 5 rotations regardless of WARNING / CRITICAL severity.

#### Don't auto-raise (return-style)

```python
"prevent": {"cyclic_delegation": True, "raise": False}
```

The trip is detected but no exception is thrown. Poll `sonar.engine.should_prevent()` between operations to check if a trip occurred.

Today, only the silent-loop guard is supported in Prevent Mode. The repeated-call and runaway-spend signals are detection-only.

## Tuning recipes

A few common tuning patterns:

### "I want fast alerts in tests"

```python
config = {
    "warning_threshold":  2,
    "critical_threshold": 4,
    "z_score_threshold":  2.0,
    "min_total_events":   5,
}
```

### "I'm running a quiet workload and the runaway-spend alerts are too sensitive"

```python
config = {
    "per_edge_limit":  50,
    "global_limit":    1000,
    "window_size":     300.0,
}
```

### "I'm in production and want auto-stop with conservative thresholds"

```python
config = {
    "prevent": {"cyclic_delegation": True},  # trips on CRITICAL = 15 rotations
    # Default thresholds suit most production workloads.
}
```

### "I want CI artifacts but no console noise"

```python
config = {
    "console_output": False,
    "file_output":    True,
    "log_level":      "WARNING",
}
```

## Environment variables

A handful of config knobs can be read from the environment, which is convenient for CI / Docker:

| Env var | Equivalent config key | Notes |
|---|---|---|
| `AGENTSONAR_LOG_DIR` | `log_dir` | Where `agentsonar_logs/` is created |
| `AGENTSONAR_KEEP_RUNS` | `keep_runs` | Integer, applied at session start |

Code values (the explicit `config={...}` dict) take precedence over environment values when both are set.

## Verifying your config

The fastest sanity check is to run a known-bad scenario with hardcoded delegation calls and confirm the alerts fire at the rotations you expect. The example in [`prevent-mode.md`](prevent-mode.md#troubleshooting) under "How do I test Prevent Mode locally without burning real LLM credits?" runs in milliseconds with zero LLM cost.

If a config knob isn't behaving the way you expect, [open an issue](https://github.com/agentsonar/agentsonar/issues/new?template=bug_report.yml) and include your config dict plus the alerts you got.
