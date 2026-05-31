# Changelog

All notable changes to AgentSonar are documented here. Format follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/), versioning
follows [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.6.9]: 2026-05-30

### Added
- Session browser CLI for the Claude Code adapter. `agentsonar reports` lists
  every session, newest first, with a memorable slug, timestamp, alert counts,
  top failure class, and the project it ran in. `agentsonar open [id|slug]`
  opens a session's `report.html` in your browser (defaults to the most
  recent). Both are read-only and never touch the detection hot path.

## [0.6.8]: 2026-05-30

### Changed
- The Claude Code adapter now ships coding-workload-calibrated detector
  defaults: `agent_stall` warns at 120s / critical at 300s (up from 30s / 120s)
  and `subagent_explosion` concurrent defaults to 8 (up from 5). These cut
  false alerts on ordinary coding sessions and remain overridable with the
  usual `AGENTSONAR_*` env vars. Other adapters keep the generic defaults.

### Fixed
- Corrected the bundled Claude Code settings template's hook `timeout` from
  `5000` to `60` (Claude Code reads the value in seconds).

## [0.6.7]: 2026-05-29

### Fixed
- Claude Code: subagent-explosion now counts genuinely concurrent subagents
  correctly. Each spawn is keyed by its unique tool-call id, so a burst of
  parallel subagents trips detection (and Prevent Mode) as intended, and
  sequential subagents no longer accumulate into a false alarm.

## [0.6.6]: 2026-05-28

### Changed
- Prevent Mode on Claude Code now defaults to "ask": when a failure trips,
  Claude Code prompts you to approve the tool call or stop, rather than hard
  blocking. Set `AGENTSONAR_PREVENT_DECISION=deny` for the hard block (exit 2).
- Alert severity scales with magnitude, so a brief stall and a long one no
  longer look identical.

## [0.6.5]: 2026-05-27

### Added
- Context-window cliff detection: AgentSonar warns as a session fills the
  model's context window toward quality degradation and the next autocompact,
  using the real token counts (LangGraph via `on_llm_end`, Claude Code via the
  session transcript).
- Failed-tool retry storm detection: catches an agent hammering the same
  failing tool or endpoint instead of stopping.

## [0.6.3]: 2026-05-24

### Added
- Redundant-work detection: the same tool called again with identical
  arguments, returning nothing new.
- Subagent-explosion detection: a runaway fan-out of subagents spawned at once.
- Stuck / hung tool-call detection (agent stalling), including hung MCP servers.

## [0.6.0]: 2026-05-21

### Added
- Prevent Mode generalized to every shipped failure class (previously cyclic
  delegation only). Arm any class with its own threshold, or `prevent_all` to
  arm them all at once. `check_prevent()` raises `PreventError` before the next
  call.

## [0.5.0]: 2026-05-17

### Added
- Claude Code adapter. AgentSonar plugs into Claude Code through its hooks
  system and runs in both the terminal CLI and the desktop app. Install with
  `agentsonar install-claude-hooks` (merge-safe). Content-blind: tool inputs,
  outputs, prompts, and file contents are never read or stored.

## [0.4.1]: 2026-05-02

### Fixed
- **`monitor_orchestrator()` now accepts an `adapter` keyword argument.**
  The 0.4.0 release shipped without this parameter, which made it
  incompatible with `@agentsonar/oma` 0.2.1+ (the bundled sidecar calls
  `monitor_orchestrator(_config, adapter="oma_sidecar")` to tag OMA
  sessions correctly in telemetry). On 0.4.0 this raised
  `TypeError: monitor_orchestrator() got an unexpected keyword argument
  'adapter'` the moment the sidecar tried to start. Anyone running OMA
  with `agentsonar==0.4.0` should upgrade to 0.4.1.

### Added
- New TypeScript export in companion `@agentsonar/oma 0.2.2`:
  `recordDelegation(source, target, opts?)`. Event-stream-oriented
  primitive for Node bus / Electron / EventEmitter integrations where
  the existing `emitDelegations(tasks)` (task-DAG-oriented) doesn't
  fit. See [`docs/integrations/electron-node-bus.md`](docs/integrations/electron-node-bus.md)
  for the full integration guide.

### Compatibility note
- `agentsonar==0.4.1` paired with `@agentsonar/oma==0.2.2` is the
  recommended combination. Older pairs (`0.4.0` + `0.2.1`) will fail at
  sidecar startup; upgrade both.

## [0.4.0]: 2026-05-01

### Added
- **Anonymous session-event telemetry.** AgentSonar now sends one
  fire-and-forget event per session start to a self-hosted Cloudflare
  Worker so we can answer "how many real humans are using this?"
  without depending on PyPI download counts (which are dominated by
  CI/CD traffic). The event contains only `install_id` (random UUID
  stored in `~/.agentsonar/state.json`), `session_id`, `version`,
  `python` (e.g. "3.12"), `os`, `arch`, and `adapter` name. It never
  sends agent names, prompts, log content, or project paths.
