# Configuration reference

Every config knob AgentSonar accepts, grouped by purpose, with the actual default values from the source code.

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

For OMA (TypeScript), the same knobs are exposed as CLI flags on the Python sidecar (`python sidecar/sidecar.py --warning-threshold 3 ...`). See [`adapters/oma.md`](adapters/oma.md) for the flag mapping.

## At a glance

| Group | Keys | What it controls |
|---|---|---|
| **Detection thresholds** | `warning_threshold`, `critical_threshold`, `re_alert_interval`, `resolve_after_seconds` | When cycles fire WARNING and CRITICAL alerts |
| **Rate limiter** | `window_size`, `per_edge_limit`, `global_limit` | When `resource_exhaustion` fires |
| **Repetitive detector** | `half_life_seconds`, `z_score_threshold`, `hard_weight_limit`, `min_edges_for_zscore`, `min_total_events` | When `repetitive_delegation` fires |
| **SCC analyzer** | `scc_interval_seconds`, `scc_interval_events` | How often the backup cycle scan runs |
| **Output** | `log_dir`, `console_output`, `file_output`, `log_level`, `keep_runs`, `report_title`, `auto_export_on_shutdown` | Where alerts and reports go |
| **Prevent Mode** | `prevent` | Auto-stop on detected loops (opt-in) |

## Detection thresholds

Where rotation alerts fire from. These govern `cyclic_delegation` and the alert state machine.

### `warning_threshold` (int, default `5`)

Rotation count at which WARNING fires. Inclusive: rotation 5 IS the trigger, not 6.

A "rotation" is one full traversal of a cycle. If the cycle is `A -> B -> A`, then rotation 1 happens at the second arrival back at A, rotation 2 at the third, and so on.

Lower this if you want earlier visibility on short-lived loops. Raise it if you have a healthy pattern that legitimately repeats a few times before converging.

### `critical_threshold` (int, default `15`)

Rotation count at which CRITICAL fires. Same `>=` semantics as warning_threshold.

The default Prevent Mode trip is on CRITICAL severity, so this is also where the auto-stop fires by default. Lower this for tighter Prevent Mode tests.

### `re_alert_interval` (float, default `30`)

Seconds to wait before re-alerting on a sustained CRITICAL alert. Prevents spamming stderr with the same alert every microsecond if a runaway loop keeps firing.

### `resolve_after_seconds` (float, default `60.0`)

Seconds of inactivity on a fingerprint before its alert is auto-resolved (status moves from active to resolved). Useful for the HTML report's "did this resolve on its own?" view.

## Rate limiter (resource_exhaustion)

A sliding-window counter that fires when traffic spikes past expected levels.

### `window_size` (float, default `180.0`)

Sliding window duration in seconds. The rate limiter counts events that fell inside the last N seconds.

Shrink it (e.g., 60.0) to detect faster spikes. Enlarge it (e.g., 600.0) to smooth over short bursts.

### `per_edge_limit` (int, default `10`)

Maximum events on a single edge (`A -> B`) within the window before firing `rate_limit_exceeded`.

Raise it if your healthy pattern has high single-edge fan-out. The default suits most "manager spawns N workers" scenarios where N is small.

### `global_limit` (int, default `200`)

Maximum total events across all edges within the window before firing `global_rate_exceeded`. Catches "the whole graph went berserk" patterns where no single edge stands out but cumulative throughput is wrong.

## Repetitive detector (repetitive_delegation)

An exponentially-decayed edge-frequency anomaly detector.

### `half_life_seconds` (float, default `180.0`)

Time constant for exponential decay. Old activity ages out: an event 180 seconds ago contributes half what an event right now does.

Shrink it for faster reactivity to recent traffic patterns. Enlarge it to incorporate more history into the baseline.

### `z_score_threshold` (float, default `3.0`)

Standard deviations above the rolling mean before an edge is flagged as a repetitive_delegation anomaly. Raise it (e.g., 4.0) for fewer false positives. Lower it (e.g., 2.0) for earlier alerts.

