"""The coupling ``--rebaseline-files`` bless: bounded, scoped, tool-computed.

A genuinely-necessary new dependency edge that stays within its absolute cap
may be recorded even though ``--update`` refuses any regression. A metric
refuses only when it BOTH exceeds its cap (per-file ``caps`` included) AND
regressed against the file's baseline committed at the comparison base (the
one ``--check`` uses, so the recorded waiver matches); every recorded number comes
from the scorer; only the named paths are touched; and each bless appends a
``"rebaseline-files"`` audit entry carrying the caller's ``reason``.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Self

from .audit import CouplingAudit
from .baseline import CouplingBaseline
from .gitio import GitRepo
from .outcome import Outcome
from .thresholds import CouplingThresholds


class CouplingBless:
    """Gate, write, audit, and report one coupling ``--rebaseline-files`` call."""

    _root: Path
    _baseline: CouplingBaseline
    _audit: CouplingAudit
    _git: GitRepo
    _caps: dict[str, dict[str, float]]
    _renames: dict[str, str]
    _reference: dict[str, dict[str, float]] | None

    def __new__(
        cls,
        root: Path,
        git: GitRepo,
        caps: dict[str, dict[str, float]] | None = None,
    ) -> Self:
        self = super().__new__(cls)
        self._root = root
        self._baseline = CouplingBaseline(root)
        self._audit = CouplingAudit(root)
        self._git = git
        self._caps = caps or {}
        self._renames = {}
        self._reference = None
        return self

    def apply(
        self,
        current: dict[str, dict[str, float]],
        paths: list[str],
        *,
        reason: str,
        source: str | None,
        allow_ci_write: bool = False,
        base_ref: str | None = None,
        require_base: bool = False,
    ) -> Outcome:
        """Bless every named path that clears the gate; exit 1 if any refused."""
        blocked = self._precondition(reason, allow_ci_write=allow_ci_write)
        if blocked is not None:
            return blocked
        loaded = self._load_base(base_ref, require_base=require_base)
        if loaded is not None:
            return loaded
        accepted, refused = self._partition(current, paths)
        if accepted:
            self._write(accepted, current, reason=reason, source=source)
        return self._report(accepted, refused, reason)

    @staticmethod
    def _precondition(reason: str, *, allow_ci_write: bool) -> Outcome | None:
        if os.environ.get("GITHUB_ACTIONS") == "true" and not allow_ci_write:
            return Outcome.failed(
                "FAIL: refusing to write coupling baseline under GITHUB_ACTIONS "
                "without --allow-ci-write"
            )
        if not reason.strip():
            return Outcome.failed("FAIL: --rebaseline-files requires --reason <text>")
        return None

    def _load_base(self, base_ref: str | None, *, require_base: bool) -> Outcome | None:
        """Load renames and the base-committed baseline the next check uses.

        An explicit ``--base-ref`` that does not resolve, or no base under
        ``--require-base``, fails; with no base at all (local first adoption)
        the worktree baseline is the reference.
        """
        base = self._git.resolve_base(base_ref)
        if base is None:
            if base_ref is not None:
                return Outcome.failed(f"FAIL: cannot resolve --base-ref {base_ref}")
            if require_base:
                return Outcome.failed(
                    "FAIL: base ref unresolvable and --require-base is set"
                )
            return None
        reference = self._git.show_baseline(base)
        if not reference and require_base:
            return Outcome.failed(
                "FAIL: no coupling baseline at the base and --require-base is set"
            )
        self._renames = self._git.diff(base).renames
        self._reference = reference or {}
        return None

    @staticmethod
    def _report(
        accepted: list[str], refused: list[tuple[str, str]], reason: str
    ) -> Outcome:
        lines = [f"\nBaseline blessed for {len(accepted)} file(s) (reason: {reason}):"]
        lines.append("  files:" if accepted else "  (none)")
        lines.extend(f"    {path}" for path in accepted)
        if refused:
            lines.append(f"  REFUSED ({len(refused)} file(s), nothing written):")
            lines.extend(f"    {path}: {why}" for path, why in refused)
        return Outcome(1 if refused else 0, tuple(lines))

    def over_cap_and_regressed(
        self, path: str, entry: dict[str, float], base: dict[str, float] | None
    ) -> list[str]:
        """Return the metrics over ``path``'s cap that also regressed vs ``base``.

        With no baseline value to grandfather against, any over-cap value
        refuses.
        """
        return [
            metric
            for metric, value in entry.items()
            if not CouplingThresholds.meets(metric, value, path, self._caps)
            and (
                base is None
                or metric not in base
                or not CouplingThresholds.better_or_equal(metric, value, base[metric])
            )
        ]

    def _partition(
        self, current: dict[str, dict[str, float]], paths: list[str]
    ) -> tuple[list[str], list[tuple[str, str]]]:
        index = {(self._root / key).resolve(): key for key in current}
        accepted: list[str] = []
        refused: list[tuple[str, str]] = []
        for requested in paths:
            path = self._resolve(requested, current, index)
            if path is None:
                refused.append((requested, "not found in scored tree"))
                continue
            entry = current[path]
            gated = self.over_cap_and_regressed(path, entry, self._base_for(path))
            if gated:
                refused.append((requested, self._gate_detail(path, entry, gated)))
                continue
            if path not in accepted:
                accepted.append(path)
        return accepted, refused

    def _base_for(self, path: str) -> dict[str, float] | None:
        """Return ``path``'s row at the base (following a rename).

        Only with no resolvable base does the worktree baseline stand in.
        """
        if self._reference is None:
            return self._baseline.get(path)
        return self._reference.get(self._renames.get(path, path))

    def _resolve(
        self,
        requested: str,
        current: dict[str, dict[str, float]],
        index: dict[Path, str],
    ) -> str | None:
        if requested in current:
            return requested
        path = Path(requested)
        if not path.is_absolute():
            hit = index.get((self._root / path).resolve())
            if hit is not None:
                return hit
        return index.get(path.resolve())

    def _gate_detail(self, path: str, entry: dict[str, float], gated: list[str]) -> str:
        parts = []
        for metric in gated:
            op, target = CouplingThresholds.target_for(metric, path, self._caps)
            parts.append(
                f"{metric}={entry[metric]:g} fails {op} {target:g} "
                "(over cap and regressed)"
            )
        return "; ".join(parts)

    def _write(
        self,
        accepted: list[str],
        current: dict[str, dict[str, float]],
        *,
        reason: str,
        source: str | None,
    ) -> None:
        new_baseline = dict(self._baseline.entries)
        waived: dict[str, dict[str, list[float]]] = {}
        gains: dict[str, dict[str, list[float]]] = {}
        for path in accepted:
            entry = current[path]
            base = self._base_for(path) or {}
            regressed = self._regressed(entry, base)
            if regressed:
                waived[path] = regressed
            better = self._improved(entry, base)
            if better:
                gains[path] = better
            self._record(new_baseline, path, entry)
        self._baseline.save(new_baseline)
        self._audit.append(
            files_scored=len(accepted),
            files_improved=len(gains.keys() - waived.keys()),
            files_regressed=len(waived),
            verdict="rebaseline-files",
            deltas=waived,
            improved=gains,
            commit=self._git.short_head(),
            source=source,
            reason=reason,
        )

    def _record(
        self,
        new_baseline: dict[str, dict[str, float]],
        path: str,
        entry: dict[str, float],
    ) -> None:
        """Write ``path``'s row, dropping the row it was renamed from."""
        old = self._renames.get(path)
        if old is not None and old != path:
            new_baseline.pop(old, None)
        new_baseline[path] = entry

    @staticmethod
    def _regressed(
        entry: dict[str, float], base: dict[str, float]
    ) -> dict[str, list[float]]:
        """Return ``[old, new]`` for each metric worse than ``base`` -- the waiver."""
        return {
            m: [base[m], entry[m]]
            for m in entry
            if m in base
            and not CouplingThresholds.better_or_equal(m, entry[m], base[m])
        }

    @staticmethod
    def _improved(
        entry: dict[str, float], base: dict[str, float]
    ) -> dict[str, list[float]]:
        """Return ``[old, new]`` for each metric better than ``base``, audit-only."""
        return {
            m: [base[m], entry[m]]
            for m in entry
            if m in base and CouplingThresholds.strictly_better(m, entry[m], base[m])
        }
