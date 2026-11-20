import os
import subprocess
from pathlib import Path
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QProgressBar, QFrame, QSizePolicy, QMessageBox
)
from PyQt6.QtCore import Qt, pyqtSignal, QSize
from PyQt6.QtGui import QPixmap, QPainter, QLinearGradient, QColor, QFont, QBrush

from core.version_checker import VersionChecker, VersionStatus
from core.utils import get_resource_path


class HeroBannerWidget(QFrame):
    def __init__(self, image_path: str, parent=None):
        super().__init__(parent)
        self.image_path = image_path
        self.pixmap: Optional[QPixmap] = None
        self._load_image()
        self.setFixedHeight(280)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)

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

        if self.pixmap and not self.pixmap.isNull():
            # Scale pixmap to cover
            scaled = self.pixmap.scaled(
                rect.size(),
                Qt.AspectRatioMode.KeepAspectRatioByExpanding,
                Qt.TransformationMode.SmoothTransformation
            )
            # Center crop
            x = (scaled.width() - rect.width()) // 2
            y = (scaled.height() - rect.height()) // 2
            painter.drawPixmap(0, 0, scaled, x, y, rect.width(), rect.height())
        else:
            painter.fillRect(rect, QColor("#111827"))

        # Vignette / Dark Gradient Overlay
        grad = QLinearGradient(0, 0, 0, rect.height())
        grad.setColorAt(0.0, QColor(11, 15, 25, 60))
        grad.setColorAt(0.5, QColor(11, 15, 25, 180))
        grad.setColorAt(1.0, QColor(11, 15, 25, 250))
        painter.fillRect(rect, QBrush(grad))


