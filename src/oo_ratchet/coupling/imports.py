"""Resolve a module's imports of other modules within the same package."""

from __future__ import annotations

import ast
from typing import Self


class ImportResolver:
    """Find which internal package modules a single module imports.

    Owns the module's own key and the package's module set, so absolute
    (``import pkg.foo``), plain (``import sibling``), and relative
    (``from . import foo``, ``from ..bar import x``) imports all resolve to the
    same dotted keys the coupling graph uses. A ``None`` result means the import
    is external -- absence of an internal match is the resolver's contract.
    """

    _own_key: str
    _pkg_modules: frozenset[str]
    _pkg_name: str
    _is_package: bool

    def __new__(
        cls,
        own_key: str,
        pkg_modules: frozenset[str],
        pkg_name: str,
        *,
        is_package: bool = False,
    ) -> Self:
        self = super().__new__(cls)
        self._is_package = is_package
        self._own_key = own_key
        self._pkg_modules = pkg_modules
        self._pkg_name = pkg_name
        return self

    def internal_imports(self, tree: ast.Module) -> set[str]:
        """Return the internal module keys imported by ``tree``."""
        imported: set[str] = set()
        for node in ast.iter_child_nodes(tree):
            if isinstance(node, ast.Import):
                imported.update(self._plain(node))
            elif isinstance(node, ast.ImportFrom):
                imported.update(self._from(node))
        return imported

    def _plain(self, node: ast.Import) -> set[str]:
        out: set[str] = set()
        for alias in node.names:
            match = self._absolute(alias.name.split("."))
            if match is not None:
                out.add(match)
        return out

    def _from(self, node: ast.ImportFrom) -> set[str]:
        if node.level == 0:
            if node.module is None:
                return set()
            parts = node.module.split(".")
            found = {self._absolute(parts)}
            # ``from pkg import mod`` imports a module named by the alias.
            found.update(
                self._absolute([*parts, alias.name])
                for alias in node.names
                if alias.name != "*"
            )
            return {m for m in found if m is not None}
        if node.module is not None:
            match = self._relative_module(node.module, node.level)
            return {match} if match is not None else set()
        return self._relative_names(node.names, node.level)

    def _absolute(self, parts: list[str]) -> str | None:
        top = parts[0]
        if top in self._pkg_modules and top != self._own_key:
            return top
        if top == self._pkg_name and len(parts) > 1:
            return self._match_inner(parts[1:])
        return None

    def _match_inner(self, inner: list[str]) -> str | None:
        for i in range(len(inner), 0, -1):
            candidate = ".".join(inner[:i])
            if candidate in self._pkg_modules and candidate != self._own_key:
                return candidate
        return None

    def _relative_module(self, module: str, level: int) -> str | None:
        parent = self._parent(level)
        resolved = f"{parent}.{module}" if parent else module
        return self._pick((resolved, module.split(".")[0]))

    def _relative_names(self, names: list[ast.alias], level: int) -> set[str]:
        parent = self._parent(level)
        out: set[str] = set()
        for alias in names:
            resolved = f"{parent}.{alias.name}" if parent else alias.name
            match = self._pick((resolved, alias.name))
            if match is not None:
                out.add(match)
        return out

    def _parent(self, level: int) -> str:
        # A package ``__init__`` is keyed by the package itself, so ``.`` is it.
        # The root ``__init__`` is keyed "__init__", not by a package name.
        nested = self._is_package and self._own_key != "__init__"
        drop = level - 1 if nested else level
        if drop == 0:
            return self._own_key
        parts = self._own_key.rsplit(".", drop)
        return parts[0] if len(parts) > 1 else ""

    def _pick(self, candidates: tuple[str, ...]) -> str | None:
        for candidate in candidates:
            if candidate in self._pkg_modules and candidate != self._own_key:
                return candidate
        return None
