# anki-grip

简体中文 · [English](README.md)

Windows 桌面版 Anki 的 Xbox 手柄伴侣。支持完整按键重映射、双摇杆四方向、
卡片滚动、操作确认后的震动反馈、实时手柄状态、系统托盘和中英文界面。

**当前公开源码候选版为 1.5.0rc1。** Linux/Windows 自动测试、双语离线 GUI 和本地 Windows 打包已通过，
项目维护者确认正常手柄与 Anki 使用实测通过。具体覆盖范围见 [验证记录](VALIDATION.md)
与 [发布清单](docs/RELEASE_CHECKLIST.md)。目前没有预编译公开安装包，可按下方说明从源码构建。

## 开始使用

1. 将经验证的 Windows 发布 ZIP 解压到可写目录，保留许可证文件，运行
   `anki-grip.exe`。打包版不需要安装 Python。
2. 通过 USB、蓝牙或 Xbox 无线适配器连接支持 XInput 的手柄。
3. 在“连接指南”中点击“安装 / 更新 Anki 连接插件”。只会安装
   `%APPDATA%\Anki2\addons21\anki_grip_bridge`，安装后重启 Anki。
4. 打开牌组开始复习。默认仅在 Anki 复习窗口位于前台时生效。

便携版或自定义数据目录请选择对应的 `addons21` 文件夹。升级前从托盘退出旧实例，
新版解压到独立目录；验收前保留旧版。个人设置继续使用 AppData 中的文件。

## 自定义完整手柄

在“按键映射”下拉框中选择输入，或点击“录入”，在手柄上按下并松开目标输入。
共支持 24 个逻辑输入：A/B/X/Y、十字键四方向、LB/RB、LT/RT、View/Back、
Menu/Start、L3/R3，以及左右摇杆各四方向。右手负责的输入同样可自由分配。

LB、RB、LT、RT 可以作为组合键的第一键，搭配任意其它支持的输入，包括
View/Menu 和其它肩键/扳机。先按住第一键，再按第二键；同时按下或多个组合键
意图不明确时忽略。同一修饰键如果还绑定单键功能，该功能会延迟到松开时触发；
已经使用组合键时不会再执行单键功能。

每个功能可以设置一个绑定。录入已有绑定时会解除原功能的绑定；下拉框选择重复绑定
时，保存会提示冲突。编辑或录入期间暂停 Anki 操作，点击“保存并应用”并松开按键后继续。

| 初始输入 | 功能 |
| --- | --- |
| 左摇杆左 | 简单 |
| 左摇杆右 | 困难 |
| 左摇杆上 | 重来 |
| 左摇杆下 | 显示答案 |
| 右摇杆上 / 下 | 向上 / 向下滚动 |
| LT | 重播音频 |
| LB | 撤销上次评分 |
| 未绑定 | 良好、空格：显示答案 / 良好、暂停 / 恢复 |

评分始终按功能含义执行。快捷键标签可选择常规顺序（1 重来 → 4 简单）或反向顺序
（1 简单 → 4 重来）；初始标签为反向顺序，不会修改 Anki 的键盘设置。
“显示答案”只翻面，不评分；“空格：显示答案 / 良好”在正面翻答案，在背面选择良好。

只有滚动会推住连发：立即滚动 160 像素，450 毫秒后每 220 毫秒重复。
回中、暂停、方向失去对齐或卡片/窗口状态变化会停止。页面没有溢出时可能看不到移动。
评分和翻面只触发一次，摇杆必须回中才可再次操作；忽略漂移和斜推。
启动或重连时已经推住/按住的输入必须先松开。

## 语言、实时响应与反馈

- “反馈与设置 → 界面语言”可即时切换简体中文、English 或跟随系统，保留其它未保存
  的编辑；“保存并应用”持久化选择。系统为其它语言时使用英文。
- 侧栏展示完整手柄。“手柄测试”提供放大图，并在测试时暂停 Anki 操作。所有按键
  高亮、摇杆原始位置、扳机幅度和轴数值会实时更新。方向亮起代表通过手势检测；
  漂移或斜推未通过时，原始位置点仍会移动。
- 实线方框表示方向触发阈值，虚线方框表示回中范围。标准 XInput 不提供 Xbox/Guide、
  Share 或独立背键；固件映射为普通按键的背键会作为那个普通按键出现。
