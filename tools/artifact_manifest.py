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
    from grip.model import default_config
    from PySide6.QtCore import qVersion

    info = {
        "app": "anki-grip", "version": __version__,
        "default_rating_order": default_config()["order"],
        "python": platform.python_version(), "os": platform.system(),
        "architecture": platform.machine(), "qt": qVersion(),
        "dependencies": {name: version(name) for name in
                         ("PySide6-Essentials", "shiboken6", "pyinstaller")},
    }
    (output / "build-info.json").write_text(json.dumps(info, indent=2) + "\n", encoding="utf-8")
    python_version = platform.python_version()
    (output / "DEPENDENCY_SOURCES.md").write_text(
        "# Dependency sources and rebuilding\n\n"
        "This package uses unmodified Qt/PySide libraries under LGPLv3. The complete\n"
        "library license texts are in licenses/. You may modify and rebuild these\n"
        "libraries and use compatible replacements with this application. There is\n"
        "no application license restriction on doing so or on reverse engineering\n"
        "for debugging library modifications.\n\n"
        "## Complete corresponding library source\n\n"
        "- Qt 6.11.2 (including its submodules):\n"
        "  https://download.qt.io/archive/qt/6.11/6.11.2/single/qt-everywhere-src-6.11.2.tar.xz\n"
        "- PySide6 and Shiboken6 6.11.2:\n"
        "  https://download.qt.io/official_releases/QtForPython/pyside6/PySide6-6.11.2-src/pyside-setup-everywhere-src-6.11.2.tar.xz\n"
        f"- CPython {python_version}: https://www.python.org/ftp/python/{python_version}/Python-{python_version}.tar.xz\n"
        "- PyInstaller 6.22.3: https://github.com/pyinstaller/pyinstaller/archive/refs/tags/v6.22.3.tar.gz\n\n"
        "## Rebuild and run with modified compatible libraries\n\n"
        f"Application source: https://github.com/zixi526526/anki-grip/tree/v{__version__}\n"
        "Qt/PySide Windows build instructions: https://doc.qt.io/qtforpython-6/building_from_source/windows.html\n\n"
        "Build/install the modified Qt/PySide wheels in a separate Python environment,\n"
        "then run build.ps1 -VenvPath <that environment> -SkipDependencyInstall\n"
        "-OutputPath <new output folder>. Retain compatible version metadata for the\n"
        "pinned checks, or adjust the open-source dependency pins/checks when using\n"
        "another compatible version. The public source includes the complete build\n"
        "entry point. Run your rebuilt executable from a writable folder; no signing\n"
        "or application lock prevents running modified builds.\n",
        encoding="utf-8",
    )
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
