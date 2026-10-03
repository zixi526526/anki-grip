"""Local Anki bridge client. Mutating requests are never retried."""
from __future__ import annotations

import json
import queue
import threading
import time
import urllib.error
import urllib.request

from PySide6.QtCore import QThread, Signal

URL = "http://127.0.0.1:18765"


def request(path: str, data: dict | None = None, timeout: float = 1.0, base: str = URL) -> dict:
    encoded = None if data is None else json.dumps(data).encode("utf-8")
    req = urllib.request.Request(base + path, data=encoded,
                                 headers={"Content-Type": "application/json", "X-Anki-Grip": "1"})
    # A localhost command must never travel through the machine's HTTP proxy.
    opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
    with opener.open(req, timeout=timeout) as response:
        value = json.loads(response.read(16384))
    if not isinstance(value, dict) or value.get("app") != "anki-grip" or value.get("protocol") != 1:
        raise ValueError("连接端不是 anki-grip 插件，或版本不兼容。")
    return value


class BridgeWorker(QThread):
    status_ready = Signal(dict)
    action_done = Signal(str, dict)

    def __init__(self):
        super().__init__()
        self.commands: queue.Queue[tuple[str, dict, float]] = queue.Queue(maxsize=1)
        self.stopping = threading.Event()

    def submit(self, action: str, payload: dict) -> bool:
        try:
            self.commands.put_nowait((action, payload, time.monotonic()))
            return True
        except queue.Full:
            return False

    def run(self) -> None:
        next_status = 0.0
        while not self.stopping.is_set():
            try:
                action, payload, created = self.commands.get(timeout=.04)
            except queue.Empty:
                action = ""
            if action:
                if self.stopping.is_set() or time.monotonic() - created > .8:
                    self.action_done.emit(action, {"ok": False, "message": "操作已过期，请重新按键。"})
                    continue
                try:
                    result = request("/action", payload, timeout=3.2)
                except (OSError, ValueError, urllib.error.URLError):
                    result = {"ok": False, "message": "未收到确认；请查看 Anki，程序不会重复提交。"}
                self.action_done.emit(action, result)
                next_status = 0.0
            if time.monotonic() >= next_status:
                try:
                    result = request("/status", timeout=.8)
                    result["connected"] = True
                except (OSError, ValueError, urllib.error.URLError):
                    result = {"connected": False}
                self.status_ready.emit(result)
                next_status = time.monotonic() + .30

    def stop(self) -> None:
        self.stopping.set()
