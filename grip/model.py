"""Semantic actions and deterministic, release-safe controller mapping."""
from __future__ import annotations

import json
import os
import time
from pathlib import Path
from .i18n import LANGUAGES, translate

ACTIONS = {
    "easy": ("简单", "完全掌握", "LSTICK_LEFT"),
    "good": ("良好", "正常记住", ""),
    "hard": ("困难", "想起但费力", "LSTICK_RIGHT"),
    "again": ("重来", "需要再学", "LSTICK_UP"),
    "show": ("显示答案", "只翻答案，不评分", "LSTICK_DOWN"),
    "space": ("空格：显示答案 / 良好", "正面翻答案，背面选良好", ""),
    "replay": ("重播音频", "当前卡片的音频", "LT"),
    "undo": ("撤销上次评分", "回到上一张已评分卡片", "LB"),
    "scroll_up": ("向上滚动", "推住连续滚动卡片页面", "RSTICK_UP"),
    "scroll_down": ("向下滚动", "推住连续滚动卡片页面", "RSTICK_DOWN"),
    "pause": ("暂停 / 恢复", "随时切换控制状态", ""),
}
SCROLL_ACTIONS = {"scroll_up", "scroll_down"}
LABELS = {
    "RSTICK_UP": "右摇杆 ↑", "RSTICK_DOWN": "右摇杆 ↓",
    "RSTICK_LEFT": "右摇杆 ←", "RSTICK_RIGHT": "右摇杆 →",
    "LSTICK_UP": "左摇杆 ↑", "LSTICK_DOWN": "左摇杆 ↓",
    "LSTICK_LEFT": "左摇杆 ←", "LSTICK_RIGHT": "左摇杆 →",
    "DPAD_UP": "十字键 ↑", "DPAD_RIGHT": "十字键 →",
    "DPAD_DOWN": "十字键 ↓", "DPAD_LEFT": "十字键 ←",
    "LT": "LT · 左扳机", "LB": "LB · 左肩键", "L3": "左摇杆按下",
    "RT": "RT · 右扳机", "RB": "RB · 右肩键", "R3": "右摇杆按下",
    "A": "A", "B": "B", "X": "X", "Y": "Y",
    "VIEW": "View · 双窗口键", "MENU": "Menu · 菜单键",
}
DPAD = {"DPAD_UP", "DPAD_RIGHT", "DPAD_DOWN", "DPAD_LEFT"}
MODIFIERS = {"LB", "RB", "LT", "RT"}
STICK_GUARD = "LSTICK_ACTIVE"
STICK_GUARDS = {STICK_GUARD, "RSTICK_ACTIVE"}
LEGACY_BINDINGS = {"easy": "DPAD_UP", "good": "DPAD_RIGHT", "hard": "DPAD_DOWN",
                   "again": "DPAD_LEFT", "show": "LT", "replay": "LB",
                   "undo": "LB+DPAD_LEFT", "pause": "L3"}
BINDINGS = [""] + list(LABELS)
for modifier in ("LB", "LT", "RB", "RT"):
    BINDINGS += [f"{modifier}+{key}" for key in LABELS
                 if key != modifier]


def binding_label(value: str, language: str = "zh_CN") -> str:
    if not value:
        return translate("未绑定", language)
    return " + ".join(translate(LABELS.get(part, part), language) for part in value.split("+"))


def rating_keys(order: str) -> dict[str, str]:
    return dict(zip(("easy", "good", "hard", "again"),
                    ("1", "2", "3", "4") if order == "reverse"
                    else ("4", "3", "2", "1")))


def default_config() -> dict:
    return {"schema": 2, "bindings": {key: value[2] for key, value in ACTIONS.items()},
            "language": "auto", "order": "standard", "vibration": True, "strength": 35,
            "anki_feedback": True, "foreground_only": True, "controller": -1, "minimize_to_tray": True}


def config_dir() -> Path:
    return Path(os.environ.get("LOCALAPPDATA", str(Path.home()))) / "anki-grip"


