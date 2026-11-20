"""
Main Window — Frameless dark launcher shell with rounded corners and smooth tab fades.
"""
import sys
from pathlib import Path

from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QStackedWidget, QSystemTrayIcon, QMenu,
    QApplication, QMessageBox, QButtonGroup, QGraphicsOpacityEffect
)
from PyQt6.QtCore import Qt, QPoint, QPropertyAnimation, QEasingCurve
from PyQt6.QtGui import QIcon, QPixmap

from core.config import ConfigManager
from core.process_manager import ProcessManager
from core.installer import InstallWorker
from core.utils import get_resource_path
from ui.theme import MODERN_DARK_THEME
from ui.tabs.home_tab import HomeTab
from ui.tabs.settings_tab import SettingsTab
from ui.tabs.console_tab import ConsoleTab


class CustomTitleBar(QWidget):
    def __init__(self, parent_window):
        super().__init__(parent_window)
        self.win = parent_window
        self.setObjectName("TitleBar")
        self.setFixedHeight(38)
        self._drag_pos = None

        layout = QHBoxLayout(self)
        layout.setContentsMargins(14, 0, 0, 0)
        layout.setSpacing(8)

        # App icon
        icon_path = get_resource_path("assets/icon.png")
        if icon_path.exists():
            lbl = QLabel(self)
            pix = QPixmap(str(icon_path)).scaled(
                18, 18, Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation,
            )
            lbl.setPixmap(pix)
            lbl.setStyleSheet("background: transparent;")
            layout.addWidget(lbl)

        # Title text using Freckle Face
        lbl_title = QLabel("ZOMBOID DAY", self)
        lbl_title.setStyleSheet("""
            color: #d4d4d4;
            font-family: 'Freckle Face', sans-serif;
            font-size: 15px;
            letter-spacing: 1px;
            background: transparent;
        """)
        layout.addWidget(lbl_title)

        layout.addStretch()

        # Window controls: Minimize, Maximize, Close
        btn_min = QPushButton("−", self)
        btn_min.setObjectName("TitleButton")
        btn_min.setFixedSize(36, 38)
        btn_min.clicked.connect(self.win.showMinimized)
        layout.addWidget(btn_min)

        self.btn_max = QPushButton("□", self)
        self.btn_max.setObjectName("TitleButton")
        self.btn_max.setFixedSize(36, 38)
        self.btn_max.clicked.connect(self._toggle_maximize)
        layout.addWidget(self.btn_max)

        btn_close = QPushButton("✕", self)
        btn_close.setObjectName("CloseButton")
        btn_close.setFixedSize(40, 38)
        btn_close.clicked.connect(self.win.close)
        layout.addWidget(btn_close)

    def _toggle_maximize(self):
        if self.win.isMaximized():
            self.win.showNormal()
            self.btn_max.setText("□")
        else:
            self.win.showMaximized()
            self.btn_max.setText("❐")

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self._drag_pos = event.globalPosition().toPoint() - self.win.frameGeometry().topLeft()
            event.accept()

    def mouseMoveEvent(self, event):
        if self._drag_pos and event.buttons() == Qt.MouseButton.LeftButton and not self.win.isMaximized():
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
        self.setMinimumSize(960, 640)
        self.resize(1020, 700)

        # Frameless window with transparent background for rounded corners
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.Window)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)

        icon_path = get_resource_path("assets/icon.png")
        self.app_icon = QIcon(str(icon_path)) if icon_path.exists() else QIcon()
        self.setWindowIcon(self.app_icon)

        self.setStyleSheet(MODERN_DARK_THEME)
        self._setup_ui()
        self._setup_system_tray()

    def _setup_ui(self):
        # Outermost container with border-radius (MainShell)
        central = QWidget(self)
        self.setCentralWidget(central)
        outer_layout = QVBoxLayout(central)
        outer_layout.setContentsMargins(0, 0, 0, 0)
        outer_layout.setSpacing(0)

        self.shell = QWidget(central)
        self.shell.setObjectName("MainShell")
        shell_layout = QVBoxLayout(self.shell)
        shell_layout.setContentsMargins(0, 0, 0, 0)
        shell_layout.setSpacing(0)

        # Title bar
        self.title_bar = CustomTitleBar(self)
        shell_layout.addWidget(self.title_bar)

        # Navigation Bar
        nav = QWidget(self.shell)
        nav.setObjectName("NavBar")
        nav_layout = QHBoxLayout(nav)
        nav_layout.setContentsMargins(18, 4, 18, 4)
        nav_layout.setSpacing(6)

        self.btn_group = QButtonGroup(self)
        self.btn_group.setExclusive(True)

        tab_names = ["Головна", "Налаштування", "Консоль"]
        self.nav_buttons = []
        for idx, name in enumerate(tab_names):
            btn = QPushButton(name, nav)
            btn.setProperty("class", "NavTab")
            btn.setCheckable(True)
            if idx == 0:
                btn.setChecked(True)
            self.btn_group.addButton(btn, idx)
            nav_layout.addWidget(btn)
            self.nav_buttons.append(btn)

        nav_layout.addStretch()
        shell_layout.addWidget(nav)

        # Stacked tabs
        self.stack = QStackedWidget(self.shell)
        self.tab_home = HomeTab(self.config, self.proc_mgr, self)
        self.tab_settings = SettingsTab(self.config, self)
        self.tab_console = ConsoleTab(self.config, self.proc_mgr, self)

        self.stack.addWidget(self.tab_home)
        self.stack.addWidget(self.tab_settings)
        self.stack.addWidget(self.tab_console)
        shell_layout.addWidget(self.stack)

        outer_layout.addWidget(self.shell)

        # Signal connections
        self.btn_group.idClicked.connect(self._on_tab_changed)
        self.tab_home.sig_install_clicked.connect(self._handle_install)
        self.tab_home.sig_start_clicked.connect(self._handle_start)
        self.tab_settings.sig_settings_saved.connect(self._handle_settings_saved)
        self.tab_settings.sig_hero_image_changed.connect(self.tab_home.hero.set_image)

    def _on_tab_changed(self, tab_id: int):
        target_widget = self.stack.widget(tab_id)
        self.stack.setCurrentIndex(tab_id)
        if tab_id == 0:
            self.tab_home.refresh_status()

        # Smooth fade-in transition
        self._fade_in_widget(target_widget)

    def _fade_in_widget(self, widget: QWidget):
        effect = QGraphicsOpacityEffect(widget)
        widget.setGraphicsEffect(effect)
        anim = QPropertyAnimation(effect, b"opacity", self)
        anim.setDuration(160)
        anim.setStartValue(0.15)
        anim.setEndValue(1.0)
        anim.setEasingCurve(QEasingCurve.Type.OutCubic)
        anim.start(QPropertyAnimation.DeletionPolicy.DeleteWhenStopped)

    def _setup_system_tray(self):
        self.tray_icon = QSystemTrayIcon(self)
        if not self.app_icon.isNull():
            self.tray_icon.setIcon(self.app_icon)
        self.tray_icon.setToolTip("Zomboid Day Launcher")

        menu = QMenu()
        menu.setStyleSheet("""
            QMenu {
                background-color: #161616;
                color: #e5e5e5;
                border: 1px solid #282828;
                border-radius: 6px;
                padding: 4px;
            }
            QMenu::item {
                padding: 6px 18px;
                border-radius: 4px;
            }
            QMenu::item:selected {
                background: #242424;
                color: #22c55e;
            }
            QMenu::separator {
                height: 1px;
                background: #262626;
                margin: 4px 6px;
            }
        """)

        menu.addAction("Показати лаунчер", self._restore_from_tray)
        menu.addSeparator()
        menu.addAction("Запустити гру", lambda: self._handle_start(False))
        menu.addAction("Debug запуск", lambda: self._handle_start(True))
        menu.addSeparator()
        menu.addAction("Вийти", QApplication.instance().quit)

        self.tray_icon.setContextMenu(menu)
        self.tray_icon.activated.connect(self._on_tray_activated)
        self.tray_icon.show()

    def _on_tray_activated(self, reason):
        if reason in (
            QSystemTrayIcon.ActivationReason.Trigger,
            QSystemTrayIcon.ActivationReason.DoubleClick,
        ):
            self._restore_from_tray()

    def _restore_from_tray(self):
        self.showNormal()
        self.activateWindow()
        self.raise_()

    def _handle_install(self):
        if self.install_worker and self.install_worker.isRunning():
            QMessageBox.information(self, "Інформація", "Встановлення вже виконується.")
            return

        self.tab_home.btn_install.setEnabled(False)
        self.tab_home.show_progress(5, "Підготовка...")

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
            QMessageBox.information(self, "Готово", message)
        else:
            QMessageBox.critical(self, "Помилка", message)

    def _handle_start(self, is_debug: bool):
        scan = self.config.get("scan_modguard_before_launch", False)
        ok = self.proc_mgr.launch_game(is_debug=is_debug, run_security_scan=scan)
        if ok:
            self.tab_home.refresh_status()
            if self.config.hide_to_tray_on_start:
                self.hide()
                mode = "Debug" if is_debug else "Стандартний"
                self.tray_icon.showMessage(
                    "Гру запущено",
                    f"{mode} запуск виконано. Лаунчер згорнуто.",
                    QSystemTrayIcon.MessageIcon.Information, 3000,
                )
        else:
            QMessageBox.critical(self, "Помилка", "Не вдалося запустити гру.")

    def _handle_settings_saved(self):
        self.tab_home.refresh_status()

    def closeEvent(self, event):
        if self.proc_mgr.is_game_running():
            reply = QMessageBox.question(
                self, "Закриття",
                "Гра працює у фоні. Згорнути в трей?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No | QMessageBox.StandardButton.Cancel,
            )
            if reply == QMessageBox.StandardButton.Yes:
                self.hide()
                event.ignore()
                return
            elif reply == QMessageBox.StandardButton.Cancel:
                event.ignore()
                return
        event.accept()
