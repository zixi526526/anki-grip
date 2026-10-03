"""Loopback-only bridge: no collection contents, UI-thread operations, real ACKs."""
from __future__ import annotations

import json
import os
import queue
import threading
import time
from dataclasses import dataclass, field
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

from aqt import gui_hooks, mw
from aqt.qt import QApplication, QLabel, QTimer, Qt

APP = {"app": "anki-grip", "protocol": 1, "version": "1.5.0rc1"}
PORT = int(os.environ.get("ANKI_GRIP_PORT", "18765"))
EASES = {"again": 1, "hard": 2, "good": 3, "easy": 4}


class ActionFeedback:
    """A mouse-transparent child of Anki, independent of its global tooltips."""
    LABELS = {
        "easy": ("简单", "Easy"), "good": ("良好", "Good"),
        "hard": ("困难", "Hard"), "again": ("重来", "Again"),
        "show": ("显示答案", "Show Answer"), "replay": ("重播音频", "Replay Audio"),
        "undo": ("撤销上次评分", "Undo Rating"),
        "scroll_up": ("向上滚动", "Scroll Up"), "scroll_down": ("向下滚动", "Scroll Down"),
    }

    def __init__(self, parent):
        self.parent = parent
        self.label = QLabel(parent)
        self.label.setTextFormat(Qt.TextFormat.PlainText)
        self.label.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.label.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, True)
        self.label.setAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating, True)
        self.label.setStyleSheet(
            "QLabel { background: #234735; color: #efffde; border: 1px solid #8bab72;"
            " border-radius: 9px; padding: 10px 16px; font-size: 16px; font-weight: 600; }")
        self.label.hide()
        self.timer = QTimer(self.label)
        self.timer.setSingleShot(True)
        self.timer.timeout.connect(self.label.hide)

    def show(self, action, language):
        labels = self.LABELS.get(action)
        if labels is None:
            return
        text = labels[1] if language == "en" else labels[0]
        self.label.setText("anki-grip · ✓ " + text)
        self.label.adjustSize()
        self.label.move(max(16, self.parent.width() - self.label.width() - 24),
                        max(16, self.parent.height() - self.label.height() - 100))
        self.label.show()
        self.label.raise_()
        self.timer.start(1000)

    def hide(self):
        self.timer.stop()
        self.label.hide()


@dataclass
class Command:
    data: dict
    deadline: float = field(default_factory=lambda: time.monotonic() + 2.6)
    done: threading.Event = field(default_factory=threading.Event)
    result: dict = field(default_factory=dict)
    cancelled: bool = False

    def finish(self, ok: bool, message: str, **extra) -> bool:
        if not self.done.is_set():
            self.result = {**APP, "ok": ok, "message": message, **extra}
            self.done.set()
            return True
        return False


