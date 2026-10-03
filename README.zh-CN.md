# anki-grip

简体中文 · [English](README.md)

用 Xbox 手柄复习 Anki。anki-grip 为 Windows 桌面版 Anki 接入 XInput 手柄。按键可以自定义，手柄状态实时显示，还可以按需开启操作提示和震动反馈。界面支持简体中文和 English。

**[下载 Windows x64 版本](https://github.com/zixi526526/anki-grip/releases/latest)**

1.5.0 是首个公开发布的二进制版本。Windows x64 ZIP 是完整发布包，内含许可证、运行时信息和 SHA-256 校验清单。

## 开始使用

1. 从 Releases 下载 Windows x64 ZIP，解压整个文件夹。保留里面的许可证文件，然后运行 `anki-grip.exe`。不需要安装 Python。
2. 连接支持 XInput 的手柄，打开 Windows 桌面版 Anki。
3. 在“连接指南”中安装或更新 Anki 插件，然后重启 Anki。
4. 打开牌组开始复习。默认情况下，只有 Anki 在前台时手柄操作才会生效。

如果使用便携版 Anki 或自定义了数据目录，可以在“连接指南”中选择对应的 `addons21` 文件夹。关闭窗口时程序通常会收进托盘，要退出请使用托盘菜单。

升级时，先从托盘退出旧版本，再把新版解压到另一个文件夹。原有设置保存在 AppData 中，会继续使用。

## 支持的 Anki 操作

- 显示答案。
- 按重来、困难、良好、简单评分。
- 空格（显示答案 / 良好）。
- 重播音频。
- 撤销上一次评分。
- 上下滚动长卡片。
- 暂停或恢复手柄操作。

可以按需开启 Anki 内的简短操作提示，以及操作确认后的手柄震动。

只有滚动会推住连发：松开按键或让摇杆回中就会停止。评分和翻面每次手势只触发一次。

## 支持的手柄输入

24 个标准 XInput 输入都可以自定义：

- A/B/X/Y
- 十字键四个方向
- LB/RB、LT/RT
- View/Back、Menu/Start
- L3/R3
- 左右摇杆各四个方向

肩键或扳机也可以和其它支持的输入组成组合键。

实时手柄图会显示按键、摇杆位置和扳机按下的深度。打开“手柄测试”会显示放大视图，测试期间 Anki 操作会暂停。标准 XInput 不会报告 Xbox/Guide 键、Share 键或独立背键。

## 兼容性与隐私

anki-grip 支持 Windows 桌面版 Anki 和 XInput 手柄。暂不支持在 macOS 或 Linux 上运行，也不支持 AnkiMobile 和 AnkiDroid。已测试的环境和测试范围见[验证记录](VALIDATION.md)。

插件只监听 `127.0.0.1:18765`，不需要 AnkiConnect。没有遥测，也没有云账户，不会记录卡片内容。Anki 更新后，请确认插件仍能正常工作。如果同时运行其它手柄转键盘的软件，一次按键可能会触发两次操作。遇到这种情况，请检查那个软件的桌面映射。

设置保存在 `%LOCALAPPDATA%\anki-grip`。卸载步骤：

1. 退出 anki-grip。
2. 在 Anki 中移除 anki-grip bridge 插件，然后重启 Anki。
3. 删除解压出来的程序文件夹。

设置文件夹可以保留，也可以删除。

## 从源码构建

构建需要 Python 和 PySide6，虚拟环境请放在仓库外。在 Windows 上运行下面的脚本，它会安装固定版本的依赖、运行测试，并在 `release/` 中生成完整发布包：

```powershell
./build.ps1
```

Linux 上只能运行模拟测试和离线预览。发布验收的更多内容见[发布清单](docs/RELEASE_CHECKLIST.md)。

## 许可证与贡献

项目源码采用 [MIT 许可证](LICENSE)。Qt/PySide 和其它依赖使用各自的许可证，详见[第三方说明](THIRD_PARTY_NOTICES.md)。请把完整的许可证文件和程序放在一起。

手柄图由原创的矢量绘制代码生成。Anki 和 Xbox 名称仅用于说明兼容性，本项目与其所有者没有关联。

提交问题或补丁请参考[贡献指南](CONTRIBUTING.md)，不要附带个人数据或凭证。
