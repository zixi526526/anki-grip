"""Install our add-on only. Existing installations are backed up outside Anki."""
from __future__ import annotations

import os
import shutil
import sys
import time
from pathlib import Path

from .model import config_dir


def resource_root() -> Path:
    return Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parent.parent))


def install_addon(target: Path | None = None) -> Path:
    source = resource_root() / "addon" / "anki_grip_bridge"
    root = target or Path(os.environ["APPDATA"]) / "Anki2" / "addons21"
    root.mkdir(parents=True, exist_ok=True)
    destination = root / "anki_grip_bridge"
    if destination.exists():
        changed = any(not (destination / name).exists() or
                      (source / name).read_bytes() != (destination / name).read_bytes()
                      for name in ("__init__.py", "manifest.json"))
        if not changed:
            return destination
        backup = config_dir() / "addon-backups" / time.strftime("%Y%m%d-%H%M%S")
        shutil.copytree(destination, backup)
    destination.mkdir(exist_ok=True)
    for name in ("__init__.py", "manifest.json"):
        shutil.copy2(source / name, destination / name)
    return destination
