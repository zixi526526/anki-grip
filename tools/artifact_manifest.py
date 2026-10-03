"""Record package/runtime versions and checksums without machine-specific paths."""
from __future__ import annotations

import argparse
import hashlib
import json
import platform
import sys
from importlib.metadata import version
from pathlib import Path


def write_manifest(output: Path) -> None:
    root = Path(__file__).resolve().parents[1]
    sys.path.insert(0, str(root))
    from grip import __version__
    from PySide6.QtCore import qVersion

    info = {
        "app": "anki-grip", "version": __version__,
        "python": platform.python_version(), "os": platform.system(),
        "architecture": platform.machine(), "qt": qVersion(),
        "dependencies": {name: version(name) for name in
                         ("PySide6-Essentials", "shiboken6", "pyinstaller")},
    }
    (output / "build-info.json").write_text(json.dumps(info, indent=2) + "\n", encoding="utf-8")
    files = sorted(path for path in output.rglob("*")
                   if path.is_file() and path.name != "SHA256SUMS.txt")
    lines = []
    for path in files:
        with path.open("rb") as stream:
            digest = hashlib.file_digest(stream, "sha256").hexdigest()
        lines.append(f"{digest}  {path.relative_to(output).as_posix()}")
    (output / "SHA256SUMS.txt").write_text("\n".join(lines) + "\n", encoding="utf-8")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("output", type=Path)
    write_manifest(parser.parse_args().output)
