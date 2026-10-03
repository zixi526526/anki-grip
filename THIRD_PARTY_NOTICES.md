# Third-party software

The application source and bridge source are provided in this project.
The packaged executable dynamically loads Qt and CPython libraries at runtime.
You can rebuild it from source with modified compatible libraries using `build.ps1`.

- **PySide6 Essentials / Shiboken6 6.11.2** — Qt for Python, LGPLv3/GPL/commercial
  licensing. This application uses the LGPL option for the included Qt modules.
  https://doc.qt.io/qtforpython-6/licenses.html
  https://code.qt.io/pyside/pyside-setup.git/
- **Qt 6.11.2** — Qt Core, Gui, Widgets, Network and supporting plugins, LGPLv3
  and applicable third-party licenses. https://www.qt.io/licensing/open-source-lgpl-obligations
  https://code.qt.io/qt/qtbase.git/
- **CPython (exact build version in `build-info.json`)** — Python Software Foundation license.
  https://www.python.org/psf/license/ and https://github.com/python/cpython
- **PyInstaller 6.22.3** — GPLv2-or-later with the bootloader exception permitting
  distribution of bundled applications under their own licenses.
  https://pyinstaller.org/en/stable/license.html

The release folder includes the available license texts shipped with these
dependencies. Dependency licenses govern their respective components.

The original controller diagram is drawn by project-owned QPainter primitives.
Emulator projects listed in the design references provided behavioral inspiration
only; their source code, assets and trademarks are not bundled. Review the actual
release license bundle and applicable Qt/PySide obligations before distribution.
