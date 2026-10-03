import tempfile
import unittest
from unittest.mock import patch
from pathlib import Path

from grip.model import InputMapper, LEGACY_BINDINGS, default_config, load_config, load_defaults, rating_keys, save_config, save_defaults, validate_bindings


class MappingTests(unittest.TestCase):
    def setUp(self):
        self.mapper = InputMapper(LEGACY_BINDINGS)
        self.mapper.step(set())

    def test_reversed_numbers_are_labels_not_scheduler_ease(self):
        self.assertEqual(rating_keys("reverse"), {"easy": "1", "good": "2", "hard": "3", "again": "4"})
        self.assertEqual(self.mapper.step({"DPAD_UP"}), ["easy"])

    def test_long_press_only_once(self):
        self.assertEqual(self.mapper.step({"DPAD_RIGHT"}), ["good"])
        for _ in range(500):
            self.assertEqual(self.mapper.step({"DPAD_RIGHT"}), [])
        self.mapper.step(set())
        self.assertEqual(self.mapper.step({"DPAD_RIGHT"}), ["good"])

    def test_diagonal_never_turns_into_a_rating_until_release(self):
        self.assertEqual(self.mapper.step({"DPAD_RIGHT", "DPAD_UP"}), [])
        self.assertEqual(self.mapper.step({"DPAD_RIGHT"}), [])
        self.mapper.step(set())
        self.assertEqual(self.mapper.step({"DPAD_RIGHT"}), ["good"])

    def test_replay_on_release(self):
        self.assertEqual(self.mapper.step({"LB"}), [])
        self.assertEqual(self.mapper.step(set()), ["replay"])

    def test_undo_consumes_replay_and_again(self):
        self.assertEqual(self.mapper.step({"LB"}), [])
        self.assertEqual(self.mapper.step({"LB", "DPAD_LEFT"}), ["undo"])
        self.assertEqual(self.mapper.step({"LB"}), [])
        self.assertEqual(self.mapper.step(set()), [])

    def test_simultaneous_chord_never_scores(self):
        self.assertEqual(self.mapper.step({"LB", "DPAD_LEFT"}), [])
        self.assertEqual(self.mapper.step(set()), [])

    def test_reconnection_requires_all_keys_released(self):
        self.mapper.reset()
        self.assertEqual(self.mapper.step({"DPAD_UP"}), [])
        self.assertEqual(self.mapper.step({"DPAD_UP"}), [])
        self.mapper.step(set())
        self.assertEqual(self.mapper.step({"DPAD_UP"}), ["easy"])

    def test_new_binding(self):
        config = default_config()
        config["bindings"]["easy"] = "X"
        mapper = InputMapper(config["bindings"])
        mapper.step(set())
        self.assertEqual(mapper.step({"X"}), ["easy"])
        mapper.step(set())
        self.assertEqual(mapper.step({"DPAD_UP"}), [])

    def test_invalid_duplicate_configuration(self):
        bindings = default_config()["bindings"]
        bindings["good"] = bindings["easy"]
        with self.assertRaises(ValueError):
            validate_bindings(bindings)

    def test_config_persists_and_recovers_from_invalid_file(self):
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "settings.json"
            config = default_config()
            config["strength"] = 23
            config["anki_feedback"] = False
            config["bindings"]["easy"] = "X"
            save_config(config, path)
            self.assertEqual(load_config(path), config)
            path.write_text('{"strength": -25, "bindings": null}', encoding="utf-8")
            self.assertEqual(load_config(path)["strength"], 0)
            path.write_text("broken", encoding="utf-8")
            self.assertEqual(load_config(path), default_config())

    def test_saved_defaults_survive_reload_and_missing_settings(self):
        with tempfile.TemporaryDirectory() as temp:
            config = default_config()
            config["bindings"].update(show="", space="LSTICK_DOWN")
            config.update(strength=32, vibration=False, controller=2)
            path = Path(temp) / "defaults.json"
            save_defaults(config, path)
            self.assertEqual(load_defaults(path), config)
            with patch("grip.model.config_dir", return_value=Path(temp)):
                self.assertEqual(load_config(), config)
                settings = {**config, "strength": 51}
                save_config(settings)
                self.assertEqual(load_config(), settings)
                self.assertEqual(load_defaults(), config)

    def test_invalid_defaults_file_falls_back_without_overwriting_settings(self):
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "defaults.json"
            path.write_text("broken", encoding="utf-8")
            self.assertEqual(load_defaults(path), default_config())


if __name__ == "__main__":
    unittest.main()
