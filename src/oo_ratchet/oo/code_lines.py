"""Count a module's code lines: no blank lines, comments or docstrings."""

from __future__ import annotations

import ast
import io
import tokenize
from typing import ClassVar, Self

type Span = tuple[tuple[int, int], tuple[int, int]]


class CodeLines:
    """The lines of one module that carry code, for ``module_size``."""

    _NOT_CODE: ClassVar[frozenset[int]] = frozenset(
        {
            tokenize.COMMENT,
            tokenize.NL,
            tokenize.NEWLINE,
            tokenize.INDENT,
            tokenize.DEDENT,
            tokenize.ENCODING,
            tokenize.ENDMARKER,
        }
    )
    _count: int

    def __new__(cls, source: str, tree: ast.Module) -> Self:
        self = super().__new__(cls)
        nonblank = {n for n, line in enumerate(source.splitlines(), 1) if line.strip()}
        self._count = len(cls._token_lines(source, cls._docstrings(tree)) & nonblank)
        return self

    @property
    def count(self) -> int:
        """Return how many lines carry code."""
        return self._count

    @classmethod
    def _docstrings(cls, tree: ast.Module) -> list[Span]:
        spans: list[Span] = []
        for node in ast.walk(tree):
            if (
                not isinstance(
                    node,
                    ast.Module | ast.ClassDef | ast.FunctionDef | ast.AsyncFunctionDef,
                )
                or not node.body
            ):
                continue
            first = node.body[0]
            if (
                isinstance(first, ast.Expr)
                and isinstance(first.value, ast.Constant)
                and isinstance(first.value.value, str)
            ):
                end = (first.end_lineno or first.lineno, first.end_col_offset or 0)
                spans.append(((first.lineno, first.col_offset), end))
        return spans

    @classmethod
    def _token_lines(cls, source: str, docstrings: list[Span]) -> set[int]:
        lines: set[int] = set()
        for tok in tokenize.generate_tokens(io.StringIO(source).readline):
            if cls._is_code(tok, docstrings):
                lines.update(range(tok.start[0], tok.end[0] + 1))
        return lines

    @classmethod
    def _is_code(cls, tok: tokenize.TokenInfo, docstrings: list[Span]) -> bool:
        if tok.type in cls._NOT_CODE:
            return False
        return tok.type != tokenize.STRING or not cls._inside(tok, docstrings)

    @staticmethod
    def _inside(tok: tokenize.TokenInfo, spans: list[Span]) -> bool:
        return any(start <= tok.start and tok.end <= end for start, end in spans)
