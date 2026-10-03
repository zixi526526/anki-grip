# anki-grip

[简体中文](README.zh-CN.md) · English

A Windows desktop companion for reviewing Anki with an Xbox controller. Remap
buttons and both sticks, scroll long cards, and feel vibration after Anki confirms
an action. The interface supports English and Simplified Chinese.

**Source candidate: 1.5.0rc1.** Linux/Windows automated tests, bilingual offline GUI
checks and a local Windows package have passed. The owner accepted normal live
controller/Anki use on Windows. See [validation](VALIDATION.md) and the
[release checklist](docs/RELEASE_CHECKLIST.md) for coverage limits. No prebuilt
public binary is available yet; build from source using the instructions below.

## Get started

1. Extract a verified Windows release ZIP to a folder you can write to. Keep its
   license files and run `anki-grip.exe`. Python is not required for a packaged release.
2. Connect an XInput-compatible controller using USB, Bluetooth or an Xbox
   wireless adapter.
3. Open **Setup → Install / Update Anki Add-on**. This installs only
   `anki_grip_bridge` in `%APPDATA%\Anki2\addons21`. Restart Anki afterwards.
4. Open a deck and start reviewing. By default, Anki must be the foreground window.

For portable Anki or a custom data directory, use **Choose Custom Anki Add-ons
Folder** and select its `addons21` folder. Install a new executable in a separate
folder after exiting the old instance from its tray menu. Keep the previous
verified release until the new one works. Personal settings remain in AppData.

## Customize your controller

Use **Mappings** to assign any action to any supported input, or select
**Capture** and press the control on your controller. All 24 logical inputs are
available: A/B/X/Y, the four D-pad directions, LB/RB, LT/RT, View/Back, Menu/Start,
L3/R3, and the four directions of each stick.

Chords can use LB, RB, LT or RT as the first control, followed by any other
supported control, including View/Menu or another bumper/trigger. Hold the
modifier first, then press the second control. Simultaneous or ambiguous chords
are ignored. A modifier with both a single action and a chord performs the
single action on release unless the chord consumed it.

Each action has one binding. Capturing an already assigned binding transfers it
from its previous action. Selecting duplicate bindings manually produces a
conflict message when saving. Editing or capturing pauses Anki actions until you
**Save & Apply** and release the controls.

| Default input | Action |
| --- | --- |
| Left stick left | Easy |
| Left stick right | Hard |
| Left stick up | Again |
| Left stick down | Show Answer |
| Right stick up / down | Scroll Up / Down |
| LT | Replay Audio |
| LB | Undo Rating |
| Unbound | Good, Space: Show / Good, Pause / Resume |

Ratings are semantic: Easy always means Easy, independently of shortcut labels.
Choose **standard** (1 Again → 4 Easy) or **reversed** (1 Easy → 4 Again) labels to
match Anki. This app's initial label setting is reversed; it does not change your
Anki keyboard shortcuts. **Show Answer** never grades an already revealed card.
**Space: Show / Good** reveals the question or grades the answer Good.

Only scrolling repeats while held: 160 pixels immediately, then after 450 ms,
every 220 ms. Centering, pausing, losing alignment or changing the card/window
stops repeat. Pages without overflow may not visibly move. Ratings and flips are
single actions; sticks must return to center between gestures. Drift and diagonal
gestures are ignored. Held inputs at startup/reconnect must first be released.

## Language, live input and feedback

- **Settings → Language** switches immediately between English, 简体中文 and the
  system language. Other unsaved edits survive switching. **Save & Apply** persists
  the choice. Other system languages fall back to English.
- The sidebar shows the full controller. **Controller Test** enlarges it and
  pauses Anki actions while testing. Button highlights, analog stick positions,
  trigger travel and raw axis values update live. Stick direction highlights
  show accepted gestures; raw dots still move during drift or rejected diagonals.
- Test-page solid squares mark the direction threshold; dashed squares mark the
  center zone. Standard XInput does not expose Xbox/Guide, Share or independent
  rear paddles. Paddles mapped by controller firmware to standard buttons appear
  as those buttons.
- **Save as Defaults** saves the entire profile, including language and feedback
  preferences. **Restore Defaults** loads it for review before applying.
