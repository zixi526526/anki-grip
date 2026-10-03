"""Original Xbox-proportioned vector diagram; rendering never dispatches actions."""
from __future__ import annotations

from PySide6.QtCore import Qt, QRectF, QPointF, QSize
from PySide6.QtGui import QColor, QPainter, QPainterPath, QPen, QFont, QLinearGradient, QRadialGradient, QPolygonF
from PySide6.QtWidgets import QWidget, QSizePolicy

from .i18n import translate
from .model import LABELS, STICK_GUARDS, StickDirections


class ControllerView(QWidget):
    WIDTH, HEIGHT = 520, 430
    FACE = {"Y": (397, 140, "#ebc65b"), "X": (363, 174, "#75b7ee"),
            "B": (431, 174, "#ef8980"), "A": (397, 208, "#96d28e")}

    def __init__(self, compact=False):
        super().__init__()
        self.compact = compact
        self.setMinimumHeight(235 if compact else 300)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.language = "zh_CN"
        self.down: set[str] = set()
        self.axes = (0, 0, 0, 0)
        self.triggers = (0, 0)
        self.connected = False
        self._sample = None
        self.setAccessibleName("Xbox controller")

    def sizeHint(self):
        return QSize(310, 256) if self.compact else QSize(600, 496)

    def set_language(self, language):
        self.language = language
        self.refresh_accessibility()
        self.update()

    def set_snapshot(self, snapshot):
        down = frozenset(snapshot.down) if snapshot else frozenset()
        axes = tuple(getattr(snapshot, key, 0) for key in ("lx", "ly", "rx", "ry"))
        triggers = tuple(getattr(snapshot, key, 0) for key in ("lt", "rt"))
        sample = (snapshot is not None, down, axes, triggers)
        if sample == self._sample:
            return
        self._sample = sample
        self.connected, self.down, self.axes, self.triggers = sample
        self.refresh_accessibility()
        self.update()

    def refresh_accessibility(self):
        pressed = ", ".join(translate(LABELS.get(key, key), self.language)
                            for key in sorted(self.down - STICK_GUARDS))
        self.setAccessibleDescription(pressed or translate(
            "等待按键" if self.connected else "未连接手柄", self.language))

    @staticmethod
    def axis_fraction(value):
        return max(-1.0, min(1.0, value / (32768 if value < 0 else 32767)))

    @staticmethod
    def shell_path():
        # Broad shoulders, a deeper face and tapering grips. The body is about
        # 1.5:1, independent of the widget's aspect ratio. All geometry is original.
        path = QPainterPath()
        path.moveTo(152, 74)
        path.cubicTo(127, 70, 112, 73, 95, 86)
        path.cubicTo(69, 105, 60, 146, 45, 192)
        path.cubicTo(28, 247, 19, 310, 27, 346)
        path.cubicTo(32, 367, 48, 379, 66, 373)
        path.cubicTo(88, 365, 109, 330, 140, 299)
        path.cubicTo(154, 284, 167, 279, 188, 279)
        path.lineTo(332, 279)
        path.cubicTo(353, 279, 366, 284, 380, 299)
        path.cubicTo(411, 330, 432, 365, 454, 373)
        path.cubicTo(472, 379, 488, 367, 493, 346)
        path.cubicTo(501, 310, 492, 247, 475, 192)
        path.cubicTo(460, 146, 451, 105, 425, 86)
        path.cubicTo(408, 73, 393, 70, 368, 74)
        path.cubicTo(317, 71, 203, 71, 152, 74)
        path.closeSubpath()
        return path

    def paintEvent(self, _event):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        scale = min(self.width() / self.WIDTH, self.height() / self.HEIGHT)
        p.translate((self.width() - self.WIDTH * scale) / 2,
                    (self.height() - self.HEIGHT * scale) / 2)
        p.scale(scale, scale)
        p.setFont(QFont("Segoe UI", 12, QFont.Weight.Bold))

        # Rear triggers meet the shoulder line instead of floating above it.
        for key, x, value in (("LT", 106, self.triggers[0]), ("RT", 333, self.triggers[1])):
            trigger = QPainterPath()
            trigger.moveTo(x, 70)
            trigger.lineTo(x + 7, 35)
            trigger.cubicTo(x + 9, 25, x + 59, 23, x + 70, 31)
            trigger.lineTo(x + 81, 74)
            trigger.closeSubpath()
            self.control_shape(p, key, trigger)
            p.setPen(QColor("#e7f3e9" if key not in self.down else "#173724"))
            p.drawText(QRectF(x + 5, 27, 68, 25), Qt.AlignmentFlag.AlignCenter, key)
            p.setPen(Qt.PenStyle.NoPen)
            p.setBrush(QColor("#142a21"))
            p.drawRoundedRect(QRectF(x + 11, 55, 59, 5), 2, 2)
            p.setBrush(QColor("#d4fa91"))
            p.drawRoundedRect(QRectF(x + 11, 55, 59 * max(0, min(255, value)) / 255, 5), 2, 2)

        shell = self.shell_path()
        gradient = QLinearGradient(260, 74, 260, 375)
        gradient.setColorAt(0, QColor("#53625a"))
        gradient.setColorAt(.48, QColor("#36473e"))
        gradient.setColorAt(1, QColor("#24352d"))
        p.setPen(QPen(QColor("#76887a"), 1.8))
        p.setBrush(gradient)
        p.drawPath(shell)

        # Subtle seams give the tapered handles their own surface.
        for right in (False, True):
            seam = QPainterPath()
            seam.moveTo(75, 227)
            seam.cubicTo(59, 265, 50, 315, 54, 351)
            p.save()
            if right:
                p.translate(self.WIDTH, 0)
                p.scale(-1, 1)
            p.setPen(QPen(QColor("#647e6b"), 1))
            p.setBrush(Qt.BrushStyle.NoBrush)
            p.drawPath(seam)
            p.restore()

        for key, right in (("LB", False), ("RB", True)):
            p.save()
            if right:
                p.translate(self.WIDTH, 0)
                p.scale(-1, 1)
            shoulder = QPainterPath()
            shoulder.moveTo(97, 69)
            shoulder.cubicTo(119, 58, 167, 57, 202, 63)
            shoulder.lineTo(202, 78)
            shoulder.cubicTo(166, 73, 123, 75, 94, 91)
            shoulder.closeSubpath()
            self.control_shape(p, key, shoulder)
            p.restore()
            p.setPen(QColor("#173724" if key in self.down else "#dcecdf"))
            p.drawText(QRectF(124 if not right else 330, 59, 66, 24), Qt.AlignmentFlag.AlignCenter, key)

        # Passive Guide / Share marks describe the hardware, not bindable inputs.
        p.setPen(QPen(QColor("#88998b"), 1.3))
        p.setBrush(QColor("#27382f"))
        p.drawEllipse(QPointF(260, 115), 17, 17)
        p.drawRoundedRect(QRectF(249, 207, 22, 17), 6, 6)
        p.drawLine(QPointF(260, 219), QPointF(260, 212))
        p.drawLine(QPointF(257, 215), QPointF(260, 212))
        p.drawLine(QPointF(260, 212), QPointF(263, 215))

        self.button(p, "VIEW", QRectF(213, 163, 26, 26), "▣", circle=True)
        self.button(p, "MENU", QRectF(281, 163, 26, 26), "≡", circle=True)
        for key, (x, y, color) in self.FACE.items():
            self.button(p, key, QRectF(x - 16, y - 16, 32, 32), key, color, circle=True)
        self.stick(p, "LSTICK", "L3", 120, 168, *self.axes[:2])
        self.stick(p, "RSTICK", "R3", 332, 244, *self.axes[2:])
        self.dpad(p, 188, 244)

        p.setFont(QFont("Segoe UI", 9))
        p.setPen(QColor("#bbcec0"))
        for x, text in ((206, "View"), (274, "Menu")):
            p.drawText(QRectF(x, 188, 40, 18), Qt.AlignmentFlag.AlignCenter, text)

        p.setFont(QFont("Segoe UI", 11))
        p.setPen(QColor("#9db6ad" if self.compact else "#526f61"))
        hint = "按下手柄，查看实时响应" if self.connected else "未连接手柄"
        p.drawText(QRectF(0, 400, self.WIDTH, 24), Qt.AlignmentFlag.AlignCenter,
                   translate(hint, self.language))
        p.end()

    def control_shape(self, painter, key, shape):
        active = key in self.down
        painter.setPen(QPen(QColor("#e8ffc4" if active else "#1e3025"), 1.5))
        painter.setBrush(QColor("#d4fa91" if active else "#40594a"))
        painter.drawPath(shape)

    def button(self, painter, key, rect, text, color="#d7e8db", circle=False):
        active = key in self.down
        gradient = QRadialGradient(rect.center() - QPointF(3, 5), rect.width())
        gradient.setColorAt(0, QColor("#d4fa91" if active else "#495b50"))
        gradient.setColorAt(1, QColor("#a4d66e" if active else "#1b2b22"))
        painter.setPen(QPen(QColor("#e8ffc4" if active else "#17271d"), 2))
        painter.setBrush(gradient)
        if circle:
            painter.drawEllipse(rect)
        else:
            painter.drawRoundedRect(rect, 7, 7)
        painter.setPen(QColor("#173724" if active else color))
        painter.drawText(rect, Qt.AlignmentFlag.AlignCenter, text)

    def stick(self, painter, prefix, click, x, y, raw_x, raw_y):
        painter.setPen(QPen(QColor("#617969"), 2))
        painter.setBrush(QColor("#15281d"))
        painter.drawEllipse(QPointF(x, y), 38, 38)
        if not self.compact:
            # Square boundaries match the model's max-axis thresholds.
            for threshold, style in ((StickDirections.ENTER, Qt.PenStyle.SolidLine),
                                      (StickDirections.CENTER, Qt.PenStyle.DashLine)):
                radius = 36 * threshold / 32768
                painter.setPen(QPen(QColor("#8aa38e"), 1, style))
                painter.setBrush(Qt.BrushStyle.NoBrush)
                painter.drawRect(QRectF(x - radius, y - radius, radius * 2, radius * 2))
        for suffix, angle, dx, dy in (("UP", 90, 0, -1), ("DOWN", 270, 0, 1),
                                      ("LEFT", 180, -1, 0), ("RIGHT", 0, 1, 0)):
            active = prefix + "_" + suffix in self.down
            painter.setPen(QPen(QColor("#d4fa91" if active else "#647d6b"), 3 if active else 1.5))
            painter.drawArc(QRectF(x - 44, y - 44, 88, 88), (angle - 25) * 16, 50 * 16)
            center = QPointF(x + dx * 43, y + dy * 43)
            # Small directional ticks belong to the ring instead of detached buttons.
            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(QColor("#d4fa91" if active else "#88a38e"))
            if dx:
                points = (center + QPointF(dx * 4, 0), center + QPointF(-dx * 3, -3), center + QPointF(-dx * 3, 3))
            else:
                points = (center + QPointF(0, dy * 4), center + QPointF(-3, -dy * 3), center + QPointF(3, -dy * 3))
            painter.drawPolygon(QPolygonF(list(points)))
        offset_x = self.axis_fraction(raw_x) * 14
        offset_y = -self.axis_fraction(raw_y) * 14
        self.button(painter, click, QRectF(x + offset_x - 23, y + offset_y - 23, 46, 46),
                    click, "#c4d9c7", circle=True)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QColor("#f1ffe3"))
        painter.drawEllipse(QPointF(x + self.axis_fraction(raw_x) * 34,
                                   y - self.axis_fraction(raw_y) * 34), 2.5, 2.5)

    def dpad(self, painter, x, y):
        painter.setPen(QPen(QColor("#607a68"), 2))
        painter.setBrush(QColor("#15261c"))
        painter.drawEllipse(QPointF(x, y), 37, 37)
        painter.setPen(QPen(QColor("#263c2c"), 1))
        for key, angle in (("DPAD_UP", 0), ("DPAD_RIGHT", 90),
                            ("DPAD_DOWN", 180), ("DPAD_LEFT", 270)):
            painter.save()
            painter.translate(x, y)
            painter.rotate(angle)
            active = key in self.down
            painter.setBrush(QColor("#d4fa91" if active else "#4d6954"))
            painter.setPen(QPen(QColor("#bfe58f" if active else "#263c2c"), 1))
            painter.drawPolygon(QPolygonF([QPointF(-11, -32), QPointF(11, -32),
                                           QPointF(11, -11), QPointF(0, 0), QPointF(-11, -11)]))
            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(QColor("#173724" if active else "#c6dbca"))
            painter.drawPolygon(QPolygonF([QPointF(0, -26), QPointF(-4, -20), QPointF(4, -20)]))
            painter.restore()
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QColor("#49624f"))
        painter.drawRect(QRectF(x - 9, y - 9, 18, 18))
