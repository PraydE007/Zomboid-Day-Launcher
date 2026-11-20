"""
Circular Loading Spinner Widget
Modern, smooth animated circular loading indicator for PyQt6.
"""
from PyQt6.QtWidgets import QWidget
from PyQt6.QtCore import Qt, QTimer, QRectF
from PyQt6.QtGui import QPainter, QPen, QColor


class LoadingSpinner(QWidget):
    def __init__(self, size: int = 38, color: QColor = QColor("#22c55e"), pen_width: float = 3.5, parent=None):
        super().__init__(parent)
        self.setFixedSize(size, size)
        self.color = color
        self.pen_width = pen_width
        self._angle = 0
        self._timer = QTimer(self)
        self._timer.timeout.connect(self._rotate)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)

    def _rotate(self):
        self._angle = (self._angle + 14) % 360
        self.update()

    def start(self):
        self._angle = 0
        self._timer.start(20)  # ~50 FPS
        self.show()

    def stop(self):
        self._timer.stop()
        self.hide()

    def is_spinning(self) -> bool:
        return self._timer.isActive()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        w = float(self.width())
        h = float(self.height())
        pad = self.pen_width + 1.0
        rect = QRectF(pad, pad, w - pad * 2.0, h - pad * 2.0)

        # Faint background track ring
        track_pen = QPen(QColor(255, 255, 255, 25), self.pen_width)
        painter.setPen(track_pen)
        painter.drawEllipse(rect)

        # Spinning glowing green arc
        arc_pen = QPen(self.color, self.pen_width)
        arc_pen.setCapStyle(Qt.PenCapStyle.RoundCap)
        painter.setPen(arc_pen)

        start_angle = int(-self._angle * 16)
        span_angle = int(-110 * 16)
        painter.drawArc(rect, start_angle, span_angle)