- **Show action feedback in Anki** is on by default. Successful actions appear
  briefly near the bottom-right of Anki: Easy, Good, Hard, Again, Show Answer,
  Replay Audio, Undo Rating and Scroll Up/Down. The one-second indicator follows
  the interface language and captures neither focus nor mouse clicks. Ratings and
  Undo wait for completion; rejected or timed-out actions have no success indicator.
  Scroll feedback is limited to once a second and confirms request submission;
  pages without overflow may not move. Only anki-grip actions are shown. Disable
  this option in Settings if desired. Update the bridge and restart Anki to use it;
  older bridges safely ignore the new feedback settings.
- Vibration follows Anki's confirmation. Test its strength in Settings. Scrolling
  does not vibrate. The mouse wheel scrolls lists without changing controls.
- Closing the window normally minimizes to the tray. Double-click to reopen;
  right-click to pause or quit.

## Compatibility and privacy

The supported runtime is **Windows desktop Anki with XInput-compatible
controllers**. Other controllers require an XInput mode or adapter. macOS,
Linux runtime, AnkiMobile and AnkiDroid are not currently supported. The owner accepted normal 1.5.0rc1 use on Windows. The previous 1.4.0 release
was tested with Windows 11, an Xbox One wireless controller and Anki 26.09.2.
These observations do not establish compatibility with every controller,
transport or Anki version.

The add-on uses Anki reviewer internals. Recheck compatibility after Anki updates.
It listens only on `127.0.0.1:18765` and requires no AnkiConnect. The application
has no analytics, automatic update downloads or cloud account, and does not log
card contents or controller input. Review actions and Undo use Anki's normal
review workflow. Stale commands are rejected; grading requests are never retried
after a timeout. If confirmation is missing, check Anki before pressing again.

Steam desktop mappings or other remappers can also send keyboard input from the
same controller. If controls fire twice, check those mappings. If Anki remains
disconnected, restart it after installing the add-on, confirm the data directory,
and check that a duplicate Anki instance is not occupying the bridge port.

## Settings and removal

Settings: `%LOCALAPPDATA%\anki-grip\settings.json`. Personal defaults:
`defaults.json` in the same folder. Add-on upgrades back up changed installations
in `addon-backups` there. Upgrading from 1.4.0 preserves existing bindings and
preferences and adds system-language selection. Changed add-on files require an
add-on update and an Anki restart.

To uninstall, quit from the tray, remove **anki-grip bridge** in Anki's add-on
manager and restart Anki, then remove the extracted app folder and shortcuts.
Retain or delete settings as you prefer. Other add-ons and card templates are not
modified by installation.

## Develop and build

Python + PySide6; native Windows XInput for input and vibration. Keep virtual
environments and build intermediates outside the repository.

```powershell
python -m venv "$env:LOCALAPPDATA\anki-grip-dev"
& "$env:LOCALAPPDATA\anki-grip-dev\Scripts\python.exe" -m pip install -r requirements.txt
& "$env:LOCALAPPDATA\anki-grip-dev\Scripts\python.exe" -m unittest discover -s tests
& "$env:LOCALAPPDATA\anki-grip-dev\Scripts\python.exe" main.py
./build.ps1
```

`build.ps1` uses an isolated environment, runs tests, and writes the executable,
documentation and license bundle to local-only `release/`. `-BuildRoot`,
`-VenvPath` and `-OutputPath` override destinations. The development output also
includes a SHA-256 manifest and runtime version metadata. Do not distribute the
EXE separately from its license bundle.

Linux can run synthetic tests and offline previews, not live XInput:

```sh
QT_QPA_PLATFORM=offscreen PYTHONDONTWRITEBYTECODE=1 python -m unittest discover -s tests
QT_QPA_PLATFORM=offscreen python main.py --language en --screenshot /tmp/anki-grip.png --screenshot-tab 3 --demo-controller
```

`--demo-controller` only works with offline `--screenshot`. Automatic tests use
fake Anki objects and temporary settings; they never score the user's collection.
The CI workflow runs tests on Linux and Windows; the manual Windows build
workflow creates an artifact for review, without publishing a release.

## License and contributions

Project source: [MIT](LICENSE). Bundled dependencies have their own licenses;
see [third-party notices](THIRD_PARTY_NOTICES.md). The controller diagram is
original vector drawing code. Anki and Xbox names identify compatibility; this
project is not affiliated with their respective owners. Bug reports and patches
are welcome; see [contributing](CONTRIBUTING.md). Please remove personal paths,
card contents and credentials from reports.
