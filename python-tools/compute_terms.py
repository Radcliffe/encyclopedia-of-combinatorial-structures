#!/usr/bin/env python3
"""Compatibility entry point for the packaged term evaluator.

New code should import :mod:`combstruct` or run the ``combstruct`` command.
This wrapper keeps the repository's historical invocation working while the
remaining scripts in ``python-tools`` are migrated in a later milestone.
"""

from __future__ import annotations

import sys
from pathlib import Path

try:
    from combstruct.terms import *  # noqa: F403
    from combstruct.terms import main
except ModuleNotFoundError as error:
    if error.name != "combstruct":
        raise
    sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
    from combstruct.terms import *  # noqa: F403
    from combstruct.terms import main


if __name__ == "__main__":
    raise SystemExit(main())
