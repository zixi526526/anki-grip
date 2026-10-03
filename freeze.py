"""Build entry point with a controlled Windows DLL dependency search path."""
from __future__ import annotations

import os
import sys
from pathlib import Path


def main():
    windows = Path(os.environ["SystemRoot"])
    # Some launchers inject native-library paths again when starting Python.
    # Set this inside Python, before PyInstaller resolves binary dependencies.
    os.environ["PATH"] = os.pathsep.join(map(str, (
        Path(sys.prefix) / "Scripts", Path(sys.base_prefix),
        windows / "System32", windows,
    )))
    from PyInstaller.__main__ import run
    run()


if __name__ == "__main__":
    main()
