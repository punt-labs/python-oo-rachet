"""Coupling/cohesion thresholds and the direction-aware comparison semantics."""

from __future__ import annotations

from typing import ClassVar


class CouplingThresholds:
    """Coupling/cohesion thresholds plus the ordering semantics each obeys.

    ``__main__.py`` legitimately wires many modules and exposes many command
    names, so it gets relaxed ``efferent_coupling`` and ``public_names`` targets
    while every other metric keeps the strict table. ``caps`` (exact
    repo-relative path -> metric -> cap, from ``CouplingConfig``) override the
    target for the named files only.
    """

    TABLE: ClassVar[dict[str, tuple[str, float]]] = {
        "efferent_coupling": ("<=", 10),
        "public_names": ("<=", 15),
        "circular_imports": ("==", 0),
        "max_lcom": ("<=", 0.8),
        "avg_lcom": ("<=", 0.5),
    }

    MAIN_TABLE: ClassVar[dict[str, tuple[str, float]]] = {
        "public_names": ("<=", 100),
        "efferent_coupling": ("<=", 15),
    }

    # Metrics whose aggregate is the worst (max) across files; the rest average.
    MAX_AGGREGATED: ClassVar[frozenset[str]] = frozenset(
        {"efferent_coupling", "public_names", "circular_imports", "max_lcom"}
    )

    @classmethod
    def names(cls) -> tuple[str, ...]:
        """Return the tracked metric names in table order."""
        return tuple(cls.TABLE)

    @classmethod
    def describe(cls, metric: str) -> str:
        """Return a human-readable ``op target`` label for a metric."""
        op, target = cls.TABLE[metric]
        return f"{op} {target}"

    @classmethod
    def target_for(
        cls,
        metric: str,
        filepath: str = "",
        caps: dict[str, dict[str, float]] | None = None,
    ) -> tuple[str, float]:
        """Return the ``(op, target)`` that ``filepath`` is judged against."""
        return cls._table_for(filepath, caps)[metric]

    @classmethod
    def _table_for(
        cls, filepath: str, caps: dict[str, dict[str, float]] | None = None
    ) -> dict[str, tuple[str, float]]:
        table = dict(cls.TABLE)
        if filepath.endswith("__main__.py"):
            table.update(cls.MAIN_TABLE)
        for metric, cap in (caps or {}).get(filepath, {}).items():
            op = cls.TABLE[metric][0]
            table[metric] = ("<=" if op == "==" else op, cap)
        return table

    @classmethod
    def meets(
        cls,
        metric: str,
        value: float,
        filepath: str = "",
        caps: dict[str, dict[str, float]] | None = None,
    ) -> bool:
        """Return whether value satisfies the metric's absolute threshold."""
        table = cls._table_for(filepath, caps)
        if metric not in table:
            return True
        op, target = table[metric]
        if op == ">=":
            return value >= target
        if op == "<=":
            return value <= target
        return value == target

    @classmethod
    def better_or_equal(cls, metric: str, current: float, baseline: float) -> bool:
        """Return whether current is at least as good as baseline."""
        op, target = cls.TABLE[metric]
        if op == ">=":
            return current >= baseline
        if op == "<=":
            return current <= baseline
        return abs(current - target) <= abs(baseline - target)

    @classmethod
    def strictly_better(cls, metric: str, current: float, baseline: float) -> bool:
        """Return whether current is strictly better than baseline."""
        op, target = cls.TABLE[metric]
        if op == ">=":
            return current > baseline
        if op == "<=":
            return current < baseline
        return abs(current - target) < abs(baseline - target)