def load_config(path: Path | None = None) -> dict:
    # Explicit paths load independently; normal startup uses the user's saved
    # defaults as the baseline if settings are missing or incomplete.
    config = load_defaults() if path is None else default_config()
    path = path or config_dir() / "settings.json"
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(data, dict):
            return config
        for key in ("vibration", "anki_feedback", "foreground_only", "minimize_to_tray"):
            if type(data.get(key)) is bool:
                config[key] = data[key]
        if data.get("language") in LANGUAGES:
            config["language"] = data["language"]
        if data.get("order") in ("reverse", "standard"):
            config["order"] = data["order"]
        if type(data.get("strength")) is int:
            config["strength"] = max(0, min(100, data["strength"]))
        if type(data.get("controller")) is int and data["controller"] in (-1, 0, 1, 2, 3):
            config["controller"] = data["controller"]
        stored = data.get("bindings", {})
        if isinstance(stored, dict) and not (data.get("schema", 1) == 1 and stored == LEGACY_BINDINGS):
            candidate = {key: stored.get(key, config["bindings"][key]) for key in ACTIONS}
            for key in SCROLL_ACTIONS:
                if key not in stored and candidate[key] in stored.values():
                    candidate[key] = ""
            if all(value in BINDINGS for value in candidate.values()):
                validate_bindings(candidate)
                config["bindings"] = candidate
    except (OSError, ValueError, TypeError):
        pass
    return config


def load_defaults(path: Path | None = None) -> dict:
    return load_config(path or config_dir() / "defaults.json")


def save_defaults(config: dict, path: Path | None = None) -> None:
    validate_bindings(config["bindings"])
    save_config(config, path or config_dir() / "defaults.json")


class StickDirections:
    """Four directional gestures: centered dead zone, settling, one per return.

    XInput positive Y points up. A gesture starts at 18000, settles for 45 ms,
    and requires both axes within 9000 before another direction can fire.
    The unbindable guard keeps startup/remapping disarmed while a stick is held.
    Diagonal gestures lock out until centered, including if straightened later.
    """
    ENTER = 18000
    CENTER = 9000
    DOMINANCE = 1.35
    SETTLE_SECONDS = .045

    def __init__(self, prefix="LSTICK"):
        self.prefix = prefix
        self.armed = False
        self.active = ""
        self.candidate = ""
        self.since = 0.0
        self.blocked = False

    def step(self, x: int, y: int, now: float | None = None) -> set[str]:
        now = time.monotonic() if now is None else now
        ax, ay = abs(x), abs(y)
        if max(ax, ay) <= self.CENTER:
            self.armed = True
            self.active = self.candidate = ""
            self.blocked = False
            return set()
        down = {self.prefix + "_ACTIVE"}
        if not self.armed or self.blocked:
            return down
        if self.active:
            return down | {self.active}
        if max(ax, ay) < self.ENTER:
            self.candidate = ""
            return down
        if ax > ay * self.DOMINANCE:
            direction = self.prefix + ("_RIGHT" if x > 0 else "_LEFT")
        elif ay > ax * self.DOMINANCE:
            direction = self.prefix + ("_UP" if y > 0 else "_DOWN")
        else:
            self.blocked = True
            self.candidate = ""
            return down
        if direction != self.candidate:
            self.candidate = direction
            self.since = now
        elif now - self.since >= self.SETTLE_SECONDS:
            self.active = direction
            down.add(direction)
        return down

    def aligned(self, x: int, y: int) -> bool:
        """A held scroll must still point strongly in its original direction."""
        direction = self.active.rsplit("_", 1)[-1]
        ax, ay = abs(x), abs(y)
        return ((direction == "UP" and y >= self.ENTER and ay > ax * self.DOMINANCE)
                or (direction == "DOWN" and y <= -self.ENTER and ay > ax * self.DOMINANCE)
                or (direction == "RIGHT" and x >= self.ENTER and ax > ay * self.DOMINANCE)
                or (direction == "LEFT" and x <= -self.ENTER and ax > ay * self.DOMINANCE))


