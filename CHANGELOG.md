# Changelog

## [Unreleased]

### Added

- `oo-ratchet` package and CLI (`oo-ratchet {oo,coupling,suppressions}`), extracted from vox's `tools/` ratchets.
- Extraction provenance for new zero-class modules, coupling `--tripwire`, `tokenize`-based suppression scan (from quarry).
- `--rebaseline-files` bounded bless with over-cap carry, vanished-row cleanup, removed rows in the audit log (from lux).
- Order-independent (Tarjan) import-cycle detection; `BaseModel`, `@dataclass` and empty-`__slots__` classes exempt from LCOM (from lux).

### Fixed

- The OO scorer reports unreadable or non-UTF-8 files as error rows instead of crashing (PL-778).
