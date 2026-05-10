# The literal diff

Going from `before/pipeline.ts` (silent burn) to `after/detect.ts` (alerts on disk) is **one import + one constructor + one call per handoff**:

```diff
+ import { AgentSonar } from 'agentsonar'
+
+ const sonar = new AgentSonar({}, 'researcher-writer-reviewer')

  for (let i = 0; i < ROTATIONS; i++) {
+   sonar.delegation('researcher', 'writer')
    // ...your writer agent...
+   sonar.delegation('writer', 'reviewer')
    // ...your reviewer agent...
+   sonar.delegation('reviewer', 'researcher')
    // ...your researcher agent...
  }
+
+ sonar.shutdown()
```

That's it. WARNING fires at rotation 5, CRITICAL at 15, and `agentsonar_logs/run-<timestamp>/report.html` lands on disk.

## Adding Prevent Mode (auto-stop)

Going from `after/detect.ts` to `after/prevent.ts` is **one config field + a try/catch**:

```diff
- const sonar = new AgentSonar({}, 'researcher-writer-reviewer')
+ const sonar = new AgentSonar(
+   { prevent: { cyclicDelegation: { maxRotations: 10 } } },
+   'researcher-writer-reviewer',
+ )

+ try {
    for (let i = 0; i < ROTATIONS; i++) {
      sonar.delegation('researcher', 'writer')
      sonar.delegation('writer', 'reviewer')
      sonar.delegation('reviewer', 'researcher')
    }
+ } catch (err) {
+   if (err instanceof PreventError) {
+     console.log(`Stopped: ${err.reason}`)
+   } else {
+     throw err
+   }
+ }
```

`PreventError` throws at rotation 10. Your code catches it cleanly and stops before the next LLM call. Roughly **$9.67 saved** versus the `before` run.
