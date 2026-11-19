# Changelog

## [Unreleased]

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
