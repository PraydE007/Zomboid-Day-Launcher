"""
Home Tab — Clean hero layout with top-anchored title & top-aligned background image.
Features text logo 'Zomboid Day Project' using 'Freckle Face' font, cinematic fades,
and bottom-anchored actions.
"""
from pathlib import Path
from typing import Optional

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QProgressBar, QSizePolicy, QGraphicsOpacityEffect
)
from PyQt6.QtCore import Qt, pyqtSignal, QPropertyAnimation, QEasingCurve
from PyQt6.QtGui import (
    QPixmap, QPainter, QLinearGradient, QColor, QBrush, QFont,
    QPainterPath
)

from core.version_checker import VersionChecker
from core.utils import get_resource_path


class HeroBannerWidget(QWidget):
    """
    Background image widget anchored to top edge (y=0) with smooth cinematic fades
    and bottom rounded corner clipping to fit the rounded window shell.
    """
    def __init__(self, image_path: str, parent=None):
        super().__init__(parent)
        self.image_path = image_path
        self.pixmap: Optional[QPixmap] = None
        self._load_image()
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)

    def _load_image(self):
        if self.image_path and Path(self.image_path).exists():
            self.pixmap = QPixmap(self.image_path)
        else:
            self.pixmap = None

    def set_image(self, new_path: str):
        self.image_path = new_path
        self._load_image()
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)
        rect = self.rect()
        w = float(rect.width())
        h = float(rect.height())

        # Clip bottom corners to match window shell border-radius (14px)
        clip_path = QPainterPath()
        clip_path.moveTo(0, 0)
        clip_path.lineTo(w, 0)
        clip_path.lineTo(w, max(0.0, h - 14.0))
        clip_path.quadTo(w, h, max(0.0, w - 14.0), h)
        clip_path.lineTo(14.0, h)
        clip_path.quadTo(0, h, 0, max(0.0, h - 14.0))
        clip_path.closeSubpath()
        painter.setClipPath(clip_path)

        # Draw background image glued to the top edge (y = 0)
        if self.pixmap and not self.pixmap.isNull():
            scaled = self.pixmap.scaled(
                rect.size(),
                Qt.AspectRatioMode.KeepAspectRatioByExpanding,
                Qt.TransformationMode.SmoothTransformation,
            )
            # Center horizontally, glue to top edge vertically (y = 0)
            x = (scaled.width() - rect.width()) // 2
            y = 0
            painter.drawPixmap(0, 0, scaled, x, y, rect.width(), rect.height())
        else:
            painter.fillRect(rect, QColor("#121212"))

        # --- FADES & GRADIENTS ---
        # 1. Subtle top fade (blends seamlessly from the nav bar)
        top_grad = QLinearGradient(0, 0, 0, min(140.0, h * 0.3))
        top_grad.setColorAt(0.0, QColor(18, 18, 18, 160))
        top_grad.setColorAt(0.5, QColor(18, 18, 18, 70))
        top_grad.setColorAt(1.0, QColor(18, 18, 18, 0))
        painter.fillRect(rect, QBrush(top_grad))

        # 2. Left side horizontal vignette for crisp text readability
        left_grad = QLinearGradient(0, 0, min(650.0, w * 0.75), 0)
        left_grad.setColorAt(0.0, QColor(14, 14, 14, 190))
        left_grad.setColorAt(0.55, QColor(14, 14, 14, 90))
        left_grad.setColorAt(1.0, QColor(14, 14, 14, 0))
        painter.fillRect(rect, QBrush(left_grad))

        # 3. Bottom cinematic fade into solid dark background for controls
        bottom_grad = QLinearGradient(0, h * 0.35, 0, h)
        bottom_grad.setColorAt(0.0, QColor(18, 18, 18, 0))
        bottom_grad.setColorAt(0.55, QColor(18, 18, 18, 160))
        bottom_grad.setColorAt(0.85, QColor(18, 18, 18, 235))
        bottom_grad.setColorAt(1.0, QColor(18, 18, 18, 255))
        painter.fillRect(rect, QBrush(bottom_grad))