def save_config(config: dict, path: Path | None = None) -> None:
    path = path or config_dir() / "settings.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_suffix(".tmp")
    temp.write_text(json.dumps(config, ensure_ascii=False, indent=2), encoding="utf-8")
    temp.replace(path)


def validate_bindings(bindings: dict[str, str], language: str = "zh_CN") -> None:
    assigned: dict[str, str] = {}
    for action, binding in bindings.items():
        if binding not in BINDINGS:
            raise ValueError(translate("存在不支持的按键。", language))
        if binding and binding in assigned:
            raise ValueError(translate("{binding} 同时分配给了“{first}”和“{second}”。", language,
                                       binding=binding_label(binding, language),
                                       first=translate(ACTIONS[assigned[binding]][0], language),
                                       second=translate(ACTIONS[action][0], language)))
        assigned[binding] = action


class InputMapper:
    """Emit at most one action per press; chord modifiers emit on release.

    A newly attached controller must first release all controls. A diagonal
    D-pad press locks out the entire directional gesture until all directions
    release. Chords require modifier-first order and consume both singles.
    """
    def __init__(self, bindings: dict[str, str]):
        self.bindings = dict(bindings)
        self.reset()

    def reset(self) -> None:
        self.previous: set[str] = set()
        self.ready = False
        self.pending: set[str] = set()
        self.consumed: set[str] = set()
        self.diagonal = False
        self.repeating = ""
        self.repeat_at = 0.0

    def step(self, down: set[str], now: float | None = None, repeat_allowed=True) -> list[str]:
        now = time.monotonic() if now is None else now
        down = set(down)
        if not self.ready:
            if not down:
                self.ready = True
            self.previous = down
            return []
        directions = down & DPAD
        if len(directions) > 1:
            self.diagonal = True
        blocked_dpad = self.diagonal
        if not directions:
            self.diagonal = False
        rising = down - self.previous
        released = self.previous - down
        events: list[str] = []
        modifiers = {b.split("+")[0] for b in self.bindings.values() if "+" in b}
        singles = {b: a for a, b in self.bindings.items() if b and "+" not in b}
        for modifier in released & modifiers:
            if modifier in self.pending and modifier not in self.consumed:
                if action := singles.get(modifier):
                    events.append(action)
            self.pending.discard(modifier)
            self.consumed.discard(modifier)
        for key in sorted(rising):
            if key in DPAD and blocked_dpad:
                continue
            if any("+" in b and b.split("+")[1] == key
                   and b.split("+")[0] in rising for b in self.bindings.values()):
                # Simultaneous modifier+direction is ambiguous: never score it.
                self.consumed.update(b.split("+")[0] for b in self.bindings.values()
                                     if "+" in b and b.split("+")[1] == key
                                     and b.split("+")[0] in rising)
                continue
            chords = [(a, b.split("+")) for a, b in self.bindings.items()
                      if "+" in b and b.split("+")[1] == key
                      and b.split("+")[0] in down
                      and b.split("+")[0] not in rising]
            if len(chords) > 1:
                # Multiple held modifiers make the intended chord ambiguous.
                self.consumed.update(parts[0] for _, parts in chords)
            elif chords:
                action, parts = chords[0]
                self.consumed.add(parts[0])
                events.append(action)
            elif key in modifiers:
                self.pending.add(key)
            elif action := singles.get(key):
                events.append(action)
        # Only scroll actions repeat. Ratings/show/space remain edge-triggered.
        controls = down - STICK_GUARDS
        scroll = next((a for a in events if a in SCROLL_ACTIONS), "")
        if scroll:
            self.repeating = scroll
            self.repeat_at = now + .45
        elif self.repeating:
            binding = set(self.bindings[self.repeating].split("+"))
            if controls != binding or blocked_dpad or not repeat_allowed:
                self.repeating = ""
            elif now >= self.repeat_at:
                events.append(self.repeating)
                self.repeat_at = now + .22
        if not repeat_allowed or any(a not in SCROLL_ACTIONS for a in events):
            self.repeating = ""
        self.previous = down
        return events
