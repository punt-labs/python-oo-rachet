"""Missing-row selection and accounting for scoped baseline updates."""

from __future__ import annotations

from pathlib import Path
from typing import Self, TypedDict


class BackfillMetadata(TypedDict, total=False):
    """The optional audit field for added out-of-diff rows."""

    backfilled: list[str]


class Backfill:
    """Add out-of-diff rows without inventing metric improvements."""

    _rows: dict[str, dict[str, float]]

    def __new__(
        cls,
        current: dict[str, dict[str, float]],
        existing: dict[str, dict[str, float]],
        touched: frozenset[str],
        renames: dict[str, str],
    ) -> Self:
        self = super().__new__(cls)
        paths = current.keys() - existing.keys() - touched - renames.keys()
        self._rows = {path: current[path] for path in sorted(paths)}
        return self

    @property
    def paths(self) -> list[str]:
        """Return the added rows in stable report order."""
        return list(self._rows)

    @property
    def metadata(self) -> BackfillMetadata:
        """Return audit-only metadata when rows were added."""
        return {"backfilled": self.paths} if self._rows else {}

    def apply(self, rows: dict[str, dict[str, float]]) -> None:
        """Populate missing rows separately from the metric-delta path."""
        rows.update(self._rows)

    def lines(self, exit_code: int) -> tuple[str, ...]:
        """Report backfills only for a successful update."""
        if exit_code:
            return ()
        return tuple(f"  backfilled: {path}" for path in self._rows)


class UpdateReport:
    """Describe accepted improvements, deletions, and refused files."""

    _lines: list[str]
    _failed: bool

    def __new__(cls, baseline: Path, improved: int, removed: int) -> Self:
        self = super().__new__(cls)
        self._lines = [
            f"\nBaseline updated: {baseline}",
            f"  files improved: {improved}",
            f"  files removed:  {removed}",
        ]
        self._failed = False
        return self

    def refuse(self, refused: list[tuple[str, str]], broken: list[str]) -> None:
        """Append per-file refusal diagnostics."""
        if broken:
            self._failed = True
            self._lines.append(f"  REFUSED ({len(broken)} unparseable, baseline kept):")
            self._lines.extend(f"    {p}: parse error" for p in broken)
        if refused:
            self._failed = True
            self._lines.append(f"  REFUSED ({len({p for p, _ in refused})} files):")
            self._lines.extend(f"    {p}: {m} regressed" for p, m in refused)

    @property
    def exit_code(self) -> int:
        """Return nonzero when any file was refused."""
        return int(self._failed)

    @property
    def lines(self) -> tuple[str, ...]:
        """Return the report's rendered lines."""
        return tuple(self._lines)
