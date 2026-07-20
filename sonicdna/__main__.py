"""Launch the GUI by default, or the CLI when arguments are supplied."""

from __future__ import annotations

import sys


def main() -> int:
    if len(sys.argv) > 1:
        from sonicdna.cli import main as cli_main

        return cli_main()
    from sonicdna.app import run

    return run()


if __name__ == "__main__":
    raise SystemExit(main())
