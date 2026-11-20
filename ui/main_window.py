import sys
from pathlib import Path
from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QStackedWidget, QSystemTrayIcon, QMenu,
    QApplication, QMessageBox, QFrame, QButtonGroup
)
from PyQt6.QtCore import Qt, QPoint, pyqtSlot
from PyQt6.QtGui import QIcon, QPixmap

from core.config import ConfigManager
from core.process_manager import ProcessManager
from core.installer import InstallWorker
from ui.theme import MODERN_DARK_THEME
from ui.tabs.home_tab import HomeTab
from ui.tabs.settings_tab import SettingsTab
from ui.tabs.console_tab import ConsoleTab


class CustomTitleBar(QWidget):
    def __init__(self, parent_window):
        super().__init__(parent_window)
        self.win = parent_window
        self.setObjectName("TitleBar")
        self.setFixedHeight(40)
        self._drag_pos = None

        layout = QHBoxLayout(self)
        layout.setContentsMargins(12, 0, 8, 0)
        layout.setSpacing(8)

        # App Icon
        icon_path = Path(__file__).resolve().parent.parent / "assets" / "icon.png"
        if icon_path.exists():
            lbl_icon = QLabel(self)
            pix = QPixmap(str(icon_path)).scaled(20, 20, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
            lbl_icon.setPixmap(pix)
            layout.addWidget(lbl_icon)

        # Title Label
        lbl_title = QLabel("ZOMBOID DAY LAUNCHER", self)
        lbl_title.setObjectName("TitleLabel")
        layout.addWidget(lbl_title)

        layout.addStretch()

        # Window Buttons
        btn_min = QPushButton("🗕", self)
        btn_min.setObjectName("TitleButton")
        btn_min.clicked.connect(self.win.showMinimized)
        layout.addWidget(btn_min)

        self.btn_max = QPushButton("🗖", self)
        self.btn_max.setObjectName("TitleButton")
        self.btn_max.clicked.connect(self._toggle_maximize)
        layout.addWidget(self.btn_max)

        btn_close = QPushButton("✕", self)
        btn_close.setObjectName("TitleButton")
        btn_close.setProperty("class", "CloseButton")
        btn_close.clicked.connect(self.win.close)
        layout.addWidget(btn_close)

    def _toggle_maximize(self):
        if self.win.isMaximized():
            self.win.showNormal()
            self.btn_max.setText("🗖")
        else:
            self.win.showMaximized()
            self.btn_max.setText("🗗")

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self._drag_pos = event.globalPosition().toPoint() - self.win.frameGeometry().topLeft()
            event.accept()

    def mouseMoveEvent(self, event):
        if self._drag_pos is not None and event.buttons() == Qt.MouseButton.LeftButton:
            if not self.win.isMaximized():
                self.win.move(event.globalPosition().toPoint() - self._drag_pos)
                event.accept()

    def mouseReleaseEvent(self, event):
        self._drag_pos = None


class MainWindow(QMainWindow):
    def __init__(self, config_manager: ConfigManager):
        super().__init__()
        self.config = config_manager
        self.proc_mgr = ProcessManager(self.config)
        self.install_worker = None

        self.setWindowTitle("Zomboid Day Launcher")
        self.setMinimumSize(960, 680)
        self.resize(1020, 720)

        # Frameless window
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.Window)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, False)

        # Set App Icon
        icon_path = Path(self.config.base_dir) / "assets" / "icon.png"
        if icon_path.exists():
            self.app_icon = QIcon(str(icon_path))
            self.setWindowIcon(self.app_icon)
        else:
            self.app_icon = QIcon()

        self.setStyleSheet(MODERN_DARK_THEME)

        self._setup_ui()
        self._setup_system_tray()

    def _setup_ui(self):
        central_widget = QWidget(self)
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # 1. Custom Title Bar
        self.title_bar = CustomTitleBar(self)
        main_layout.addWidget(self.title_bar)

        # 2. Top Navigation Bar
        nav_bar = QWidget(self)
        nav_bar.setObjectName("NavBar")
        nav_layout = QHBoxLayout(nav_bar)
        nav_layout.setContentsMargins(18, 6, 18, 6)
        nav_layout.setSpacing(10)

        self.btn_group = QButtonGroup(self)
        self.btn_group.setExclusive(True)

        self.btn_tab_home = QPushButton("🎮 Головна", nav_bar)
        self.btn_tab_home.setProperty("class", "NavTab")
        self.btn_tab_home.setCheckable(True)
        self.btn_tab_home.setChecked(True)
        self.btn_group.addButton(self.btn_tab_home, 0)
        nav_layout.addWidget(self.btn_tab_home)

        self.btn_tab_settings = QPushButton("⚙ Налаштування", nav_bar)
        self.btn_tab_settings.setProperty("class", "NavTab")
        self.btn_tab_settings.setCheckable(True)
        self.btn_group.addButton(self.btn_tab_settings, 1)
        nav_layout.addWidget(self.btn_tab_settings)

        self.btn_tab_console = QPushButton("📟 Консоль", nav_bar)
        self.btn_tab_console.setProperty("class", "NavTab")
        self.btn_tab_console.setCheckable(True)
        self.btn_group.addButton(self.btn_tab_console, 2)
        nav_layout.addWidget(self.btn_tab_console)

        nav_layout.addStretch()

        main_layout.addWidget(nav_bar)

        # 3. Stacked Pages
        self.stack = QStackedWidget(self)

        self.tab_home = HomeTab(self.config, self.proc_mgr, self)
        self.tab_settings = SettingsTab(self.config, self)
        self.tab_console = ConsoleTab(self.config, self.proc_mgr, self)

        self.stack.addWidget(self.tab_home)
        self.stack.addWidget(self.tab_settings)
        self.stack.addWidget(self.tab_console)

        main_layout.addWidget(self.stack)

        # Connect Navigation
        self.btn_group.idClicked.connect(self._on_tab_changed)

        # Connect Home Tab Actions
        self.tab_home.sig_install_clicked.connect(self._handle_install)
        self.tab_home.sig_start_clicked.connect(self._handle_start)

        # Connect Settings Tab Signals
        self.tab_settings.sig_settings_saved.connect(self._handle_settings_saved)
        self.tab_settings.sig_hero_image_changed.connect(self.tab_home.hero.set_image)

    def _on_tab_changed(self, tab_id: int):
        self.stack.setCurrentIndex(tab_id)
        if tab_id == 0:
            self.tab_home.refresh_status()

    def _setup_system_tray(self):
        """Setup Windows System Tray icon, menu and notifications."""
        self.tray_icon = QSystemTrayIcon(self)
        if not self.app_icon.isNull():
            self.tray_icon.setIcon(self.app_icon)
        self.tray_icon.setToolTip("Zomboid Day Launcher")

        # Context Menu
        menu = QMenu()
        menu.setStyleSheet("""
            QMenu {
                background-color: #111726;
                color: #f1f5f9;
                border: 1px solid #1e293b;
                border-radius: 6px;
                padding: 6px;
            }
            QMenu::item:selected {
                background-color: #1e293b;
                color: #38bdf8;
            }
        """)

        act_show = menu.addAction("🎮 Показати лаунчер")
        act_show.triggered.connect(self._restore_from_tray)

        act_console = menu.addAction("📟 Відкрити консоль")
        act_console.triggered.connect(lambda: (self._restore_from_tray(), self.btn_tab_console.click()))

        menu.addSeparator()

        act_start = menu.addAction("▶ Запустити гру")
        act_start.triggered.connect(lambda: self._handle_start(False))

        act_debug = menu.addAction("⚙ Дебаг запуск")
        act_debug.triggered.connect(lambda: self._handle_start(True))

        menu.addSeparator()

        act_exit = menu.addAction("🚪 Вийти з лаунчера (процес гри триватиме)")
        act_exit.triggered.connect(QApplication.instance().quit)

        self.tray_icon.setContextMenu(menu)
        self.tray_icon.activated.connect(self._on_tray_activated)
        self.tray_icon.show()

    def _on_tray_activated(self, reason):
        if reason in (QSystemTrayIcon.ActivationReason.Trigger, QSystemTrayIcon.ActivationReason.DoubleClick):
            self._restore_from_tray()

    def _restore_from_tray(self):
        self.showNormal()
        self.activateWindow()
        self.raise_()

    def _handle_install(self):
        """Trigger background installation worker."""
        if self.install_worker and self.install_worker.isRunning():
            QMessageBox.information(self, "Інформація", "Процес встановлення вже виконується!")
            return

        self.tab_home.btn_install.setEnabled(False)
        self.tab_home.show_progress(5, "Підготовка до встановлення...")

        self.install_worker = InstallWorker(self.config, self)
        self.install_worker.sig_progress.connect(self.tab_home.show_progress)
        self.install_worker.sig_log.connect(self.tab_console.append_log)
        self.install_worker.sig_finished.connect(self._on_install_finished)
        self.install_worker.start()

    def _on_install_finished(self, success: bool, message: str):
        self.tab_home.btn_install.setEnabled(True)
        self.tab_home.hide_progress()
        self.tab_home.refresh_status()

        if success:
            QMessageBox.information(self, "Встановлення завершено", message)
        else:
            QMessageBox.critical(self, "Помилка встановлення", message)

    def _handle_start(self, is_debug: bool):
        """Launch the game via ProcessManager detached."""
        scan_before = self.config.get("scan_modguard_before_launch", False)
        success = self.proc_mgr.launch_game(is_debug=is_debug, run_security_scan=scan_before)

        if success:
            self.tab_home.refresh_status()

            # Check if hide to tray is requested
            if self.config.hide_to_tray_on_start:
                self.hide()
                mode = "Дебаг" if is_debug else "Стандартний"
                self.tray_icon.showMessage(
                    "Project Zomboid запущено!",
                    f"{mode} запуск гри виконано. Лаунчер згорнуто в трей.\nНатисніть на іконку для повернення.",
                    QSystemTrayIcon.MessageIcon.Information,
                    4000
                )
        else:
            QMessageBox.critical(self, "Помилка запуску", "Не вдалося запустити гру. Перевірте вкладку Консоль для деталей.")

    def _handle_settings_saved(self):
        self.tab_home.refresh_status()

    def closeEvent(self, event):
        """
        When closing, inform user that game process keeps running,
        or minimize to tray if game is active.
        """
        if self.proc_mgr.is_game_running():
            reply = QMessageBox.question(
                self,
                "Закриття лаунчера",
                "Project Zomboid наразі запущено у фоні.\n"
                "При закритті лаунчера гра та її консоль ПРОДОВЖАТЬ ПРАЦЮВАТИ без зупинки.\n\n"
                "Згорнути в системний трей замість виходу?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No | QMessageBox.StandardButton.Cancel
            )
            if reply == QMessageBox.StandardButton.Yes:
                self.hide()
                event.ignore()
                return
            elif reply == QMessageBox.StandardButton.Cancel:
                event.ignore()
                return

        event.accept()
