# Changelog

## [Unreleased]

## [0.2.1] - 2026-11-18

### Fixed

- `stateless-values = "any"` now counts in-place writes to private collections (`self._x[k] = v`, `+=`, `del`, and mutator calls such as `self._x.append(...)` / `.update(...)`) as private state, so those classes are no longer exempted from LCOM.

## [0.2.0] - 2026-11-18

### Added (ported from lux)

- `[tool.oo-ratchet.coupling] stateless-values = "any"`: LCOM skips every class that writes no private `self._*` state, counting `object`/`super()`/`type(self)` `.__setattr__` writes as state.
- `[tool.oo-ratchet.coupling.caps]`: per-file metric caps keyed by exact repository-relative path, used by `--check`, the per-file report and the bless gate.
- `oo-ratchet coupling --rebaseline-files PATHS --reason TEXT`: bounded, audited bless of named files; refuses a metric that is both over its cap and regressed against the base-committed baseline.

- `oo-ratchet suppressions --rebaseline --reason TEXT [--source REF]`: audited reset of the suppression baseline to the current counts, the one write allowed to raise the total, e.g. after adopting a package version that counts differently (PL-1175).

### Changed

- LCOM's stateless-value check no longer looks inside nested classes, in either mode: an inner class's `self` stores don't block exempting its parent.
- The summary grades (and exit code) judge a capped file against its cap and `__main__.py` against its relaxed table, so they agree with the per-file report.

## [0.1.0] - 2026-11-18

### Added

- Published to PyPI as `punt-oo-ratchet` (CLI `oo-ratchet`) via `release.yml` trusted publishing.

### Fixed (Qodo review of #1)

- `--tripwire` on all three gates, and it fails when main has no baseline.
- Coupling: `from pkg import mod`, relative imports in `__init__.py`, nested-package efferent coupling; audit records removed paths.
- Git paths with non-ASCII names are no longer dropped from the diff.
- Extraction provenance counts repeated lines (multiset overlap).
- Suppressions: PEP 263 coding cookies, file-level directives (`# ruff: noqa`, leading `# type: ignore`, ...), `.` targets.
- Non-object audit lines raise the gate's audit error; single-file OO targets record an error row.
- `--rebaseline-files` resolves relative paths against the repo root.

### Added

- `oo-ratchet` package and CLI (`oo-ratchet {oo,coupling,suppressions}`), extracted from vox's `tools/` ratchets.
- Extraction provenance for new zero-class modules, coupling `--tripwire`, `tokenize`-based suppression scan (from quarry).
- `--rebaseline-files` bounded bless with over-cap carry, vanished-row cleanup, removed rows in the audit log (from lux).
- Order-independent (Tarjan) import-cycle detection; `BaseModel`, `@dataclass` and empty-`__slots__` classes exempt from LCOM (from lux).

### Fixed

- The OO scorer reports unreadable or non-UTF-8 files as error rows instead of crashing (PL-778).
