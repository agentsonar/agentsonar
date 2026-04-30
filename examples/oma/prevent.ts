/**
 * AgentSonar OMA adapter, with Prevent Mode.
 *
 * Setup:
 *   1. npm install @agentsonar/oma @open-multi-agent/core
 *   2. pip install agentsonar
 *   3. In one terminal:
 *        python -m agentsonar.sidecar --prevent-cyclic-delegation
 *   4. In another:
 *        OPENAI_API_KEY=sk-... npx tsx prevent.ts
 *
 * Note the --prevent-cyclic-delegation flag on the sidecar. That single
 * flag is what flips Prevent Mode on. The TypeScript code is identical
 * to detect.ts, plus a try/catch around emitDelegations() / runTasks().
 */
import { OpenMultiAgent } from '@open-multi-agent/core'
import {
  createTraceHandler,
  emitDelegations,
  shutdown,
  PreventError,
} from '@agentsonar/oma'

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

try {
  await emitDelegations(tasks)
  await orchestrator.runTasks(team, tasks)
} catch (e) {
  if (e instanceof PreventError) {
    console.error(`Stopped: ${e.reason}`)
    console.error(`Cycle:   ${e.cyclePath.join(' -> ')}`)
    console.error(`After:   ${e.rotations} rotations`)
  } else {
    throw e
  }
} finally {
  await shutdown()
}
