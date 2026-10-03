import ctypes
import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

from grip.model import StickDirections, STICK_GUARD, InputMapper, default_config, LEGACY_BINDINGS, load_config, save_config
from grip.xinput import XInput


class StickTests(unittest.TestCase):
    def setUp(self):
        self.stick = StickDirections()
        self.mapper = InputMapper(default_config()["bindings"])
        self.now = 0.0
        self.feed(0, 0)

    def feed(self, x, y, delta=.05):
        self.now += delta
        return self.mapper.step(self.stick.step(x, y, self.now))

    def push(self, x, y):
        self.assertEqual(self.feed(x, y), [])
        return self.feed(x, y)

    def test_requested_defaults_are_exact(self):
        self.assertEqual(default_config()["bindings"], {
            "easy": "LSTICK_LEFT", "good": "", "hard": "LSTICK_RIGHT",
            "again": "LSTICK_UP", "show": "LSTICK_DOWN", "space": "", "replay": "LT",
            "undo": "LB", "pause": "", "scroll_up": "RSTICK_UP", "scroll_down": "RSTICK_DOWN",
        })

    def test_all_four_axes_have_correct_sign_and_semantics(self):
        for x, y, action in ((-32768, 0, "easy"), (0, -32768, "show"),
                             (32767, 0, "hard"), (0, 32767, "again")):
            self.feed(0, 0)
            self.assertEqual(self.push(x, y), [action])

    def test_hold_does_not_repeat_or_change_direction_until_center(self):
        self.assertEqual(self.push(-25000, 0), ["easy"])
        for _ in range(100):
            self.assertEqual(self.feed(-25000, 0), [])
        self.assertEqual(self.feed(0, 25000), [])
        self.assertEqual(self.feed(0, 25000), [])
        self.feed(0, 0)
        self.assertEqual(self.push(0, 25000), ["again"])

    def test_deadzone_and_threshold_jitter_do_not_rearm(self):
        for x in (1000, -2200, 7000, -8999):
            self.assertEqual(self.feed(x, 0), [])
        self.assertEqual(self.push(25000, 0), ["hard"])
        for x in (19000, 17999, 11000, 9001, 25000, 18001):
            self.assertEqual(self.feed(x, 0), [])
        self.feed(0, 0)
        self.assertEqual(self.push(25000, 0), ["hard"])

    def test_diagonal_remains_blocked_until_center(self):
        self.assertEqual(self.feed(25000, 25000), [])
        self.assertEqual(self.feed(25000, 0), [])
        self.assertEqual(self.feed(25000, 0), [])
        self.feed(0, 0)
        self.assertEqual(self.push(25000, 0), ["hard"])

    def test_settling_catches_direction_that_becomes_diagonal(self):
        self.assertEqual(self.feed(25000, 0, .001), [])
        self.assertEqual(self.feed(25000, 22000, .015), [])
        self.assertEqual(self.feed(25000, 0, .1), [])

    def test_stick_held_at_startup_needs_center(self):
        self.stick = StickDirections()
        self.mapper.reset()
        self.assertEqual(self.feed(25000, 0), [])
        self.assertEqual(self.feed(25000, 0), [])
        self.feed(0, 0)
        self.assertEqual(self.push(25000, 0), ["hard"])

    def test_remapping_while_held_needs_center(self):
        self.assertEqual(self.push(25000, 0), ["hard"])
        self.mapper.reset()
        self.assertEqual(self.feed(25000, 0), [])
        self.feed(0, 0)
        self.assertEqual(self.push(25000, 0), ["hard"])

    def test_right_stick_scroll_signs_and_hold_repeat(self):
        stick = StickDirections("RSTICK")
        for y, action in ((25000, "scroll_up"), (-25000, "scroll_down")):
            self.mapper.reset()
            self.mapper.step(stick.step(0, 0, 0), now=0)
            self.mapper.step(stick.step(0, y, .1), now=.1)
            self.assertEqual(self.mapper.step(stick.step(0, y, .2), now=.2), [action])
            self.assertEqual(self.mapper.step(stick.step(0, y, .3), now=.3), [])
            self.assertEqual(self.mapper.step(stick.step(0, y, .7), now=.7), [action])
            self.assertEqual(self.mapper.step(stick.step(0, 0, .8), now=.8), [])
            self.assertEqual(self.mapper.step(set(), now=2), [])

    def test_scroll_repeat_stops_when_deflection_no_longer_aligned(self):
        self.mapper.step({"RSTICK_UP"}, now=0)
        self.assertEqual(self.mapper.step({"RSTICK_UP"}, now=1, repeat_allowed=False), [])
        self.assertEqual(self.mapper.step({"RSTICK_UP"}, now=2), [])

    def test_scroll_repeat_reset_and_chord_suppression(self):
        self.mapper.step({"RSTICK_UP"}, now=0)
        self.mapper.reset()
        self.assertEqual(self.mapper.step({"RSTICK_UP"}, now=1), [])
        self.assertEqual(self.mapper.step({"RSTICK_UP"}, now=2), [])
        self.mapper.step(set(), now=3)
        self.mapper.bindings["show"] = "LB+RSTICK_UP"
        self.mapper.step({"LB"}, now=4)
        self.assertEqual(self.mapper.step({"LB", "RSTICK_UP"}, now=5), ["show"])
        self.assertEqual(self.mapper.step({"LB", "RSTICK_UP"}, now=6), [])

    def test_lt_and_lb_fire_on_press_with_new_defaults(self):
        self.assertEqual(self.mapper.step({"LT"}), ["replay"])
        self.assertEqual(self.mapper.step({"LT"}), [])
        self.assertEqual(self.mapper.step(set()), [])
        self.assertEqual(self.mapper.step({"LB"}), ["undo"])
        self.assertEqual(self.mapper.step(set()), [])

    def test_legacy_default_migrates_and_preserves_strength(self):
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "settings.json"
            config = default_config()
            config.update(schema=1, bindings=LEGACY_BINDINGS, strength=32)
            save_config(config, path)
            loaded = load_config(path)
            self.assertEqual(loaded["schema"], 2)
            self.assertEqual(loaded["strength"], 32)
            self.assertEqual(loaded["bindings"], default_config()["bindings"])

    def test_custom_legacy_bindings_are_preserved(self):
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "settings.json"
            config = default_config()
            config.update(schema=1, bindings={**LEGACY_BINDINGS, "easy": "X"})
            save_config(config, path)
            self.assertEqual(load_config(path)["bindings"], dict(config["bindings"], space="", scroll_up="RSTICK_UP", scroll_down="RSTICK_DOWN"))

    def test_schema_two_unbound_values_survive_reload(self):
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "settings.json"
            save_config(default_config(), path)
            self.assertEqual(load_config(path), default_config())

    def test_existing_schema_two_adds_unbound_space_without_changing_preferences(self):
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "settings.json"
            config = default_config()
            config["bindings"].pop("space")
            config["bindings"]["easy"] = "X"
            config["strength"] = 32
            save_config(config, path)
            loaded = load_config(path)
            self.assertEqual(loaded["bindings"], dict(config["bindings"], space="", scroll_up="RSTICK_UP", scroll_down="RSTICK_DOWN"))
            self.assertEqual(loaded["strength"], 32)

    def test_existing_profile_gains_scroll_and_keeps_personal_bindings(self):
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "settings.json"
            config = default_config()
            config["bindings"].pop("scroll_up")
            config["bindings"].pop("scroll_down")
            config["bindings"].update(show="", space="LSTICK_DOWN")
            config["strength"] = 50
            save_config(config, path)
            loaded = load_config(path)
            self.assertEqual(loaded["bindings"], dict(config["bindings"],
                             scroll_up="RSTICK_UP", scroll_down="RSTICK_DOWN"))
            self.assertEqual(loaded["strength"], 50)

    def test_new_scroll_default_never_overwrites_an_existing_binding(self):
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "settings.json"
            config = default_config()
            config["bindings"].pop("scroll_up")
            config["bindings"]["easy"] = "RSTICK_UP"
            save_config(config, path)
            loaded = load_config(path)
            self.assertEqual(loaded["bindings"]["easy"], "RSTICK_UP")
            self.assertEqual(loaded["bindings"]["scroll_up"], "")

    def test_xinput_right_stick_axes_alignment_and_reconnection(self):
        native = Mock()
        native.XInputGetBatteryInformation.return_value = 1
        sample = {"x": 0, "y": 0, "connected": True}
        def get_state(index, pointer):
            if not sample["connected"]:
                return 1167
            pointer._obj.gamepad.rx = sample["x"]
            pointer._obj.gamepad.ry = sample["y"]
            return 0
        native.XInputGetState.side_effect = get_state
        with patch("grip.xinput.ctypes.WinDLL", return_value=native, create=True):
            pad = XInput()
        with patch("grip.model.time.monotonic", return_value=1):
            self.assertEqual(pad.read(0).down, set())
            sample["y"] = 25000
            self.assertEqual(pad.read(0).down, {"RSTICK_ACTIVE"})
        with patch("grip.model.time.monotonic", return_value=1.1):
            state = pad.read(0)
            self.assertEqual(state.down, {"RSTICK_ACTIVE", "RSTICK_UP"})
            self.assertTrue(state.scroll_allowed)
            sample["x"] = 25000
            self.assertFalse(pad.read(0).scroll_allowed)
            sample["connected"] = False
            self.assertIsNone(pad.read(0))
            self.assertEqual(pad.right_sticks, {})
            sample.update(connected=True, x=0)
            self.assertEqual(pad.read(0).down, {"RSTICK_ACTIVE"})

    def test_xinput_reads_axes_and_clears_state_after_disconnect(self):
        native = Mock()
        native.XInputGetBatteryInformation.return_value = 1
        sample = {"x": 0, "y": 0, "connected": True}

        def get_state(index, pointer):
            if not sample["connected"]:
                return 1167
            pointer._obj.gamepad.lx = sample["x"]
            pointer._obj.gamepad.ly = sample["y"]
            return 0

        native.XInputGetState.side_effect = get_state
        with patch("grip.xinput.ctypes.WinDLL", return_value=native, create=True):
            pad = XInput()
        with patch("grip.model.time.monotonic", return_value=1.0):
            self.assertEqual(pad.read(0).down, set())
            sample.update(x=-25000)
            self.assertEqual(pad.read(0).down, {STICK_GUARD})
        with patch("grip.model.time.monotonic", return_value=1.1):
            state = pad.read(0)
            self.assertEqual(state.down, {STICK_GUARD, "LSTICK_LEFT"})
            self.assertEqual(state.lx, -25000)
            sample["connected"] = False
            self.assertIsNone(pad.read(0))
            self.assertEqual(pad.sticks, {})
            sample["connected"] = True
            self.assertEqual(pad.read(0).down, {STICK_GUARD})


if __name__ == "__main__":
    unittest.main()
