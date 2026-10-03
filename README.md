# anki-grip

[简体中文](README.zh-CN.md) · English

Review Anki cards with an Xbox controller. anki-grip connects an XInput controller to desktop Anki on Windows. You can customize the controls, watch controller input live, and turn on optional feedback and vibration. The interface is available in English and Simplified Chinese.

**[Download anki-grip for Windows x64](https://github.com/zixi526526/anki-grip/releases/latest)**

Version 1.5.0 is the first public binary release. It comes as a complete Windows x64 ZIP that includes licenses, runtime metadata and SHA-256 checksums.

## Get started

1. Download the Windows x64 ZIP from Releases and extract the whole folder. Keep the license files next to `anki-grip.exe`, then run it. You don't need Python.
2. Connect an XInput-compatible controller and open desktop Anki.
3. In Setup, install or update the Anki add-on, then restart Anki.
4. Start reviewing a deck. By default, controller actions only work while Anki is the foreground window.

If you use portable Anki or a custom data directory, you can choose its `addons21` folder in Setup. Closing the window usually minimizes anki-grip to the tray. To exit, use the tray menu.

To upgrade, quit the old version from the tray and extract the new release into a separate folder. Your existing settings stay in AppData.

## Supported Anki actions

- Show the answer.
- Rate a card Again, Hard, Good or Easy.
- Space (Show / Good).
- Replay audio.
- Undo the last rating.
- Scroll long cards up or down.
- Pause and resume controller actions.

If you want, anki-grip can show brief feedback inside Anki and vibrate the controller after an action is confirmed.

Only scrolling repeats while held. It stops when you release the control or let the stick return to center. Ratings and answer flips trigger once per gesture.

## Supported controller inputs

You can customize all 24 standard XInput inputs:

- A/B/X/Y
- the four D-pad directions
- LB/RB and LT/RT
- View/Back and Menu/Start
- L3/R3
- four directions on each stick

You can also combine a bumper or trigger with another supported input.

The live controller view shows button presses, stick positions and how far each trigger is pulled. Controller Test opens a larger view and pauses Anki actions while it is open. Standard XInput doesn't report the Xbox/Guide button, the Share button or separate rear paddles.

## Compatibility and privacy

anki-grip supports desktop Anki on Windows with XInput-compatible controllers. It doesn't run on macOS or Linux, and it doesn't work with AnkiMobile or AnkiDroid. See [validation](VALIDATION.md) for the environments that have been tested and the limits of that testing.

The add-on only listens on `127.0.0.1:18765`. It doesn't need AnkiConnect. There is no telemetry and no cloud account, and card contents are never logged. After you update Anki, check that the add-on still works. If another controller-to-keyboard tool is running, the same press can trigger an action twice. If that happens, check that tool's desktop mappings.

Settings are saved in `%LOCALAPPDATA%\anki-grip`. To uninstall:

1. Quit anki-grip.
2. Remove the anki-grip bridge add-on in Anki and restart Anki.
3. Delete the extracted folder.

You can keep or delete your settings folder.

## Build from source

You need Python and PySide6 to build anki-grip. Keep your virtual environments outside the repository. On Windows, this script installs pinned dependencies, runs the tests and puts a complete release bundle in `release/`:

```powershell
./build.ps1
```

On Linux you can only run the synthetic tests and offline previews. See the [release checklist](docs/RELEASE_CHECKLIST.md) for more on release validation.

## License and contributions

The project source is [MIT licensed](LICENSE). Qt/PySide and the other dependencies have their own licenses. See [third-party notices](THIRD_PARTY_NOTICES.md), and keep the full license bundle with the executable.

The controller illustration is drawn by original vector code. The Anki and Xbox names are used only to show compatibility, and this project is not affiliated with their owners.

To report a problem or send a patch, see [contributing](CONTRIBUTING.md). Leave out personal data and credentials.
