"""
Home Tab — Clean hero layout with top-anchored title & top-aligned background image.
Features a stylish, dynamic game title with 3D drop shadow, crystal clear transparent
text overlays, stable non-breaking buttons, DEBUG MODE, a refresh button with icon,
system detection/verification, and a bottom-right language selector.
"""
from pathlib import Path
from typing import Optional

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QProgressBar, QSizePolicy, QGraphicsDropShadowEffect, QComboBox
)
from PyQt6.QtCore import Qt, pyqtSignal, QTimer, QPointF
from PyQt6.QtGui import (
    QPixmap, QPainter, QLinearGradient, QRadialGradient, QColor, QBrush,
    QPainterPath, QFont
)

from core.version_checker import VersionChecker
from core.detector import SystemDetector
from core.i18n import t, get_available_locales, set_locale
from ui.dialogs.diagnostics_dialog import DiagnosticsDialog
from ui.widgets.spinner import LoadingSpinner


class HeroBannerWidget(QWidget):
    """
    Background image widget anchored strictly to top edge (y=0).
    Pre-renders and caches scaled pixmap on resize to ensure 60+ FPS butter-smooth rendering.
    Overlays a subtle micro-dot halftone matrix matching mriyu.com/bio/prayde007 (.bio-fx-dots).
    Keeps background artwork clear and vibrant with only a soft bottom fade for action buttons.
    """
    def __init__(self, image_path: str, parent=None):
        super().__init__(parent)
        self.image_path = image_path
        self.source_pixmap: Optional[QPixmap] = None
        self._cached_pixmap: Optional[QPixmap] = None
        self._dot_brush: QBrush = self._create_dot_grid_brush()
        self._load_image()
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)

    @staticmethod
    def _create_dot_grid_brush() -> QBrush:
        """
        Creates a high-performance tiled texture brush matching the exact
        .bio-fx-dots pattern from mriyu.com/bio/prayde007:
        radial-gradient(#0009 1.3px, #0000 1.8px) with background-size: 6px 6px.
        """
        cell_size = 6
        radius = 1.3
        pix = QPixmap(cell_size, cell_size)
        pix.fill(Qt.GlobalColor.transparent)
        p = QPainter(pix)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        p.setPen(Qt.PenStyle.NoPen)
        grad = QRadialGradient(cell_size / 2.0, cell_size / 2.0, radius * 1.35)
        # #0009 in CSS is rgba(0, 0, 0, 0.56) ~= alpha 145-160
        grad.setColorAt(0.0, QColor(0, 0, 0, 160))
        grad.setColorAt(0.72, QColor(0, 0, 0, 135))
        grad.setColorAt(1.0, QColor(0, 0, 0, 0))
        p.setBrush(QBrush(grad))
        p.drawEllipse(QPointF(cell_size / 2.0, cell_size / 2.0), radius * 1.35, radius * 1.35)
        p.end()
        return QBrush(pix)

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
        # Inset by 1px at the bottom and right to stay strictly inside MainShell's 1px border (#262626)
        # Prevents 1px background image bleed/overhang at the bottom-left seam and bottom edge
        w = float(rect.width()) - 1.0
        h = float(rect.height()) - 1.0

        # Clip bottom-right corner to match window shell inner border-radius (13px)
        clip_path = QPainterPath()
        clip_path.moveTo(0, 0)
        clip_path.lineTo(w, 0)
        clip_path.lineTo(w, max(0.0, h - 13.0))
        clip_path.quadTo(w, h, max(0.0, w - 13.0), h)
        clip_path.lineTo(0, h)
        clip_path.lineTo(0, 0)
        clip_path.closeSubpath()
        painter.setClipPath(clip_path)

        # Draw cached pre-scaled pixmap (instantaneous, 0ms latency)
        if self._cached_pixmap and not self._cached_pixmap.isNull():
            painter.drawPixmap(0, 0, self._cached_pixmap)
        else:
            painter.fillRect(rect, QColor("#121212"))

        # --- DOT GRID OVERLAY (mriyu.com .bio-fx-dots pattern) ---
        painter.fillRect(rect, self._dot_brush)

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


