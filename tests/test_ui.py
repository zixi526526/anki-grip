import os
import time
import types
import unittest
from unittest.mock import Mock, patch

from PySide6.QtCore import Qt, QPoint, QPointF
from PySide6.QtGui import QWheelEvent
from PySide6.QtWidgets import QApplication, QScrollArea
from grip.ui import MainWindow
from grip.model import default_config, STICK_GUARD


class UiTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def setUp(self):
        self.defaults_patch = patch("grip.ui.load_defaults", return_value=default_config())
        self.defaults_patch.start()
        self.addCleanup(self.defaults_patch.stop)
        with patch("grip.ui.load_config", return_value=default_config()):
            self.window = MainWindow(offline=True)
        self.window.snapshot = types.SimpleNamespace(index=0)

    def tearDown(self):
        self.window.quitting = True
        self.window.close()

    def test_custom_rating_labels_and_defaults(self):
        self.assertEqual([self.window.key_labels[key].text() for key in ("easy", "good", "hard", "again")], ["1", "2", "3", "4"])
        self.assertFalse(self.window.dirty())
        self.assertEqual(self.window.key_labels["space"].text(), "␣")
        self.assertEqual(self.window.mapping_combos["space"].currentData(), "")

    def prepare_review(self, state):
        self.window.worker = Mock()
        self.window.worker.submit.return_value = True
        self.window.anki_seen_at = time.monotonic()
        self.window.anki_status = {"connected": True, "foreground": True,
                                   "state": state, "revision": 17, "session": "test-session"}

    def test_scroll_dispatch_uses_revision_and_has_no_rumble(self):
        self.prepare_review("question")
        self.window.dispatch("scroll_down")
        self.window.worker.submit.assert_called_once_with("scroll_down", {
            "action": "scroll_down", "revision": 17, "session": "test-session", "foreground_only": True,
            "show_feedback": True, "feedback_language": self.window.language})
        with patch.object(self.window, "rumble") as rumble:
            self.window.on_result("scroll_down", {"ok": True})
            rumble.assert_not_called()
        self.assertEqual(self.window.last_review_state, "")

    def test_scroll_repeat_cancelled_on_card_or_foreground_change(self):
        self.prepare_review("question")
        self.window.mapper.repeating = "scroll_down"
        self.window.on_status({**self.window.anki_status, "revision": 18})
        self.assertEqual(self.window.mapper.repeating, "")
        self.window.mapper.repeating = "scroll_down"
        self.window.on_status({**self.window.anki_status, "foreground": False})
        self.assertEqual(self.window.mapper.repeating, "")

    def test_right_stick_capture_for_scroll(self):
        self.window.begin_capture("scroll_up")
        self.window.capture_step(set())
        self.window.capture_step({"RSTICK_ACTIVE", "RSTICK_UP"})
        self.window.capture_step(set())
        self.assertEqual(self.window.mapping_combos["scroll_up"].currentData(), "RSTICK_UP")

    def test_space_on_question_only_shows_answer(self):
        self.prepare_review("question")
        self.window.dispatch("space")
        self.window.worker.submit.assert_called_once_with("show", {
            "action": "show", "revision": 17, "session": "test-session", "foreground_only": True,
            "show_feedback": True, "feedback_language": self.window.language})
        with patch.object(self.window, "rumble") as rumble:
            self.window.on_result("show", {"ok": True})
            rumble.assert_called_once_with("show")
        self.assertEqual(self.window.last_review_state, "")

    def test_space_on_answer_rates_good_in_both_keyboard_orders(self):
        for order in ("reverse", "standard"):
            with self.subTest(order=order):
                self.prepare_review("answer")
                self.window.order_combo.setCurrentIndex(self.window.order_combo.findData(order))
                self.window.config["order"] = order
                self.window.inflight = False
                self.window.last_dispatch = 0
                self.window.dispatch("space")
                self.window.worker.submit.assert_called_once_with("good", {
                    "action": "good", "revision": 17, "session": "test-session", "foreground_only": True,
            "show_feedback": True, "feedback_language": self.window.language})
                with patch.object(self.window, "rumble") as rumble:
                    self.window.on_result("good", {"ok": True})
                    rumble.assert_called_once_with("good")
                self.assertEqual(self.window.last_review_state, "rated")

    def test_space_obeys_connection_foreground_and_revision_freshness_guards(self):
        for changes, stale in (({"connected": False}, False), ({"foreground": False}, False),
                               ({"blocked": True}, False), ({"state": "deckBrowser"}, False), ({}, True)):
            with self.subTest(changes=changes, stale=stale):
                self.prepare_review("answer")
                self.window.anki_status.update(changes)
                if stale:
                    self.window.anki_seen_at -= 2
                self.window.dispatch("space")
                self.window.worker.submit.assert_not_called()

    def test_holding_space_binding_never_rates_after_answer_appears(self):
        self.prepare_review("question")
        self.window.mapper.bindings["space"] = "X"
        self.window.mapper.step(set())
        for action in self.window.mapper.step({"X"}):
            self.window.dispatch(action)
        self.window.on_result("show", {"ok": True})
        self.window.anki_status["state"] = "answer"
        self.window.last_dispatch = 0
        for _ in range(50):
            for action in self.window.mapper.step({"X"}):
                self.window.dispatch(action)
        self.assertEqual(self.window.worker.submit.call_count, 1)
        self.window.mapper.step(set())
        for action in self.window.mapper.step({"X"}):
            self.window.dispatch(action)
        self.assertEqual(self.window.worker.submit.call_count, 2)
        self.assertEqual(self.window.worker.submit.call_args.args[0], "good")

    def test_space_rejected_command_does_not_rumble_or_retry(self):
        self.prepare_review("answer")
        self.window.dispatch("space")
        with patch.object(self.window, "rumble") as rumble:
            self.window.on_result("good", {"ok": False, "message": "状态已过期"})
            rumble.assert_not_called()
        self.assertEqual(self.window.worker.submit.call_count, 1)
        self.assertFalse(self.window.inflight)

    def test_space_binding_capture_and_save(self):
        self.window.begin_capture("space")
        self.window.capture_step(set())
        self.window.capture_step({"L3"})
        self.window.capture_step(set())
        with patch("grip.ui.save_config") as save:
            self.window.apply_settings()
            self.assertEqual(save.call_args.args[0]["bindings"]["space"], "L3")
        self.assertEqual(self.window.mapper.bindings["space"], "L3")

    def test_capture_new_single_and_save(self):
        self.window.begin_capture("easy")
        self.window.capture_step(set())
        self.window.capture_step({"X"})
        self.window.capture_step(set())
        self.assertEqual(self.window.mapping_combos["easy"].currentData(), "X")
        self.assertTrue(self.window.dirty())
        with patch("grip.ui.save_config") as save:
            self.window.apply_settings()
            save.assert_called_once()
        self.assertEqual(self.window.mapper.bindings["easy"], "X")
        self.assertFalse(self.window.dirty())

    def test_capture_chord(self):
        self.window.begin_capture("undo")
        self.window.capture_step(set())
        self.window.capture_step({"LT"})
        self.window.capture_step({"LT", "X"})
        self.window.capture_step({"LT"})
        self.window.capture_step(set())
        self.assertEqual(self.window.mapping_combos["undo"].currentData(), "LT+X")

    def test_captured_duplicate_moves_existing_binding(self):
        self.window.begin_capture("easy")
        self.window.capture_step(set())
        self.window.capture_step({"LT"})
        self.window.capture_step(set())
        self.assertEqual(self.window.mapping_combos["replay"].currentData(), "")
        self.assertEqual(self.window.mapping_combos["easy"].currentData(), "LT")

    def test_capture_stick_direction_and_return_to_center(self):
        self.window.begin_capture("good")
        self.window.capture_step({STICK_GUARD})
        self.assertFalse(self.window.capture_ready)
        self.window.capture_step(set())
        self.window.capture_step({STICK_GUARD})
        self.window.capture_step({STICK_GUARD, "LSTICK_RIGHT"})
        self.window.capture_step({STICK_GUARD, "LSTICK_RIGHT"})
        self.window.capture_step(set())
        self.assertEqual(self.window.mapping_combos["good"].currentData(), "LSTICK_RIGHT")
        self.assertEqual(self.window.mapping_combos["hard"].currentData(), "")

    def test_restore_defaults_recovers_entire_saved_profile(self):
        defaults = default_config()
        defaults.update(strength=32, vibration=False, anki_feedback=False, foreground_only=False,
                        controller=2, order="standard", minimize_to_tray=False)
        defaults["bindings"].update(show="", space="LSTICK_DOWN")
        with patch("grip.ui.load_defaults", return_value=defaults):
            self.window.restore_defaults()
        self.assertEqual(self.window.current_ui_config(), defaults)
        self.assertTrue(self.window.dirty())

    def test_set_as_defaults_saves_and_applies_current_whole_profile(self):
        self.window.mapping_combos["show"].setCurrentIndex(0)
        combo = self.window.mapping_combos["space"]
        combo.setCurrentIndex(combo.findData("LSTICK_DOWN"))
        self.window.strength_slider.setValue(32)
        self.window.vibration_check.setChecked(False)
        expected = self.window.current_ui_config()
        with patch("grip.ui.save_config") as save, patch("grip.ui.save_defaults") as defaults:
            self.window.set_as_defaults()
            save.assert_called_once_with(expected)
            defaults.assert_called_once_with(expected)
        self.assertEqual(self.window.config, expected)
        self.assertFalse(self.window.dirty())

    def test_duplicate_binding_cannot_replace_saved_defaults(self):
        combo = self.window.mapping_combos["good"]
        combo.setCurrentIndex(combo.findData("LSTICK_LEFT"))
        with patch("grip.ui.save_config") as save, patch("grip.ui.save_defaults") as defaults, \
                patch("grip.ui.QMessageBox.warning"):
            self.window.set_as_defaults()
            save.assert_not_called()
            defaults.assert_not_called()

    @staticmethod
    def wheel():
        return QWheelEvent(QPointF(10, 10), QPointF(10, 10), QPoint(), QPoint(0, -120),
                           Qt.MouseButton.NoButton, Qt.KeyboardModifier.NoModifier,
                           Qt.ScrollPhase.NoScrollPhase, False)

    def test_wheel_cannot_change_any_setting_even_when_focused(self):
        controls = [*self.window.mapping_combos.values(), self.window.order_combo,
                    self.window.device_combo, self.window.pattern_combo, self.window.language_combo, self.window.strength_slider]
        for widget in controls:
            for focused in (False, True):
                with self.subTest(widget=type(widget).__name__, focused=focused):
                    if focused:
                        widget.setFocus()
                    else:
                        widget.clearFocus()
                    before = widget.value() if hasattr(widget, "value") else widget.currentData()
                    event = self.wheel()
                    QApplication.sendEvent(widget, event)
                    after = widget.value() if hasattr(widget, "value") else widget.currentData()
                    self.assertEqual(after, before)
                    self.assertFalse(event.isAccepted())
        self.assertFalse(self.window.dirty())

    def test_mapping_list_still_scrolls_with_wheel(self):
        self.window.resize(930, 660)
        self.window.show()
        self.app.processEvents()
        scroll = self.window.tabs.widget(0).findChild(QScrollArea)
        bar = scroll.verticalScrollBar()
        self.assertGreater(bar.maximum(), 0)
        bar.setValue(0)
        QApplication.sendEvent(scroll.viewport(), self.wheel())
        self.assertGreater(bar.value(), 0)
        self.assertFalse(self.window.dirty())

    def test_anki_feedback_preference_is_applied_and_sent_in_selected_language(self):
        self.window.anki_feedback_check.setChecked(False)
        self.window.language_combo.setCurrentIndex(self.window.language_combo.findData("en"))
        with patch("grip.ui.save_config") as save:
            self.assertTrue(self.window.apply_settings())
            self.assertFalse(save.call_args.args[0]["anki_feedback"])
        self.prepare_review("answer")
        self.window.dispatch("easy")
        payload = self.window.worker.submit.call_args.args[1]
        self.assertFalse(payload["show_feedback"])
        self.assertEqual(payload["feedback_language"], "en")
        self.assertEqual(payload["action"], "easy")

    def test_pause_and_resume(self):
        self.window.toggle_pause()
        self.assertTrue(self.window.paused)
        self.window.toggle_pause()
        self.assertFalse(self.window.paused)


if __name__ == "__main__":
    unittest.main()
