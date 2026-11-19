"""Which top-level classes count toward ``classes_per_module``."""

from __future__ import annotations

import ast
from typing import ClassVar, Self


class ClassKinds:
    """Count a module's top-level classes, leaving out value and type shapes.

    Exceptions, enums, dataclasses, ``Protocol``s and ``TypedDict``s do not
    count: they are declarations that sit beside the module's real class
    rather than extra responsibilities.
    """

    _TYPE_BASES: ClassVar[frozenset[str]] = frozenset({"Protocol", "TypedDict"})
    _ENUM_BASES: ClassVar[frozenset[str]] = frozenset(
        {"Enum", "IntEnum", "StrEnum", "Flag", "IntFlag", "ReprEnum"}
    )
    _EXCEPTION_BASES: ClassVar[frozenset[str]] = frozenset(
        {"Exception", "BaseException"}
    )
    _EXCEPTION_SUFFIXES: ClassVar[tuple[str, ...]] = ("Error", "Exception", "Warning")

    _exempt: set[str]
    _count: int

    def __new__(cls, tree: ast.Module) -> Self:
        self = super().__new__(cls)
        self._exempt = set()
        self._count = 0
        for node in ast.iter_child_nodes(tree):
            if isinstance(node, ast.ClassDef):
                self._classify(node)
        return self

    @property
    def count(self) -> int:
        """Return how many top-level classes count toward the cap."""
        return self._count

    def _classify(self, node: ast.ClassDef) -> None:
        if self._is_exempt(node):
            self._exempt.add(node.name)
        else:
            self._count += 1

    def _is_exempt(self, node: ast.ClassDef) -> bool:
        if any(self._is_dataclass_decorator(d) for d in node.decorator_list):
            return True
        return any(self._is_exempt_base(self._base_name(b)) for b in node.bases)

    def _is_exempt_base(self, name: str | None) -> bool:
        if name is None:
            return False
        return (
            name in self._exempt
            or name in self._TYPE_BASES
            or name in self._ENUM_BASES
            or name in self._EXCEPTION_BASES
            or name.endswith(self._EXCEPTION_SUFFIXES)
        )

    @classmethod
    def _is_dataclass_decorator(cls, node: ast.expr) -> bool:
        target = node.func if isinstance(node, ast.Call) else node
        return cls._base_name(target) == "dataclass"

    @staticmethod
    def _base_name(node: ast.expr) -> str | None:
        if isinstance(node, ast.Subscript):
            node = node.value
        if isinstance(node, ast.Name):
            return node.id
        if isinstance(node, ast.Attribute):
            return node.attr
        return None
