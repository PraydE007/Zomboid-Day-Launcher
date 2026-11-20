"""
Console Tab — Clean terminal view with neutral dark styling and responsive prompt.
"""
import time
from pathlib import Path
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPlainTextEdit,
    QPushButton, QLineEdit, QCheckBox, QFileDialog, QMessageBox
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

        self.proc_mgr.sig_log.connect(self.append_log)

        # Polling timer with safe interval (5s) using fast non-blocking checks
        self.status_timer = QTimer(self)
        self.status_timer.timeout.connect(self._check_process_status)
        self.status_timer.start(5000)

    def _setup_ui(self):
        self.setStyleSheet("background: transparent;")
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 18, 24, 24)
        layout.setSpacing(12)

        # ---- Toolbar
        toolbar = QHBoxLayout()
        toolbar.setSpacing(10)

        self.lbl_proc_indicator = QLabel("Гра не запущена", self)
        self.lbl_proc_indicator.setStyleSheet(
            "color: #737373; font-size: 11px; font-weight: 600;"
        )
        toolbar.addWidget(self.lbl_proc_indicator)

        toolbar.addStretch()

        self.chk_autoscroll = QCheckBox("Автоскрол", self)
        self.chk_autoscroll.setChecked(True)
        toolbar.addWidget(self.chk_autoscroll)

        btn_clear = QPushButton("Очистити", self)
        btn_clear.setProperty("class", "SecondaryButton")
        btn_clear.clicked.connect(self.clear_console)
        toolbar.addWidget(btn_clear)

        btn_save = QPushButton("Зберегти", self)
        btn_save.setProperty("class", "SecondaryButton")
        btn_save.clicked.connect(self._save_log_file)
        toolbar.addWidget(btn_save)

        layout.addLayout(toolbar)

        # ---- Terminal
        self.terminal = QPlainTextEdit(self)
        self.terminal.setProperty("class", "TerminalView")
        self.terminal.setReadOnly(True)
        self.terminal.setMaximumBlockCount(10000)
        layout.addWidget(self.terminal)

        # ---- Command input
        cmd_row = QHBoxLayout()
        cmd_row.setSpacing(10)

        lbl_prompt = QLabel(">", self)
        lbl_prompt.setStyleSheet(
            "color: #22c55e; font-weight: 700; font-family: Consolas, monospace; font-size: 15px;"
        )
        cmd_row.addWidget(lbl_prompt)

        self.edit_cmd = QLineEdit(self)
        self.edit_cmd.setPlaceholderText("Введіть команду CMD для запуску...")
        self.edit_cmd.returnPressed.connect(self._send_command)
        cmd_row.addWidget(self.edit_cmd)

        btn_exec = QPushButton("Виконати", self)
        btn_exec.setProperty("class", "PrimaryButton")
        btn_exec.setFixedHeight(34)
        btn_exec.clicked.connect(self._send_command)
        cmd_row.addWidget(btn_exec)

        layout.addLayout(cmd_row)

        self.append_log(f"[{time.strftime('%H:%M:%S')}] Консоль готова. Процеси запускаються автономно.")

    def append_log(self, text: str):
        if not text:
            return
        ts = time.strftime("%H:%M:%S")
        self.terminal.appendPlainText(f"[{ts}] {text}")
        if self.chk_autoscroll.isChecked():
            self.terminal.moveCursor(QTextCursor.MoveOperation.End)

    def clear_console(self):
        self.terminal.clear()

    def _send_command(self):
        cmd = self.edit_cmd.text().strip()
        if not cmd:
            return
        self.edit_cmd.clear()
        self.append_log(f"> {cmd}")
        self.proc_mgr.execute_custom_cmd(cmd)

    def _save_log_file(self):
        path, _ = QFileDialog.getSaveFileName(
            self, "Зберегти лог", f"zomboid_log_{int(time.time())}.log",
            "Log Files (*.log *.txt)"
        )
        if path:
            try:
                with open(path, "w", encoding="utf-8") as f:
                    f.write(self.terminal.toPlainText())
                QMessageBox.information(self, "Збережено", f"Лог збережено:\n{path}")
            except Exception as e:
                QMessageBox.critical(self, "Помилка", str(e))

    def _check_process_status(self):
        if self.proc_mgr.is_game_running():
            pid = self.proc_mgr.current_pid
            self.lbl_proc_indicator.setText(f"Гра працює (PID: {pid})")
            self.lbl_proc_indicator.setStyleSheet(
                "color: #22c55e; font-size: 11px; font-weight: 700;"
            )
        else:
            self.lbl_proc_indicator.setText("Гра не запущена")
            self.lbl_proc_indicator.setStyleSheet(
                "color: #737373; font-size: 11px; font-weight: 600;"
            )