- “设为默认”保存整套设置（包括语言和反馈偏好）；“恢复默认设置”先载入，确认后应用。
- “在 Anki 中显示操作提示”默认开启。执行成功后，Anki 窗口右下方会显示约 1 秒的
  “简单 / 良好 / 困难 / 重来 / 显示答案 / 重播音频 / 撤销上次评分 / 向上或向下滚动”。
  提示跟随界面语言，不抢焦点，也不接收鼠标点击。评分和撤销等待实际完成确认；
  操作被拒绝或超时时不显示成功提示。连续滚动提示最多每秒一次，代表滚动请求已提交，
  页面没有溢出时仍可能不移动。提示只针对 anki-grip 发出的操作，可在设置中关闭。
  本候选版需要更新连接插件并重启 Anki 才能显示；旧插件会忽略新增提示设置。
- 震动只在 Anki 确认操作完成后发生；可在设置中测试强度。滚动不震动。
  滚轮只滚动列表，不会修改下拉框或滑块。
- 关闭窗口默认收进托盘；双击重新打开，右键暂停或退出。

## 兼容性与隐私

支持 **Windows 桌面版 Anki + XInput 手柄**。其它手柄需要 XInput 模式或适配器。
暂不支持 macOS、Linux 实际运行、AnkiMobile 或 AnkiDroid。
维护者已确认 1.5.0rc1 在其 Windows 环境正常使用。旧版 1.4.0 曾在 Windows 11、
Xbox One 无线手柄和 Anki 26.09.2 上验证；这些结果不代表所有手柄、连接方式或 Anki 版本均已覆盖。

插件使用 Anki reviewer 内部接口，Anki 升级后需重新核实兼容性。
桥接只监听 `127.0.0.1:18765`，无需 AnkiConnect。没有遥测、自动下载更新或云账户，
不记录卡片内容和手柄输入。评分和撤销使用 Anki 正常复习流程；过期指令被拒绝，
评分超时不会重试。未收到确认时先查看 Anki 当前状态，再决定是否重新按键。

Steam 桌面布局或其它映射器可能同时发出键盘输入；如出现重复操作，检查这些映射。
Anki 未连接时，确认安装后的重启、实际数据目录，以及是否有重复 Anki 实例占用端口。

## 设置位置与卸载

`%LOCALAPPDATA%\anki-grip\settings.json` 保存设置，同目录 `defaults.json`
保存个人默认配置。升级插件时将有变化的旧版本备份到 `addon-backups`。
从 1.4.0 升级会保留已有按键和偏好，并补充跟随系统的语言选项；
插件文件有变化时需更新插件并重启 Anki。

卸载时先从托盘退出，在 Anki 插件管理器删除 **anki-grip bridge** 并重启 Anki，
然后删除程序目录和快捷方式。设置目录可自行保留或删除。安装过程不修改其它插件或卡片模板。

## 开发与构建

Python + PySide6；Windows 原生 XInput 读取输入和控制震动。
虚拟环境和构建中间文件放在仓库外。Windows PowerShell：

```powershell
python -m venv "$env:LOCALAPPDATA\anki-grip-dev"
& "$env:LOCALAPPDATA\anki-grip-dev\Scripts\python.exe" -m pip install -r requirements.txt
& "$env:LOCALAPPDATA\anki-grip-dev\Scripts\python.exe" -m unittest discover -s tests
& "$env:LOCALAPPDATA\anki-grip-dev\Scripts\python.exe" main.py
./build.ps1
```

构建脚本使用隔离环境，先运行测试，再输出 EXE、双语说明、许可证、SHA-256 清单
和运行时版本信息到本机 `release/`。可通过 `-BuildRoot`、`-VenvPath`、`-OutputPath`
调整路径。不要单独分发缺少许可证包的 EXE。

Linux 只能跑模拟测试和离线预览：

```sh
QT_QPA_PLATFORM=offscreen PYTHONDONTWRITEBYTECODE=1 python -m unittest discover -s tests
QT_QPA_PLATFORM=offscreen python main.py --language zh_CN --screenshot /tmp/anki-grip.png --screenshot-tab 3 --demo-controller
```

`--demo-controller` 必须配合离线 `--screenshot`。测试使用假 Anki 对象和临时设置，
不对用户牌组评分。CI 检查 Linux/Windows 测试；手动 Windows 构建工作流只生成
待验收的构建产物，不自动发布 Release。

## 许可证与贡献

源码使用 [MIT](LICENSE)；第三方依赖分别适用其许可证，见
[第三方说明](THIRD_PARTY_NOTICES.md)。手柄图由原创矢量绘制代码生成。
Anki 和 Xbox 名称仅表示兼容性，项目不隶属于其所有者。
提交问题或补丁请参考 [贡献指南](CONTRIBUTING.md)，不要附带卡片内容、个人路径或凭证。
