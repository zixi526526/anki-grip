# Changelog

## 1.5.0rc1 — unreleased / 未发布

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
- Existing bindings and preferences remain compatible. Windows packaging and live
  controller validation for this candidate are pending.

中文：增加中英文/跟随系统切换，完整手柄实时图与暂停操作的测试页，开放 View/Menu
及肩键/扳机之间的组合键，补充双语发布文档和 CI。旧配置保留；本候选版尚待 Windows
打包和真实手柄验收。

## 1.4.0 — 2026-10-02

- Right-stick directions and Scroll Up/Down, with hold-repeat cancellation guards.
- Private Windows deployment accepted with 63 passing automated tests.

## 1.3.0 and earlier

- Personal defaults, Space: Show / Good, four-direction left-stick mapping,
  safe semantic ratings, audio replay, Undo, vibration and tray support.
