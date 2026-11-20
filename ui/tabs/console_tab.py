import os
import subprocess
import time
from pathlib import Path
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPlainTextEdit,
    QPushButton, QLineEdit, QCheckBox, QFileDialog, QFrame, QMessageBox
)
from PyQt6.QtCore import Qt, pyqtSignal, QTimer
from PyQt6.QtGui import QTextCursor


class ConsoleTab(QWidget):
    sig_run_cmd = pyqtSignal(str)

    def __init__(self, config_manager, process_manager, parent=None):
        super().__init__(parent)
        self.config = config_manager
        self.proc_mgr = process_manager
        self._setup_ui()

        # Connect process manager signals
        self.proc_mgr.sig_log.connect(self.append_log)

        # Polling timer for process status badge
        self.status_timer = QTimer(self)
        self.status_timer.timeout.connect(self._check_process_status)
        self.status_timer.start(2000)

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 16, 20, 20)
        layout.setSpacing(12)

        # Top Bar: Title, Search, Status, Actions
        top_bar = QHBoxLayout()
        top_bar.setSpacing(10)

        lbl_console_title = QLabel("📟 СИСТЕМНА КОНСОЛЬ ТА ЛОГИ", self)
        lbl_console_title.setStyleSheet("color: #38bdf8; font-size: 13px; font-weight: 700; letter-spacing: 0.5px;")
        top_bar.addWidget(lbl_console_title)

        # Search / Filter
        self.edit_filter = QLineEdit(self)
        self.edit_filter.setPlaceholderText("🔍 Фільтр логів...")
        self.edit_filter.setMaximumWidth(220)
        self.edit_filter.textChanged.connect(self._apply_filter)
        top_bar.addWidget(self.edit_filter)

        top_bar.addStretch()

        # Process Status Indicator
        self.lbl_proc_indicator = QLabel("○ Гра: не активна", self)
        self.lbl_proc_indicator.setStyleSheet("""
            background-color: #111827;
            color: #94a3b8;
            border: 1px solid #1f2937;
            border-radius: 10px;
            padding: 3px 10px;
            font-size: 11px;
            font-weight: 600;
        """)
        top_bar.addWidget(self.lbl_proc_indicator)

        self.chk_autoscroll = QCheckBox("Автоскрол", self)
        self.chk_autoscroll.setChecked(True)
        top_bar.addWidget(self.chk_autoscroll)

        btn_clear = QPushButton("Очистити", self)
        btn_clear.setProperty("class", "SecondaryButton")
        btn_clear.clicked.connect(self.clear_console)
        top_bar.addWidget(btn_clear)

        btn_save_log = QPushButton("Зберегти лог...", self)
        btn_save_log.setProperty("class", "SecondaryButton")
        btn_save_log.clicked.connect(self._save_log_file)
        top_bar.addWidget(btn_save_log)

        btn_open_logs = QPushButton("Папка логів", self)
        btn_open_logs.setProperty("class", "SecondaryButton")
        btn_open_logs.clicked.connect(self._open_logs_dir)
        top_bar.addWidget(btn_open_logs)

        layout.addLayout(top_bar)

        # Terminal Output View
        self.terminal = QPlainTextEdit(self)
        self.terminal.setProperty("class", "TerminalView")
        self.terminal.setReadOnly(True)
        self.terminal.setMaximumBlockCount(10000)
        layout.addWidget(self.terminal)

        # Interactive CMD Execution Row
        cmd_card = QFrame(self)
        cmd_card.setProperty("class", "GlassCard")
        cmd_layout = QHBoxLayout(cmd_card)
        cmd_layout.setContentsMargins(10, 8, 10, 8)
        cmd_layout.setSpacing(10)

        lbl_prompt = QLabel("CMD >", cmd_card)
        lbl_prompt.setStyleSheet("color: #34d399; font-weight: 700; font-family: monospace;")
        cmd_layout.addWidget(lbl_prompt)

        self.edit_cmd = QLineEdit(cmd_card)
        self.edit_cmd.setPlaceholderText("Введіть CMD команду для запуску (наприклад: java -version, git status, dir)...")
        self.edit_cmd.returnPressed.connect(self._send_command)
        cmd_layout.addWidget(self.edit_cmd)

        btn_execute = QPushButton("Виконати", cmd_card)
        btn_execute.setProperty("class", "PrimaryButton")
        btn_execute.setMinimumHeight(32)
        btn_execute.clicked.connect(self._send_command)
        cmd_layout.addWidget(btn_execute)

        layout.addWidget(cmd_card)

        # Welcome message
        self.append_log(f"[{time.strftime('%H:%M:%S')}] Zomboid Day Launcher Console ініціалізовано.")
        self.append_log(f"[{time.strftime('%H:%M:%S')}] Всі процеси CMD запускаються в автономних групах (не закриваються при виході з лаунчера).")

    def append_log(self, text: str):
        if not text:
            return
        timestamp = time.strftime("%H:%M:%S")
        formatted = f"[{timestamp}] {text}"
        self.terminal.appendPlainText(formatted)
        if self.chk_autoscroll.isChecked():
            self.terminal.moveCursor(QTextCursor.MoveOperation.End)

    def clear_console(self):
        self.terminal.clear()

    def _apply_filter(self, query: str):
        # We can implement highlight or search
        if not query:
            return
        # Simple find
        self.terminal.find(query)

    def _send_command(self):
        cmd = self.edit_cmd.text().strip()
        if not cmd:
            return
        self.edit_cmd.clear()
        self.append_log(f"> Виконання команди: {cmd}")
        # Run via process manager
        self.proc_mgr.execute_custom_cmd(cmd)

    def _save_log_file(self):
        path, _ = QFileDialog.getSaveFileName(self, "Зберегти лог консолі", f"zomboid_launcher_{int(time.time())}.log", "Log Files (*.log *.txt)")
        if path:
            try:
                with open(path, "w", encoding="utf-8") as f:
                    f.write(self.terminal.toPlainText())
                QMessageBox.information(self, "Успіх", f"Лог збережено до:\n{path}")
            except Exception as e:
                QMessageBox.critical(self, "Помилка", f"Не вдалося зберегти лог: {e}")

    def _open_logs_dir(self):
        logs_dir = Path(self.config.base_dir) / "logs"
        logs_dir.mkdir(parents=True, exist_ok=True)
        subprocess.Popen(f'explorer.exe "{logs_dir}"')

    def _check_process_status(self):
        if self.proc_mgr.is_game_running():
            pid = self.proc_mgr.current_pid
            self.lbl_proc_indicator.setText(f"● Гра: Працює (PID: {pid})")
            self.lbl_proc_indicator.setStyleSheet("""
                background-color: rgba(16, 185, 129, 0.2);
                color: #10b981;
                border: 1px solid #10b981;
                border-radius: 10px;
                padding: 3px 10px;
                font-size: 11px;
                font-weight: 700;
            """)
        else:
            self.lbl_proc_indicator.setText("○ Гра: не активна")
            self.lbl_proc_indicator.setStyleSheet("""
                background-color: #111827;
                color: #94a3b8;
                border: 1px solid #1f2937;
                border-radius: 10px;
                padding: 3px 10px;
                font-size: 11px;
                font-weight: 600;
            """)
