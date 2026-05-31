# Claude Code adapter

AgentSonar plugs into Claude Code through its hooks system. It watches the
tool calls and subagent activity in a session as coordination events, in real
time, and writes a session report you can open in a browser. It works the same
way in **both the Claude Code terminal CLI and the Claude Code desktop app** —
both read the same `.claude/settings.json` hooks, so a single setup covers both.

It is **content-blind**: tool inputs, tool outputs, prompts, and file contents
are never read, logged, or persisted. AgentSonar only sees the *shape* of the
activity — which tool ran, when, whether it succeeded, how subagents fanned out.

## Install

```bash
pip install agentsonar
agentsonar install-claude-hooks
# (or: `python -m agentsonar install-claude-hooks` — works without `agentsonar`
#  on PATH, helpful on Windows or inside an unactivated virtual environment)
```

`install-claude-hooks` writes the right hooks into `.claude/settings.json` for
you in one command. It is **merge-safe**: existing non-AgentSonar hooks and any
other settings are preserved, and re-running it never double-registers. By
default it writes to `./.claude/settings.json`; pass `--path` to target a
different location (for example a user-level `~/.claude/settings.json`).

Start a fresh Claude Code session after installing so the hooks load.

## Manual setup

If you'd rather wire it by hand, add this `hooks` block to your
`.claude/settings.json`. This is exactly what `install-claude-hooks` writes —
the minimal set of events AgentSonar needs, nothing more:

```json
{
  "hooks": {
    "PreToolUse": [
      { "matcher": "*", "hooks": [ { "type": "command", "command": "python -m agentsonar claude-code-hook PreToolUse", "timeout": 60 } ] }
    ],
    "PostToolUse": [
      { "matcher": "*", "hooks": [ { "type": "command", "command": "python -m agentsonar claude-code-hook PostToolUse", "timeout": 60 } ] }
    ],
    "PostToolUseFailure": [
      { "matcher": "*", "hooks": [ { "type": "command", "command": "python -m agentsonar claude-code-hook PostToolUseFailure", "timeout": 60 } ] }
    ],
    "Stop": [
      { "hooks": [ { "type": "command", "command": "python -m agentsonar claude-code-hook Stop", "timeout": 60 } ] }
    ],
    "SubagentStop": [
      { "hooks": [ { "type": "command", "command": "python -m agentsonar claude-code-hook SubagentStop", "timeout": 60 } ] }
    ]
  }
}
```

`.claude/settings.json` must be strict JSON — no comments, no trailing commas —
or Claude Code silently ignores it.

Why these five and not more: each one feeds detection, and nothing here is
noise. `PreToolUse` is the one that sees every tool call (and is where Prevent
Mode can block); `PostToolUse` / `PostToolUseFailure` close out each call so a
finished tool isn't mistaken for a hung one and so repeated failures are caught;
`Stop` and `SubagentStop` are low-frequency lifecycle events that regenerate the
report and keep the subagent count honest. AgentSonar deliberately does **not**
subscribe to `UserPromptSubmit`, `Notification`, or the compaction hooks — they
carry no coordination signal and would only add overhead.

`timeout` is in **seconds** (60 here), comfortably above AgentSonar's own
internal lock timeout so a hook is never killed mid-write.

> **Performance note (optional).** On recent Claude Code builds you can add
> `"async": true` to the `PostToolUse` and `PostToolUseFailure` command entries
> so those two run fully in the background, off the tool-call hot path. Leave
> `PreToolUse` synchronous — Prevent Mode blocks a tool call by exiting there,
> which only works on a blocking hook. Older builds simply ignore the flag.

## What gets detected

The full coordination-failure surface applies — AgentSonar watches the shape of
the tool and subagent traffic, not the content:

- **Silent loops** — work bouncing between agents/steps forever with no progress.
- **Repeated calls** — the same agent or tool invoked over and over with the same input.
- **Traffic spikes** — a sudden burst of calls wildly out of pattern.
- **Redundant work** — the same tool called again with identical arguments, returning nothing new.
- **Stuck / hung tool calls** — a tool (including a hung MCP server) that starts and never returns.
- **Subagent explosion** — a runaway fan-out of subagents spawned at once.
- **Failed-tool retry storms** — an agent hammering the same failing tool or endpoint.
- **Context-window cliff** — the session filling the model's context window toward quality degradation and the next autocompact, read from the real token counts in the transcript.

## Prevent Mode

Prevent Mode is opt-in. When a failure crosses the limit you set, AgentSonar can
stop the run *before* the next tool call. On Claude Code it surfaces two ways,
chosen by the `AGENTSONAR_PREVENT_DECISION` environment variable:

- **`ask` (default)** — AgentSonar emits a `permissionDecision: "ask"` response,
  so Claude Code prompts *you* ("AgentSonar flagged a possible … — approve, or
  stop and rethink?"). Non-destructive; you stay in the loop. Surfaced once per
  edge per session so it doesn't nag.
- **`deny`** — AgentSonar hard-blocks the tool call (the hook exits with code 2,
  which Claude Code treats as "block this call") and prints why on stderr.

Arm a class with its env knob, e.g.:

```bash
# block a runaway loop after 3 rotations
export AGENTSONAR_PREVENT_CYCLE_MAX_ROTATIONS=3
# or turn on prevention for every class at once
export AGENTSONAR_PREVENT_ALL=1
# choose the surface (default is ask)
export AGENTSONAR_PREVENT_DECISION=deny
```

Each failure class has its own knob (`AGENTSONAR_PREVENT_<CLASS>_<KEY>`); see
[`../prevent-mode.md`](../prevent-mode.md) and [`../configuration.md`](../configuration.md)
for the full list.

## Privacy / content-blind contract

AgentSonar never reads or stores tool input bodies, tool output bodies, prompts,
or file contents — only identifiers and counts (tool name, timestamps,
success/error, subagent type). For regulated environments, set
`AGENTSONAR_REGULATED=1` and file paths are stored as SHA-256 hashes instead of
cleartext.

## Output

A Claude Code session writes a canonical, append-only event log plus the usual
reports under your home directory:

```
~/.agentsonar/sessions/<session-id>/
├── timeline.jsonl     # append-only event record (schema v1.0.0)
├── alerts.log
├── report.json
└── report.html        # open this
```

The report is regenerated cumulatively when the root session ends, so a
long-running session (Claude Code sessions can run for days) keeps an
up-to-date `report.html` rather than one report per turn.

## See also

- [Concepts](../concepts.md): what counts as a coordination failure.
- [Prevent Mode](../prevent-mode.md): the full auto-stop / ask walkthrough.
- [Configuration](../configuration.md): every config knob and environment variable.
- [FAQ](../faq.md)
