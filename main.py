from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from grip import __version__


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--language", choices=("auto", "zh_CN", "en"), help="Override the interface language")
    parser.add_argument("--demo-controller", action="store_true", help="Synthetic controller input (offline screenshots only)")
    parser.add_argument("--install-addon", action="store_true")
    parser.add_argument("--probe", action="store_true")
    parser.add_argument("--screenshot", type=Path)
    parser.add_argument("--screenshot-tab", type=int, default=0)
    parser.add_argument("--diagnostic-output", type=Path)
    parser.add_argument("--capture-live", type=Path)
    args = parser.parse_args()
    if args.demo_controller and not args.screenshot:
        parser.error("--demo-controller requires --screenshot")
    if args.install_addon:
        from grip.install import install_addon
        print(install_addon())
        return 0
    if args.probe:
        from grip.xinput import XInput
        pad = XInput()
        result = []
        for index in pad.connected():
            snapshot = pad.read(index)
            result.append({"slot": index + 1, "battery": snapshot.battery,
                           "pressed": sorted(snapshot.down), "left_stick": [snapshot.lx, snapshot.ly]})
        print(json.dumps(result, ensure_ascii=False))
        return 0
    from PySide6.QtCore import QTimer
    from PySide6.QtWidgets import QApplication, QMessageBox
    from PySide6.QtNetwork import QLocalServer, QLocalSocket
    from PySide6.QtGui import QFont
    from grip.ui import MainWindow, STYLE
    from grip.model import load_config
    from grip.i18n import translate, resolve_language
    from PySide6.QtCore import QLocale
    language = resolve_language(args.language or load_config()["language"], QLocale.system().name())
    app = QApplication(sys.argv[:1])
    app.setApplicationName("anki-grip")
    app.setOrganizationName("anki-grip")
    app.setFont(QFont("Segoe UI", 10))
    app.setStyleSheet(STYLE)
    app.setQuitOnLastWindowClosed(False)
    server = None
    if not args.screenshot:
        socket = QLocalSocket()
        socket.connectToServer("anki-grip-desktop-v1")
        if socket.waitForConnected(500):
            socket.write(b"show")
            socket.waitForBytesWritten(500)
            return 0
        QLocalServer.removeServer("anki-grip-desktop-v1")
        server = QLocalServer()
        if not server.listen("anki-grip-desktop-v1"):
            QMessageBox.warning(None, "anki-grip", translate("无法创建程序实例。", language))
            return 1
    try:
        window = MainWindow(offline=bool(args.screenshot), language=args.language)
    except Exception as error:
        QMessageBox.critical(None, translate("anki-grip 启动失败", language), translate(str(error), language))
        return 1
    if server:
        def connected():
            socket = server.nextPendingConnection()
            socket.disconnectFromServer()
            window.show_window()
        server.newConnection.connect(connected)
    window.show()
    app.aboutToQuit.connect(window.cleanup)
    if args.diagnostic_output or args.capture_live:
        def diagnostic():
            if args.diagnostic_output:
                from grip.model import load_defaults
                args.diagnostic_output.parent.mkdir(parents=True, exist_ok=True)
                args.diagnostic_output.write_text(json.dumps({
                    "app": "anki-grip", "version": __version__,
                    "controller_connected": window.snapshot is not None,
                    "controller_slot": window.snapshot.index + 1 if window.snapshot else None,
                    "anki_connected": bool(window.anki_status.get("connected")),
                    "anki_state": window.anki_status.get("state"),
                    "bindings": window.config["bindings"],
                    "strength": window.config["strength"],
                    "defaults_match_current": load_defaults() == window.config,
                    "rating_labels": {key: widget.text() for key, widget in window.key_labels.items()
                                      if key in ("easy", "good", "hard", "again")},
                }, ensure_ascii=False, indent=2), encoding="utf-8")
            if args.capture_live:
                args.capture_live.parent.mkdir(parents=True, exist_ok=True)
                window.grab().save(str(args.capture_live))
        QTimer.singleShot(4000, diagnostic)
    if args.screenshot:
        window.tabs.setCurrentIndex(args.screenshot_tab)
        if args.demo_controller:
            from grip.xinput import Snapshot
            window.snapshot = Snapshot(0, {"A", "RB", "RT", "RSTICK_ACTIVE", "RSTICK_RIGHT"},
                                       64, 220, "电量充足", -6000, 10000, 27000, 3000)
            window.controller_view.set_snapshot(window.snapshot)
            window.test_controller_view.set_snapshot(window.snapshot)
            window.update_controller_labels()
        window.set_notice("离线预览 · 输入为模拟数据，不连接 Anki。")
        def screenshot():
            args.screenshot.parent.mkdir(parents=True, exist_ok=True)
            window.grab().save(str(args.screenshot))
            window.quitting = True
            window.close()
            app.quit()
        QTimer.singleShot(450, screenshot)
    result = app.exec()
    return result


if __name__ == "__main__":
    raise SystemExit(main())
