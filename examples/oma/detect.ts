/**
 * AgentSonar OMA adapter, detection only.
 *
 * Setup:
 *   1. npm install @agentsonar/oma @open-multi-agent/core
 *   2. pip install agentsonar
 *   3. In one terminal:  python -m agentsonar.sidecar
 *   4. In another:       OPENAI_API_KEY=sk-... npx tsx detect.ts
 *
 * What you'll see:
 *   - As tasks delegate, the sidecar streams alerts to stderr.
 *   - On shutdown(), the sidecar writes the HTML report and exits.
 *
 * The AgentSonar wiring is two lines:
 *   - createTraceHandler() in your OMA constructor
 *   - emitDelegations(tasks) before runTasks()
 */
import { OpenMultiAgent } from '@open-multi-agent/core'
import { createTraceHandler, emitDelegations, shutdown } from '@agentsonar/oma'

const orchestrator = new OpenMultiAgent({
  defaultModel: 'gpt-4o-mini',
  onTrace: createTraceHandler(),
})

const team = orchestrator.createTeam({
  name: 'review-pipeline',
  agents: [
    { id: 'generator', systemPrompt: 'Write a 1-line draft.' },
    { id: 'reviewer',  systemPrompt: 'Review the draft. Reply APPROVE or REVISE.' },
  ],
})

const tasks = [
  { id: 't1', title: 'Draft',     assignee: 'generator' },
  { id: 't2', title: 'Review',    assignee: 'reviewer',  dependsOn: ['t1'] },
  { id: 't3', title: 'Revise',    assignee: 'generator', dependsOn: ['t2'] },
  { id: 't4', title: 'Re-review', assignee: 'reviewer',  dependsOn: ['t3'] },
]

await emitDelegations(tasks)
await orchestrator.runTasks(team, tasks)
await shutdown()