class StyledTitleWidget(QWidget):
    """
    Renders the game title with 3D drop shadow and dual-color typography:
    'ZOMBOID DAY' prominent in toxic green (#22c55e, size 46),
    and ONLY 'PROJECT' in smaller crisp white (#ffffff, size 24).
    Subtitle removed per user request for clean foreground legibility.
    """
    def __init__(self, subtitle_text: str = "", parent=None):
        super().__init__(parent)
        self.subtitle_text = ""
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, True)
        self.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Fixed)
        self.setFixedHeight(80)

    def set_subtitle(self, text: str):
        pass  # Subtitle tagline removed per user request

    def setText(self, text: str):
        pass

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setRenderHint(QPainter.RenderHint.TextAntialiasing)

        # 1. Main Title: 'ZOMBOID DAY' (large size 46)
        font_main = QFont("Freckle Face", 46)
        font_main.setWeight(QFont.Weight.Black)

        # 2. Only 'PROJECT' is smaller (size 24)
        font_proj = QFont("Freckle Face", 24)
        font_proj.setWeight(QFont.Weight.Black)

        painter.setFont(font_main)
        fm_main = painter.fontMetrics()

        part1 = "ZOMBOID DAY "
        part2 = "PROJECT"
        w1 = fm_main.horizontalAdvance(part1)

        base_y = fm_main.ascent() + 2

        # Deep 3D Drop Shadows
        shadow_layers = [
            (0, 4, QColor(0, 0, 0, 160)),
            (1, 3, QColor(0, 0, 0, 200)),
            (0, 2, QColor(0, 0, 0, 240)),
            (0, 1, QColor(0, 0, 0, 255)),
        ]
        for dx, dy, col in shadow_layers:
            painter.setPen(col)
            painter.setFont(font_main)
            painter.drawText(dx, base_y + dy, part1)
            painter.setFont(font_proj)
            painter.drawText(w1 + dx, base_y + dy, part2)

        # Part 1: ZOMBOID DAY — Large Toxic Green (#22c55e)
        painter.setFont(font_main)
        painter.setPen(QColor("#22c55e"))
        painter.drawText(0, base_y, part1)

        # Part 2: PROJECT — Smaller Pure White (#ffffff)
        painter.setFont(font_proj)
        painter.setPen(QColor("#ffffff"))
        painter.drawText(w1, base_y, part2)


# Button Styles for Main Actions (Explicit QSS ensures 100% reliable background fill in Qt6)
STYLE_PLAY_READY = """
QPushButton#btn_start {
    background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #22c55e, stop:1 #16a34a);
    color: #ffffff;
    border: 1px solid #15803d;
    border-radius: 6px;
    font-family: 'Segoe UI', -apple-system, sans-serif;
    font-size: 15px;
    font-weight: 800;
    padding: 12px 30px;
    text-align: center;
}
QPushButton#btn_start:hover {
    background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #4ade80, stop:1 #22c55e);
    border-color: #4ade80;
}
QPushButton#btn_start:pressed {
    background: #15803d;
}
"""

STYLE_PLAY_FIX = """
QPushButton#btn_start {
    background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #ef4444, stop:1 #dc2626);
    color: #ffffff;
    border: 1px solid #b91c1c;
    border-radius: 6px;
    font-family: 'Segoe UI', -apple-system, sans-serif;
    font-size: 15px;
    font-weight: 900;
    letter-spacing: 1px;
    padding: 12px 30px;
    text-align: center;
}
QPushButton#btn_start:hover {
    background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #f87171, stop:1 #ef4444);
    border-color: #f87171;
}
QPushButton#btn_start:pressed {
    background: #b91c1c;
}
"""

