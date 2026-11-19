"""Per-metric differences between a coupling baseline and current scores."""

from __future__ import annotations

from .thresholds import CouplingThresholds

Rows = dict[str, dict[str, float]]
Deltas = dict[str, dict[str, list[float]]]


class BaselineDelta:
    """Static diffs used to audit an unconditional coupling ``--rebaseline``."""

    @staticmethod
    def changes(old_rows: Rows, current: Rows) -> Deltas:
        """Return ``{file: {metric: [old, new]}}`` for every changed or new metric."""
        changes: Deltas = {}
        for path, entry in current.items():
            old = old_rows.get(path, {})
            diff = {
                m: [old.get(m, 0.0), v] for m, v in entry.items() if old.get(m) != v
            }
            if diff:
                changes[path] = diff
        return changes

    @staticmethod
    def tally(old_rows: Rows, deltas: Deltas) -> tuple[int, int]:
        """Count files with a gain and no regression, and files with a regression."""
        improved = regressed = 0
        for path, diff in deltas.items():
            if path not in old_rows:
                continue
            worse = any(
                not CouplingThresholds.better_or_equal(m, new, old)
                for m, (old, new) in diff.items()
            )
            regressed += worse
            improved += not worse
        return improved, regressed
