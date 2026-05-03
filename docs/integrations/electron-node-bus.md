# AgentSonar for Node bus and Electron apps

This guide is for multi-agent setups where agents communicate through an
EventEmitter, message bus, or any direct hand-off pattern in Node.js or
Electron. You don't need to be using OMA, CrewAI, or any specific
framework. The integration is one line per `bus.send(...)` call.

If your setup matches this shape:

```javascript
class AgentBus extends EventEmitter {
  send(from, to, message) { /* delivers message between agents */ }
}
```

…you're 5 minutes from having AgentSonar detecting cycles, repeated
handoffs, and runaway throughput in your bus.

## What this gives you

Once wired in, AgentSonar will:

- Detect when two of your agents get stuck handing work back and forth (`cyclic_delegation`)
- Detect when one agent is hammering another past the rolling baseline (`repetitive_delegation`)
- Detect when traffic on any single edge spikes past a rate limit (`resource_exhaustion`)
- Stream alerts (WARNING + CRITICAL) to stderr in real time
- Write a self-contained HTML report at session end (no external CSS / JS / network)

Detection is purely structural. AgentSonar never reads prompts, LLM responses, or message contents.

## Before you start

You need:

- **Node 18+** (you almost certainly have this in Electron)
- **Python 3.10+** with `pip`
- About **5 minutes**

If you're planning to ship inside a packaged Electron binary to end users, see [End-user packaging](#end-user-packaging) at the bottom. The setup below is great for dev, CI, internal tools, and power-user installs.

## Step 1: install both packages

```bash
# In your Node project: install the TypeScript client
npm install @agentsonar/oma

# Install the Python detection engine (one-time, system-wide or per-venv)
pip install agentsonar
```

Verify both are in place:

```bash
# The npm package exports the right surface
node -e "import('@agentsonar/oma').then(m => console.log(Object.keys(m)))"
# Should include: recordDelegation, emitDelegations, shutdown, PreventError
```

```bash
# The Python package version is 0.4.1 or higher (earlier versions had a bug)
python -c "import agentsonar; print(agentsonar.__version__)"
# Should print: 0.4.1 (or higher)
```

If you have an older `agentsonar`, upgrade:

```bash
pip install --upgrade "agentsonar>=0.4.1"
```

## Step 2: wire it into your bus

Add **one line** to your `send()` (or equivalent):

```javascript
import { EventEmitter } from 'events'
import { recordDelegation } from '@agentsonar/oma'

class AgentBus extends EventEmitter {
  send(fromAgent, toAgent, message) {
    // Existing: deliver the message between agents
    this.emit(`agent:${toAgent}`, { from: fromAgent, message })

    // New: tell AgentSonar one agent handed work to another.
    // Fire-and-forget. Never blocks. Never throws on network errors.
    recordDelegation(fromAgent, toAgent).catch(() => {})
  }
}
```

That's the whole integration on the bus side.

The `.catch(() => {})` is the fire-and-forget pattern. If the sidecar is down, slow, or unreachable, AgentSonar silently drops the event. Your bus continues serving messages normally. **Observability must never break the observed.**

### Optional: attach metadata for breadcrumbs in the report

```javascript
recordDelegation(fromAgent, toAgent, {
  metadata: {
    taskId: 'task-42',
    sessionId: 'sess-01',
    via: 'electron_bus',
  },
}).catch(() => {})
```

Anything you put in `metadata` shows up in the per-event view of the HTML report. Useful for debugging which task or session caused a detected loop.

## Step 3: start the sidecar

The sidecar is a small Python script that listens on `localhost:8787` and runs the AgentSonar detection engine on the events your bus posts. It's bundled inside the npm package; no separate install needed.

In a separate terminal (during dev) or as a child process from your app:

```bash
python node_modules/@agentsonar/oma/sidecar/sidecar.py
```

You should see:

```
AgentSonar OMA sidecar listening on http://localhost:8787
  POST /ingest    delegation events
  POST /trace     OMA trace events (stashed for cost work)
  POST /shutdown  write report.html + exit
  GET  /health    liveness + current counts
```

The sidecar listens until you call `shutdown()` from your code or kill the process.

### Spawning the sidecar from your Electron app

If you'd rather not require users (or yourself) to start a separate terminal:

