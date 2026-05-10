# OMA (TypeScript) adapter

AgentSonar runs in Python, OMA runs in TypeScript. The bridge: a small Python sidecar that listens on `localhost:8787`, and a TypeScript client (`@agentsonar/oma`) that posts delegation events to it.

This is the only adapter that needs two pieces. Once both are running, the experience matches the Python adapters: same detection, same Prevent Mode, same HTML report.

## Install

Two parts.

### TypeScript client

```bash
npm install @agentsonar/oma
```

### Python sidecar

```bash
pip install agentsonar
```

The sidecar ships inside the same Python package. You start it as a separate process from your TypeScript app.

## Runnable example

Two minimal TypeScript scripts you can copy and run:

- [`examples/oma/detect.ts`](../../examples/oma/detect.ts): TypeScript app paired with a plain sidecar (`python -m agentsonar.sidecar`).
- [`examples/oma/prevent.ts`](../../examples/oma/prevent.ts): same TypeScript app, paired with a sidecar started with `--prevent-cyclic-delegation`.

## Start the sidecar

```bash
python -m agentsonar.sidecar
```

Or, if you cloned the OMA repo:

```bash
python sidecar/sidecar.py
```

The sidecar binds to `localhost:8787` by default. While it's running, your TypeScript app posts delegation events to it. When you call `shutdown()` from TypeScript, the sidecar writes its reports and exits.

### Sidecar CLI flags

All flags map to AgentSonar config keys. Defaults match the Python SDK.

#### Detection thresholds

| Flag | Default | Maps to config key |
|---|---|---|
| `--warning-threshold` | `5` | `warning_threshold` |
| `--critical-threshold` | `15` | `critical_threshold` |
| `--resolve-after` | `60.0` | `resolve_after_seconds` |

#### Rate limiter

| Flag | Default | Maps to config key |
|---|---|---|
| `--window-size` | `180.0` | `window_size` |
| `--per-edge-limit` | `10` | `per_edge_limit` |
| `--global-limit` | `200` | `global_limit` |

#### Repeated-call sensitivity

| Flag | Default | Maps to config key |
|---|---|---|
| `--half-life` | `180.0` | `half_life_seconds` |
| `--z-score-threshold` | `3.0` | `z_score_threshold` |

#### Prevent Mode

| Flag | Default | What it does |
|---|---|---|
| `--prevent-cyclic-delegation` | off | Enable Prevent Mode. Trips on CRITICAL severity. |
| `--prevent-max-rotations N` | off | Trip at exactly N rotations, regardless of severity. |

#### Output

| Flag | Default | Notes |
|---|---|---|
| `--log-dir` | `.` | Where `agentsonar_logs/` lands. Env: `AGENTSONAR_LOG_DIR`. |
| `--no-console` | false | Disable stderr alerts. |
| `--no-report` | false | Skip writing `report.html` and `report.json`. |
| `--report-title` | `"AgentSonar Report"` | HTML title. |
| `--port N` | `8787` | TCP port to bind. Env: `AGENTSONAR_PORT`. |

Resolution order for any setting: CLI flag > environment variable > built-in default.

## TypeScript API

Three functions plus one error class.

### `emitDelegations(tasks, opts?)`

```typescript
function emitDelegations(
  tasks: readonly DelegationTask[],
  opts?: AgentSonarOptions
): Promise<number>;
```

Walks an array of OMA tasks and emits one delegation edge per `dependsOn` link. Returns the number of edges emitted (0 if input is invalid; never throws on bad input).

**Throws `PreventError` only** if the sidecar reports HTTP 409 with a Prevent Mode trip.

```typescript
import { emitDelegations, PreventError } from '@agentsonar/oma'

try {
  const edges = await emitDelegations(tasks)
  console.log(`Recorded ${edges} delegations`)
  await orchestrator.runTasks(team, tasks)
} catch (e) {
  if (e instanceof PreventError) {
    console.error(`Stopped: ${e.reason}`)
    console.error(`Cycle:   ${e.cyclePath.join(' -> ')}`)
  } else {
    throw e
  }
}
```

### `createTraceHandler(opts?, existing?)`

```typescript
function createTraceHandler(
  opts?: AgentSonarOptions,
  existing?: (event: TraceEvent) => void | Promise<void>
): (event: TraceEvent) => Promise<void>;
```

Returns an OMA `onTrace` handler that forwards `agent` and `task` events to the sidecar in real time. (Other event types like `llm_call` and `tool_call` are intentionally skipped because their counts are already aggregated into the `agent` and `task` events.)

If you already have an `onTrace` handler, pass it as `existing` and the AgentSonar handler will compose with yours instead of replacing it.

```typescript
import { OpenMultiAgent } from '@open-multi-agent/core'
import { createTraceHandler } from '@agentsonar/oma'

const orchestrator = new OpenMultiAgent({
  defaultModel: 'gpt-4o-mini',
  onTrace: createTraceHandler(),
})
```

With an existing handler:

```typescript
const myExistingHandler = (event) => { /* your code */ }

const orchestrator = new OpenMultiAgent({
  defaultModel: 'gpt-4o-mini',
  onTrace: createTraceHandler({}, myExistingHandler),
})
```

### `shutdown(opts?)`

```typescript
function shutdown(opts?: AgentSonarOptions): Promise<void>;
```

Tells the sidecar to write its reports and exit. Safe to call multiple times. After the first call, the sidecar exits, so subsequent calls become no-ops on the TypeScript side.

