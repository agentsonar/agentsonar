# Changelog

All notable changes to AgentSonar are documented here. Format follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/), versioning
follows [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.1.4] — Unreleased

### Changed
- PyPI metadata: added `Homepage`, `Repository`, `Issues`, and
  `Changelog` links pointing at this public repo so the PyPI page
  has a clear path to bug reports and documentation.

## [0.1.3] — 2026-04

### Fixed
- `__version__` string in `agentsonar/__init__.py` now matches the
  `version` field in `pyproject.toml` (was stale at `"0.1.0"` while
  the package had been published as `0.1.2`).

## [0.1.2] — 2026-04

### Changed
- README rewritten for the design-partner audience: shorter opening
  line with a token-budget hook, Configuration section collapsed
  under a `<details>` disclosure, Host safety section shrunk to the
  user-facing essentials (never crashes host, `AGENTSONAR_DISABLED`
  kill switch, degraded-mode flag).
- Moved `Calling shutdown()` to the top of the Output section —
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

## [0.1.0] — 2026-04

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