class Bridge:
    def __init__(self):
        self.commands: queue.Queue[Command] = queue.Queue(maxsize=4)
        self.snapshot = {**APP, "state": "starting", "revision": 0, "foreground": False}
        self.revision = 0
        self.session = time.monotonic_ns()
        self.pending: tuple[Command, int, int] | None = None
        self.last_answered_id: int | None = None
        self.undo_busy = False
        self.closed = False
        self.feedback = None
        self.last_feedback_at = float("-inf")
        self.timer = QTimer(mw.app)
        self.timer.timeout.connect(self.tick)
        self.timer.start(35)
        owner = self

        class Handler(BaseHTTPRequestHandler):
            def log_message(self, *args):
                pass

            def send_json(self, value: dict, code=200):
                raw = json.dumps(value, ensure_ascii=False).encode("utf-8")
                self.send_response(code)
                self.send_header("Content-Type", "application/json; charset=utf-8")
                self.send_header("Cache-Control", "no-store")
                self.send_header("Content-Length", str(len(raw)))
                self.end_headers()
                try:
                    self.wfile.write(raw)
                except OSError:
                    pass

            def valid_client(self):
                # No CORS, redirects, browser origins or DNS-rebinding hosts.
                if self.headers.get("Origin") or self.headers.get("Host") != f"127.0.0.1:{PORT}":
                    self.send_json({**APP, "ok": False, "message": "请求来源被拒绝。"}, 403)
                    return False
                if self.headers.get("X-Anki-Grip") != "1":
                    self.send_json({**APP, "ok": False, "message": "缺少客户端标记。"}, 403)
                    return False
                return True

            def do_GET(self):
                if not self.valid_client():
                    return
                if self.path != "/status":
                    self.send_json({**APP, "ok": False}, 404)
                    return
                self.send_json(owner.snapshot)

            def do_POST(self):
                if not self.valid_client():
                    return
                try:
                    length = int(self.headers.get("Content-Length", "0"))
                except ValueError:
                    length = 0
                if self.path != "/action" or not 0 < length <= 2048:
                    self.send_json({**APP, "ok": False, "message": "无效请求。"}, 400)
                    return
                try:
                    data = json.loads(self.rfile.read(length))
                except (ValueError, UnicodeError):
                    self.send_json({**APP, "ok": False}, 400)
                    return
                if not isinstance(data, dict):
                    self.send_json({**APP, "ok": False}, 400)
                    return
                command = Command(data)
                try:
                    owner.commands.put_nowait(command)
                except queue.Full:
                    command.finish(False, "Anki 正忙，请稍后再按。")
                if not command.done.wait(2.7):
                    command.cancelled = True
                    command.finish(False, "Anki 未及时确认，请查看卡片状态。")
                self.send_json(command.result)

        self.server = ThreadingHTTPServer(("127.0.0.1", PORT), Handler)
        self.server.daemon_threads = True
        self.server_thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.server_thread.start()
        gui_hooks.reviewer_did_show_question.append(self.on_card)
        gui_hooks.reviewer_did_show_answer.append(self.on_card)
        gui_hooks.reviewer_did_answer_card.append(self.on_answered)
        gui_hooks.state_did_change.append(self.on_state)
        gui_hooks.profile_will_close.append(self.on_profile_close)
        mw.app.aboutToQuit.connect(self.shutdown)

    def status(self) -> dict:
        reviewer = mw.reviewer
        review = mw.state == "review" and reviewer.card is not None
        active = QApplication.activeWindow()
        modal = QApplication.activeModalWidget() is not None
        return {**APP, "state": reviewer.state if review else mw.state,
                "revision": self.revision, "session": self.session,
                "foreground": bool(mw.isActiveWindow()),
                "blocked": modal or (active is not None and active is not mw),
                "busy": self.pending is not None or self.undo_busy,
                "can_undo": bool(review and self.last_answered_id is not None
                                  and mw.col and mw.col.undo_status().undo == mw.col.tr.actions_answer_card())}

    def tick(self):
        if self.pending and (self.pending[0].cancelled or time.monotonic() > self.pending[0].deadline):
            self.pending[0].finish(False, "评分未收到完成确认，请查看 Anki。")
            self.pending = None
        try:
            self.snapshot = self.status()
        except Exception:
            self.snapshot = {**APP, "state": "unavailable", "revision": self.revision}
        try:
            command = self.commands.get_nowait()
        except queue.Empty:
            return
        if command.cancelled or time.monotonic() >= command.deadline:
            command.finish(False, "操作已过期。")
            return
        try:
            self.execute(command)
        except Exception:
            if self.pending and self.pending[0] is command:
                self.pending = None
            command.finish(False, "Anki 无法执行此操作，请查看当前界面。")

    def complete(self, command, ok, message):
        # Only completion paths on Anki's Qt thread may display UI. Commands
        # completed/rejected by the HTTP thread never create a success toast.
        first_completion = command.finish(ok, message)
        if first_completion and ok:
            self.notify_feedback(command)

    def notify_feedback(self, command):
        if (self.closed or command.cancelled or time.monotonic() > command.deadline
                or command.data.get("show_feedback", True) is not True):
            return
        if (not mw.isActiveWindow() or QApplication.activeModalWidget() is not None
                or QApplication.activeWindow() not in (None, mw)):
            return
        action = command.data.get("action")
        now = time.monotonic()
        if action in ("scroll_up", "scroll_down") and now - self.last_feedback_at < 1:
            return
        try:
            if self.feedback is None:
                self.feedback = ActionFeedback(mw)
            self.feedback.show(action, command.data.get("feedback_language", "zh_CN"))
            self.last_feedback_at = now
        except Exception:
            # Visual feedback must never change a completed action or its ACK.
            pass

    def hide_feedback(self):
        if self.feedback is not None:
            try:
                self.feedback.hide()
            except RuntimeError:
                pass

    def execute(self, command: Command):
        status = self.status()
        data = command.data
        action = data.get("action")
        if action not in {*EASES, "show", "replay", "undo", "scroll_up", "scroll_down"}:
            command.finish(False, "不支持的操作。")
            return
        if status["state"] not in ("question", "answer"):
            command.finish(False, "请先在 Anki 中进入复习。")
            return
        if status["blocked"] or (data.get("foreground_only", True) and not status["foreground"]):
            command.finish(False, "Anki 未在前台，或有其他窗口打开。")
            return
        if data.get("session") != self.session or data.get("revision") != self.revision:
            command.finish(False, "卡片状态已改变，请重新按键。")
            return
        if status["busy"]:
            command.finish(False, "Anki 正在处理上一操作。")
            return
        reviewer = mw.reviewer
        if action in EASES:
            if reviewer.state != "answer":
                command.finish(False, "请先显示答案，再评分。")
                return
            ease = EASES[action]
            self.pending = (command, reviewer.card.id, ease)
            reviewer._answerCard(ease)
        elif action == "show":
            if reviewer.state != "question":
                command.finish(False, "答案已显示。")
                return
            reviewer._showAnswer()
            self.complete(command, reviewer.state == "answer", "已显示答案。")
        elif action == "replay":
            card = reviewer.card
            tags = list(card.question_av_tags()) if reviewer.state == "question" else list(card.answer_av_tags())
            if reviewer.state == "answer" and card.replay_question_audio_on_answer_side():
                tags += list(card.question_av_tags())
            if not tags:
                command.finish(False, "这张卡片没有可重播的音频。")
                return
            reviewer.replayAudio()
            self.complete(command, True, "已重播音频。")
        elif action in ("scroll_up", "scroll_down"):
            delta = -160 if action == "scroll_up" else 160
            # Execute only on Qt's main thread, in the current review webview.
            reviewer.web.eval(f"window.scrollBy({{top: {delta}, left: 0, behavior: 'instant'}});")
            self.complete(command, True, "已请求向上滚动。" if delta < 0 else "已请求向下滚动。")
        elif action == "undo":
            if not status["can_undo"]:
                command.finish(False, "没有可撤销的评分。")
                return
            from aqt.operations import CollectionOp
            self.undo_busy = True

            def finished(_changes):
                gui_hooks.state_did_undo(_changes)
                self.undo_busy = False
                self.last_answered_id = None
                self.revision += 1
                self.complete(command, True, "已撤销上次评分。")

            def failed(_error):
                self.undo_busy = False
                command.finish(False, "撤销未完成。")

            CollectionOp(mw, lambda col: col.undo()).success(finished).failure(failed).run_in_background()

    def on_card(self, *_args):
        self.revision += 1

    def on_state(self, *_args):
        self.revision += 1
        if mw.state != "review":
            self.hide_feedback()

    def on_answered(self, _reviewer, card, ease):
        self.last_answered_id = card.id
        self.revision += 1
        if self.pending:
            command, expected_card, expected_ease = self.pending
            if card.id == expected_card and ease == expected_ease:
                self.pending = None
                self.complete(command, True, "评分已确认。")

    def on_profile_close(self):
        self.hide_feedback()
        self.last_answered_id = None
        if self.pending:
            self.pending[0].finish(False, "Anki 配置已关闭。")
            self.pending = None
        self.revision += 1

    def shutdown(self):
        if self.closed:
            return
        self.closed = True
        self.hide_feedback()
        try:
            self.timer.stop()
        except RuntimeError:
            # Some Anki versions destroy Qt parents before aboutToQuit.
            pass
        if self.pending:
            self.pending[0].finish(False, "Anki 正在退出。")
        # server shutdown may wait; never block Qt's closing main thread.
        threading.Thread(target=self.server.shutdown, daemon=True).start()
        self.server.server_close()


try:
    _bridge = Bridge()
except OSError:
    from aqt.utils import show_warning
    QTimer.singleShot(1500, lambda: show_warning(
        f"anki-grip 无法监听本机端口 {PORT}。请关闭重复的 Anki 实例后重启。\n"
        f"anki-grip could not listen on local port {PORT}. Close duplicate Anki instances and restart."))
