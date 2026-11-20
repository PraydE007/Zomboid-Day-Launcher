"""
Home Tab — Clean hero layout with top-anchored title & top-aligned background image.
Features a stylish, dynamic game title with 3D drop shadow, crystal clear transparent
text overlays (no murky dark boxes), and stable non-breaking buttons.
"""
from pathlib import Path
from typing import Optional

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QProgressBar, QSizePolicy, QGraphicsDropShadowEffect
)
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import (
    QPixmap, QPainter, QLinearGradient, QColor, QBrush,
    QPainterPath
)

from core.version_checker import VersionChecker


class HeroBannerWidget(QWidget):
    """
    Background image widget anchored strictly to top edge (y=0).
    Pre-renders and caches scaled pixmap on resize to ensure 60+ FPS butter-smooth rendering.
    Keeps background artwork clear and vibrant with only a soft bottom fade for action buttons.
    """
    def __init__(self, image_path: str, parent=None):
        super().__init__(parent)
        self.image_path = image_path
        self.source_pixmap: Optional[QPixmap] = None
        self._cached_pixmap: Optional[QPixmap] = None
        self._load_image()
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)

    def _load_image(self):
        if self.image_path and Path(self.image_path).exists():
            self.source_pixmap = QPixmap(self.image_path)
        else:
            self.source_pixmap = None
        self._update_cache()

    def set_image(self, new_path: str):
        self.image_path = new_path
        self._load_image()
        self.update()

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self._update_cache()

    def _update_cache(self):
        w = self.width()
        h = self.height()
        if w <= 0 or h <= 0 or not self.source_pixmap or self.source_pixmap.isNull():
            self._cached_pixmap = None
            return

        # Scale once on resize (NOT in paintEvent)
        scaled = self.source_pixmap.scaled(
            self.size(),
            Qt.AspectRatioMode.KeepAspectRatioByExpanding,
            Qt.TransformationMode.SmoothTransformation,
        )
        crop_x = max(0, (scaled.width() - w) // 2)
        crop_y = 0  # Anchor strictly to top edge
        self._cached_pixmap = scaled.copy(crop_x, crop_y, w, h)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
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

        # Draw cached pre-scaled pixmap (instantaneous, 0ms latency)
        if self._cached_pixmap and not self._cached_pixmap.isNull():
            painter.drawPixmap(0, 0, self._cached_pixmap)
        else:
            painter.fillRect(rect, QColor("#121212"))

        # --- FADES & GRADIENTS ---
        # 1. Subtle top seam fade (only 35px to smoothly connect with nav bar)
        top_grad = QLinearGradient(0, 0, 0, min(35.0, h * 0.1))
        top_grad.setColorAt(0.0, QColor(21, 21, 21, 140))
        top_grad.setColorAt(1.0, QColor(21, 21, 21, 0))
        painter.fillRect(rect, QBrush(top_grad))

        # 2. Smooth bottom cinematic fade (only at lower 40% where buttons live)
        bottom_grad = QLinearGradient(0, h * 0.55, 0, h)
        bottom_grad.setColorAt(0.0, QColor(18, 18, 18, 0))
        bottom_grad.setColorAt(0.60, QColor(18, 18, 18, 160))
        bottom_grad.setColorAt(0.90, QColor(18, 18, 18, 240))
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
        overlay.setContentsMargins(40, 28, 40, 32)
        overlay.setSpacing(0)

        # ==============================================================
        # 1. TOP-ANCHORED SECTION: Dynamic Styled Title & Version Badge
        # ==============================================================
        self.lbl_title = QLabel(self.hero)
        self.lbl_title.setText(
            '<span style="font-family:\'Freckle Face\',sans-serif; font-size:50px; color:#22c55e; font-weight:900;">ZOMBOID DAY PROJECT</span>'
        )
        self.lbl_title.setStyleSheet("background: transparent; padding: 0; margin: 0;")
        
        # 3D Drop shadow for AAA title effect (no background box required)
        title_shadow = QGraphicsDropShadowEffect(self.lbl_title)
        title_shadow.setBlurRadius(24)
        title_shadow.setColor(QColor(0, 0, 0, 240))
        title_shadow.setOffset(0, 3)
        self.lbl_title.setGraphicsEffect(title_shadow)
        overlay.addWidget(self.lbl_title)

        overlay.addSpacing(6)

        # Subtitle / Tagline
        self.lbl_subtitle = QLabel("SURVIVAL CLIENT & MODPACK • BUILD 42+", self.hero)
        self.lbl_subtitle.setStyleSheet("""
            color: #d4d4d4;
            font-family: 'Segoe UI', -apple-system, sans-serif;
            font-size: 11px;
            font-weight: 700;
            letter-spacing: 1.5px;
            background: transparent;
        """)
        sub_shadow = QGraphicsDropShadowEffect(self.lbl_subtitle)
        sub_shadow.setBlurRadius(16)
        sub_shadow.setColor(QColor(0, 0, 0, 220))
        sub_shadow.setOffset(0, 2)
        self.lbl_subtitle.setGraphicsEffect(sub_shadow)
        overlay.addWidget(self.lbl_subtitle)

        overlay.addSpacing(12)

        # Version Pill Badge (clean glass style with no dark box)
        self.badge_version = QLabel("Перевірка версії...", self.hero)
        self.badge_version.setFixedHeight(24)
        self.badge_version.setSizePolicy(QSizePolicy.Policy.Maximum, QSizePolicy.Policy.Fixed)
        self.badge_version.setStyleSheet("""
            background-color: rgba(0, 0, 0, 0.40);
            color: #22c55e;
            border: 1px solid rgba(255, 255, 255, 0.15);
            border-radius: 12px;
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
        self.btn_install.setMinimumHeight(48)
        self.btn_install.setMinimumWidth(200)
        self.btn_install.clicked.connect(self.sig_install_clicked.emit)
        btn_row.addWidget(self.btn_install)

        # Play Button
        self.btn_start = QPushButton("ГРАТИ", self.hero)
        self.btn_start.setProperty("class", "PrimaryButton")
        self.btn_start.setMinimumHeight(48)
        self.btn_start.setMinimumWidth(200)
        self.btn_start.clicked.connect(lambda: self.sig_start_clicked.emit(False))
        btn_row.addWidget(self.btn_start)

        # Debug Button
        self.btn_debug_start = QPushButton("DEBUG", self.hero)
        self.btn_debug_start.setProperty("class", "DebugButton")
        self.btn_debug_start.setMinimumHeight(48)
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
        ver = str(status.get("version", "")).strip().lstrip("v")

        # Format cleanly: "Актуальна • v1.0.0"
        if is_installed and ver and ver not in ["—", "Не встановлено", "Помилка"]:
            badge_text = f"{text} • v{ver}"
        else:
            badge_text = text

        self.badge_version.setText(badge_text)
        self.badge_version.setStyleSheet(f"""
            background-color: rgba(0, 0, 0, 0.40);
            color: {color};
            border: 1px solid {color};
            border-radius: 12px;
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