```javascript
import { spawn } from 'child_process'
import { join } from 'path'

const sidecarPath = join(
  __dirname,
  'node_modules',
  '@agentsonar',
  'oma',
  'sidecar',
  'sidecar.py',
)

const sidecar = spawn('python', [sidecarPath], { stdio: 'inherit' })

process.on('exit', () => sidecar.kill())
```

This launches the sidecar alongside your app and kills it on shutdown.

## Step 4: shutdown gracefully

When your app exits, signal the sidecar to write its final report:

```javascript
import { shutdown } from '@agentsonar/oma'

process.on('SIGINT', async () => {
  await shutdown()
  process.exit(0)
})
```

This causes the sidecar to write `agentsonar_logs/run-<slug>/report.html` and exit. Open that file in any browser to see the full coordination graph plus all detected failures.

## Verifying it works

After wiring everything up, run your app for a minute. You should see:

**In the sidecar's stderr (Terminal 1):**

```
delegation: reviewer -> builder
delegation: builder -> reviewer
delegation: reviewer -> builder
...
WARNING cycle: [reviewer -> builder -> reviewer] 5 rotations
CRITICAL cycle: [reviewer -> builder -> reviewer] 15 rotations
```

**In the report (`agentsonar_logs/run-<...>/report.html`):**

The full agent graph with cycles highlighted, plus cards per detected failure showing topology, thresholds, and (for rate-limit alerts) provider-error mapping.

If nothing flows, enable debug logging on a single test call:

```javascript
recordDelegation('a', 'b', { debug: true }).catch(() => {})
```

You'll see exactly what the client sends and what error (if any) it hits.

## Optional: Prevent Mode (auto-stop on detected loops)

By default AgentSonar only observes. To make it halt your bus when a coordination failure trips a threshold, start the sidecar with `--prevent-cyclic-delegation`:

```bash
python node_modules/@agentsonar/oma/sidecar/sidecar.py --prevent-cyclic-delegation
```

Then handle `PreventError` in the bus:

```javascript
import { recordDelegation, PreventError } from '@agentsonar/oma'

class AgentBus extends EventEmitter {
  async send(fromAgent, toAgent, message) {
    this.emit(`agent:${toAgent}`, { from: fromAgent, message })

    // Note: NOT swallowing the error here, we want to know if Prevent fires
    try {
      await recordDelegation(fromAgent, toAgent)
    } catch (err) {
      if (err instanceof PreventError) {
        console.error(`Coordination failure stopped: ${err.reason}`)
        console.error(`Cycle: ${err.cyclePath.join(' -> ')}`)
        // Halt your bus, show a UI, escalate to a human, etc.
        throw err
      }
      // Any other error: silently swallow (back to fire-and-forget)
    }
  }
}
```

`PreventError` is the **only** exception type AgentSonar throws. Network errors, sidecar crashes, and everything else stay silent.

## Tuning detection thresholds

The sidecar accepts CLI flags for all detection knobs. The most common:

```bash
python node_modules/@agentsonar/oma/sidecar/sidecar.py \
  --warning-threshold 3 \
  --critical-threshold 8 \
  --per-edge-limit 20 \
  --window-size 60.0
```

| Flag | Default | What it controls |
|---|---|---|
| `--warning-threshold` | `5` | Rotation count for the first WARNING |
| `--critical-threshold` | `15` | Rotation count for CRITICAL |
| `--per-edge-limit` | `10` | Max events on one edge in the window before `resource_exhaustion` fires |
| `--window-size` | `180.0` | Sliding window in seconds |
| `--prevent-cyclic-delegation` | off | Enable Prevent Mode (see above) |
| `--prevent-max-rotations` | off | Trip Prevent Mode at exactly N rotations regardless of severity |

Run `python ...sidecar.py --help` for the full list.

## Troubleshooting