Call this in your app's shutdown hook (`process.on('SIGINT', ...)`, the `finally` block of your main, or wherever your normal cleanup happens).

```typescript
import { shutdown } from '@agentsonar/oma'

process.on('SIGINT', async () => {
  await shutdown()
  process.exit(0)
})
```

### `PreventError`

```typescript
class PreventError extends Error {
  readonly failureClass: string;       // 'cyclic_delegation'
  readonly severity: string;           // 'CRITICAL' | 'WARNING'
  readonly rotations: number;          // actual rotation count at trip
  readonly cyclePath: readonly string[]; // ['reviewer', 'generator', 'reviewer']
  readonly reason: string;             // human-readable summary
  readonly timestamp: number;          // epoch seconds
}
```

Mirror of the Python `PreventError`. Thrown from `emitDelegations()` when the sidecar reports a Prevent Mode trip.

### `AgentSonarOptions`

```typescript
interface AgentSonarOptions {
  readonly endpoint?: string;    // default: http://localhost:8787 (env: AGENTSONAR_ENDPOINT)
  readonly debug?: boolean;      // default: false (logs wire activity)
  readonly timeoutMs?: number;   // default: 2000 (per HTTP request)
}
```

Pass the same options to every AgentSonar call, or set the env var once and skip the options object entirely.

## Wire format

Useful if you're debugging or you want to use the sidecar from a non-TypeScript client.

| Method | Path | Purpose | Body | Response |
|---|---|---|---|---|
| `POST` | `/ingest` | Record a delegation | `{"source": str, "target": str, "timestamp"?: float, "metadata"?: dict}` | 204 (or 409 on Prevent trip) |
| `POST` | `/trace` | Forward an OMA trace event | `{"type": "agent" \| "task" \| ..., ...}` | 204 |
| `POST` | `/shutdown` | Finalize the run | (empty) | 200 + JSON status |
| `GET` | `/health` | Liveness check | (none) | 200 + counters JSON |

### Prevent Mode 409 response (RFC 7807)

When Prevent Mode trips, `/ingest` returns:

```http
HTTP/1.1 409 Conflict
Content-Type: application/problem+json

{
  "type": "https://github.com/agentsonar/agentsonar/blob/main/docs/problems/coordination-prevented.md",
  "title": "Coordination Failure Prevented",
  "status": 409,
  "detail": "<human-readable reason>",
  "instance": "/ingest",
  "agentsonar": {
    "failure_class": "cyclic_delegation",
    "severity": "CRITICAL",
    "rotations": 15,
    "cycle_path": ["reviewer", "generator"],
    "reason": "...",
    "timestamp": 1745891234.5
  }
}
```

The TypeScript client recognizes `status==409` + `Content-Type: application/problem+json` + `body.agentsonar` and throws `PreventError` with the parsed payload.

## End-to-end example

Two terminals.

### Terminal 1: sidecar

```bash
python -m agentsonar.sidecar --warning-threshold 3 --critical-threshold 8 --prevent-cyclic-delegation
```

### Terminal 2: TypeScript app

```typescript
import { OpenMultiAgent } from '@open-multi-agent/core'
import { createTraceHandler, emitDelegations, shutdown, PreventError } from '@agentsonar/oma'

const orchestrator = new OpenMultiAgent({
  defaultModel: 'gpt-4o-mini',
  onTrace: createTraceHandler(),
})

const team = orchestrator.createTeam({
  name: 'review-pipeline',
  agents: [
    { id: 'generator', systemPrompt: 'Write a draft.' },
    { id: 'reviewer', systemPrompt: 'Review and revise.' },
  ],
})

const tasks = [
  { id: 't1', title: 'Write draft', assignee: 'generator' },
  { id: 't2', title: 'Review', assignee: 'reviewer', dependsOn: ['t1'] },
  { id: 't3', title: 'Revise', assignee: 'generator', dependsOn: ['t2'] },
  // ...possibly cyclic if reviewer never approves
]

try {
  await emitDelegations(tasks)
  await orchestrator.runTasks(team, tasks)
} catch (e) {
  if (e instanceof PreventError) {
    console.error(`Stopped: ${e.reason}`)
    console.error(`Cycle:   ${e.cyclePath.join(' -> ')}`)
  } else {
    throw e
  }
} finally {
  await shutdown()
}
```

## Output

Reports are written by the sidecar (Python side) to wherever `--log-dir` points:

```
agentsonar_logs/
└── run-2026-04-29_05-12-34-amber-fox/
    ├── timeline.jsonl
    ├── alerts.log
    ├── report.json
    └── report.html
```

Same shape and content as the Python adapters.

## Limitations

- **Cross-process state**: each sidecar instance keeps its own state. If you run multiple OMA processes against one sidecar, they share a session. If you run multiple sidecars, they don't share anything. Pick whichever fits your topology.
- **Local-only by default**: the sidecar binds `127.0.0.1` only. To run it on a different host, override with `--port` and bind explicitly through your reverse proxy or container network. We don't recommend exposing the sidecar publicly today; it has no auth.

## See also

- [Concepts](../concepts.md): what counts as a coordination failure.
- [Configuration](../configuration.md): the canonical config key names that the sidecar's CLI flags map to.
- [Prevent Mode](../prevent-mode.md): the full auto-stop walkthrough, including OMA-specific troubleshooting.
- [Custom Python adapter](custom-python.md): the Python equivalent if you have a service that spans Python and TypeScript and you want to track delegations from both sides.
