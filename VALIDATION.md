# Validation — 1.5.0rc1

## Observed checks

- 92 automated application tests passed on Linux with Python 3.14.7 and PySide6
  6.11.2, and Windows 11 with Python 3.14.4 and PySide6 6.11.2. Tests use isolated
  settings and synthetic input/fake Anki objects; they do not grade a user collection.
- Coverage includes all 24 standard XInput logical controls, ordered chords and
  ambiguity rejection, input edge/center/reconnect guards, scrolling, language
  persistence, preserved unsaved edits, controller rendering, disconnect reset,
  test-page action suppression and package checksums.
- Bridge feedback tests cover completed semantic ratings, asynchronous Undo,
  Show/replay, rejected and expired commands, late/duplicate completion, foreground
  and disabled guards, scroll rate limiting, focus and mouse transparency, bounded
  placement, and timer hiding.
- Windows packaging passed with PyInstaller 6.22.3. English and Simplified Chinese
  Settings and Controller Test previews rendered and exited successfully. License
  files, runtime metadata and the SHA-256 manifest were checked.
- The project owner accepted normal live controller/Anki use on Windows on
  2026-10-03. Existing personal settings were preserved. This is a local acceptance
  result, not coverage of every controller, transport, scaling or Anki version.

## Publication scope and remaining coverage

This repository contains reviewed source with an independent history. It provides
no prebuilt public binary release yet. Build from source using the README.

Clean-machine operation without Python, all display scaling levels, transport and
controller combinations, additional Anki versions, and full isolated-profile
failure scenarios remain on the [release checklist](docs/RELEASE_CHECKLIST.md).
Do not treat a successful synthetic test suite as hardware compatibility proof.
