# Contributing

Please include the app version, Windows version, Anki version, controller model,
connection type and steps to reproduce a bug. Remove card contents, personal paths,
settings files and credentials from screenshots and attachments. Reports should be
readable in English or Simplified Chinese.

Use an isolated Python environment outside the checkout, install
`requirements.txt`, and run `python -m unittest discover -s tests` before a patch.
On Linux, set `QT_QPA_PLATFORM=offscreen` and `PYTHONDONTWRITEBYTECODE=1` for offline
tests. GUI preview: `python main.py --screenshot <path> --language en`.

Test Anki behavior with fake objects or a throwaway profile only. Never use someone
else's collection for automated scoring, Undo or replay tests. Keep semantic ratings,
revision/session checks, no-retry grading, foreground guards, reconnect release guards
and chord/diagonal suppression intact. Scrolling is the only repeating action.

UI strings belong in `grip/i18n.py`. Settings store stable action/control/language
IDs, not translated names. Language switching must preserve unsaved edits. Draw
controller artwork from project-owned primitives; do not import emulator assets
without an explicit license review.

Windows/XInput tests and packaging remain necessary before shipping even if Linux
offline checks pass. Keep profiles, screenshots, generated files and EXEs out of Git.

中文：问题反馈请提供版本、手柄型号/连接方式与复现步骤，删除卡片内容、个人路径和凭证。
提交前在隔离环境运行测试；真实评分仅在专门的测试账户中验收。翻译放进统一语言表，
不得用翻译后的名称作为配置标识。Linux 离线测试不能替代 Windows 打包和手柄实机验收。
