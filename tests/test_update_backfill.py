"""Scoped updates backfill missing rows without refreshing untouched debt."""

from __future__ import annotations

import json
from collections.abc import Callable
from typing import TYPE_CHECKING

import pytest

from oo_ratchet.coupling.cli import main as coupling_main
from oo_ratchet.oo.cli import main as oo_main

if TYPE_CHECKING:
    from tests.conftest import GitSandbox

pytestmark = pytest.mark.slow

SOURCE = "class Thing:\n    def name(self) -> str:\n        return 'thing'\n"


@pytest.mark.parametrize(
    ("run", "baseline"),
    [(coupling_main, ".oo-coupling-baseline.json"), (oo_main, ".oo-baseline.json")],
)
@pytest.mark.parametrize("scenario", ["post_merge", "branch", "untracked"])
def test_update_backfills_missing_rows(
    git_sandbox: GitSandbox,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    run: Callable[[list[str]], int],
    baseline: str,
    scenario: str,
) -> None:
    monkeypatch.chdir(git_sandbox.root)
    for name in ("a", "b", "untouched"):
        git_sandbox.write(f"pkg/{name}.py", SOURCE)
    assert run(["pkg", "--rebaseline", "--allow-ci-write"]) == 0
    path = git_sandbox.root / baseline
    entries = json.loads(path.read_text())
    del entries["pkg/b.py"]
    entries["pkg/untouched.py"] = {"deliberately_stale": 42.0}
    path.write_text(json.dumps(entries))
    if scenario == "untracked":
        (git_sandbox.root / "pkg/b.py").unlink()
    base = git_sandbox.commit("base with missing row")
    git_sandbox.run_git("update-ref", "refs/remotes/origin/main", base)
    if scenario == "branch":
        git_sandbox.run_git("checkout", "-b", "feature")
        git_sandbox.write("pkg/a.py", SOURCE + "\n# touched\n")
        git_sandbox.commit("touch a only")
    elif scenario == "untracked":
        git_sandbox.write("pkg/b.py", SOURCE)
    else:
        assert git_sandbox.run_git("diff", "--name-only", base) == ""
    capsys.readouterr()
    assert run(["pkg", "--update", "--allow-ci-write"]) == 0
    result = json.loads(path.read_text())
    assert "pkg/b.py" in result
    assert result["pkg/untouched.py"] == entries["pkg/untouched.py"]
    assert result["pkg/a.py"] == entries["pkg/a.py"]
    output = capsys.readouterr().out
    assert "backfilled" in output.lower()
    assert "pkg/b.py" in output
