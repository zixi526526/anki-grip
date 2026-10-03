"""Execute the actual add-on with a minimal Anki adapter; no user data touched."""
import importlib.util
import sys
import time
import types
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch


class Hook(list):
    pass


class FakeCard:
    id = 91
    def question_av_tags(self):
        return ["fake-audio"]
    def answer_av_tags(self):
        return []
    def replay_question_audio_on_answer_side(self):
        return True


class FakeReviewer:
    card = FakeCard()
    state = "question"
    def __init__(self):
        self.grades = []
        self.replays = 0
        self.web = MagicMock()
    def _showAnswer(self):
        self.state = "answer"
    def _answerCard(self, ease):
        self.grades.append(ease)
    def replayAudio(self):
        self.replays += 1


class BridgeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.mw = types.SimpleNamespace(state="review", reviewer=FakeReviewer(),
                                      app=types.SimpleNamespace(aboutToQuit=MagicMock()),
                                      isActiveWindow=lambda: True,
                                      col=types.SimpleNamespace(undo_status=lambda: types.SimpleNamespace(undo="回答卡片"),
                                                                tr=types.SimpleNamespace(actions_answer_card=lambda: "回答卡片")))
        qt = types.ModuleType("aqt.qt")
        qt.QTimer = MagicMock()
        qt.QLabel = MagicMock()
        qt.Qt = MagicMock()
        qt.QApplication = MagicMock()
        qt.QApplication.activeWindow.return_value = cls.mw
        qt.QApplication.activeModalWidget.return_value = None
        aqt = types.ModuleType("aqt")
        aqt.mw = cls.mw
        aqt.gui_hooks = types.SimpleNamespace(**{n: Hook() for n in (
            "reviewer_did_show_question", "reviewer_did_show_answer", "reviewer_did_answer_card", "state_did_change", "profile_will_close")})
        aqt.gui_hooks.state_did_undo = MagicMock()
        cls.modules = patch.dict(sys.modules, {"aqt": aqt, "aqt.qt": qt})
        cls.modules.start()
        source = Path(__file__).resolve().parents[1] / "addon" / "anki_grip_bridge" / "__init__.py"
        spec = importlib.util.spec_from_file_location("grip_addon_test", source)
        cls.module = importlib.util.module_from_spec(spec)
        sys.modules[spec.name] = cls.module
        with patch("http.server.ThreadingHTTPServer") as server:
            spec.loader.exec_module(cls.module)
        cls.bridge = cls.module._bridge

    @classmethod
    def tearDownClass(cls):
        cls.modules.stop()

    def setUp(self):
        self.mw.reviewer = FakeReviewer()
        self.bridge.pending = None
        self.bridge.undo_busy = False
        self.bridge.last_answered_id = None
        self.bridge.revision = 5
        self.bridge.closed = False
        self.bridge.feedback = MagicMock()
        self.bridge.last_feedback_at = float("-inf")

    def command(self, action, **extra):
        return self.module.Command({"action": action, "revision": 5,
                                    "session": self.bridge.session, **extra})

    def test_rating_requires_answer(self):
        command = self.command("easy")
        self.bridge.execute(command)
        self.assertFalse(command.result["ok"])
        self.assertEqual(self.mw.reviewer.grades, [])

    def test_easy_maps_to_internal_four_and_requires_completion_hook(self):
        self.mw.reviewer.state = "answer"
        command = self.command("easy")
        self.bridge.execute(command)
        self.assertEqual(self.mw.reviewer.grades, [4])
        self.assertFalse(command.done.is_set())
        self.bridge.on_answered(self.mw.reviewer, self.mw.reviewer.card, 4)
        self.assertTrue(command.result["ok"])

    def test_stale_revision_rejected(self):
        command = self.command("show", revision=4)
        self.bridge.execute(command)
        self.assertFalse(command.result["ok"])
        self.assertEqual(self.mw.reviewer.state, "question")

    def test_new_session_rejected(self):
        command = self.command("show", session=0)
        self.bridge.execute(command)
        self.assertFalse(command.result["ok"])

    def test_show_answer_twice_does_not_grade(self):
        first = self.command("show")
        self.bridge.execute(first)
        self.assertTrue(first.result["ok"])
        second = self.command("show")
        self.bridge.execute(second)
        self.assertFalse(second.result["ok"])
        self.assertEqual(self.mw.reviewer.grades, [])

    def test_scroll_uses_current_review_webview_without_grading(self):
        for state in ("question", "answer"):
            self.mw.reviewer.state = state
            for action, delta in (("scroll_up", -160), ("scroll_down", 160)):
                command = self.command(action)
                self.bridge.execute(command)
                self.assertTrue(command.result["ok"])
                self.mw.reviewer.web.eval.assert_called_with(
                    f"window.scrollBy({{top: {delta}, left: 0, behavior: 'instant'}});")
                self.assertEqual(self.mw.reviewer.grades, [])
                self.assertEqual(self.bridge.revision, 5)

    def test_scroll_rejects_stale_blocked_background_and_busy(self):
        for extra in ({"revision": 4}, {"session": 0}):
            self.bridge.execute(command := self.command("scroll_down", **extra))
            self.assertFalse(command.result["ok"])
        for change in ("foreground", "blocked", "busy", "state"):
            status = self.bridge.status()
            status[change] = {"foreground": False, "blocked": True, "busy": True, "state": "deckBrowser"}[change]
            with patch.object(self.bridge, "status", return_value=status):
                self.bridge.execute(command := self.command("scroll_down"))
                self.assertFalse(command.result["ok"])
        self.mw.reviewer.web.eval.assert_not_called()

    def test_replay_audio(self):
        command = self.command("replay")
        self.bridge.execute(command)
        self.assertTrue(command.result["ok"])
        self.assertEqual(self.mw.reviewer.replays, 1)

    def test_translated_undo_name(self):
        self.bridge.last_answered_id = 91
        self.assertTrue(self.bridge.status()["can_undo"])

    def test_timed_out_queue_entry_not_executed(self):
        command = self.command("show")
        command.deadline = time.monotonic() - 1
        self.bridge.commands.put(command)
        self.bridge.tick()
        self.assertFalse(command.result["ok"])
        self.assertEqual(self.mw.reviewer.state, "question")

    def test_feedback_for_each_rating_waits_for_exact_completed_action(self):
        for action, ease in (("again", 1), ("hard", 2), ("good", 3), ("easy", 4)):
            with self.subTest(action=action):
                self.bridge.revision = 5
                self.bridge.feedback.reset_mock()
                self.mw.reviewer.state = "answer"
                command = self.command(action, feedback_language="en")
                self.bridge.execute(command)
                self.bridge.feedback.show.assert_not_called()
                self.bridge.on_answered(self.mw.reviewer, self.mw.reviewer.card, ease)
                self.assertTrue(command.result["ok"])
                self.bridge.feedback.show.assert_called_once_with(action, "en")
                self.bridge.on_answered(self.mw.reviewer, self.mw.reviewer.card, ease)
                self.assertEqual(self.bridge.feedback.show.call_count, 1)

    def test_show_and_replay_feedback_match_confirmed_action(self):
        for action in ("show", "replay"):
            self.bridge.feedback.reset_mock()
            command = self.command(action, feedback_language="zh_CN")
            self.bridge.execute(command)
            self.assertTrue(command.result["ok"])
            self.bridge.feedback.show.assert_called_once_with(action, "zh_CN")

    def test_rejected_and_expired_operations_have_no_success_feedback(self):
        for command in (self.command("easy"), self.command("show", revision=0)):
            self.bridge.execute(command)
            self.assertFalse(command.result["ok"])
        expired = self.command("show")
        expired.deadline = time.monotonic() - 1
        self.bridge.commands.put(expired)
        self.bridge.tick()
        self.bridge.feedback.show.assert_not_called()

    def test_cancelled_or_timed_out_rating_cannot_later_show_success(self):
        self.mw.reviewer.state = "answer"
        command = self.command("easy")
        self.bridge.execute(command)
        command.cancelled = True
        command.finish(False, "timeout")
        self.bridge.on_answered(self.mw.reviewer, self.mw.reviewer.card, 4)
        self.assertFalse(command.result["ok"])
        self.bridge.feedback.show.assert_not_called()

    def test_feedback_switch_and_foreground_guards_do_not_change_results(self):
        command = self.command("show", show_feedback=False)
        self.bridge.execute(command)
        self.assertTrue(command.result["ok"])
        self.bridge.feedback.show.assert_not_called()
        command = self.command("replay", foreground_only=False)
        with patch.object(self.mw, "isActiveWindow", return_value=False):
            self.bridge.execute(command)
        self.assertTrue(command.result["ok"])
        self.bridge.feedback.show.assert_not_called()

    def test_scroll_feedback_is_rate_limited_but_other_actions_are_immediate(self):
        with patch.object(self.module.time, "monotonic", return_value=10):
            self.bridge.execute(self.command("scroll_down"))
        with patch.object(self.module.time, "monotonic", return_value=10.22):
            self.bridge.execute(self.command("scroll_down"))
        self.assertEqual(self.bridge.feedback.show.call_count, 1)
        with patch.object(self.module.time, "monotonic", return_value=10.3):
            self.bridge.execute(self.command("replay"))
        self.assertEqual(self.bridge.feedback.show.call_count, 2)
        with patch.object(self.module.time, "monotonic", return_value=11.4):
            self.bridge.execute(self.command("scroll_up"))
        self.assertEqual(self.bridge.feedback.show.call_count, 3)

    def test_undo_feedback_waits_for_success_callback_and_failure_stays_silent(self):
        for successful in (True, False):
            with self.subTest(successful=successful):
                self.bridge.revision = 5
                self.bridge.last_answered_id = 91
                self.bridge.feedback.reset_mock()
                operation = MagicMock()
                operation.success.return_value = operation
                operation.failure.return_value = operation
                operations = types.ModuleType("aqt.operations")
                operations.CollectionOp = MagicMock(return_value=operation)
                command = self.command("undo", feedback_language="en")
                with patch.dict(sys.modules, {"aqt.operations": operations}):
                    self.bridge.execute(command)
                    self.bridge.feedback.show.assert_not_called()
                    self.assertFalse(command.done.is_set())
                    callback = operation.success if successful else operation.failure
                    callback.call_args.args[0](None)
                self.assertEqual(command.result["ok"], successful)
                if successful:
                    self.bridge.feedback.show.assert_called_once_with("undo", "en")
                else:
                    self.bridge.feedback.show.assert_not_called()

    def test_feedback_failure_does_not_corrupt_ack_or_repeat_action(self):
        self.bridge.feedback.show.side_effect = RuntimeError("deleted")
        command = self.command("replay")
        self.bridge.execute(command)
        self.assertTrue(command.result["ok"])
        self.assertEqual(self.mw.reviewer.replays, 1)

    def test_native_feedback_does_not_take_focus_and_clears_on_timer(self):
        from PySide6.QtCore import Qt, QTimer
        from PySide6.QtWidgets import QApplication, QLabel, QLineEdit, QWidget
        app = QApplication.instance() or QApplication([])
        parent = QWidget()
        parent.resize(800, 600)
        field = QLineEdit(parent)
        parent.show()
        field.setFocus()
        app.processEvents()
        focused = app.focusWidget()
        with patch.object(self.module, "QLabel", QLabel), patch.object(self.module, "Qt", Qt), patch.object(self.module, "QTimer", QTimer):
            feedback = self.module.ActionFeedback(parent)
            feedback.show("easy", "zh_CN")
            self.assertTrue(feedback.label.isVisible())
            self.assertEqual(feedback.label.text(), "anki-grip · ✓ 简单")
            self.assertEqual(app.focusWidget(), focused)
            self.assertTrue(feedback.label.testAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents))
            self.assertEqual(feedback.label.textFormat(), Qt.TextFormat.PlainText)
            self.assertEqual(feedback.timer.interval(), 1000)
            feedback.show("undo", "en")
            self.assertEqual(feedback.label.text(), "anki-grip · ✓ Undo Rating")
            self.assertTrue(parent.rect().contains(feedback.label.geometry()))
            feedback.timer.timeout.emit()
            self.assertFalse(feedback.label.isVisible())
            feedback.hide()
        parent.close()

    def test_shutdown_tolerates_deleted_qt_timer(self):
        with patch.object(self.bridge.timer, "stop", side_effect=RuntimeError("deleted")):
            self.bridge.shutdown()
            self.bridge.shutdown()
        self.assertTrue(self.bridge.closed)
        self.bridge.feedback.hide.assert_called_once()


if __name__ == "__main__":
    unittest.main()
