"""The suppression gate's audited ``--rebaseline`` (PL-1175)."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from oo_ratchet.suppression.cli import main

from .conftest import GitSandbox

pytestmark = pytest.mark.slow

_TWO = "x = 1  # noqa: E501\ny = 2  # type: ignore[misc]\n"
_THREE = _TWO + "z = 3  # noqa: F401\n"


def _setup(sandbox: GitSandbox, monkeypatch: pytest.MonkeyPatch) -> Path:
    monkeypatch.delenv("GITHUB_ACTIONS", raising=False)
    sandbox.write("pkg/a.py", _TWO)
    monkeypatch.chdir(sandbox.root)
    assert main(["pkg", "--update"]) == 0
    sandbox.write("pkg/a.py", _THREE)
    return sandbox.root


def _baseline_total(root: Path) -> int:
    return int(json.loads((root / ".suppression-baseline.json").read_text())["total"])


def test_update_refuses_raise_but_rebaseline_writes_and_audits(
    git_sandbox: GitSandbox, monkeypatch: pytest.MonkeyPatch
) -> None:
    root = _setup(git_sandbox, monkeypatch)
    assert main(["pkg", "--update"]) == 1
    assert _baseline_total(root) == 2
    code = main(
        ["pkg", "--rebaseline", "--reason", "package counter", "--source", "PL-1175"]
    )
    assert code == 0
    assert _baseline_total(root) == 3
    audit = (root / ".suppression-audit.jsonl").read_text().splitlines()
    entry = json.loads(audit[-1])
    assert entry["verdict"] == "rebaseline"
    assert (entry["before"], entry["total"]) == (2, 3)
    assert (entry["reason"], entry["source"]) == ("package counter", "PL-1175")


def test_rebaseline_requires_reason(
    git_sandbox: GitSandbox, monkeypatch: pytest.MonkeyPatch
) -> None:
    root = _setup(git_sandbox, monkeypatch)
    assert main(["pkg", "--rebaseline"]) == 1
    assert main(["pkg", "--rebaseline", "--reason", "  "]) == 1
    assert _baseline_total(root) == 2


def test_rebaseline_blocked_in_ci(
    git_sandbox: GitSandbox, monkeypatch: pytest.MonkeyPatch
) -> None:
    root = _setup(git_sandbox, monkeypatch)
    monkeypatch.setenv("GITHUB_ACTIONS", "true")
    assert main(["pkg", "--rebaseline", "--reason", "r"]) == 1
    assert _baseline_total(root) == 2