### `hard_weight_limit` (float, default `10.0`)

Cap on the weight sum per edge. Bounds memory per edge so a hot edge can't grow its tracking state unboundedly.

### `min_edges_for_zscore` (int, default `10`)

Minimum number of distinct edges seen before the z-score computation runs. Bootstrap guard: with too few edges, the variance estimate is noisy and you'd get spurious alerts.

### `min_total_events` (int, default `20`)

Minimum total events seen before the z-score computation runs. Bootstrap guard pair to `min_edges_for_zscore`.

## SCC analyzer (backup cycle detector)

A periodic full-graph cycle scan that runs alongside the incremental cycle detector. Catches multi-agent cycles the incremental detector might miss.

### `scc_interval_seconds` (float, default `10.0`)

How often the SCC analyzer runs (in seconds since its last run).

### `scc_interval_events` (int, default `50`)

Minimum events ingested between SCC sweeps. Both conditions must be satisfied (time elapsed AND enough new events) for the scan to run.

If your run is short, increase the time interval and lower the event interval to make sure the SCC sweep fires at all. If your run is fire-hose busy, raise the event interval to keep the sweep affordable.

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

Logging verbosity. Set to `"DEBUG"` to see internal engine decisions (state transitions, dedup decisions, SCC sweeps). Set to `"WARNING"` to suppress informational lines and only see alerts.

### `keep_runs` (int | None, default `None`)

Number of recent run directories to keep on disk. Older runs are pruned at session start. `None` reads from the env var `AGENTSONAR_KEEP_RUNS`, falling back to a built-in default.

Set to a fixed integer (e.g., `keep_runs=20`) to keep the 20 most recent runs and delete older ones. Set to `0` to delete every run except the current one. Disable cleanup entirely with `keep_runs=10**9` (effectively unlimited).

### `report_title` (str, default `"AgentSonar Report"`)

Title string used in the HTML report header. Customize per project (`"Acme Order Pipeline AgentSonar"`).

### `auto_export_on_shutdown` (bool, default same as `file_output`)

Whether to write `report.json` and `report.html` automatically when `shutdown()` is called. Set to `False` if you want to manage report generation yourself.

## Prevent Mode

Opt-in auto-stop on detected coordination failures. The full walkthrough lives in [`prevent-mode.md`](prevent-mode.md); this section is the config reference only.

### `prevent` (dict | None, default `None`)

Enables Prevent Mode. Three valid shapes:

#### Trip on CRITICAL (default)

```python
"prevent": {"cyclic_delegation": True}
```

`PreventError` raises when the cycle alert reaches CRITICAL severity (using `critical_threshold`).

#### Trip at exactly N rotations

```python
"prevent": {"cyclic_delegation": {"max_rotations": 5}}
```

`PreventError` raises at exactly 5 rotations regardless of WARNING / CRITICAL severity. AgentSonar auto-lowers `warning_threshold` to match if it would otherwise be higher than `max_rotations` (so the alert state machine can see the trip).

#### Don't auto-raise (return-style)

```python
"prevent": {"cyclic_delegation": True, "raise": False}
```

The trip is detected but no exception is thrown. Poll `sonar.engine.should_prevent()` between operations to check if a trip occurred.

Today, only `cyclic_delegation` is supported in Prevent Mode. `repetitive_delegation` and `resource_exhaustion` are detection-only.

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

### "I'm running in a quiet workload and the rate limiter is too sensitive"

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

The fastest sanity check is to run a known-bad scenario with `print` instrumentation and confirm the alerts fire at the rotations you expect. The example in [`prevent-mode.md`](prevent-mode.md#troubleshooting) under "How do I test Prevent Mode locally without burning real LLM credits?" runs in milliseconds with zero LLM cost.

If a config knob isn't behaving the way you expect, [open an issue](https://github.com/agentsonar/agentsonar/issues/new?template=bug_report.yml) and include your config dict plus the alerts you got.