class HomeTab(QWidget):
    sig_install_clicked = pyqtSignal()
    sig_start_clicked = pyqtSignal(bool)   # True = debug
    sig_open_settings = pyqtSignal()

    def __init__(self, config_manager, process_manager, parent=None):
        super().__init__(parent)
        self.config = config_manager
        self.proc_mgr = process_manager
        self.version_checker = VersionChecker(self.config)
        self._setup_ui()
        self.refresh_status()

    def _setup_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        # Hero banner fills entire tab
        self.hero = HeroBannerWidget(self.config.hero_image, self)

        # Overlay layout: top-anchored header, bottom-anchored actions
        overlay = QVBoxLayout(self.hero)
        overlay.setContentsMargins(40, 32, 40, 36)
        overlay.setSpacing(0)

        # ==============================================================
        # 1. TOP-ANCHORED SECTION: Text logo & version status
        # ==============================================================
        self.lbl_title = QLabel("Zomboid Day Project", self.hero)
        self.lbl_title.setStyleSheet("""
            color: #ffffff;
            font-family: 'Freckle Face', sans-serif;
            font-size: 48px;
            letter-spacing: 1.5px;
            background: transparent;
            padding: 0px;
            margin: 0px;
        """)
        overlay.addWidget(self.lbl_title)

        overlay.addSpacing(10)

        # Version Pill Badge (subtle neutral dark with green/amber indicator)
        self.badge_version = QLabel("Перевірка версії...", self.hero)
        self.badge_version.setFixedHeight(26)
        self.badge_version.setSizePolicy(QSizePolicy.Policy.Maximum, QSizePolicy.Policy.Fixed)
        self.badge_version.setStyleSheet("""
            background-color: rgba(20, 20, 20, 0.85);
            color: #a3a3a3;
            border: 1px solid #333333;
            border-radius: 13px;
            padding: 2px 14px;
            font-size: 11px;
            font-weight: 600;
        """)
        overlay.addWidget(self.badge_version)

        # ==============================================================
        # STRETCH pushes action buttons to the bottom
        # ==============================================================
        overlay.addStretch()

        # ==============================================================
        # 2. BOTTOM-ANCHORED SECTION: Action buttons & progress
        # ==============================================================
        btn_row = QHBoxLayout()
        btn_row.setSpacing(12)

        # Install Button
        self.btn_install = QPushButton("ВСТАНОВИТИ", self.hero)
        self.btn_install.setProperty("class", "PrimaryButton")
        self.btn_install.setMinimumHeight(52)
        self.btn_install.setMinimumWidth(220)
        self.btn_install.clicked.connect(self.sig_install_clicked.emit)
        btn_row.addWidget(self.btn_install)

        # Play Button
        self.btn_start = QPushButton("ГРАТИ", self.hero)
        self.btn_start.setProperty("class", "PrimaryButton")
        self.btn_start.setMinimumHeight(52)
        self.btn_start.setMinimumWidth(220)
        self.btn_start.clicked.connect(lambda: self.sig_start_clicked.emit(False))
        btn_row.addWidget(self.btn_start)

        # Debug Button
        self.btn_debug_start = QPushButton("Debug", self.hero)
        self.btn_debug_start.setProperty("class", "DebugButton")
        self.btn_debug_start.setMinimumHeight(52)
        self.btn_debug_start.setMinimumWidth(110)
        self.btn_debug_start.clicked.connect(lambda: self.sig_start_clicked.emit(True))
        btn_row.addWidget(self.btn_debug_start)

        btn_row.addStretch()
        overlay.addLayout(btn_row)

        overlay.addSpacing(10)

        # Progress bar (only visible during install)
        self.progress_bar = QProgressBar(self.hero)
        self.progress_bar.setVisible(False)
        self.progress_bar.setValue(0)
        self.progress_bar.setFixedHeight(12)
        overlay.addWidget(self.progress_bar)

        self.lbl_progress_status = QLabel("", self.hero)
        self.lbl_progress_status.setStyleSheet(
            "color: #22c55e; font-size: 11px; font-weight: 600; background: transparent; margin-top: 4px;"
        )
        self.lbl_progress_status.setVisible(False)
        overlay.addWidget(self.lbl_progress_status)

        root.addWidget(self.hero)

    def refresh_status(self):
        status = self.version_checker.check_status()
        is_installed = status["is_installed"]
        color = status["color"]
        text = status["text"]
        ver = status["version"]

        self.badge_version.setText(f"{text}  v{ver}")
        self.badge_version.setStyleSheet(f"""
            background-color: rgba(18, 18, 18, 0.88);
            color: {color};
            border: 1px solid {color};
            border-radius: 13px;
            padding: 2px 14px;
            font-size: 11px;
            font-weight: 600;
        """)

        if not is_installed:
            self.btn_install.setVisible(True)
            self.btn_start.setVisible(False)
            self.btn_debug_start.setVisible(False)
        else:
            self.btn_install.setVisible(False)
            self.btn_start.setVisible(True)
            self.btn_debug_start.setVisible(True)

    def show_progress(self, percentage: int, message: str):
        self.progress_bar.setVisible(True)
        self.lbl_progress_status.setVisible(True)
        self.progress_bar.setValue(percentage)
        self.lbl_progress_status.setText(message)

    def hide_progress(self):
        self.progress_bar.setVisible(False)
        self.lbl_progress_status.setVisible(False)