STYLE_DEBUG_BTN = """
QPushButton#btn_debug_start {
    background-color: rgba(30, 30, 30, 0.90);
    color: #e4e4e7;
    border: 1px solid #444444;
    border-radius: 6px;
    font-family: 'Segoe UI', -apple-system, sans-serif;
    font-size: 13px;
    font-weight: 700;
    padding: 12px 24px;
    text-align: center;
}
QPushButton#btn_debug_start:hover {
    color: #ffffff;
    border-color: #666666;
    background-color: rgba(50, 50, 50, 0.95);
}
QPushButton#btn_debug_start:pressed {
    background-color: #181818;
}
QPushButton#btn_debug_start:disabled {
    background-color: rgba(20, 20, 20, 0.50);
    color: #52525b;
    border-color: #27272a;
}
"""

STYLE_REFRESH_BTN = """
QPushButton#btn_refresh {
    background-color: rgba(30, 30, 30, 0.90);
    color: #22c55e;
    border: 1px solid #383838;
    border-radius: 6px;
    font-size: 18px;
    font-weight: 800;
}
QPushButton#btn_refresh:hover {
    color: #ffffff;
    border-color: #22c55e;
    background-color: rgba(34, 197, 94, 0.20);
}
QPushButton#btn_refresh:pressed {
    background-color: rgba(34, 197, 94, 0.35);
}
"""


