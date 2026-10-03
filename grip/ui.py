from __future__ import annotations

import time
from pathlib import Path

from PySide6.QtCore import Qt, QTimer, QLocale
from PySide6.QtGui import QColor, QPainter, QIcon, QPixmap
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QFrame, QComboBox, QTabWidget, QSlider, QCheckBox, QMessageBox,
    QSystemTrayIcon, QMenu, QFileDialog, QScrollArea, QLayout,
)

from .controller_view import ControllerView
from .i18n import resolve_language, translate
from .bridge import BridgeWorker
from .install import install_addon, resource_root
from .model import ACTIONS, BINDINGS, LABELS, MODIFIERS, STICK_GUARDS, SCROLL_ACTIONS, InputMapper, binding_label, default_config, load_config, load_defaults, rating_keys, save_config, save_defaults, validate_bindings
from . import __version__
from .xinput import XInput

STYLE = """
QMainWindow, QWidget#main { background: #f3f5f2; }
QWidget { color: #20322e; font-family: 'Segoe UI', 'Microsoft YaHei UI', sans-serif; font-size: 12px; }
QFrame#sidebar { background: #172d29; border-radius: 18px; }
QFrame#sidebar QLabel { color: #d4e2dc; }
QLabel#brand { color: #d4fa91; font-family: 'Segoe UI'; font-size: 30px; font-weight: 700; }
QLabel#sideNote { color: #9db6ad; font-size: 12px; }
QLabel#heading { font-size: 25px; font-weight: 700; }
QLabel#subtle { color: #75837b; }
QLabel#status { color: #b8dda7; background: #254139; border-radius: 9px; padding: 10px; }
QLabel#actionTitle { font-size: 14px; font-weight: 600; }
QLabel#key { color: #325b44; background: #ecf4e4; border-radius: 6px; padding: 4px; font-family: 'Segoe UI'; font-weight: 700; }
QFrame#card { background: #ffffff; border: 1px solid #e3e9df; border-radius: 12px; }
QPushButton { background: #ffffff; border: 1px solid #d9e1d5; border-radius: 8px; padding: 9px 15px; }
QPushButton:hover { border-color: #759964; background: #f4f9ee; }
QPushButton:pressed { background: #e5f1d8; }
QPushButton:disabled { color: #a6afa8; }
QPushButton#primary { background: #244d3c; color: #ffffff; border: none; font-weight: 600; padding: 11px 22px; }
QPushButton#primary:hover { background: #32654f; }
QPushButton#pause { background: #d4fa91; color: #1c3527; border: none; font-weight: 600; padding: 12px; }
QPushButton#capture { padding: 8px 12px; }
QComboBox { background: #f8faf6; border: 1px solid #dfe6da; border-radius: 7px; padding: 8px; min-height: 18px; }
QComboBox::drop-down { border: none; width: 24px; }
QComboBox QAbstractItemView { background: white; selection-background-color: #e8f4dc; selection-color: #20322e; }
QTabWidget::pane { border: none; background: transparent; }
QTabBar::tab { color: #79877e; padding: 12px 17px; border-bottom: 2px solid transparent; }
QTabBar::tab:selected { color: #234735; border-bottom: 2px solid #427b52; font-weight: 600; }
QTabBar::tab:hover { color: #234735; }
QSlider::groove:horizontal { background: #e3ebde; height: 6px; border-radius: 3px; }
QSlider::sub-page:horizontal { background: #78a660; border-radius: 3px; }
QSlider::handle:horizontal { background: #2f6247; border: 3px solid #ffffff; width: 16px; height: 16px; margin: -7px 0; border-radius: 10px; }
QCheckBox { spacing: 10px; padding: 6px 0; }
QCheckBox::indicator { width: 17px; height: 17px; border: 1px solid #b6c4b1; border-radius: 4px; background: white; }
QCheckBox::indicator:checked { background: #3f7651; border-color: #3f7651; image: none; }
QScrollArea { background: transparent; border: none; }
QScrollArea > QWidget > QWidget { background: transparent; }
QScrollBar:vertical { width: 7px; background: transparent; }
QScrollBar::handle:vertical { background: #c7d5c1; border-radius: 3px; min-height: 30px; }
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height: 0; }
QToolTip { background: #213e31; color: white; border: none; padding: 7px; }
"""
STYLE += f"""
QComboBox::down-arrow {{ image: url('{(resource_root() / 'assets' / 'chevron.svg').as_posix()}'); width: 16px; height: 16px; }}
QCheckBox::indicator:checked {{ image: url('{(resource_root() / 'assets' / 'check.svg').as_posix()}'); }}
"""


def label(text: str, object_name: str = "", wrap=False) -> QLabel:
    result = QLabel(text)
    result.setObjectName(object_name)
    result.setWordWrap(wrap)
    return result


class WheelSafeComboBox(QComboBox):
    def wheelEvent(self, event):
        # Let the surrounding scroll area scroll without selecting another
        # setting, even when this control currently has keyboard focus.
        event.ignore()


class WheelSafeSlider(QSlider):
    def wheelEvent(self, event):
        event.ignore()


