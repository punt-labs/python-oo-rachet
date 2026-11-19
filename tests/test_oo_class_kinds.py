"""``classes_per_module`` leaves out exceptions, enums, dataclasses and types."""

from __future__ import annotations

import ast

from oo_ratchet.oo.class_kinds import ClassKinds
from oo_ratchet.oo.metrics import ModuleMetrics


def _count(source: str) -> int:
    return ClassKinds(ast.parse(source)).count


class TestClassKinds:
    def test_plain_classes_count(self) -> None:
        assert _count("class A:\n    pass\nclass B(A):\n    pass\n") == 2

    def test_exceptions_do_not_count(self) -> None:
        source = (
            "class AppError(Exception): ...\n"
            "class Missing(AppError): ...\n"
            "class Bad(ValueError): ...\n"
            "class Odd(errors.ConfigError): ...\n"
            "class Real: ...\n"
        )
        assert _count(source) == 1

    def test_enums_do_not_count(self) -> None:
        source = (
            "class Color(Enum): ...\n"
            "class Mode(enum.StrEnum): ...\n"
            "class Bits(IntFlag): ...\n"
        )
        assert _count(source) == 0

    def test_dataclasses_do_not_count(self) -> None:
        source = (
            "@dataclass\nclass A: ...\n"
            "@dataclass(frozen=True)\nclass B: ...\n"
            "@dataclasses.dataclass(slots=True)\nclass C: ...\n"
            "@other\nclass D: ...\n"
        )
        assert _count(source) == 1

    def test_protocols_and_typed_dicts_still_do_not_count(self) -> None:
        assert _count("class P(Protocol): ...\nclass T(TypedDict): ...\n") == 0

    def test_nested_classes_are_ignored(self) -> None:
        assert _count("class A:\n    class B: ...\n") == 1

    def test_class_to_func_ratio_still_sees_every_class(self) -> None:
        source = "@dataclass\nclass A: ...\ndef f() -> None: ...\n"
        metrics = ModuleMetrics("a.py", source).compute()
        assert metrics["classes_per_module"] == 0
        assert metrics["class_to_func_ratio"] == 0.5