class HomeTab(QWidget):
    sig_install_clicked = pyqtSignal()
    sig_start_clicked = pyqtSignal(bool)  # is_debug (True=Debug, False=Standard)
    sig_open_settings = pyqtSignal()

    def __init__(self, config_manager, process_manager, parent=None):
        super().__init__(parent)
        self.config = config_manager
        self.proc_mgr = process_manager
        self.version_checker = VersionChecker(self.config)

        self._setup_ui()
        self.refresh_status()

    def _setup_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(20, 16, 20, 20)
        main_layout.setSpacing(18)

        # 1. Hero Banner with overlaid title & status
        self.hero = HeroBannerWidget(self.config.hero_image, self)
        hero_layout = QVBoxLayout(self.hero)
        hero_layout.setContentsMargins(28, 20, 28, 20)
        hero_layout.setSpacing(8)

        # Top row inside hero: Badge & Quick info
        top_hero_row = QHBoxLayout()
        self.badge_version = QLabel("● Перевірка...", self.hero)
        self.badge_version.setStyleSheet("""
            background-color: rgba(17, 24, 39, 0.85);
            color: #38bdf8;
            border: 1px solid #38bdf8;
            border-radius: 12px;
            padding: 4px 14px;
            font-size: 12px;
            font-weight: 700;
        """)
        top_hero_row.addWidget(self.badge_version)
        top_hero_row.addStretch()

        self.btn_refresh = QPushButton("🔄 Перевірити", self.hero)
        self.btn_refresh.setProperty("class", "SecondaryButton")
        self.btn_refresh.clicked.connect(self.refresh_status)
        top_hero_row.addWidget(self.btn_refresh)
        hero_layout.addLayout(top_hero_row)

        hero_layout.addStretch()

        # Title Logo & Subtitle inside Hero
        logo_path = get_resource_path("assets/text-logo.png")
        if logo_path.exists():
            self.lbl_logo = QLabel(self.hero)
            pix = QPixmap(str(logo_path))
            scaled_logo = pix.scaledToHeight(62, Qt.TransformationMode.SmoothTransformation)
            self.lbl_logo.setPixmap(scaled_logo)
            self.lbl_logo.setStyleSheet("background: transparent; margin-bottom: 4px;")
            hero_layout.addWidget(self.lbl_logo)
        else:
            lbl_game_title = QLabel("PROJECT ZOMBOID: DAY", self.hero)
            lbl_game_title.setStyleSheet("""
                color: #ffffff;
                font-family: 'Freckle Face', 'Segoe UI', sans-serif;
                font-size: 32px;
                font-weight: 900;
                letter-spacing: 1.5px;
                background: transparent;
            """)
            hero_layout.addWidget(lbl_game_title)

        lbl_game_sub = QLabel("Автоматичне оновлення конфігурацій, патчів, безпеки та ZombieBuddy", self.hero)
        lbl_game_sub.setStyleSheet("""
            color: #94a3b8;
            font-size: 13px;
            font-weight: 500;
            background: transparent;
        """)
        hero_layout.addWidget(lbl_game_sub)

        main_layout.addWidget(self.hero)

        # 2. Main Actions Area (Install or Start / Debug Start)
        action_card = QFrame(self)
        action_card.setProperty("class", "GlassCard")
        action_layout = QVBoxLayout(action_card)
        action_layout.setContentsMargins(16, 14, 16, 14)
        action_layout.setSpacing(12)

        # Buttons Row
        self.btn_row_layout = QHBoxLayout()
        self.btn_row_layout.setSpacing(14)

        # Big Install Button
        self.btn_install = QPushButton("📥 ВСТАНОВИТИ ВСЕ", self)
        self.btn_install.setProperty("class", "PrimaryButton")
        self.btn_install.setMinimumHeight(52)
        self.btn_install.clicked.connect(self.sig_install_clicked.emit)
        self.btn_row_layout.addWidget(self.btn_install)

        # Start Button (for installed state)
        self.btn_start = QPushButton("▶ СТАРТ ГРИ", self)
        self.btn_start.setProperty("class", "PrimaryButton")
        self.btn_start.setMinimumHeight(52)
        self.btn_start.clicked.connect(lambda: self.sig_start_clicked.emit(False))
        self.btn_row_layout.addWidget(self.btn_start)

        # Debug Start Button (for installed state)
        self.btn_debug_start = QPushButton("⚙ ДЕБАГ СТАРТ", self)
        self.btn_debug_start.setProperty("class", "DebugButton")
        self.btn_debug_start.setMinimumHeight(52)
        self.btn_debug_start.clicked.connect(lambda: self.sig_start_clicked.emit(True))
        self.btn_row_layout.addWidget(self.btn_debug_start)

        # Extra utility buttons
        self.btn_open_folder = QPushButton("📂 Папка гри", self)
        self.btn_open_folder.setProperty("class", "SecondaryButton")
        self.btn_open_folder.setMinimumHeight(52)
        self.btn_open_folder.clicked.connect(self._open_game_folder)
        self.btn_row_layout.addWidget(self.btn_open_folder)

        action_layout.addLayout(self.btn_row_layout)

        # Progress bar (for installation / download)
        self.progress_bar = QProgressBar(self)
        self.progress_bar.setVisible(False)
        self.progress_bar.setValue(0)
        action_layout.addWidget(self.progress_bar)

        self.lbl_progress_status = QLabel("", self)
        self.lbl_progress_status.setStyleSheet("color: #38bdf8; font-size: 12px; font-weight: 600;")
        self.lbl_progress_status.setVisible(False)
        action_layout.addWidget(self.lbl_progress_status)

        main_layout.addWidget(action_card)

        # 3. Status Info Cards (3 Columns)
        cards_row = QHBoxLayout()
        cards_row.setSpacing(14)

        # Card 1: Version & Integrity
        card1 = QFrame(self)
        card1.setProperty("class", "GlassCard")
        c1_layout = QVBoxLayout(card1)
        c1_layout.setContentsMargins(14, 12, 14, 12)
        lbl_c1_title = QLabel("📌 ВЕРСІЯ ПРОЄКТУ", card1)
        lbl_c1_title.setStyleSheet("color: #94a3b8; font-size: 11px; font-weight: 700; letter-spacing: 0.5px;")
        self.lbl_c1_value = QLabel("—", card1)
        self.lbl_c1_value.setStyleSheet("color: #f8fafc; font-size: 15px; font-weight: 700;")
        self.lbl_c1_sub = QLabel("Перевірка...", card1)
        self.lbl_c1_sub.setStyleSheet("color: #64748b; font-size: 11px;")
        c1_layout.addWidget(lbl_c1_title)
        c1_layout.addWidget(self.lbl_c1_value)
        c1_layout.addWidget(self.lbl_c1_sub)
        cards_row.addWidget(card1)

        # Card 2: Process State
        card2 = QFrame(self)
        card2.setProperty("class", "GlassCard")
        c2_layout = QVBoxLayout(card2)
        c2_layout.setContentsMargins(14, 12, 14, 12)
        lbl_c2_title = QLabel("🎮 СТАН ГРИ", card2)
        lbl_c2_title.setStyleSheet("color: #94a3b8; font-size: 11px; font-weight: 700; letter-spacing: 0.5px;")
        self.lbl_c2_value = QLabel("Готово до запуску", card2)
        self.lbl_c2_value.setStyleSheet("color: #10b981; font-size: 15px; font-weight: 700;")
        self.lbl_c2_sub = QLabel("Процес не запущено", card2)
        self.lbl_c2_sub.setStyleSheet("color: #64748b; font-size: 11px;")
        c2_layout.addWidget(lbl_c2_title)
        c2_layout.addWidget(self.lbl_c2_value)
        c2_layout.addWidget(self.lbl_c2_sub)
        cards_row.addWidget(card2)

        # Card 3: Repositories
        card3 = QFrame(self)
        card3.setProperty("class", "GlassCard")
        c3_layout = QVBoxLayout(card3)
        c3_layout.setContentsMargins(14, 12, 14, 12)
        lbl_c3_title = QLabel("📦 РЕПОЗИТОРІЇ", card3)
        lbl_c3_title.setStyleSheet("color: #94a3b8; font-size: 11px; font-weight: 700; letter-spacing: 0.5px;")
        self.lbl_c3_value = QLabel("2 активні", card3)
        self.lbl_c3_value.setStyleSheet("color: #38bdf8; font-size: 15px; font-weight: 700;")
        self.lbl_c3_sub = QLabel("Zomboid Day Files, PZ-ModGuard", card3)
        self.lbl_c3_sub.setStyleSheet("color: #64748b; font-size: 11px;")
        c3_layout.addWidget(lbl_c3_title)
        c3_layout.addWidget(self.lbl_c3_value)
        c3_layout.addWidget(self.lbl_c3_sub)
        cards_row.addWidget(card3)

        main_layout.addLayout(cards_row)
        main_layout.addStretch()

    def refresh_status(self):
        """Update version status, integrity and button visibility."""
        status = self.version_checker.check_status()
        is_installed = status["is_installed"]
        color = status["color"]
        text = status["text"]
        ver = status["version"]

        # Update Badge in Hero
        self.badge_version.setText(f"● {text}: {ver}")
        self.badge_version.setStyleSheet(f"""
            background-color: rgba(17, 24, 39, 0.85);
            color: {color};
            border: 1px solid {color};
            border-radius: 12px;
            padding: 4px 14px;
            font-size: 12px;
            font-weight: 700;
        """)

        # Update Card 1
        self.lbl_c1_value.setText(f"{ver}")
        self.lbl_c1_value.setStyleSheet(f"color: {color}; font-size: 15px; font-weight: 700;")
        if is_installed:
            last_sync = self.config.get("last_sync_time", "Синхронізовано")
            self.lbl_c1_sub.setText(f"Синхронізовано: {last_sync}")
        else:
            self.lbl_c1_sub.setText("Файли не налаштовано або відсутні")

        # Update Card 2 (Process state)
        if self.proc_mgr.is_game_running():
            pid = self.proc_mgr.current_pid
            self.lbl_c2_value.setText("Гра працює")
            self.lbl_c2_value.setStyleSheet("color: #38bdf8; font-size: 15px; font-weight: 700;")
            self.lbl_c2_sub.setText(f"PID: {pid} (активний процес)")
        else:
            if is_installed:
                self.lbl_c2_value.setText("Готово до запуску")
                self.lbl_c2_value.setStyleSheet("color: #10b981; font-size: 15px; font-weight: 700;")
                self.lbl_c2_sub.setText("Очікує старту")
            else:
                self.lbl_c2_value.setText("Потрібно встановити")
                self.lbl_c2_value.setStyleSheet("color: #ef4444; font-size: 15px; font-weight: 700;")
                self.lbl_c2_sub.setText("Натисніть кнопку Встановити")

        # Update Card 3 (Repositories count)
        repos = self.config.repositories
        active_repos = [r for r in repos if r.get("enabled", True)]
        self.lbl_c3_value.setText(f"{len(active_repos)} активні (з {len(repos)})")
        names = ", ".join([r.get("name", "").split("(")[0].strip() for r in active_repos])
        self.lbl_c3_sub.setText(names if names else "Немає активних")

        # Switch Buttons visibility:
        # If not installed or update available:
        if not is_installed:
            self.btn_install.setVisible(True)
            self.btn_install.setText("📥 ВСТАНОВИТИ ВСЕ")
            self.btn_start.setVisible(False)
            self.btn_debug_start.setVisible(False)
        else:
            # Installed
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

    def _open_game_folder(self):
        game_dir = self.config.game_dir
        if game_dir and Path(game_dir).exists():
            subprocess.Popen(f'explorer.exe "{game_dir}"')
        else:
            QMessageBox.warning(self, "Помилка", f"Папка гри не існує:\n{game_dir}")
