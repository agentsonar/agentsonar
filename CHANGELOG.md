# Changelog

All notable changes to AgentSonar are documented here. Format follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/), versioning
follows [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

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
