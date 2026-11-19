"""``oo-ratchet <gate> <src> [flags]`` — dispatch to one of the three ratchets."""

from __future__ import annotations

import sys
from collections.abc import Callable

from oo_ratchet import __version__
from oo_ratchet.coupling.cli import main as coupling_main
from oo_ratchet.oo.cli import main as oo_main
from oo_ratchet.suppression.cli import main as suppression_main

GATES: dict[str, Callable[[list[str] | None], int]] = {
    "oo": oo_main,
    "coupling": coupling_main,
    "suppressions": suppression_main,
}

USAGE = (
    "usage: oo-ratchet {oo,coupling,suppressions} <src> [flags]\n"
    "       oo-ratchet <gate> --help for that gate's flags"
)


def main(argv: list[str] | None = None) -> int:
    """Run the gate named by the first argument with the remaining arguments."""
    args = sys.argv[1:] if argv is None else argv
    if not args or args[0] in {"-h", "--help"}:
        sys.stdout.write(USAGE + "\n")
        return 0 if args else 2
    if args[0] == "--version":
        sys.stdout.write(f"oo-ratchet {__version__}\n")
        return 0
    gate = GATES.get(args[0])
    if gate is None:
        sys.stderr.write(f"oo-ratchet: unknown gate {args[0]!r}\n{USAGE}\n")
        return 2
    return gate(args[1:])


if __name__ == "__main__":
    sys.exit(main())