class HomeTab(QWidget):
    sig_install_clicked = pyqtSignal()
    sig_start_clicked = pyqtSignal(bool)   # True = debug
    sig_open_settings = pyqtSignal()
    sig_language_changed = pyqtSignal(str)

    def __init__(self, config_manager, process_manager, parent=None):
        super().__init__(parent)
        self.config = config_manager
        self.proc_mgr = process_manager
        self.version_checker = VersionChecker(self.config)
        self.detector = SystemDetector(self.config)
        self.last_diag = None
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
        overlay.setContentsMargins(40, 26, 40, 30)
        overlay.setSpacing(0)

        # ==============================================================
        # 1. TOP-ANCHORED SECTION: Dynamic Styled Title & Diagnostics
        # ==============================================================
        lang = self.config.language
        self.lbl_title = StyledTitleWidget(t("subtitle", lang), self.hero)
        self.lbl_subtitle = self.lbl_title
        overlay.addWidget(self.lbl_title)

        overlay.addSpacing(6)

        # Warning banner if launcher is not lying next to ProjectZomboid64.exe
        self.banner_loc = QLabel(self.hero)
        self.banner_loc.setObjectName("WarningBanner")
        self.banner_loc.setText(t("banner_launcher_not_in_game", lang))
        self.banner_loc.setWordWrap(True)
        self.banner_loc.setVisible(False)
        overlay.addWidget(self.banner_loc)

        overlay.addSpacing(8)

        # Status & Diagnostics Row
        badge_row = QHBoxLayout()
        badge_row.setSpacing(10)

        # Version Pill Badge (100% solid opaque fill)
        self.badge_version = QLabel(t("checking_version", lang), self.hero)
        self.badge_version.setObjectName("badge_version")
        self.badge_version.setFixedHeight(24)
        self.badge_version.setSizePolicy(QSizePolicy.Policy.Maximum, QSizePolicy.Policy.Fixed)
        self.badge_version.setStyleSheet("""
            QLabel#badge_version {
                background-color: #141414;
                color: #22c55e;
                border: 1px solid #22c55e;
                border-radius: 12px;
                padding: 2px 14px;
                font-family: 'Segoe UI', -apple-system, sans-serif;
                font-size: 11px;
                font-weight: 700;
            }
        """)
        badge_row.addWidget(self.badge_version)

        # Quick Diagnostics Action Pill (100% solid opaque fill)
        self.btn_diag = QPushButton(f"🔍 {t('view_diagnostics', lang)}", self.hero)
        self.btn_diag.setObjectName("btn_diag")
        self.btn_diag.setFixedHeight(24)
        self.btn_diag.setStyleSheet("""
            QPushButton#btn_diag {
                background-color: #141414;
                color: #e4e4e7;
                border: 1px solid #383838;
                border-radius: 12px;
                padding: 2px 14px;
                font-family: 'Segoe UI', -apple-system, sans-serif;
                font-size: 11px;
                font-weight: 600;
            }
            QPushButton#btn_diag:hover {
                background-color: #262626;
                color: #ffffff;
                border-color: #525252;
            }
            QPushButton#btn_diag:pressed {
                background-color: #0d0d0d;
            }
        """)
        self.btn_diag.clicked.connect(self._open_diagnostics)
        badge_row.addWidget(self.btn_diag)

        badge_row.addStretch()
        overlay.addLayout(badge_row)

        # ==============================================================
        # STRETCH pushes action buttons to the bottom
        # ==============================================================
        overlay.addStretch()

        # ==============================================================
        # LAUNCH SPINNER & STATUS NOTIFICATION (Active during launch / scan)
        # ==============================================================
        self.launch_container = QWidget(self.hero)
        self.launch_container.setObjectName("LaunchContainer")
        self.launch_container.setVisible(False)
        self.launch_container.setStyleSheet("""
            #LaunchContainer {
                background-color: #141414;
                border: 1px solid #22c55e;
                border-radius: 12px;
            }
        """)
        launch_layout = QHBoxLayout(self.launch_container)
        launch_layout.setContentsMargins(14, 10, 14, 10)
        launch_layout.setSpacing(14)

        self.spinner = LoadingSpinner(size=34, parent=self.launch_container)
        launch_layout.addWidget(self.spinner)

        lbl_box = QVBoxLayout()
        lbl_box.setSpacing(2)
        self.lbl_launch_title = QLabel(t("launching_game", lang), self.launch_container)
        self.lbl_launch_title.setStyleSheet("color: #22c55e; font-size: 13px; font-weight: 700; background: transparent;")
        lbl_box.addWidget(self.lbl_launch_title)

        self.lbl_launch_desc = QLabel("", self.launch_container)
        self.lbl_launch_desc.setStyleSheet("color: #9ca3af; font-size: 11px; font-weight: 500; background: transparent;")
        lbl_box.addWidget(self.lbl_launch_desc)

        launch_layout.addLayout(lbl_box)
        launch_layout.addStretch()

        overlay.addWidget(self.launch_container)
        overlay.addSpacing(6)

        # ==============================================================
        # 2. BOTTOM-ANCHORED SECTION: Action buttons & Language Selector
        # ==============================================================
        btn_row = QHBoxLayout()
        btn_row.setSpacing(10)

        # Install Button
        self.btn_install = QPushButton(t("btn_install", lang), self.hero)
        self.btn_install.setProperty("class", "PrimaryButton")
        self.btn_install.setMinimumHeight(48)
        self.btn_install.setMinimumWidth(180)
        self.btn_install.clicked.connect(self.sig_install_clicked.emit)
        btn_row.addWidget(self.btn_install)

        # Play / Fix Button (Green = PLAY, Red = FIX)
        self.can_play = False
        self.btn_start = QPushButton(t("btn_play", lang), self.hero)
        self.btn_start.setObjectName("btn_start")
        self.btn_start.setStyleSheet(STYLE_PLAY_READY)
        self.btn_start.setMinimumHeight(48)
        self.btn_start.setMinimumWidth(180)
        self.btn_start.clicked.connect(self._handle_main_action_clicked)
        btn_row.addWidget(self.btn_start)

        # Debug Mode Button (Renamed to DEBUG MODE)
        self.btn_debug_start = QPushButton(t("btn_debug", lang), self.hero)
        self.btn_debug_start.setObjectName("btn_debug_start")
        self.btn_debug_start.setStyleSheet(STYLE_DEBUG_BTN)
        self.btn_debug_start.setMinimumHeight(48)
        self.btn_debug_start.setMinimumWidth(130)
        self.btn_debug_start.clicked.connect(lambda: self.sig_start_clicked.emit(True))
        btn_row.addWidget(self.btn_debug_start)

        # Refresh Button with Icon right after DEBUG MODE
        self.btn_refresh = QPushButton("⟳", self.hero)
        self.btn_refresh.setObjectName("btn_refresh")
        self.btn_refresh.setStyleSheet(STYLE_REFRESH_BTN)
        self.btn_refresh.setFixedSize(48, 48)
        self.btn_refresh.setToolTip(t("btn_refresh_tooltip", lang))
        self.btn_refresh.clicked.connect(self._handle_manual_refresh)
        btn_row.addWidget(self.btn_refresh)

        btn_row.addStretch()

        # Language Selector at bottom right
        self.combo_lang = QComboBox(self.hero)
        self.combo_lang.setObjectName("LangSelector")
        self.combo_lang.setMinimumHeight(42)
        self.combo_lang.setMinimumWidth(115)
        for code, display_name in get_available_locales():
            self.combo_lang.addItem(display_name, code)

        # Default is English ("en") if not already saved
        idx = self.combo_lang.findData(self.config.language)
        if idx >= 0:
            self.combo_lang.setCurrentIndex(idx)
        else:
            self.combo_lang.setCurrentIndex(0)

        self.combo_lang.currentIndexChanged.connect(self._on_lang_changed)
        btn_row.addWidget(self.combo_lang)

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

    def _on_lang_changed(self):
        new_lang = self.combo_lang.currentData()
        if new_lang and new_lang != self.config.language:
            self.config.language = new_lang
            set_locale(new_lang)
            self.sig_language_changed.emit(new_lang)
            self.retranslate_ui()

    def _handle_manual_refresh(self):
        """User clicked refresh button: animate icon, re-run diagnostics & update status."""
        self.btn_refresh.setText("⏳")
        self.refresh_status()
        QTimer.singleShot(350, lambda: self.btn_refresh.setText("⟳"))

    def _handle_main_action_clicked(self):
        if getattr(self, "can_play", False):
            self.sig_start_clicked.emit(False)
        else:
            lang = self.config.language
            status = self.version_checker.check_status(lang)
            if status.get("status") == "INVALID_PLACEMENT":
                self._open_diagnostics()
            elif not status.get("is_installed"):
                self.sig_install_clicked.emit()
            else:
                self.sig_install_clicked.emit()

    def _open_diagnostics(self):
        dlg = DiagnosticsDialog(self.detector, self.config, self.config.language, self.window())
        dlg.exec()
        self.refresh_status()

    def retranslate_ui(self):
        lang = self.config.language
        self.lbl_subtitle.setText(t("subtitle", lang))
        self.btn_install.setText(t("btn_install", lang))
        if getattr(self, "can_play", False):
            self.btn_start.setText(t("btn_play", lang))
            self.btn_start.setStyleSheet(STYLE_PLAY_READY)
        else:
            self.btn_start.setText("FIX")
            self.btn_start.setStyleSheet(STYLE_PLAY_FIX)
        self.btn_debug_start.setText(t("btn_debug", lang))
        self.btn_refresh.setToolTip(t("btn_refresh_tooltip", lang))
        self.btn_diag.setText(f"🔍 {t('view_diagnostics', lang)}")
        self.banner_loc.setText(t("banner_launcher_not_in_game", lang))
        self.refresh_status()

    def refresh_status(self):
        lang = self.config.language
        status = self.version_checker.check_status(lang)
        self.last_diag = self.detector.run_diagnostics(lang)

        is_invalid_placement = (status.get("status") == "INVALID_PLACEMENT") or (not self.last_diag["launcher_beside_game"])

        # 1. Launcher Location Warning Banner
        if is_invalid_placement:
            self.banner_loc.setText(t("banner_launch_prohibited", lang))
            self.banner_loc.setProperty("status", "danger")
            self.banner_loc.style().unpolish(self.banner_loc)
            self.banner_loc.style().polish(self.banner_loc)
            self.banner_loc.setVisible(True)
        else:
            self.banner_loc.setProperty("status", "normal")
            self.banner_loc.style().unpolish(self.banner_loc)
            self.banner_loc.style().polish(self.banner_loc)
            self.banner_loc.setVisible(False)

        # 2. Version badge & status
        is_installed = status["is_installed"]
        is_update = (status.get("status") == "UPDATE_AVAILABLE")
        color = status["color"]
        text = status["text"]
        ver = str(status.get("version", "")).strip().lstrip("v")

        # Format cleanly: "Up to date • v1.0.1" or "Update • v1.0.0 → v1.0.1"
        if is_installed and ver and ver != "—":
            badge_text = f"{text} • v{ver}"
        else:
            badge_text = text

        self.badge_version.setText(badge_text)
        self.badge_version.setStyleSheet(f"""
            QLabel#badge_version {{
                background-color: #141414;
                color: {color};
                border: 1px solid {color};
                border-radius: 12px;
                padding: 2px 14px;
                font-family: 'Segoe UI', -apple-system, sans-serif;
                font-size: 11px;
                font-weight: 700;
            }}
        """)

        # 3. Main Action Button: Green PLAY if ready, Red FIX if not ready
        self.can_play = is_installed and (not is_invalid_placement) and (not is_update)

        if self.can_play:
            self.btn_start.setText(t("btn_play", lang))
            self.btn_start.setStyleSheet(STYLE_PLAY_READY)
            self.btn_start.setProperty("status", "ready")
            self.btn_start.setToolTip("")
            self.btn_debug_start.setEnabled(True)
            self.btn_debug_start.setToolTip("")
        else:
            self.btn_start.setText(t("btn_fix", lang))
            self.btn_start.setStyleSheet(STYLE_PLAY_FIX)
            self.btn_start.setProperty("status", "fix")
            if is_invalid_placement:
                self.btn_start.setToolTip(t("banner_launcher_not_in_game", lang))
            elif is_update:
                self.btn_start.setToolTip(f"{t('status_update_available', lang)} • {t('tip_click_fix_to_update', lang)}")
            else:
                self.btn_start.setToolTip(t("btn_install", lang))
            self.btn_debug_start.setEnabled(False)
            self.btn_debug_start.setToolTip(t("err_launch_prohibited_tooltip", lang))

        self.btn_start.setVisible(True)
        self.btn_start.setEnabled(True)
        self.btn_install.setVisible(False)
        self.btn_debug_start.setVisible(True)

    def show_progress(self, percentage: int, message: str):
        self.progress_bar.setVisible(True)
        self.lbl_progress_status.setVisible(True)
        self.progress_bar.setValue(percentage)
        self.lbl_progress_status.setText(message)

    def hide_progress(self):
        self.progress_bar.setVisible(False)
        self.lbl_progress_status.setVisible(False)

    def show_launch_spinner(self, title: str, subtitle: str = ""):
        self.lbl_launch_title.setText(title)
        self.lbl_launch_desc.setText(subtitle)
        self.lbl_launch_desc.setVisible(bool(subtitle))
        self.launch_container.setVisible(True)
        self.spinner.start()

        # Disable buttons while launching/scanning
        self.btn_start.setEnabled(False)
        self.btn_debug_start.setEnabled(False)
        self.btn_install.setEnabled(False)
        self.btn_refresh.setEnabled(False)

    def set_launch_spinner_text(self, title: str, subtitle: str = ""):
        self.lbl_launch_title.setText(title)
        self.lbl_launch_desc.setText(subtitle)
        self.lbl_launch_desc.setVisible(bool(subtitle))

    def hide_launch_spinner(self):
        self.spinner.stop()
        self.launch_container.setVisible(False)
        self.refresh_status()
