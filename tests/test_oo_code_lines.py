"""``module_size`` counts code lines only: no blanks, comments or docstrings."""

from __future__ import annotations

import ast

from oo_ratchet.oo.code_lines import CodeLines
from oo_ratchet.oo.metrics import ModuleMetrics


def _count(source: str) -> int:
    return CodeLines(source, ast.parse(source)).count


class TestCodeLines:
    def test_comments_and_blank_lines_do_not_count(self) -> None:
        assert _count("# header\n\nx = 1  # trailing\n\n# y = 2\n") == 1

    def test_module_class_and_function_docstrings_do_not_count(self) -> None:
        source = (
            '"""Module.\n\nMore.\n"""\n'
            "class A:\n"
            '    """Class."""\n'
            "    def f(self) -> int:\n"
            "        '''Multi\n        line.\n        '''\n"
            "        return 1\n"
            "async def g() -> None:\n"
            '    """Async."""\n'
        )
        assert _count(source) == 4

    def test_implicitly_concatenated_docstring_does_not_count(self) -> None:
        assert _count('def f() -> None:\n    "a" \\\n    "b"\n    x = 1\n') == 2

    def test_non_docstring_strings_count(self) -> None:
        source = (
            "def f() -> str:\n"
            "    x = 1\n"
            '    """not a docstring"""\n'
            '    return """a\n\nb"""\n'
        )
        assert _count(source) == 5

    def test_docstring_sharing_a_line_with_code_counts_once(self) -> None:
        assert _count('def f() -> None: "doc"\n') == 1
        assert _count('"""doc"""; x = 1\n') == 1

    def test_module_size_uses_code_lines(self) -> None:
        source = '"""Doc."""\n\n# c\nx = 1\n'
        assert ModuleMetrics("a.py", source).compute()["module_size"] == 1

    def test_docstring_after_non_ascii_name_does_not_count(self) -> None:
        source = "class Café: '''multi\n    line\n    '''\nx = 1\n"
        assert _count(source) == 2
