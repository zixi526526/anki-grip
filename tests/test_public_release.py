"""Release regressions use synthetic input and temporary settings only."""
import ast
import json
import tempfile
import time
import unittest
from pathlib import Path
from string import Formatter
from unittest.mock import Mock, patch

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QApplication, QLabel, QPushButton, QCheckBox

from grip.controller_view import ControllerView
from grip.i18n import EN, translate, resolve_language
from grip.model import ACTIONS, BINDINGS, LABELS, InputMapper, default_config, load_config, save_config, validate_bindings
from grip.ui import MainWindow, STYLE
from grip.xinput import Snapshot, XInput


class LocalizationTests(unittest.TestCase):
    def test_system_locale_resolution_and_explicit_override(self):
        for language, system, expected in (("auto", "zh_CN", "zh_CN"), ("auto", "zh_TW", "zh_CN"),
                                           ("auto", "en_US", "en"), ("auto", "de_DE", "en"),
                                           ("zh_CN", "en_US", "zh_CN"), ("en", "zh_CN", "en")):
            with self.subTest(language=language, system=system):
                self.assertEqual(resolve_language(language, system), expected)

    def test_translation_placeholders_match_and_known_text_is_english(self):
        def fields(text):
            return {field for _, field, _, _ in Formatter().parse(text) if field is not None}
        for source, english in EN.items():
            with self.subTest(source=source):
                self.assertEqual(fields(source), fields(english))
                if source not in ("界面语言 / Language", "跟随系统 / System"):
                    self.assertFalse(any("\u4e00" <= char <= "\u9fff" for char in english))
        self.assertEqual(translate("third-party detail", "en"), "third-party detail")

    def test_every_known_bridge_message_has_an_english_translation(self):
        for filename in ("grip/bridge.py", "addon/anki_grip_bridge/__init__.py", "grip/xinput.py"):
            tree = ast.parse((Path(__file__).resolve().parents[1] / filename).read_text(encoding="utf-8"))
            for node in ast.walk(tree):
                if isinstance(node, ast.Constant) and isinstance(node.value, str) and "\n" not in node.value:
                    if any("\u4e00" <= ch <= "\u9fff" for ch in node.value):
                        # The standalone add-on's startup warning is explicitly bilingual.
                        if "anki-grip 无法监听本机端口" not in node.value:
                            self.assertIn(node.value, EN, f"Missing translation in {filename}")

    def test_old_configuration_preserves_preferences_and_adds_language(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "settings.json"
            config = default_config()
            config.pop("language")
            config.pop("anki_feedback")
            config.update(strength=23, order="standard", vibration=False, controller=2)
            config["bindings"].update(show="A", space="B", undo="RB+MENU", good="RT+VIEW")
            path.write_text(json.dumps(config))
            original = path.read_bytes()
            self.assertEqual(load_config(path), {**config, "language": "auto", "anki_feedback": True})
            self.assertEqual(path.read_bytes(), original)
            loaded = load_config(path)
            loaded["language"] = "en"
            save_config(loaded, path)
            self.assertEqual(load_config(path), loaded)
            loaded["language"] = "unsupported"
            save_config(loaded, path)
            self.assertEqual(load_config(path)["language"], "auto")

    def test_conflict_errors_use_selected_language(self):
        config = default_config()
        config["bindings"]["good"] = "LSTICK_LEFT"
        with self.assertRaisesRegex(ValueError, "Left stick.*Easy.*Good"):
            validate_bindings(config["bindings"], "en")


class FullInputTests(unittest.TestCase):
    def test_every_xinput_control_can_be_remapped_and_is_edge_triggered(self):
        for control in LABELS:
            with self.subTest(control=control):
                mapper = InputMapper({"good": control})
                self.assertEqual(mapper.step({control}), [])  # held when attached
                mapper.step(set())
                self.assertEqual(mapper.step({control}), ["good"])
                for _ in range(20):
                    self.assertEqual(mapper.step({control}), [])
                self.assertEqual(mapper.step(set()), [])

    def test_every_supported_chord_requires_modifier_first_and_consumes_singles(self):
        for binding in BINDINGS:
            if "+" not in binding:
                continue
            with self.subTest(binding=binding):
                modifier, key = binding.split("+")
                mapper = InputMapper({"undo": binding, "easy": key, "replay": modifier})
                mapper.step(set())
                self.assertEqual(mapper.step({modifier}), [])
                self.assertEqual(mapper.step({modifier, key}), ["undo"])
                self.assertEqual(mapper.step({modifier, key}), [])
                self.assertEqual(mapper.step({modifier}), [])
                self.assertEqual(mapper.step(set()), [])
                self.assertEqual(mapper.step({modifier, key}), [])  # simultaneous rejected
                self.assertEqual(mapper.step(set()), [])

    def test_ambiguous_chords_do_not_choose_a_rating(self):
        mapper = InputMapper({"easy": "LB+A", "hard": "RB+A", "undo": "LB", "replay": "RB"})
        mapper.step(set())
        mapper.step({"LB"})
        mapper.step({"LB", "RB"})
        self.assertEqual(mapper.step({"LB", "RB", "A"}), [])
        self.assertEqual(mapper.step(set()), [])

    def test_native_xinput_bitmasks_and_trigger_hysteresis(self):
        native = Mock()
        native.XInputGetBatteryInformation.return_value = 1
        sample = {"buttons": 0, "lt": 0, "rt": 0}
        def state(_index, pointer):
            for name, value in sample.items():
                setattr(pointer._obj.gamepad, name, value)
            return 0
        native.XInputGetState.side_effect = state
        with patch("grip.xinput.ctypes.WinDLL", return_value=native, create=True):
            pad = XInput()
        for mask, expected in ((1, "DPAD_UP"), (2, "DPAD_DOWN"), (4, "DPAD_LEFT"), (8, "DPAD_RIGHT"),
                               (16, "MENU"), (32, "VIEW"), (64, "L3"), (128, "R3"), (256, "LB"),
                               (512, "RB"), (4096, "A"), (8192, "B"), (16384, "X"), (32768, "Y")):
            sample["buttons"] = mask
            self.assertEqual(pad.read(0).down, {expected})
        sample["buttons"] = 0
        for trigger in ("lt", "rt"):
            for value, active in ((160, False), (161, True), (100, True), (95, False)):
                sample[trigger] = value
                snapshot = pad.read(0)
                self.assertEqual(getattr(snapshot, trigger), value)
                self.assertEqual(trigger.upper() in snapshot.down, active)
            sample[trigger] = 0


class PublicUiTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])
        cls.app.setStyleSheet(STYLE)

    def setUp(self):
        config = default_config()
        config["language"] = "zh_CN"
        with patch("grip.ui.load_config", return_value=config):
            self.window = MainWindow(offline=True)
        self.window.snapshot = Snapshot(0, set(), 0, 0, "电量充足")

    def tearDown(self):
        self.window.quitting = True
        self.window.close()

    def select_language(self, language):
        self.window.language_combo.setCurrentIndex(self.window.language_combo.findData(language))

    def test_language_switch_retains_unsaved_controls_and_translates_tray_and_bindings(self):
        combo = self.window.mapping_combos["good"]
        combo.setCurrentIndex(combo.findData("RB+MENU"))
        self.window.strength_slider.setValue(48)
        self.window.order_combo.setCurrentIndex(self.window.order_combo.findData("standard"))
        before = self.window.current_ui_config()
        with patch("grip.ui.save_config") as save:
            self.select_language("en")
            save.assert_not_called()
        self.assertEqual(self.window.current_ui_config(), {**before, "language": "en"})
        self.assertEqual(self.window.tabs.tabText(0), "Mappings")
        self.assertEqual(self.window.tray_pause_action.text(), "Pause Control")
        self.assertIn("Right bumper", combo.currentText())
        self.assertEqual([self.window.key_labels[k].text() for k in ("easy", "good", "hard", "again")], ["4", "3", "2", "1"])
        self.select_language("zh_CN")
        self.assertEqual(self.window.current_ui_config(), before)

    def test_language_is_saved_and_restored_with_entire_profile(self):
        self.select_language("en")
        expected = self.window.current_ui_config()
        with patch("grip.ui.save_config") as save:
            self.assertTrue(self.window.apply_settings())
            save.assert_called_once_with(expected)
        self.assertFalse(self.window.dirty())
        defaults = {**expected, "language": "zh_CN", "strength": 27}
        with patch("grip.ui.load_defaults", return_value=defaults):
            self.window.restore_defaults()
        self.assertEqual(self.window.language, "zh_CN")
        self.assertEqual(self.window.current_ui_config(), defaults)

    def test_english_ui_has_no_untranslated_user_text(self):
        self.select_language("en")
        for widget in [widget for kind in (QLabel, QPushButton, QCheckBox)
                       for widget in self.window.findChildren(kind)]:
            text = widget.text()
            if "Language /" not in text:
                self.assertFalse(any("\u4e00" <= ch <= "\u9fff" for ch in text), text)
        self.window.on_result("good", {"ok": True, "message": "评分已确认。"})
        self.assertEqual(self.window.notice.text(), "Rating confirmed.")
        self.select_language("zh_CN")
        self.assertEqual(self.window.pause_button.text(), "暂停控制")

    def test_capture_all_new_chords_and_transfer_duplicate_binding(self):
        for binding in ("RB+VIEW", "RT+MENU", "LB+RT", "RT+RB", "RB+RSTICK_RIGHT"):
            with self.subTest(binding=binding):
                modifier, key = binding.split("+")
                self.window.begin_capture("good")
                self.window.capture_step(set())
                self.window.capture_step({modifier})
                self.window.capture_step({modifier, key})
                self.window.capture_step({modifier})
                self.window.capture_step(set())
                self.assertEqual(self.window.mapping_combos["good"].currentData(), binding)

    def test_switching_language_during_capture_preserves_capture_and_edit(self):
        self.window.begin_capture("good")
        self.window.capture_step(set())
        self.select_language("en")
        self.assertEqual(self.window.capture_action, "good")
        self.assertEqual(self.window.capture_buttons["good"].text(), "Waiting…")
        self.window.capture_step({"A"})
        self.window.capture_step(set())
        self.assertEqual(self.window.mapping_combos["good"].currentData(), "A")
        self.assertIn("Captured A", self.window.notice.text())

    def test_test_tab_never_sends_review_commands_and_requires_release_on_return(self):
        self.window.worker = Mock()
        self.window.worker.submit.return_value = True
        self.window.anki_status = {"connected": True, "foreground": True, "state": "answer", "revision": 5, "session": "fake"}
        self.window.anki_seen_at = time.monotonic()
        self.window.mapper.bindings["good"] = "A"
        self.window.mapper.step(set())
        self.window.tabs.setCurrentIndex(self.window.test_tab_index)
        self.window.dispatch("good")
        self.window.worker.submit.assert_not_called()
        self.assertTrue(self.window.testing)
        self.window.tabs.setCurrentIndex(0)
        self.assertFalse(self.window.testing)
        self.assertEqual(self.window.mapper.step({"A"}), [])
        self.window.mapper.step(set())
        self.assertEqual(self.window.mapper.step({"A"}), ["good"])

    def test_view_updates_when_analog_values_change_without_button_edges_and_clears_disconnect(self):
        self.window.pad = Mock()
        self.window.pad.read.return_value = self.window.snapshot
        self.window.poll()
        held = Snapshot(0, {"RT", "RSTICK_ACTIVE"}, 8, 220, "电量充足", -1000, 2000, 26000, -23000)
        self.window.pad.read.return_value = held
        self.window.poll()
        view = self.window.test_controller_view
        first = view._sample
        self.assertEqual(view.axes, (-1000, 2000, 26000, -23000))
        self.assertEqual(view.triggers, (8, 220))
        self.assertIn("-23000", self.window.axes_label.text())
        held.rt = 245
        self.window.poll()
        self.assertNotEqual(view._sample, first)
        self.assertEqual(view.triggers, (8, 245))
        self.window.pad.read.return_value = None
        self.window.poll()
        self.assertEqual(view.down, frozenset())
        self.assertEqual(view.axes, (0, 0, 0, 0))
        self.assertEqual(view.triggers, (0, 0))

    def test_small_window_can_scroll_without_overlapping_the_controller(self):
        self.window.resize(1080, 700)
        self.window.snapshot = Snapshot(0, set(LABELS), 255, 255, "电量充足")
        self.window.show()
        self.app.processEvents()
        self.window.update_controller_labels()
        self.app.processEvents()
        view = self.window.controller_view
        for button in view.parentWidget().findChildren(QPushButton):
            self.assertFalse(view.geometry().intersects(button.geometry()), button.text())
        self.assertGreater(self.window.sidebar_scroll.verticalScrollBar().maximum(), 0)

    def test_controller_paint_handles_extremes_resizing_and_disconnect(self):
        self.window.tabs.setCurrentIndex(self.window.test_tab_index)
        self.window.show()
        self.app.processEvents()
        view = self.window.test_controller_view
        for snapshot in (Snapshot(0, set(LABELS), 255, 255, "有线连接", -32768, 32767, 32767, -32768), None):
            view.set_snapshot(snapshot)
            for width, height in ((520, 360), (300, 220), (780, 500)):
                view.resize(width, height)
                self.assertFalse(view.grab().isNull())
        self.assertEqual(ControllerView.axis_fraction(-32768), -1)
        self.assertEqual(ControllerView.axis_fraction(32767), 1)


if __name__ == "__main__":
    unittest.main()