def icon() -> QIcon:
    pixmap = QPixmap(64, 64)
    pixmap.fill(Qt.GlobalColor.transparent)
    p = QPainter(pixmap)
    p.setRenderHint(QPainter.RenderHint.Antialiasing)
    p.setBrush(QColor("#234735"))
    p.setPen(Qt.PenStyle.NoPen)
    p.drawRoundedRect(2, 2, 60, 60, 16, 16)
    p.setBrush(QColor("#d4fa91"))
    p.drawRoundedRect(15, 28, 34, 8, 2, 2)
    p.drawRoundedRect(28, 15, 8, 34, 2, 2)
    p.end()
    return QIcon(pixmap)


class MainWindow(QMainWindow):
    def __init__(self, offline=False, language=None):
        super().__init__()
        self.setWindowTitle("anki-grip")
        self.setWindowIcon(icon())
        self.resize(1200, 850)
        self.setMinimumSize(1080, 700)
        self.config = load_config()
        if language is not None:
            self.config["language"] = language
        self.language = resolve_language(self.config.get("language", "auto"), QLocale.system().name())
        self.translated_widgets = []
        self.translated_combos = []
        self.notice_source = "按键映射已载入。首次使用请查看“连接指南”。"
        self.notice_values = {}
        self.testing = False
        self.mapper = InputMapper(self.config["bindings"])
        self.offline = offline
        self.pad = None if offline else XInput()
        self.snapshot = None
        self.anki_status: dict = {}
        self.anki_seen_at = 0.0
        self.paused = False
        self.inflight = False
        self.last_dispatch = 0.0
        self.capture_action: str | None = None
        self.capture_deadline = 0.0
        self.capture_down: set[str] = set()
        self.capture_candidate = ""
        self.capture_ready = False
        self.quitting = False
        self.last_controller = None
        self.last_review_state = ""
        self.mapping_combos: dict[str, QComboBox] = {}
        self.capture_buttons: dict[str, QPushButton] = {}
        self.key_labels: dict[str, QLabel] = {}
        self.setup_ui()
        self.setup_tray()
        self.retranslate_ui()
        self.worker = None
        if not offline:
            self.worker = BridgeWorker()
            self.worker.status_ready.connect(self.on_status)
            self.worker.action_done.connect(self.on_result)
            self.worker.start()
        self.poll_timer = QTimer(self)
        self.poll_timer.timeout.connect(self.poll)
        self.poll_timer.start(16)
        self.update_status_labels()

    def t(self, source, **values):
        return translate(source, self.language, **values)

    def ui_label(self, source, object_name="", wrap=False):
        widget = label(self.t(source), object_name, wrap)
        self.translated_widgets.append((widget, "setText", source))
        return widget

    def ui_button(self, source):
        widget = QPushButton(self.t(source).replace("&", "&&"))
        self.translated_widgets.append((widget, "setText", source))
        return widget

    def ui_check(self, source):
        widget = QCheckBox(self.t(source))
        self.translated_widgets.append((widget, "setText", source))
        return widget

    def ui_tooltip(self, widget, source):
        widget.setToolTip(self.t(source))
        self.translated_widgets.append((widget, "setToolTip", source))

    def add_item(self, combo, source, data, **values):
        index = combo.count()
        combo.addItem(self.t(source, **values), data)
        self.translated_combos.append((combo, index, source, values))

    def set_notice(self, source, **values):
        self.notice_source, self.notice_values = source, values
        resolved = {key: value() if callable(value) else value for key, value in values.items()}
        self.notice.setText(self.t(source, **resolved))

    def on_language_changed(self, *_args):
        self.language = resolve_language(self.language_combo.currentData(), QLocale.system().name())
        self.retranslate_ui()
        self.mark_dirty()
        if self.capture_action:
            action = self.capture_action
            self.set_notice("正在录入“{action}”：摇杆先回中，再推向目标方向并回中；按键则按下再松开。Esc 取消。", action=lambda: self.t(ACTIONS[action][0]))
        self.update_status_labels()

    def retranslate_ui(self):
        for widget, method, source in self.translated_widgets:
            text = self.t(source)
            if method == "setText" and isinstance(widget, QPushButton):
                text = text.replace("&", "&&")
            getattr(widget, method)(text)
        for combo, index, source, values in self.translated_combos:
            combo.blockSignals(True)
            combo.setItemText(index, self.t(source, **values))
            combo.blockSignals(False)
        for combo in self.mapping_combos.values():
            combo.blockSignals(True)
            for index in range(combo.count()):
                combo.setItemText(index, binding_label(combo.itemData(index), self.language))
            combo.blockSignals(False)
        for index, source in enumerate(("按键映射", "反馈与设置", "连接指南", "手柄测试")):
            self.tabs.setTabText(index, self.t(source))
        self.pause_button.setText(self.t("恢复控制" if self.paused else "暂停控制"))
        self.tray_pause_action.setText(self.pause_button.text())
        self.tray_open_action.setText(self.t("打开 anki-grip"))
        self.tray_quit_action.setText(self.t("退出"))
        self.save_button.setText(self.t("保存并应用 ·" if self.dirty() else "保存并应用").replace("&", "&&"))
        for action, button in self.capture_buttons.items():
            button.setText(self.t("等待…" if self.capture_action == action else "录入"))
        self.controller_view.set_language(self.language)
        self.test_controller_view.set_language(self.language)
        self.set_notice(self.notice_source, **self.notice_values)
        self.update_controller_labels()
        self.update_status_labels()

    def controller_test_page(self):
        page = QWidget()
        body = QVBoxLayout(page)
        body.setContentsMargins(0, 18, 0, 0)
        body.addWidget(self.ui_label("实时输入 · 测试期间暂停 Anki 操作", "actionTitle", True))
        body.addWidget(self.ui_label("原始摇杆位置和扳机幅度会直接显示；亮起的方向代表已通过手势检测。", "subtle", True))
        frame = QFrame()
        frame.setObjectName("card")
        view_layout = QVBoxLayout(frame)
        self.test_controller_view = ControllerView()
        self.test_controller_view.set_language(self.language)
        view_layout.addWidget(self.test_controller_view)
        body.addWidget(frame, 1)
        self.axes_label = label("")
        self.axes_label.setWordWrap(True)
        self.axes_label.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        body.addWidget(self.axes_label)
        body.addWidget(self.ui_label("实线：方向触发阈值 · 虚线：回中范围", "subtle", True))
        body.addWidget(self.ui_label("Xbox/Guide、Share 和独立背键不在标准 XInput 输入范围内。", "subtle", True))
        return page

    def on_tab_changed(self, index):
        testing = index == self.test_tab_index
        was_testing = self.testing
        self.testing = testing
        if testing or was_testing:
            self.end_capture()
            if self.pad:
                self.pad.stop()
        if testing:
            self.set_notice("手柄测试已打开，Anki 操作暂停。离开测试页并松开按键后继续。")
        elif was_testing:
            self.set_notice("更改尚未应用，控制已暂停。点击“保存并应用”后继续。" if self.dirty()
                            else "控制已暂停。" if self.paused else "控制已恢复，松开按键后继续。")
        self.update_status_labels()

    def update_controller_labels(self):
        snapshot = self.snapshot
        down = snapshot.down if snapshot and hasattr(snapshot, "down") else set()
        shown = down - STICK_GUARDS
        self.input_label.setText(" + ".join(self.t(LABELS.get(k, k)) for k in sorted(shown)) if shown
                                 else self.t("摇杆推动中 · 等待稳定方向" if STICK_GUARDS & down else "等待按键"))
        self.controller_status.setText(self.t("●  Xbox 手柄 {slot}\n{battery}", slot=snapshot.index + 1,
                                             battery=self.t(getattr(snapshot, "battery", "电量未知"))) if snapshot
                                       else self.t("○  手柄未连接\nUSB / 蓝牙 / 无线适配器"))
        if snapshot:
            axes = [getattr(snapshot, key, 0) for key in ("lx", "ly", "rx", "ry", "lt", "rt")]
            self.axes_label.setText("LX {:+6d}   LY {:+6d}   RX {:+6d}   RY {:+6d}\nLT {:3d}/255   RT {:3d}/255".format(*axes))
        else:
            self.axes_label.setText(self.t("未连接手柄"))
        self.update_sidebar_height()

    def update_sidebar_height(self):
        if self.quitting or not hasattr(self, "sidebar_scroll"):
            return
        # Wrapped live-input text changes the content height. Keep the scroll
        # widget tall enough instead of allowing Qt to overlap its children.
        layout = self.sidebar.layout()
        self.sidebar.setMinimumHeight(max(layout.minimumSize().height(),
                                          layout.totalHeightForWidth(self.sidebar_scroll.viewport().width())))

    def resizeEvent(self, event):
        super().resizeEvent(event)
        if hasattr(self, "sidebar_scroll"):
            QTimer.singleShot(0, self.update_sidebar_height)

    def setup_ui(self):
        central = QWidget()
        central.setObjectName("main")
        self.setCentralWidget(central)
        layout = QHBoxLayout(central)
        layout.setContentsMargins(18, 18, 22, 18)
        layout.setSpacing(25)
        sidebar = QFrame()
        sidebar.setObjectName("sidebar")
        side = QVBoxLayout(sidebar)
        side.setSizeConstraint(QLayout.SizeConstraint.SetNoConstraint)
        side.setContentsMargins(20, 25, 20, 22)
        side.setSpacing(11)
        side.addWidget(label("anki-grip", "brand"))
        side.addWidget(self.ui_label("把复习握在手里", "sideNote"))
        side.addSpacing(12)
        self.controller_view = ControllerView(compact=True)
        self.controller_view.set_language(self.language)
        side.addWidget(self.controller_view)
        test_button = self.ui_button("查看完整手柄测试")
        test_button.clicked.connect(lambda: self.tabs.setCurrentIndex(self.test_tab_index))
        side.addWidget(test_button)
        self.controller_status = self.ui_label("正在寻找手柄…", "status", True)
        self.bridge_status = self.ui_label("正在连接 Anki…", "status", True)
        side.addWidget(self.controller_status)
        side.addWidget(self.bridge_status)
        self.input_label = self.ui_label("等待按键", "sideNote", True)
        self.input_label.setMinimumHeight(40)
        side.addWidget(self.input_label)
        side.addStretch()
        self.pause_button = self.ui_button("暂停控制")
        self.pause_button.setObjectName("pause")
        self.pause_button.clicked.connect(self.toggle_pause)
        side.addWidget(self.pause_button)
        side.addWidget(label(f"v{__version__}  ·  Windows + Xbox", "sideNote"))
        sidebar_scroll = QScrollArea()
        sidebar_scroll.setWidgetResizable(True)
        sidebar_scroll.setFixedWidth(328)
        sidebar_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        sidebar_scroll.setWidget(sidebar)
        self.sidebar = sidebar
        self.sidebar_scroll = sidebar_scroll
        layout.addWidget(sidebar_scroll)

        right = QVBoxLayout()
        right.setSpacing(12)
        right.addWidget(self.ui_label("你的节奏，你的按键。", "heading"))
        right.addWidget(self.ui_label("用你习惯的手柄布局复习。每个输入都可重新分配。", "subtle", True))
        self.tabs = QTabWidget()
        self.tabs.addTab(self.mapping_page(), self.t("按键映射"))
        self.tabs.addTab(self.feedback_page(), self.t("反馈与设置"))
        self.tabs.addTab(self.connection_page(), self.t("连接指南"))
        self.test_tab_index = self.tabs.addTab(self.controller_test_page(), self.t("手柄测试"))
        self.tabs.currentChanged.connect(self.on_tab_changed)
        right.addWidget(self.tabs, 1)
        self.notice = self.ui_label("按键映射已载入。首次使用请查看“连接指南”。", "subtle", True)
        self.notice.setMinimumHeight(42)
        right.addWidget(self.notice)
        footer = QHBoxLayout()
        reset = self.ui_button("恢复默认设置")
        reset.clicked.connect(self.restore_defaults)
        footer.addWidget(reset)
        self.defaults_button = self.ui_button("设为默认")
        self.ui_tooltip(self.defaults_button, "保存并应用当前全部设置，同时将它们设为以后恢复的默认设置。")
        self.defaults_button.clicked.connect(self.set_as_defaults)
        footer.addWidget(self.defaults_button)
        footer.addStretch()
        self.save_button = self.ui_button("保存并应用")
        self.save_button.setObjectName("primary")
        self.save_button.clicked.connect(self.apply_settings)
        footer.addWidget(self.save_button)
        right.addLayout(footer)
        layout.addLayout(right, 1)

    def mapping_page(self):
        page = QWidget()
        body = QVBoxLayout(page)
        body.setContentsMargins(0, 13, 0, 0)
        order_row = QHBoxLayout()
        order_row.addWidget(self.ui_label("Anki 的评分快捷键", "subtle"))
        self.order_combo = WheelSafeComboBox()
        self.add_item(self.order_combo, "1 简单 → 4 重来（反向顺序）", "reverse")
        self.add_item(self.order_combo, "1 重来 → 4 简单（常规顺序）", "standard")
        self.ui_tooltip(self.order_combo, "选择与你的 Anki 一致的快捷键标签；评分始终按功能名称执行。")
        self.order_combo.setCurrentIndex(0 if self.config["order"] == "reverse" else 1)
        self.order_combo.currentIndexChanged.connect(self.update_rating_labels)
        order_row.addWidget(self.order_combo, 1)
        body.addLayout(order_row)
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        rows = QWidget()
        rows_layout = QVBoxLayout(rows)
        rows_layout.setContentsMargins(0, 4, 8, 4)
        rows_layout.setSpacing(7)
        for action, (title, detail, _) in ACTIONS.items():
            frame = QFrame()
            frame.setObjectName("card")
            row = QHBoxLayout(frame)
            row.setContentsMargins(12, 7, 12, 7)
            row.setSpacing(10)
            key = label("", "key")
            key.setFixedWidth(29)
            key.setAlignment(Qt.AlignmentFlag.AlignCenter)
            self.key_labels[action] = key
            row.addWidget(key)
            description = QVBoxLayout()
            description.setSpacing(1)
            description.addWidget(self.ui_label(title, "actionTitle", True))
            description.addWidget(self.ui_label(detail, "subtle", True))
            row.addLayout(description, 1)
            combo = WheelSafeComboBox()
            combo.setFixedWidth(235)
            combo.setMaxVisibleItems(12)
            for binding in BINDINGS:
                combo.addItem(binding_label(binding, self.language), binding)
            combo.setCurrentIndex(combo.findData(self.config["bindings"][action]))
            combo.currentIndexChanged.connect(self.mark_dirty)
            self.mapping_combos[action] = combo
            row.addWidget(combo)
            capture = self.ui_button("录入")
            capture.setObjectName("capture")
            self.ui_tooltip(capture, "点击后推摇杆并回中，或按下并松开按键；组合键先按住肩键或扳机。")
            capture.clicked.connect(lambda checked=False, a=action: self.begin_capture(a))
            self.capture_buttons[action] = capture
            row.addWidget(capture)
            rows_layout.addWidget(frame)
        rows_layout.addStretch()
        scroll.setWidget(rows)
        body.addWidget(scroll, 1)
        body.addWidget(self.ui_label("评分/翻面需回中 · 滚动可推住连滚 · 斜推不评分", "subtle", True))
        body.addWidget(self.ui_label("完整 Xbox 输入：A/B/X/Y、十字键、双摇杆、LB/RB、LT/RT、View/Menu。", "subtle", True))
        self.update_rating_labels()
        return page

    def feedback_page(self):
        page = QWidget()
        body = QVBoxLayout(page)
        body.setContentsMargins(0, 18, 0, 0)
        body.setSpacing(15)
        language_row = QHBoxLayout()
        language_row.addWidget(self.ui_label("界面语言 / Language", "actionTitle"))
        self.language_combo = WheelSafeComboBox()
        self.add_item(self.language_combo, "跟随系统 / System", "auto")
        self.language_combo.addItem("简体中文", "zh_CN")
        self.language_combo.addItem("English", "en")
        self.language_combo.setCurrentIndex(self.language_combo.findData(self.config["language"]))
        self.language_combo.currentIndexChanged.connect(self.on_language_changed)
        language_row.addWidget(self.language_combo, 1)
        body.addLayout(language_row)
        feedback = QFrame()
        feedback.setObjectName("card")
        items = QVBoxLayout(feedback)
        items.setContentsMargins(20, 18, 20, 18)
        self.anki_feedback_check = self.ui_check("在 Anki 中显示操作提示")
        self.anki_feedback_check.setChecked(self.config["anki_feedback"])
        self.anki_feedback_check.toggled.connect(self.mark_dirty)
        self.ui_tooltip(self.anki_feedback_check, "操作成功后在 Anki 内短暂显示功能名称，提示不接收鼠标或键盘输入。")
        items.addWidget(self.anki_feedback_check)
        self.vibration_check = self.ui_check("启用手柄震动")
        self.vibration_check.setChecked(self.config["vibration"])
        self.vibration_check.toggled.connect(self.mark_dirty)
        items.addWidget(self.vibration_check)
        line = QHBoxLayout()
        line.addWidget(self.ui_label("震动强度", "actionTitle"))
        line.addStretch()
        self.strength_label = label(f"{self.config['strength']}%", "subtle")
        line.addWidget(self.strength_label)
        items.addLayout(line)
        self.strength_slider = WheelSafeSlider(Qt.Orientation.Horizontal)
        self.strength_slider.setRange(0, 100)
        self.strength_slider.setValue(self.config["strength"])
        self.strength_slider.valueChanged.connect(lambda value: self.strength_label.setText(f"{value}%"))
        self.strength_slider.valueChanged.connect(self.mark_dirty)
        items.addWidget(self.strength_slider)
        items.addWidget(self.ui_label("简单：短震   ·   良好：轻震   ·   困难：双震   ·   重来：稍长震动", "subtle", True))
        test_line = QHBoxLayout()
        self.pattern_combo = WheelSafeComboBox()
        for key in ("test", "easy", "good", "hard", "again", "show", "replay", "complete"):
            self.add_item(self.pattern_combo, {"test": "双马达测试", "complete": "本轮完成"}.get(key, ACTIONS.get(key, (key,))[0]), key)
        test_line.addWidget(self.pattern_combo, 1)
        test = self.ui_button("测试震动")
        test.clicked.connect(self.test_vibration)
        test_line.addWidget(test)
        items.addLayout(test_line)
        body.addWidget(feedback)
        behavior = QFrame()
        behavior.setObjectName("card")
        settings = QVBoxLayout(behavior)
        settings.setContentsMargins(20, 16, 20, 18)
        self.foreground_check = self.ui_check("仅在 Anki 位于前台时控制（推荐）")
        self.foreground_check.setChecked(self.config["foreground_only"])
        self.foreground_check.toggled.connect(self.mark_dirty)
        self.tray_check = self.ui_check("关闭窗口时收进系统托盘")
        self.tray_check.setChecked(self.config["minimize_to_tray"])
        self.tray_check.toggled.connect(self.mark_dirty)
        settings.addWidget(self.foreground_check)
        settings.addWidget(self.tray_check)
        self.device_combo = WheelSafeComboBox()
        self.add_item(self.device_combo, "自动使用第一个已连接手柄", -1)
        for i in range(4):
            self.add_item(self.device_combo, "手柄槽位 {slot}", i, slot=i + 1)
        self.device_combo.setCurrentIndex(self.device_combo.findData(self.config["controller"]))
        self.device_combo.currentIndexChanged.connect(self.mark_dirty)
        settings.addWidget(self.device_combo)
        settings.addWidget(self.ui_label("编辑映射或录入按键时暂停控制。震动只在操作确认后发生。", "subtle", True))
        body.addWidget(behavior)
        body.addStretch()
        return page

    def connection_page(self):
        page = QWidget()
        body = QVBoxLayout(page)
        body.setContentsMargins(0, 18, 0, 0)
        body.setSpacing(15)
        frame = QFrame()
        frame.setObjectName("card")
        items = QVBoxLayout(frame)
        items.setContentsMargins(21, 20, 21, 20)
        items.setSpacing(15)
        items.addWidget(self.ui_label("三步开始复习", "actionTitle"))
        items.addWidget(self.ui_label("1   将 Xbox 手柄连接到 Windows。\n\n2   安装连接插件，然后退出并重新打开 Anki。\n\n3   打开牌组开始复习，按映射页的设置操作。", wrap=True))
        install = self.ui_button("安装 / 更新 Anki 连接插件")
        install.clicked.connect(self.install_bridge)
        items.addWidget(install)
        custom = self.ui_button("选择自定义 Anki 插件目录…")
        custom.clicked.connect(self.install_custom_bridge)
        items.addWidget(custom)
        items.addWidget(self.ui_label("如果使用便携版或自定义数据目录，请选择其 addons21 文件夹。", "subtle", True))
        body.addWidget(frame)
        tips = QFrame()
        tips.setObjectName("card")
        tips_layout = QVBoxLayout(tips)
        tips_layout.setContentsMargins(21, 20, 21, 20)
        tips_layout.addWidget(self.ui_label("布局与操作提示", "actionTitle"))
        tips_layout.addWidget(self.ui_label("• 左右摇杆四方向均可绑定。\n• 右摇杆上/下默认滚动；推住连滚，回中停止。\n• 空格功能：正面显示答案，背面选良好。\n• “设为默认”保存整套设置；“恢复默认设置”找回。\n• 滚轮只滚动列表，不修改下拉框或震动强度。\n• 每次推动后需回中，再进行下一操作；斜推忽略。", wrap=True))
        tips_layout.addWidget(self.ui_label("评分按功能含义执行；快捷键标签可选常规或反向顺序。", "subtle", True))
        body.addWidget(tips)
        body.addStretch()
        return page

    def setup_tray(self):
        self.tray = QSystemTrayIcon(self.windowIcon(), self)
        self.ui_tooltip(self.tray, "anki-grip · 手柄复习")
        menu = QMenu()
        self.tray_open_action = menu.addAction(self.t("打开 anki-grip"), self.show_window)
        self.tray_pause_action = menu.addAction(self.t("暂停控制"), self.toggle_pause)
        menu.addSeparator()
        self.tray_quit_action = menu.addAction(self.t("退出"), self.quit_app)
        self.tray.setContextMenu(menu)
        self.tray.activated.connect(lambda reason: self.show_window()
                                   if reason == QSystemTrayIcon.ActivationReason.DoubleClick else None)
        if QSystemTrayIcon.isSystemTrayAvailable():
            self.tray.show()

    def show_window(self):
        self.showNormal()
        self.raise_()
        self.activateWindow()

    def mark_dirty(self, *_args):
        if hasattr(self, "notice"):
            self.set_notice("更改尚未应用，控制已暂停。点击“保存并应用”后继续。")
            self.save_button.setText(self.t("保存并应用 ·").replace("&", "&&"))
        self.mapper.reset()
        if self.pad:
            self.pad.stop()

    def dirty(self) -> bool:
        return self.current_ui_config() != self.config

    def current_ui_config(self) -> dict:
        return {"schema": 2, "language": self.language_combo.currentData(),
                "bindings": {a: c.currentData() for a, c in self.mapping_combos.items()},
                "order": self.order_combo.currentData(),
                "vibration": self.vibration_check.isChecked(),
                "anki_feedback": self.anki_feedback_check.isChecked(),
                "strength": self.strength_slider.value(),
                "foreground_only": self.foreground_check.isChecked(),
                "controller": self.device_combo.currentData(),
                "minimize_to_tray": self.tray_check.isChecked()}

    def update_rating_labels(self, *_args):
        keys = rating_keys(self.order_combo.currentData())
        symbols = {"show": "↵", "space": "␣", "replay": "R", "undo": "↶", "pause": "Ⅱ"}
        for action, widget in self.key_labels.items():
            widget.setText(keys.get(action, symbols.get(action, "")))
        if hasattr(self, "notice"):
            self.mark_dirty()

    def apply_settings(self):
        updated = self.current_ui_config()
        try:
            validate_bindings(updated["bindings"], self.language)
            save_config(updated)
        except (ValueError, OSError) as error:
            QMessageBox.warning(self, self.t("未能保存"), str(error))
            return False
        self.config = updated
        self.mapper = InputMapper(updated["bindings"])
        if self.pad:
            self.pad.stop()
        self.end_capture()
        self.set_notice("已保存并应用。松开手柄按键后即可继续。")
        self.save_button.setText(self.t("保存并应用").replace("&", "&&"))
        self.update_status_labels()
        return True

    def set_as_defaults(self):
        if not self.apply_settings():
            return
        try:
            save_defaults(self.config)
        except OSError as error:
            QMessageBox.warning(self, self.t("默认设置未保存"), str(error))
            return
        self.set_notice("当前全部设置已保存为默认。以后可点击“恢复默认设置”找回。")

    def restore_defaults(self):
        defaults = load_defaults()
        self.end_capture()
        for action, combo in self.mapping_combos.items():
            combo.setCurrentIndex(combo.findData(defaults["bindings"][action]))
        self.order_combo.setCurrentIndex(self.order_combo.findData(defaults["order"]))
        self.vibration_check.setChecked(defaults["vibration"])
        self.anki_feedback_check.setChecked(defaults["anki_feedback"])
        self.strength_slider.setValue(defaults["strength"])
        self.foreground_check.setChecked(defaults["foreground_only"])
        self.device_combo.setCurrentIndex(self.device_combo.findData(defaults["controller"]))
        self.tray_check.setChecked(defaults["minimize_to_tray"])
        self.language_combo.setCurrentIndex(self.language_combo.findData(defaults["language"]))
        self.mark_dirty()
        self.set_notice("默认设置已载入。点击“保存并应用”后生效。")

    def toggle_pause(self):
        self.paused = not self.paused
        self.mapper.reset()
        if self.pad:
            self.pad.stop()
        self.pause_button.setText(self.t("恢复控制" if self.paused else "暂停控制"))
        self.tray_pause_action.setText(self.t("恢复控制" if self.paused else "暂停控制"))
        self.set_notice("控制已暂停。" if self.paused else "控制已恢复，松开按键后继续。")
        self.rumble("pause")
        self.update_status_labels()

    def begin_capture(self, action: str):
        self.end_capture()
        if not self.snapshot:
            self.set_notice("请先连接手柄，再录入按键。")
            return
        self.capture_action = action
        self.capture_deadline = time.monotonic() + 10
        self.capture_ready = False
        self.capture_candidate = ""
        self.capture_down = set()
        self.capture_buttons[action].setText(self.t("等待…"))
        self.set_notice("正在录入“{action}”：摇杆先回中，再推向目标方向并回中；按键则按下再松开。Esc 取消。", action=lambda: self.t(ACTIONS[action][0]))
        self.mapper.reset()
        if self.pad:
            self.pad.stop()

    def end_capture(self):
        if self.capture_action:
            self.capture_buttons[self.capture_action].setText(self.t("录入"))
        self.capture_action = None
        self.capture_down = set()
        self.mapper.reset()

    def capture_step(self, down: set[str]):
        if time.monotonic() > self.capture_deadline:
            self.end_capture()
            self.set_notice("录入已超时，可重新点击“录入”。")
            return
        if not self.capture_ready:
            self.capture_ready = not down
            return
        down = down - STICK_GUARDS
        rising = down - self.capture_down
        if rising:
            if len(down) == 1:
                self.capture_candidate = next(iter(down))
            elif len(down) == 2 and len(down & self.capture_down & MODIFIERS) == 1:
                modifier = next(iter(down & self.capture_down & MODIFIERS))
                other = next(iter(down - {modifier}))
                self.capture_candidate = modifier + "+" + other
            else:
                self.capture_candidate = ""
        if not down and self.capture_down and self.capture_candidate:
            candidate = self.capture_candidate
            action = self.capture_action
            self.end_capture()
            if candidate in BINDINGS:
                # Moving a binding explicitly unbinds its prior owner.
                for other, combo in self.mapping_combos.items():
                    if other != action and combo.currentData() == candidate:
                        combo.setCurrentIndex(0)
                combo = self.mapping_combos[action]
                combo.setCurrentIndex(combo.findData(candidate))
                self.set_notice("已录入 {binding}。点击“保存并应用”生效。", binding=lambda: binding_label(candidate, self.language))
            return
        self.capture_down = set(down)

    def poll(self):
        if not self.pad:
            return
        self.pad.tick()
        snapshot = self.pad.read(self.config["controller"])
        index = snapshot.index if snapshot else None
        if index != self.last_controller:
            self.mapper.reset()
            self.pad.stop()
            self.last_controller = index
        self.snapshot = snapshot
        down = snapshot.down if snapshot else set()
        self.controller_view.set_snapshot(snapshot)
        self.test_controller_view.set_snapshot(snapshot)
        self.update_controller_labels()
        if self.capture_action:
            self.capture_step(down)
            return
        if self.dirty() or self.testing:
            self.mapper.reset()
            return
        events = self.mapper.step(down, repeat_allowed=getattr(snapshot, "scroll_allowed", True))
        if self.paused:
            self.mapper.repeating = ""
        for action in events:
            if action == "pause":
                self.toggle_pause()
            elif not self.paused:
                self.dispatch(action)

    def on_status(self, status: dict):
        self.anki_seen_at = time.monotonic()
        old = self.anki_status
        self.anki_status = status
        if any(old.get(k) != status.get(k) for k in ("revision", "session", "foreground", "blocked", "state")):
            self.mapper.repeating = ""
        if old.get("connected") and not status.get("connected"):
            self.mapper.reset()
            if self.pad:
                self.pad.stop()
        # Completion feedback only after this app's successful rating ended a round.
        if (self.last_review_state == "rated" and status.get("state") == "overview"
                and status.get("connected")):
            self.rumble("complete")
            self.set_notice("本轮复习已结束。")
            self.last_review_state = ""
        elif status.get("state") == "question":
            self.last_review_state = ""
        self.update_status_labels()

    def update_status_labels(self):
        if not self.anki_status.get("connected"):
            self.bridge_status.setText(self.t("○  Anki 尚未连接\n安装插件后重启 Anki"))
            return
        state = self.anki_status.get("state")
        scene = {"question": "正面 · 等待翻答案", "answer": "背面 · 可以评分", "overview": "牌组概览", "deckBrowser": "牌组列表", "profileManager": "账户选择"}.get(state, "等待复习")
        if self.paused:
            scene = "控制已暂停"
        elif self.testing:
            scene = "测试中 · 控制暂停"
        elif self.dirty():
            scene = "编辑中 · 控制暂停"
        elif self.config["foreground_only"] and not self.anki_status.get("foreground"):
            scene = "切回 Anki 窗口后可操作"
        self.bridge_status.setText(self.t("●  Anki 已连接\n{scene}", scene=self.t(scene)))

    def dispatch(self, action: str):
        now = time.monotonic()
        if self.testing or self.capture_action or self.dirty() or self.paused:
            return
        if self.inflight or now - self.last_dispatch < .20:
            return
        status = self.anki_status
        if not status.get("connected") or now - self.anki_seen_at > 1.2:
            self.set_notice("Anki 未连接，请安装插件并重启 Anki。")
            return
        if status.get("blocked") or (self.config["foreground_only"] and not status.get("foreground")):
            self.set_notice("切回 Anki 的复习窗口后再操作。")
            return
        if status.get("state") not in ("question", "answer"):
            self.set_notice("请先在 Anki 中打开牌组，开始复习。")
            return
        if action == "space":
            # Resolve against the same revision/session used in the command.
            # The bridge rejects stale state; feedback follows the real action.
            action = "show" if status["state"] == "question" else "good"
        if action in {"easy", "good", "hard", "again"} and status.get("state") != "answer":
            self.set_notice("请先显示答案（默认左摇杆下），再评分。")
            return
        payload = {"action": action, "revision": status.get("revision"),
                   "session": status.get("session"), "foreground_only": self.config["foreground_only"],
                   "show_feedback": self.config["anki_feedback"], "feedback_language": self.language}
        if self.worker and self.worker.submit(action, payload):
            self.inflight = True
            self.last_dispatch = now

    def on_result(self, action: str, result: dict):
        self.inflight = False
        self.set_notice(result.get("message", "操作未完成。"))
        if result.get("ok"):
            if action not in SCROLL_ACTIONS:
                self.rumble(action)
            if action in {"easy", "good", "hard", "again"}:
                self.last_review_state = "rated"

    def rumble(self, action: str):
        if self.pad and self.snapshot and self.config["vibration"]:
            self.pad.play(self.snapshot.index, action, self.config["strength"])

    def test_vibration(self):
        if not self.pad or not self.snapshot:
            self.set_notice("请先连接手柄。")
            return
        self.pad.play(self.snapshot.index, self.pattern_combo.currentData(), self.strength_slider.value())
        self.set_notice("已发送测试震动。若未感觉到震动，请检查手柄电量并重新连接。")

    def install_bridge(self, checked=False, target: Path | None = None):
        try:
            install_addon(target)
        except OSError as error:
            QMessageBox.warning(self, self.t("安装未完成"), str(error))
            return
        self.set_notice("连接插件已安装。请退出并重新打开 Anki，程序会自动连接。")
        QMessageBox.information(self, self.t("连接插件已安装"), self.t("请退出并重新打开 Anki。\n之后打开牌组开始复习即可。"))

    def install_custom_bridge(self):
        chosen = QFileDialog.getExistingDirectory(self, self.t("选择 Anki 的 addons21 目录"))
        if chosen:
            self.install_bridge(target=Path(chosen))

    def keyPressEvent(self, event):
        if event.key() == Qt.Key.Key_Escape and self.capture_action:
            self.end_capture()
            self.set_notice("已取消按键录入。")
        else:
            super().keyPressEvent(event)

    def closeEvent(self, event):
        if not self.quitting and self.config["minimize_to_tray"] and self.tray.isVisible():
            event.ignore()
            self.hide()
            self.tray.showMessage("anki-grip", self.t("已收进托盘。双击图标重新打开；右键可退出。"),
                                  QSystemTrayIcon.MessageIcon.Information, 2000)
            return
        self.cleanup()
        event.accept()
        QTimer.singleShot(0, QApplication.quit)

    def cleanup(self):
        self.poll_timer.stop()
        if self.pad:
            self.pad.shutdown()
        if self.worker:
            self.worker.stop()
            self.worker.wait(4200)
        self.tray.hide()

    def quit_app(self):
        self.quitting = True
        self.close()
        QApplication.quit()
