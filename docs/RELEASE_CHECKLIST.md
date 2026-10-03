# Release checklist / 发布清单

Source candidate: **1.5.0rc1**. Source availability and binary releases are tracked
separately. This checklist does not itself authorize a version bump or release.

## Completed preparation

- [x] English and Simplified Chinese UI, system-language fallback and translated bridge results.
- [x] All 24 standard XInput inputs and ordered bumper/trigger-first chords.
- [x] Original full-controller drawing, analog positions, trigger travel and enlarged input test.
- [x] Optional in-Anki action feedback with completion guards and focus/mouse transparency.
- [x] Linux and Windows application tests, bilingual offline GUI checks and a local Windows build.
- [x] Local live controller/Anki acceptance reported by the owner.
- [x] File selection and public documentation reviewed for a new independent source history.
- [x] README, install/update/uninstall guidance, contribution instructions and MIT source license.
- [x] CI test matrix and an explicitly triggered Windows candidate-artifact workflow.

## Before a public binary

- [ ] Run the package on a clean Windows 11 x64 machine without Python; verify tray,
  restart, installation, upgrade and uninstall at 100%, 125%, 150% and 200% scaling.
- [ ] Record exact controller/transport/Anki-version coverage. Physically test all
  inputs, motors, reconnection and held inputs for USB/Bluetooth and any supported adapter.
- [ ] In a throwaway Anki profile, test all ratings, Space, Show, replay, Undo,
  scrolling, stale state, focus loss, modal dialogs and timeouts; compare recorded
  ratings with semantic actions.
- [ ] Verify feedback in both languages, disappearance, disabled behavior,
  focus/mouse handling, failed-command suppression and coexistence with Anki alerts.
- [ ] Verify entering/leaving Controller Test with controls held requires release
  before actions resume. Check preserved custom settings and incompatible bridges.
- [ ] Review the actual dependency/license bundle and applicable Qt/PySide obligations.
- [ ] Agree on the release version, build the exported source, verify metadata and
  checksums, and publish the complete ZIP with release notes.

## Design references

No emulator source, artwork or controller graphics were copied.

- [Dolphin controller configuration](https://dolphin-emu.org/docs/guides/configuring-controllers/)
- [Dolphin MappingIndicator](https://github.com/dolphin-emu/dolphin/blob/master/Source/Core/DolphinQt/Config/Mapping/MappingIndicator.cpp)
- [PCSX2 controller documentation](https://github.com/PCSX2/pcsx2-net-www/blob/main/docs/configuration/controllers.md)
- [RetroArch input and controls](https://docs.libretro.com/guides/input-and-controls/)
- [Microsoft XINPUT_GAMEPAD](https://learn.microsoft.com/en-us/windows/win32/api/xinput/ns-xinput-xinput_gamepad)
- [Qt/PySide licenses](https://doc.qt.io/qtforpython-6/licenses.html)
- [Qt LGPL obligations](https://www.qt.io/development/open-source-lgpl-obligations)
