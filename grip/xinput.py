"""Windows XInput, including battery status and deterministic rumble cleanup."""
from __future__ import annotations

import ctypes
import time
from dataclasses import dataclass
from .model import StickDirections

WORD = ctypes.c_uint16
BYTE = ctypes.c_uint8
DWORD = ctypes.c_uint32


class Gamepad(ctypes.Structure):
    _fields_ = [("buttons", WORD), ("lt", BYTE), ("rt", BYTE),
                ("lx", ctypes.c_int16), ("ly", ctypes.c_int16),
                ("rx", ctypes.c_int16), ("ry", ctypes.c_int16)]


class State(ctypes.Structure):
    _fields_ = [("packet", DWORD), ("gamepad", Gamepad)]


class Vibration(ctypes.Structure):
    _fields_ = [("left", WORD), ("right", WORD)]


class Battery(ctypes.Structure):
    _fields_ = [("type", BYTE), ("level", BYTE)]


BUTTONS = {0x0001: "DPAD_UP", 0x0002: "DPAD_DOWN", 0x0004: "DPAD_LEFT",
           0x0008: "DPAD_RIGHT", 0x0010: "MENU", 0x0020: "VIEW",
           0x0040: "L3", 0x0080: "R3", 0x0100: "LB", 0x0200: "RB",
           0x1000: "A", 0x2000: "B", 0x4000: "X", 0x8000: "Y"}
PATTERNS = {
    "easy": [(70, .20, .60)], "good": [(85, .30, .42)],
    "hard": [(65, .42, .35), (70, 0, 0), (65, .42, .35)],
    "again": [(185, .70, .25)], "show": [(40, .12, .35)],
    "replay": [(35, .10, .28)], "undo": [(60, .40, .40), (65, 0, 0), (60, .40, .40)],
    "pause": [(50, .20, .30), (75, 0, 0), (50, .20, .30)],
    "complete": [(90, .30, .50), (100, 0, 0), (150, .45, .60)],
    "test": [(140, .55, .35), (130, 0, 0), (140, .20, .65)],
}


@dataclass
class Snapshot:
    index: int
    down: set[str]
    lt: int
    rt: int
    battery: str
    lx: int = 0
    ly: int = 0
    rx: int = 0
    ry: int = 0
    scroll_allowed: bool = True


class XInput:
    def __init__(self):
        self.dll = None
        for name in ("xinput1_4.dll", "xinput1_3.dll", "xinput9_1_0.dll"):
            try:
                self.dll = ctypes.WinDLL(name)
                break
            except (OSError, AttributeError):
                continue
        if self.dll is None:
            raise OSError("Windows XInput 不可用。")
        self.dll.XInputGetState.argtypes = [DWORD, ctypes.POINTER(State)]
        self.dll.XInputGetState.restype = DWORD
        self.dll.XInputSetState.argtypes = [DWORD, ctypes.POINTER(Vibration)]
        self.dll.XInputSetState.restype = DWORD
        self.trigger_down: dict[tuple[int, str], bool] = {}
        self.sticks: dict[int, StickDirections] = {}
        self.right_sticks: dict[int, StickDirections] = {}
        self.battery_cache: dict[int, tuple[float, str]] = {}
        self.rumble_steps: list[tuple[float, float, float]] = []
        self.rumble_index: int | None = None
        self.last_vibration_result: int | None = None

    def connected(self) -> list[int]:
        return [i for i in range(4) if self.dll.XInputGetState(i, ctypes.byref(State())) == 0]

    def read(self, preferred: int = -1) -> Snapshot | None:
        for index in ([preferred] if preferred >= 0 else range(4)):
            state = State()
            if self.dll.XInputGetState(index, ctypes.byref(state)):
                for key in ("LT", "RT"):
                    self.trigger_down.pop((index, key), None)
                self.sticks.pop(index, None)
                self.right_sticks.pop(index, None)
                continue
            pad = state.gamepad
            down = {label for mask, label in BUTTONS.items() if pad.buttons & mask}
            stick = self.sticks.setdefault(index, StickDirections())
            down.update(stick.step(pad.lx, pad.ly))
            right = self.right_sticks.setdefault(index, StickDirections("RSTICK"))
            down.update(right.step(pad.rx, pad.ry))
            for key, value in (("LT", pad.lt), ("RT", pad.rt)):
                active = self.trigger_down.get((index, key), False)
                active = value > (95 if active else 160)
                self.trigger_down[(index, key)] = active
                if active:
                    down.add(key)
            return Snapshot(index, down, pad.lt, pad.rt, self.battery(index), pad.lx, pad.ly, pad.rx, pad.ry,
                            (not stick.active or stick.aligned(pad.lx, pad.ly))
                            and (not right.active or right.aligned(pad.rx, pad.ry)))
        return None

    def battery(self, index: int) -> str:
        cached = self.battery_cache.get(index)
        if cached and time.monotonic() - cached[0] < 15:
            return cached[1]
        value = Battery()
        label = "电量未知"
        if hasattr(self.dll, "XInputGetBatteryInformation"):
            if self.dll.XInputGetBatteryInformation(index, 0, ctypes.byref(value)) == 0:
                if value.type == 1:
                    label = "有线连接"
                elif value.type in (2, 3):
                    label = ["电量耗尽", "电量低", "电量中等", "电量充足"][min(value.level, 3)]
        self.battery_cache[index] = (time.monotonic(), label)
        return label

    def set_motors(self, index: int, left: float, right: float) -> int:
        value = Vibration(int(max(0, min(1, left)) * 65535),
                          int(max(0, min(1, right)) * 65535))
        self.last_vibration_result = int(self.dll.XInputSetState(index, ctypes.byref(value)))
        return self.last_vibration_result

    def play(self, index: int, pattern: str, strength: int) -> None:
        self.stop()
        factor = max(0, min(100, strength)) / 100
        self.rumble_index = index
        now = time.monotonic()
        for duration, left, right in PATTERNS.get(pattern, PATTERNS["good"]):
            self.rumble_steps.append((now, left * factor, right * factor))
            now += duration / 1000
        self.rumble_steps.append((now, 0, 0))
        self.tick()

    def tick(self) -> None:
        if self.rumble_index is None:
            return
        now = time.monotonic()
        latest = None
        while self.rumble_steps and self.rumble_steps[0][0] <= now:
            latest = self.rumble_steps.pop(0)
        if latest:
            self.set_motors(self.rumble_index, latest[1], latest[2])
        if not self.rumble_steps:
            self.rumble_index = None

    def stop(self) -> None:
        if self.rumble_index is not None:
            self.set_motors(self.rumble_index, 0, 0)
        self.rumble_index = None
        self.rumble_steps.clear()

    def shutdown(self) -> None:
        self.stop()
