# Changelog

## 1.5.0 — 2026-10-03

- English and Simplified Chinese interface with a system-language option. Live
  switching preserves unsaved settings; language is included in personal defaults.
- Full Xbox-style controller diagram and a larger Controller Test page. Raw stick
  positions, trigger travel and button highlights update while Anki actions are paused.
  A revised Xbox-like silhouette uses deeper proportions, tapered grips and integrated
  controls; small windows can scroll the sidebar without obscuring the diagram.
- Optional one-second action feedback inside Anki, following the selected language.
  Ratings and Undo display only after completion. The indicator captures no input;
  scroll indicators are rate limited and rejected/timed-out commands stay silent.
- Bumper/trigger-first chords now include View/Menu and other bumpers/triggers.
  Ambiguous multi-modifier chords do not choose an action.
- Public-facing bilingual documentation, release checklist, test CI and a manual
  Windows build-artifact workflow. Runtime versions and checksums accompany builds.
- New installations use standard rating shortcut labels. Saved preferences,
  including reversed labels, remain unchanged.
- First public Windows x64 release with bilingual documentation and a complete
  dependency/license bundle. Local candidate controller/Anki use was accepted.

中文：增加中英文/跟随系统切换，完整手柄实时图与暂停操作的测试页，开放 View/Menu
及肩键/扳机之间的组合键，发布首个 Windows x64 安装包。新配置使用常规评分标签；已有
配置和个人偏好保留。README 以功能、支持输入及下载/使用为主。

## 1.4.0 — 2026-10-02

- Right-stick directions and Scroll Up/Down, with hold-repeat cancellation guards.
- Private Windows deployment accepted with 63 passing automated tests.

## 1.3.0 and earlier

- Personal defaults, Space: Show / Good, four-direction left-stick mapping,
  safe semantic ratings, audio replay, Undo, vibration and tray support.