| Symptom | Cause | Fix |
|---|---|---|
| `recordDelegation is not a function` | Old npm package | `npm install @agentsonar/oma@0.2.2` (or later) |
| `TypeError: monitor_orchestrator() got an unexpected keyword argument 'adapter'` | Old `agentsonar` (`< 0.4.1`) | `pip install --upgrade "agentsonar>=0.4.1"` |
| Sidecar prints nothing when bus fires | Sidecar not actually running OR firewall blocking localhost | `curl http://localhost:8787/health` should return `{"status":"ok"}` |
| Events fire but no report file | Forgot to call `shutdown()` on app exit | Add the SIGINT handler from Step 4 |
| `ModuleNotFoundError: agentsonar` when running sidecar | Python venv mismatch (sidecar running in a Python without the package) | Run `which python` and `python -c "import agentsonar"` in the same shell |
| `npm install` succeeds but `node` can't find the package | Project's `package.json` doesn't have `"type": "module"` and you're using `import` | Add `"type": "module"` OR use `import('@agentsonar/oma').then(...)` |

## End-user packaging

The setup above requires Python 3.10+ on the user's machine. That's fine for:

- Development on your own machines
- CI environments
- Internal tools your team runs
- Power users installing your app from source

It is **not** ideal for shipping a packaged Electron binary to end users who don't have Python (or don't want to install it).

A pure-JS AgentSonar SDK (no Python sidecar) is on the post-0.5 roadmap. Estimated timeline once prioritized: 4-6 weeks. If you're shipping to consumer Electron and need it sooner, [open an issue](https://github.com/agentsonar/agentsonar/issues/new?template=feature_request.yml) describing your use case. Design partner slots are available with priority feature requests in exchange for monthly feedback.

## Reference

- **npm package**: [npmjs.com/package/@agentsonar/oma](https://www.npmjs.com/package/@agentsonar/oma)
- **PyPI package**: [pypi.org/project/agentsonar](https://pypi.org/project/agentsonar/)
- **GitHub**: [github.com/agentsonar/agentsonar](https://github.com/agentsonar/agentsonar)
- **Discord**: [discord.gg/cPPD4xHe](https://discord.gg/cPPD4xHe)
- **Full docs**: [docs/](../README.md)
- **Concepts (what's a coordination failure?)**: [docs/concepts.md](../concepts.md)
- **Configuration reference**: [docs/configuration.md](../configuration.md)
- **Prevent Mode walkthrough**: [docs/prevent-mode.md](../prevent-mode.md)

## Working example

A complete, runnable Electron-style example with a fake bus, two agents, and a stuck loop that triggers detection:

```javascript
// integration-example.mjs
import { EventEmitter } from 'events'
import { recordDelegation, shutdown } from '@agentsonar/oma'

class AgentBus extends EventEmitter {
  send(fromAgent, toAgent, message) {
    this.emit(`agent:${toAgent}`, { from: fromAgent, message })
    recordDelegation(fromAgent, toAgent).catch(() => {})
  }
}

const bus = new AgentBus()

// Pretend Reviewer + Builder are agents that get stuck in a review loop
let rounds = 0
bus.on('agent:builder', () => {
  if (rounds++ >= 30) return
  setImmediate(() => bus.send('builder', 'reviewer', 'draft'))
})
bus.on('agent:reviewer', () => {
  setImmediate(() => bus.send('reviewer', 'builder', 'needs more work'))
})

// Kick off the loop
bus.send('main', 'reviewer', 'review the draft')

// After 2 seconds, shutdown so the report writes
setTimeout(async () => {
  await shutdown()
  console.log('Done. Open agentsonar_logs/run-<latest>/report.html in a browser.')
  process.exit(0)
}, 2000)
```

Run it:

```bash
# Terminal 1
python node_modules/@agentsonar/oma/sidecar/sidecar.py

# Terminal 2
node integration-example.mjs
```

After 2 seconds, open the latest report in `agentsonar_logs/`. You'll see the cycle detected with both `cyclic_delegation` (CRITICAL at 15 rotations) and `resource_exhaustion` (the rate limiter firing on the tight loop).

## Questions / blockers

If anything in this guide breaks or doesn't fit your setup, the fastest path to a fix:

1. **Discord** ([discord.gg/cPPD4xHe](https://discord.gg/cPPD4xHe)) for synchronous help
2. **GitHub issue** ([new issue](https://github.com/agentsonar/agentsonar/issues/new)) for anything reproducible
3. **Email** [agentsonarai@gmail.com](mailto:agentsonarai@gmail.com) for design partner inquiries or anything not public

The team responds same-day on weekdays.
