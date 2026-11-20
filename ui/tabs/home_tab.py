"""
Home Tab — Cinematic hero-first layout.
Giant background image, logo overlay, single action button, minimal chrome.
"""
import os
import subprocess
from pathlib import Path
from typing import Optional

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QProgressBar, QSizePolicy, QMessageBox, QGraphicsOpacityEffect
)
from PyQt6.QtCore import Qt, pyqtSignal, QSize, QPropertyAnimation, QEasingCurve
from PyQt6.QtGui import QPixmap, QPainter, QLinearGradient, QColor, QBrush, QFont

from core.version_checker import VersionChecker, VersionStatus
from core.utils import get_resource_path


class HeroBannerWidget(QWidget):
    """Full-bleed background image that stretches to fill."""
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
        painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)
        rect = self.rect()

        if self.pixmap and not self.pixmap.isNull():
            scaled = self.pixmap.scaled(
                rect.size(),
                Qt.AspectRatioMode.KeepAspectRatioByExpanding,
                Qt.TransformationMode.SmoothTransformation,
            )
            x = (scaled.width() - rect.width()) // 2
            y = (scaled.height() - rect.height()) // 2
            painter.drawPixmap(0, 0, scaled, x, y, rect.width(), rect.height())
        else:
            painter.fillRect(rect, QColor("#0a0e17"))

        # Heavy bottom vignette so text is always readable
        grad = QLinearGradient(0, 0, 0, rect.height())
        grad.setColorAt(0.00, QColor(10, 14, 23, 0))
        grad.setColorAt(0.35, QColor(10, 14, 23, 30))
        grad.setColorAt(0.65, QColor(10, 14, 23, 160))
        grad.setColorAt(1.00, QColor(10, 14, 23, 245))
        painter.fillRect(rect, QBrush(grad))


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

    # ------------------------------------------------------------------ UI
    def _setup_ui(self):
        # The whole tab is one big stack: hero behind, content on top
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        # Hero occupies all available space
        self.hero = HeroBannerWidget(self.config.hero_image, self)

        # Overlay layout pinned to bottom of hero
        overlay = QVBoxLayout(self.hero)
        overlay.setContentsMargins(36, 24, 36, 32)
        overlay.setSpacing(0)

        overlay.addStretch()

        # ---- Logo
        logo_path = get_resource_path("assets/text-logo.png")
        if logo_path.exists():
            self.lbl_logo = QLabel(self.hero)
            pix = QPixmap(str(logo_path))
            scaled_logo = pix.scaledToHeight(56, Qt.TransformationMode.SmoothTransformation)
            self.lbl_logo.setPixmap(scaled_logo)
            self.lbl_logo.setStyleSheet("background:transparent;")
            overlay.addWidget(self.lbl_logo)
        else:
            lbl_title = QLabel("ZOMBOID DAY", self.hero)
            lbl_title.setStyleSheet(
                "color:#fff; font-family:'Freckle Face','Segoe UI',sans-serif;"
                "font-size:36px; font-weight:900; background:transparent;"
            )
            overlay.addWidget(lbl_title)

        overlay.addSpacing(6)

        # ---- Version pill
        self.badge_version = QLabel("Перевірка...", self.hero)
        self.badge_version.setFixedHeight(24)
        self.badge_version.setSizePolicy(QSizePolicy.Policy.Maximum, QSizePolicy.Policy.Fixed)
        self.badge_version.setStyleSheet(
            "background:rgba(10,14,23,0.7); color:#64748b; border:1px solid #1e293b;"
            "border-radius:12px; padding:2px 14px; font-size:11px; font-weight:600;"
        )
        overlay.addWidget(self.badge_version)

        overlay.addSpacing(20)

        # ---- Action buttons row
        btn_row = QHBoxLayout()
        btn_row.setSpacing(12)

        self.btn_install = QPushButton("ВСТАНОВИТИ", self.hero)
        self.btn_install.setProperty("class", "PrimaryButton")
        self.btn_install.setMinimumHeight(50)
        self.btn_install.setMinimumWidth(220)
        self.btn_install.clicked.connect(self.sig_install_clicked.emit)
        btn_row.addWidget(self.btn_install)

        self.btn_start = QPushButton("ГРАТИ", self.hero)
        self.btn_start.setProperty("class", "PrimaryButton")
        self.btn_start.setMinimumHeight(50)
        self.btn_start.setMinimumWidth(220)
        self.btn_start.clicked.connect(lambda: self.sig_start_clicked.emit(False))
        btn_row.addWidget(self.btn_start)

        self.btn_debug_start = QPushButton("Debug", self.hero)
        self.btn_debug_start.setProperty("class", "DebugButton")
        self.btn_debug_start.setMinimumHeight(50)
        self.btn_debug_start.setMinimumWidth(100)
        self.btn_debug_start.clicked.connect(lambda: self.sig_start_clicked.emit(True))
        btn_row.addWidget(self.btn_debug_start)

        btn_row.addStretch()
        overlay.addLayout(btn_row)

        overlay.addSpacing(8)

        # ---- Progress (hidden by default)
        self.progress_bar = QProgressBar(self.hero)
        self.progress_bar.setVisible(False)
        self.progress_bar.setValue(0)
        self.progress_bar.setFixedHeight(14)
        overlay.addWidget(self.progress_bar)

        self.lbl_progress_status = QLabel("", self.hero)
        self.lbl_progress_status.setStyleSheet(
            "color:#22c55e; font-size:11px; font-weight:600; background:transparent;"
        )
        self.lbl_progress_status.setVisible(False)
        overlay.addWidget(self.lbl_progress_status)

        root.addWidget(self.hero)

    # ------------------------------------------------------------------ Logic
    def refresh_status(self):
        status = self.version_checker.check_status()
        is_installed = status["is_installed"]
        color = status["color"]
        text = status["text"]
        ver = status["version"]

        self.badge_version.setText(f"{text}  v{ver}")
        self.badge_version.setStyleSheet(
            f"background:rgba(10,14,23,0.7); color:{color}; border:1px solid {color};"
            f"border-radius:12px; padding:2px 14px; font-size:11px; font-weight:600;"
        )

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
