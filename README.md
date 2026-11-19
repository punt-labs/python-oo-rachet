# oo-ratchet

The Punt Labs quality ratchets for Python repos, extracted from the copies that
lived in `tools/` of vox, quarry, lux and z-spec. One installable package, one
CLI, three gates:

| Gate | Command | Rule |
|------|---------|------|
| OO metrics | `oo-ratchet oo <src> --check` | must-improve: no metric regresses on a touched file and at least one improves |
| Coupling/cohesion | `oo-ratchet coupling <src> --check` | regression-only |
| Suppressions | `oo-ratchet suppressions <src> --check` | regression-only on the total `noqa` / `type: ignore` / `pylint: disable` / `pyright: ignore` / per-file-ignores count |

Every gate compares against the baseline committed at the merge base, fails
closed when the base or baseline cannot be read, and only loosens through
audited operations (`--relax`, `--rebaseline-files`, `--rebaseline`). The
policy it enforces is
[`python-oo-adoption.md`](https://github.com/punt-labs/punt-kit/blob/main/lang-rules/python/python-oo-adoption.md)
in punt-kit; the formal model is [`docs/ratchet.tex`](docs/ratchet.tex).

## Install

```bash
uv add --dev "oo-ratchet @ git+https://github.com/punt-labs/oo-ratchet@v0.1.0"
```

Requires Python 3.13+. No runtime dependencies.

## Use

```make
check-oo:
	uv run oo-ratchet oo src/pkg/ --check $(OO_BASE)
update-oo:
	uv run oo-ratchet oo src/pkg/ --update $(OO_BASE)
check-coupling:
	uv run oo-ratchet coupling src/pkg/ --check $(COUPLING_BASE)
check-suppressions:
	uv run oo-ratchet suppressions src/pkg/ --check $(SUPPRESSION_BASE)
```

CI passes `--base-ref origin/main --require-base` on PRs. On the post-merge
`push: [main]` run, pass `--tripwire` to the coupling gate so the one-time
adoption merge bootstrap-passes. `oo-ratchet <gate> --help` lists each gate's
flags. Baseline and audit files (`.oo-baseline.json`, `.oo-audit.jsonl`,
`.oo-coupling-baseline.json`, ...) keep the same names as the embedded copies,
so a repo switches over without rebaselining.

## Provenance

Seeded from vox (`tools/oo_ratchet`, `tools/coupling`, `tools/suppression`),
then merged:

- **quarry**: extraction provenance for new zero-class modules (`diffmodel.py`,
  `provenance.py`), coupling `--tripwire`, `tokenize`-based suppression scan.
- **lux**: `--rebaseline-files` bounded bless with over-cap carry (`bless.py`),
  vanished-row cleanup on `--update`, removed rows recorded in the audit log.
- **new here**: unreadable or non-UTF-8 files become error rows instead of
  crashing the OO scorer (PL-778).

## Develop

```bash
uv sync
make check   # ruff, mypy, pyright (tests), full pytest suite
```
