"""
Main Window — Frameless dark launcher shell with rounded corners, smooth tab fades,
and dynamic multi-language localization.
"""
import sys
import time
from pathlib import Path

from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QStackedWidget, QSystemTrayIcon, QMenu,
    QApplication, QMessageBox, QButtonGroup, QGraphicsOpacityEffect
)
from PyQt6.QtCore import Qt, QPoint, QPropertyAnimation, QEasingCurve
from PyQt6.QtGui import QIcon, QPixmap, QPainterPath, QRegion

from core.config import ConfigManager
from core.process_manager import (
    ProcessManager, ModGuardScanThread, determine_modguard_scan_profile, compute_modguard_fingerprint
)
from core.version_checker import RemoteUpdateCheckThread
from core.installer import InstallWorker
from core.utils import get_resource_path, get_app_dir
from core.i18n import t
from ui.theme import MODERN_DARK_THEME
from ui.widgets.hotbar import HotbarDock
from ui.tabs.home_tab import HomeTab
from ui.tabs.settings_tab import SettingsTab
from ui.tabs.console_tab import ConsoleTab


class CustomTitleBar(QWidget):
    def __init__(self, parent_window):
        super().__init__(parent_window)
        self.win = parent_window
        self.setObjectName("TitleBar")
        self.setFixedHeight(34)
        self._drag_pos = None

        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # Clean drag strip across the top (no icon, no title text)
        layout.addStretch()

        # Window controls: Minimize, Close
        btn_min = QPushButton("−", self)
        btn_min.setObjectName("TitleButton")
        btn_min.setFixedSize(36, 34)
        btn_min.clicked.connect(self.win.showMinimized)
        layout.addWidget(btn_min)

        btn_close = QPushButton("✕", self)
        btn_close.setObjectName("CloseButton")
        btn_close.setFixedSize(40, 34)
        btn_close.clicked.connect(self.win.close)
        layout.addWidget(btn_close)

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
        self.scan_worker = None

        self.setWindowTitle("Zomboid Day Launcher")
        self.setMinimumSize(960, 640)
        self.resize(1020, 700)

        # Frameless window with transparent background for rounded corners
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.Window)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)

        # Load application icon (prefer .ico with multi-resolution for Windows, fallback to .png)
        self.app_icon = QIcon()
        for icon_name in ("assets/icon.ico", "assets/icon.png"):
            p = get_resource_path(icon_name)
            if p.exists():
                self.app_icon = QIcon(str(p))
                break
        self.setWindowIcon(self.app_icon)

        self.setStyleSheet(MODERN_DARK_THEME)
        self._setup_ui()
        self._setup_system_tray()
        self.retranslate_ui()
        self._log_startup_diagnostics()

    def _log_startup_diagnostics(self):
        diag = self.tab_home.detector.run_diagnostics("en")
        self.tab_console.append_log("══════════════════════════════════════════════════")
        self.tab_console.append_log("   ZOMBOID DAY LAUNCHER — SYSTEM DIAGNOSTICS      ")
        self.tab_console.append_log("══════════════════════════════════════════════════")
        for chk in diag.get("checks", []):
            mark = "[✓]" if chk["status"] == "ok" else ("[⚠]" if chk["status"] == "warn" else "[✗]")
            self.tab_console.append_log(f"{mark} {chk['title']}: {chk['details']}")
        score = f"{diag['passed_count']}/{diag['total_count']} checks passed"
        self.tab_console.append_log(f"Status: {score} | Ready: {diag['is_ready']}")
        self.tab_console.append_log("══════════════════════════════════════════════════")

    def _setup_ui(self):
        # Outermost container with border-radius (MainShell)
        central = QWidget(self)
        central.setObjectName("CentralWidget")
        central.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        self.setCentralWidget(central)
        outer_layout = QVBoxLayout(central)
        outer_layout.setContentsMargins(0, 0, 0, 0)
        outer_layout.setSpacing(0)

        self.shell = QWidget(central)
        self.shell.setObjectName("MainShell")
        shell_layout = QVBoxLayout(self.shell)
        shell_layout.setContentsMargins(0, 0, 0, 0)
        shell_layout.setSpacing(0)

        # Title bar (top-anchored, spans full window width)
        self.title_bar = CustomTitleBar(self)
        shell_layout.addWidget(self.title_bar)

        # Body Container: Left Hotbar Dock + Right Stacked Tabs Area
        self.body_widget = QWidget(self.shell)
        self.body_widget.setObjectName("BodyWidget")
        self.body_widget.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        body_layout = QHBoxLayout(self.body_widget)
        body_layout.setContentsMargins(0, 0, 0, 0)
        body_layout.setSpacing(0)

        # 1. Left Hotbar Dock with beautiful icons
        self.hotbar = HotbarDock(self.config, self.body_widget)
        body_layout.addWidget(self.hotbar)

        # 2. Right Stacked Content Tabs
        self.stack = QStackedWidget(self.body_widget)
        self.stack.setStyleSheet("background: transparent;")
        self.tab_home = HomeTab(self.config, self.proc_mgr, self)
        self.tab_settings = SettingsTab(self.config, self)
        self.tab_console = ConsoleTab(self.config, self.proc_mgr, self)

        self.stack.addWidget(self.tab_home)
        self.stack.addWidget(self.tab_settings)
        self.stack.addWidget(self.tab_console)
        body_layout.addWidget(self.stack)

        shell_layout.addWidget(self.body_widget)

        outer_layout.addWidget(self.shell)

        # Signal connections
        self.hotbar.sig_tab_changed.connect(self._on_tab_changed)
        self.hotbar.sig_diag_clicked.connect(self.tab_home._open_diagnostics)
        self.tab_home.sig_install_clicked.connect(self._handle_install)
        self.tab_home.sig_start_clicked.connect(self._handle_start)
        self.tab_home.sig_language_changed.connect(self._handle_language_changed)
        self.tab_settings.sig_settings_saved.connect(self._handle_settings_saved)
        self.proc_mgr.sig_game_crashed.connect(self._on_game_crashed)
        self.proc_mgr.sig_process_stopped.connect(lambda pid: self.tab_home.refresh_status())

        # Background remote update check (checks GitHub releases and remote manifest silently)
        if self.config.get("auto_check_updates", True):
            self.update_checker_worker = RemoteUpdateCheckThread(self.tab_home.version_checker, parent=self)
            self.update_checker_worker.sig_update_checked.connect(lambda info: self.tab_home.refresh_status())
            self.update_checker_worker.start()

    def _on_tab_changed(self, tab_id: int):
        self.hotbar.set_current_tab(tab_id)
        target_widget = self.stack.widget(tab_id)
        self.stack.setCurrentIndex(tab_id)
        if tab_id == 0:
            self.tab_home.refresh_status()

        # Smooth fade-in transition
        self._fade_in_widget(target_widget)

    def keyPressEvent(self, event):
        # Hotkeys for switching hotbar tabs: Ctrl+1, Ctrl+2, Ctrl+3
        modifiers = event.modifiers()
        if modifiers & Qt.KeyboardModifier.ControlModifier:
            if event.key() == Qt.Key.Key_1:
                self._on_tab_changed(0)
                return
            elif event.key() == Qt.Key.Key_2:
                self._on_tab_changed(1)
                return
            elif event.key() == Qt.Key.Key_3:
                self._on_tab_changed(2)
                return
        super().keyPressEvent(event)

    def _fade_in_widget(self, widget: QWidget):
        effect = QGraphicsOpacityEffect(widget)
        widget.setGraphicsEffect(effect)
        anim = QPropertyAnimation(effect, b"opacity", self)
        anim.setDuration(160)
        anim.setStartValue(0.15)
        anim.setEndValue(1.0)
        anim.setEasingCurve(QEasingCurve.Type.OutCubic)
        anim.start(QPropertyAnimation.DeletionPolicy.DeleteWhenStopped)

    def _handle_language_changed(self, lang: str):
        self.retranslate_ui()

    def retranslate_ui(self):
        lang = self.config.language
        self.hotbar.retranslate_ui(lang)
        self.tab_home.retranslate_ui()
        if hasattr(self, "tab_settings") and hasattr(self.tab_settings, "retranslate_ui"):
            self.tab_settings.retranslate_ui()
        if hasattr(self, "tab_console") and hasattr(self.tab_console, "retranslate_ui"):
            self.tab_console.retranslate_ui()
        self._setup_system_tray()

    def _setup_system_tray(self):
        lang = self.config.language
        if not hasattr(self, "tray_icon"):
            self.tray_icon = QSystemTrayIcon(self)
            if not self.app_icon.isNull():
                self.tray_icon.setIcon(self.app_icon)
            self.tray_icon.setToolTip("Zomboid Day Launcher")
            self.tray_icon.activated.connect(self._on_tray_activated)
            self.tray_icon.show()

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

        menu.addAction(t("tray_show", lang), self._restore_from_tray)
        menu.addSeparator()
        menu.addAction(t("tray_start", lang), lambda: self._handle_start(False))
        menu.addAction(t("tray_debug", lang), lambda: self._handle_start(True))
        menu.addSeparator()
        menu.addAction(t("tray_exit", lang), QApplication.instance().quit)

        self.tray_icon.setContextMenu(menu)

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
        lang = self.config.language
        if self.install_worker and self.install_worker.isRunning():
            QMessageBox.information(self, t("info", lang), t("install_in_progress", lang))
            return

        self.tab_home.btn_install.setEnabled(False)
        self.tab_home.show_progress(5, t("install_prep", lang))

        self.install_worker = InstallWorker(self.config, self)
        self.install_worker.sig_progress.connect(self.tab_home.show_progress)
        self.install_worker.sig_log.connect(self.tab_console.append_log)
        self.install_worker.sig_finished.connect(self._on_install_finished)
        self.install_worker.start()

    def _on_install_finished(self, success: bool, message: str):
        lang = self.config.language
        self.tab_home.btn_install.setEnabled(True)
        self.tab_home.hide_progress()
        self.tab_home.refresh_status()
        if success:
            QMessageBox.information(self, t("done", lang), message)
        else:
            QMessageBox.critical(self, t("error", lang), message)

    def _handle_start(self, is_debug: bool):
        lang = self.config.language
        app_dir = get_app_dir()
        game_dir = Path(self.config.game_dir)

        # 1. Prohibit launch strictly if launcher is not located in the game folder
        if not (app_dir / "ProjectZomboid64.exe").exists():
            QMessageBox.critical(
                self,
                t("err_launch_prohibited_title", lang),
                t("err_launch_prohibited_msg", lang, app_dir=str(app_dir), game_dir=self.config.game_dir)
            )
            return

        # 2. Check if game is already running
        if self.proc_mgr.is_game_running():
            QMessageBox.information(
                self,
                t("info", lang),
                t("game_already_running", lang)
            )
            return

        scan = self.config.get("scan_modguard_before_launch", True)
        modguard_path = game_dir / "PZ-ModGuard.bat"

        # 3. Smart PZ-ModGuard Security Scan before launching
        if scan and modguard_path.exists():
            profile_id, profile_title_key, scan_reason_key = determine_modguard_scan_profile(self.config)
            profile_name = t(profile_title_key, lang)
            profile_reason = t(scan_reason_key, lang)

            # Show animated spinner circle on HomeTab
            self.tab_home.show_launch_spinner(
                f"PZ-ModGuard: {profile_name}",
                profile_reason
            )

            # Run asynchronous scan in background thread
            self.scan_worker = ModGuardScanThread(game_dir=game_dir, profile_id=profile_id, parent=self)
            self.scan_worker.sig_log.connect(self.tab_console.append_log)
            self.scan_worker.sig_finished.connect(
                lambda is_clean, code, summary, threats: self._on_modguard_scan_completed(
                    is_debug=is_debug,
                    profile_id=profile_id,
                    is_clean=is_clean,
                    code=code,
                    summary=summary,
                    threats=threats
                )
            )
            self.scan_worker.start()
        else:
            # Direct launch with spinner
            self.tab_home.show_launch_spinner(t("launching_game", lang), "")
            QApplication.processEvents()
            self._do_launch_game(is_debug)

    def _on_modguard_scan_completed(
        self,
        is_debug: bool,
        profile_id: int,
        is_clean: bool,
        code: int,
        summary: str,
        threats: list
    ):
        lang = self.config.language

        # Critical threat found: TERMINATE launch immediately!
        if (not is_clean) and len(threats) > 0:
            self.tab_home.hide_launch_spinner()

            self.tab_console.append_log(t("threat_abort_msg", "en"))
            self.tab_console.append_log(t("threat_code_msg", "en", code=code))
            for t_item in threats:
                self.tab_console.append_log(f"   -> {t_item}")

            from ui.dialogs.threat_dialog import ThreatDialog
            raw_lines = self.tab_console.terminal.toPlainText().splitlines()[-40:] if hasattr(self.tab_console, "terminal") else threats
            dlg = ThreatDialog(raw_logs=raw_lines, threats=threats, game_dir=Path(self.config.game_dir), lang=lang, parent=self)
            dlg.sig_rescan_requested.connect(lambda: self._handle_start(is_debug))
            dlg.sig_launch_approved.connect(lambda: self._do_launch_game(is_debug))
            dlg.exec()
            return

        # Scan clean: remember successful scan state and current file/mod fingerprint
        current_fp = compute_modguard_fingerprint(self.config)
        self.config.set("modguard_full_scan_done", True)
        self.config.set("modguard_last_full_scan_time", time.time())
        self.config.set("modguard_last_fingerprint", current_fp)
        game_dir = Path(self.config.game_dir)
        engine_mtime = 0.0
        for ef in ["projectzomboid.jar", "ProjectZomboid64.exe", "ProjectZomboid64.json"]:
            p = game_dir / ef
            if p.exists():
                try:
                    m = p.stat().st_mtime
                    if m > engine_mtime:
                        engine_mtime = m
                except Exception:
                    pass
        self.config.set("modguard_last_engine_mtime", engine_mtime)

        self.tab_home.set_launch_spinner_text(t("launching_game", lang), "")
        QApplication.processEvents()
        self._do_launch_game(is_debug)

    def _do_launch_game(self, is_debug: bool):
        lang = self.config.language
        ok = self.proc_mgr.launch_game(is_debug=is_debug, run_security_scan=False)
        self.tab_home.hide_launch_spinner()
        if ok:
            self.tab_home.refresh_status()
            if self.config.hide_to_tray_on_start:
                self.hide()
                mode = t("mode_debug", lang) if is_debug else t("mode_standard", lang)
                self.tray_icon.showMessage(
                    t("tray_game_started_title", lang),
                    t("tray_game_started_msg", lang, mode=mode),
                    QSystemTrayIcon.MessageIcon.Information, 3000,
                )
        else:
            QMessageBox.critical(
                self,
                t("error", lang),
                t("game_failed_to_start", lang)
            )

    def _on_game_crashed(self, error_msg: str):
        lang = self.config.language
        # 1. Immediately restore window from system tray so user sees the problem
        if self.isHidden() or self.isMinimized():
            self.showNormal()
            self.raise_()
            self.activateWindow()

        # 2. Reset Home tab status so the button is not 'Running'
        self.tab_home.hide_launch_spinner()
        self.tab_home.refresh_status()

        # 3. Switch to Console tab to show log details
        self._on_tab_changed(2)

        # 4. Show modal alert with details
        QMessageBox.critical(
            self,
            t("game_launch_err_title", lang),
            t("game_launch_err_msg", lang, error_msg=error_msg)
        )

    def _handle_settings_saved(self):
        self.tab_home.refresh_status()

    def showEvent(self, event):
        super().showEvent(event)
        self._apply_native_corners()
        self._update_window_shape()

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self._update_window_shape()

    def _apply_native_corners(self):
        """Enable native rounded corners on Windows 11 (DWM corner preference) if supported."""
        try:
            import ctypes
            hwnd = int(self.winId())
            # DWMWA_WINDOW_CORNER_PREFERENCE = 33, DWMWCP_ROUND = 2
            val = ctypes.c_int(2)
            ctypes.windll.dwmapi.DwmSetWindowAttribute(hwnd, 33, ctypes.byref(val), 4)
        except Exception:
            pass

    def _update_window_shape(self):
        """Apply physical rounded window mask so corners are cleanly rounded on Windows 10/11."""
        if self.isMaximized():
            self.clearMask()
            self.shell.setStyleSheet("#MainShell { border-radius: 0px; border: none; }")
            return

        self.shell.setStyleSheet("")
        radius = 14.0
        path = QPainterPath()
        path.addRoundedRect(0.0, 0.0, float(self.width()), float(self.height()), radius, radius)
        self.setMask(QRegion(path.toFillPolygon().toPolygon()))

    def closeEvent(self, event):
        lang = self.config.language
        if self.proc_mgr.is_game_running():
            reply = QMessageBox.question(
                self, t("tray_exit", lang),
                t("game_running_close_confirm", lang),
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