- First-run disclosure printed once to stderr the first time AgentSonar
  runs on a machine, with clear opt-out instructions. Subsequent runs
  are silent.
- Three opt-out paths, all honored:
  - `AGENTSONAR_TELEMETRY=off` (or `0`/`false`/`no`/`disabled`)
  - `DO_NOT_TRACK=1` (the universal opt-out signal)
  - `monitor_orchestrator(config={"telemetry": False})` (persists across
    runs via the state file)
- `enable_persistently()` symmetric counterpart to `disable_persistently()`,
  so `config={"telemetry": True}` clears any prior opt-out.
- `_version.py` as the single source of truth for `__version__`. Both
  `agentsonar/__init__.py` and `agentsonar._core.engine` import from
  here, eliminating the version-sync bug we hit in earlier releases.
- `adapter` kwarg on `monitor_orchestrator()` and `CustomAdapter` for
  embedded contexts (e.g. the OMA sidecar identifies itself as
  `oma_sidecar` instead of `custom_python` for accurate attribution).
- 50 new tests covering telemetry behavior, including: env var
  precedence, persistent state, concurrent state writes, malformed
  state files, daemon-thread invariants, network failure swallowing,
  and the cardinal rule (engine constructs cleanly even if
  `_telemetry.py` itself fails to import).

### Changed
- `DetectionEngine.__init__` now accepts an `adapter: str` kwarg
  defaulting to `"unknown"`. Each integration passes its own name
  (`custom_python`, `crewai`, `langgraph`, `oma_sidecar`).
- `_load_state()` now validates that the loaded JSON is a dict before
  returning, so a malformed `state.json` (containing `null`, a list,
  a string, etc.) is treated as empty rather than crashing callers.
- `_save_state()` uses a unique per-thread temp filename
  (`state.json.tmp.{pid}.{tid}`) to prevent two concurrent writers
  from corrupting each other's tmp file.
- `_telemetry` is lazy-imported inside `DetectionEngine.__init__` so
  any future bug in the telemetry module cannot prevent the engine
  from constructing. Detection survives even if telemetry is
  completely unloadable.

### Documentation
- New `/telemetry` page on the website documenting exactly what's
  sent, what's never sent, four ways to disable, and why we collect
  any of this.
- FAQ section in `docs/faq.md` rewritten to reflect the new telemetry
  posture.
- README install section now carries a one-line heads-up about
  telemetry with the disable command inline.

## [0.2.0 to 0.3.3]: 2026-04

These versions were not individually documented in this changelog.
Headline changes: Prevent Mode shipped (0.2.0+), CrewAI / LangGraph /
OMA TypeScript adapters, comprehensive `docs/` folder with adapter
guides and concept walkthroughs.

## [0.1.4]: Unreleased

### Changed
- PyPI metadata: added `Homepage`, `Repository`, `Issues`, and
  `Changelog` links pointing at this public repo so the PyPI page
  has a clear path to bug reports and documentation.

## [0.1.3]: 2026-04

### Fixed
- `__version__` string in `agentsonar/__init__.py` now matches the
  `version` field in `pyproject.toml` (was stale at `"0.1.0"` while
  the package had been published as `0.1.2`).

## [0.1.2]: 2026-04

### Changed
- README rewritten for the design-partner audience: shorter opening
  line with a token-budget hook, Configuration section collapsed
  under a `<details>` disclosure, Host safety section shrunk to the
  user-facing essentials (never crashes host, `AGENTSONAR_DISABLED`
  kill switch, degraded-mode flag).
- Moved `Calling shutdown()` to the top of the Output section,
  it's the single most load-bearing thing users need to know about.
- Explicit HTML anchors (`<a id="...">`) added above five target
  headings so intra-doc links render correctly on PyPI.
- Removed all `examples/*.py` path references; examples don't ship
  in the wheel, so the pointers were misleading for pip-install users.

### Removed
- Internal JSON schema reference section (topology / fingerprint
  internals / cascade risk / interaction pattern enums). Those live
  in the private dev repo; design partners discover them by using
  the SDK.

## [0.1.0]: 2026-04

### Added
- Initial public beta release.
- Framework-agnostic detection engine with three live failure
  classes: `cyclic_delegation`, `repetitive_delegation`,
  `resource_exhaustion`.
- CrewAI integration (`AgentSonarListener`) via the CrewAI event bus.
- LangGraph / LangChain integration (`AgentSonarCallback` and the
  `monitor()` wrapper).
- Per-run session directories under `agentsonar_logs/` with four
  artifacts: `timeline.jsonl`, `alerts.log`, `report.json`,
  `report.html`.
- Clean-run signals on every channel (HTML banner, JSONL
  `clean_run: true`, stderr confirmation line).
- Host-safety guarantees: three-layer catch-all in `engine.ingest`,
  `build_engine_safely` fallback to `_NoOpEngine` on construction
  failure, `AGENTSONAR_DISABLED` environment kill switch.
- Standalone HTML report with dark mode, severity filtering, and an
  embedded Raw JSON view.
