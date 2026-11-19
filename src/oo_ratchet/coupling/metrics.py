"""Coupling and cohesion metrics for a single parsed Python module."""

from __future__ import annotations

import ast
from itertools import combinations
from typing import Self

from .imports import ImportResolver

_TYPE_BASES = frozenset({"Protocol", "TypedDict", "BaseModel"})


class ModuleCouplingMetrics:
    """Compute one module's efferent coupling, interface width, and LCOM.

    ``circular_imports`` is left at 0 here and filled in by the scorer once the
    whole-package import graph is known -- a single module cannot see a cycle it
    only participates in.
    """

    _path: str
    _tree: ast.Module
    _resolver: ImportResolver
    _stateless_values: str

    def __new__(
        cls,
        path: str,
        tree: ast.Module,
        resolver: ImportResolver,
        stateless_values: str = "dataclass",
    ) -> Self:
        self = super().__new__(cls)
        self._path = path
        self._tree = tree
        self._resolver = resolver
        self._stateless_values = stateless_values
        return self

    def compute(self) -> dict[str, float | int | str]:
        """Return every per-module metric as a JSON-serializable dict."""
        lcom_values = self._lcom_values()
        return {
            "file": self._path,
            "efferent_coupling": len(self._resolver.internal_imports(self._tree)),
            "public_names": self._public_names(),
            "circular_imports": 0,  # filled by the scorer after graph analysis
            "max_lcom": max(lcom_values) if lcom_values else 0.0,
            "avg_lcom": (
                round(sum(lcom_values) / len(lcom_values), 3) if lcom_values else 0.0
            ),
        }

    # ---- public interface width ----

    def _public_names(self) -> int:
        explicit = self._all_count()
        return explicit if explicit is not None else self._heuristic_count()

    def _all_count(self) -> int | None:
        """Return ``len(__all__)`` if the module declares it, else ``None``."""
        for node in ast.iter_child_nodes(self._tree):
            if not isinstance(node, ast.Assign):
                continue
            for target in node.targets:
                if (
                    isinstance(target, ast.Name)
                    and target.id == "__all__"
                    and isinstance(node.value, (ast.List, ast.Tuple))
                ):
                    return len(node.value.elts)
        return None

    def _heuristic_count(self) -> int:
        return sum(
            self._node_public_names(node) for node in ast.iter_child_nodes(self._tree)
        )

    @staticmethod
    def _node_public_names(node: ast.AST) -> int:
        if isinstance(node, ast.ClassDef):
            return 0 if node.name.startswith("_") else 1
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            return 0 if node.name.startswith("_") else 1
        if isinstance(node, ast.Assign):
            return sum(
                1
                for t in node.targets
                if isinstance(t, ast.Name) and not t.id.startswith("_")
            )
        return 0

    # ---- LCOM cohesion ----

    def _lcom_values(self) -> list[float]:
        values: list[float] = []
        for node in ast.iter_child_nodes(self._tree):
            if not isinstance(node, ast.ClassDef) or self._is_exempt(node):
                continue
            lcom = self._class_lcom(node)
            if lcom is not None:
                values.append(lcom)
        return values

    def _class_lcom(self, cls_node: ast.ClassDef) -> float | None:
        """Return the class's LCOM, or ``None`` when it has < 2 instance methods."""
        methods = self._instance_method_attrs(cls_node)
        if len(methods) <= 1:
            return None
        return self._lcom_from(methods)

    def _instance_method_attrs(self, cls_node: ast.ClassDef) -> list[set[str]]:
        methods: list[set[str]] = []
        for item in ast.iter_child_nodes(cls_node):
            if not isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef)):
                continue
            if self._is_static_or_class(item):
                continue
            methods.append(self._method_self_attrs(item))
        return methods

    @staticmethod
    def _is_static_or_class(item: ast.FunctionDef | ast.AsyncFunctionDef) -> bool:
        marks = {"staticmethod", "classmethod"}
        for dec in item.decorator_list:
            if isinstance(dec, ast.Name) and dec.id in marks:
                return True
            if isinstance(dec, ast.Attribute) and dec.attr in marks:
                return True
        return False

    @staticmethod
    def _method_self_attrs(method: ast.FunctionDef | ast.AsyncFunctionDef) -> set[str]:
        # LCOM measures DATA cohesion -- fields shared between methods. Count
        # every ``self.<name>`` field read/write, public or private (an
        # underscore-only filter under-reads frozen dataclass value objects
        # whose fields are public by contract, PY-CC-6), but exclude
        # ``self.helper()`` call targets: sharing a helper method is method
        # dispatch, not shared state.
        call_targets = {
            node.func
            for node in ast.walk(method)
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute)
        }
        return {
            node.attr
            for node in ast.walk(method)
            if isinstance(node, ast.Attribute)
            and isinstance(node.value, ast.Name)
            and node.value.id == "self"
            and node not in call_targets
        }

    @staticmethod
    def _lcom_from(methods: list[set[str]]) -> float:
        total = 0
        disjoint = 0
        for m1, m2 in combinations(methods, 2):
            total += 1
            if not m1 & m2:
                disjoint += 1
        return round(disjoint / total, 3) if total else 0.0

    def _is_exempt(self, node: ast.ClassDef) -> bool:
        """Return True for data shapes and stateless values, which LCOM cannot see.

        ``stateless_values == "any"`` exempts every class that stores no
        private ``self._*`` state; the default exempts only value shapes.
        """
        if self._is_type_definition(node):
            return True
        if self._stateless_values == "any":
            return self._stores_no_private_state(node)
        return self._declares_value_shape(node) and self._is_stateless_value(node)

    @staticmethod
    def _declares_value_shape(node: ast.ClassDef) -> bool:
        """Return True for a ``@dataclass`` or an empty-``__slots__`` marker class."""
        for deco in node.decorator_list:
            target = deco.func if isinstance(deco, ast.Call) else deco
            name = target.attr if isinstance(target, ast.Attribute) else None
            if isinstance(target, ast.Name):
                name = target.id
            if name == "dataclass":
                return True
        return any(
            isinstance(item, ast.Assign)
            and any(
                isinstance(t, ast.Name) and t.id == "__slots__" for t in item.targets
            )
            and isinstance(item.value, ast.Tuple)
            and not item.value.elts
            for item in node.body
        )

    @staticmethod
    def _is_slots(target: ast.expr) -> bool:
        return isinstance(target, ast.Name) and target.id == "__slots__"

    @staticmethod
    def _is_stateless_value(node: ast.ClassDef) -> bool:
        """Return True when the class never stores instance state in its own AST.

        Applied only to a marker (``__slots__ = ()``) or a ``@dataclass``, whose
        fields the generated ``__init__`` sets; either reads as LCOM 1.0 otherwise. A
        ``object.__setattr__(self, ...)`` call counts as a store (lux #498).
        """
        for sub in ast.walk(node):
            if (
                isinstance(sub, ast.Attribute)
                and isinstance(sub.value, ast.Name)
                and sub.value.id == "self"
                and isinstance(sub.ctx, ast.Store)
            ):
                return False
            if (
                isinstance(sub, ast.Call)
                and isinstance(sub.func, ast.Attribute)
                and sub.func.attr == "__setattr__"
                and sub.args
                and isinstance(sub.args[0], ast.Name)
                and sub.args[0].id == "self"
            ):
                return False
        return True

    @classmethod
    def _stores_no_private_state(cls, node: ast.ClassDef) -> bool:
        """Return True when the class never writes a private ``self._*`` attr.

        A write through ``object``/``super()``/``type(self)`` ``.__setattr__``
        (the frozen-class idiom) counts as a store too (lux #498).
        """
        return not any(cls._writes_private_state(sub) for sub in ast.walk(node))

    @classmethod
    def _writes_private_state(cls, sub: ast.AST) -> bool:
        if isinstance(sub, ast.Call):
            return cls._is_private_setattr(sub)
        return (
            isinstance(sub, ast.Attribute)
            and isinstance(sub.ctx, ast.Store)
            and isinstance(sub.value, ast.Name)
            and sub.value.id == "self"
            and sub.attr.startswith("_")
        )

    @classmethod
    def _is_private_setattr(cls, call: ast.Call) -> bool:
        """Return True for ``object.__setattr__(self, "_x", ...)`` and kin."""
        func = call.func
        if not isinstance(func, ast.Attribute) or func.attr != "__setattr__":
            return False
        if len(call.args) < 2 or not cls._is_setattr_receiver(func.value):
            return False
        target, name = call.args[0], call.args[1]
        if not (isinstance(target, ast.Name) and target.id == "self"):
            return False
        return isinstance(name, ast.Constant) and str(name.value).startswith("_")

    @staticmethod
    def _is_setattr_receiver(receiver: ast.expr) -> bool:
        """Return True for ``object``, ``super()``, or ``type(...)``."""
        if isinstance(receiver, ast.Name):
            return receiver.id == "object"
        return (
            isinstance(receiver, ast.Call)
            and isinstance(receiver.func, ast.Name)
            and receiver.func.id in ("super", "type")
        )

    @staticmethod
    def _is_type_definition(node: ast.ClassDef) -> bool:
        """Return True for Protocol/TypedDict/BaseModel classes (excluded from LCOM)."""
        for base in node.bases:
            if isinstance(base, ast.Name) and base.id in _TYPE_BASES:
                return True
            if (
                isinstance(base, ast.Subscript)
                and isinstance(base.value, ast.Name)
                and base.value.id in _TYPE_BASES
            ):
                return True
        return False
