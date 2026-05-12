# Quickstart

Copy-paste only.

## Try the demo (5 seconds, either language)

```bash
# Python
pip install agentsonar && agentsonar demo

# Node
npm install agentsonar && npx agentsonar demo
```

Bundled hello-world: three agents loop forever in a silent failure, AgentSonar catches it at the 5th rotation, stops the run, and writes an HTML report you can open in your browser. No config required.

> **`agentsonar: command not found`?** Use `python -m agentsonar demo` — it's equivalent and works without `agentsonar` being on your PATH (helpful on Windows, in unactivated virtual environments, or in sandboxed installs).

## Python (5 lines)

```bash
pip install agentsonar
python -c "import agentsonar; print(agentsonar.__version__)"
```

```python
from agentsonar import monitor_orchestrator
sonar = monitor_orchestrator()
sonar.delegation(source="agent_a", target="agent_b")
sonar.delegation(source="agent_b", target="agent_a")
sonar.shutdown()
```

Then open `agentsonar_logs/run-<latest>/report.html`.

## Node / Electron (5 lines)

```bash
npm install agentsonar
node -e "import('agentsonar').then(m => console.log(Object.keys(m)))"
```

```javascript
import { recordDelegation, shutdown } from 'agentsonar'
await recordDelegation('agent_a', 'agent_b')
await recordDelegation('agent_b', 'agent_a')
await shutdown()
```

Then open `agentsonar_logs/run-<latest>/report.html`.

## Next

- Runnable before/after example: [`examples/custom-python/`](examples/custom-python/) or [`examples/langgraph/`](examples/langgraph/)
- Full docs: [`docs/README.md`](docs/README.md)
