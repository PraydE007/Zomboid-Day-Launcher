"""
Console Tab — High-performance terminal view with batched ring-buffer rendering,
zero-copy autoscrolling, and neutral dark styling with full i18n support.
"""
import time
from collections import deque
from pathlib import Path
from typing import List, Optional

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPlainTextEdit,
    QPushButton, QLineEdit, QCheckBox, QFileDialog, QMessageBox
)
from PyQt6.QtCore import Qt, pyqtSignal, QTimer
from PyQt6.QtGui import QTextCursor

from core.i18n import t


class ConsoleTab(QWidget):
    sig_run_cmd = pyqtSignal(str)

    def __init__(self, config_manager, process_manager, parent=None):
        super().__init__(parent)
        self.config = config_manager
        self.proc_mgr = process_manager

        # High-performance lock-free deque queue (capped at 25,000 lines)
        self._log_queue: deque = deque(maxlen=25000)
        self._last_ts_sec: int = -1
        self._cached_ts: str = ""

        self._setup_ui()
        self.retranslate_ui()

        # Connect both single-line and high-throughput batched log streams
        self.proc_mgr.sig_log.connect(self.append_log)
        if hasattr(self.proc_mgr, "sig_log_batch"):
            self.proc_mgr.sig_log_batch.connect(self.append_log_batch)

        # High-frequency batch flush timer: ~33ms (30 FPS) for smooth zero-freeze UI
        self._flush_timer = QTimer(self)
        self._flush_timer.timeout.connect(self._flush_buffer)
        self._flush_timer.start(33)

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

        self.lbl_proc_indicator = QLabel(self)
        self.lbl_proc_indicator.setStyleSheet(
            "color: #737373; font-size: 11px; font-weight: 600;"
        )
        toolbar.addWidget(self.lbl_proc_indicator)

        toolbar.addStretch()

        self.chk_autoscroll = QCheckBox(self)
        self.chk_autoscroll.setChecked(True)
        toolbar.addWidget(self.chk_autoscroll)

        self.btn_clear = QPushButton(self)
        self.btn_clear.setProperty("class", "SecondaryButton")
        self.btn_clear.clicked.connect(self.clear_console)
        toolbar.addWidget(self.btn_clear)

        self.btn_save = QPushButton(self)
        self.btn_save.setProperty("class", "SecondaryButton")
        self.btn_save.clicked.connect(self._save_log_file)
        toolbar.addWidget(self.btn_save)

        layout.addLayout(toolbar)

        # ---- Terminal with maximum hardware/Qt text rendering optimizations
        self.terminal = QPlainTextEdit(self)
        self.terminal.setProperty("class", "TerminalView")
        self.terminal.setReadOnly(True)
        # Disabling undo/redo stack saves tens of megabytes of RAM and thousands of allocations
        self.terminal.setUndoRedoEnabled(False)
        # Fixed upper block bound guarantees memory ceiling
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
        self.edit_cmd.returnPressed.connect(self._send_command)
        cmd_row.addWidget(self.edit_cmd)

        self.btn_exec = QPushButton(self)
        self.btn_exec.setProperty("class", "PrimaryButton")
        self.btn_exec.setFixedHeight(34)
        self.btn_exec.clicked.connect(self._send_command)
        cmd_row.addWidget(self.btn_exec)

        layout.addLayout(cmd_row)

    def retranslate_ui(self):
        lang = self.config.language
        self.chk_autoscroll.setText(t("autoscroll", lang))
        self.btn_clear.setText(t("clear", lang))
        self.btn_save.setText(t("save", lang))
        self.edit_cmd.setPlaceholderText(t("cmd_placeholder", lang))
        self.btn_exec.setText(t("execute", lang))
        self._check_process_status()

    def _get_timestamp(self) -> str:
        """Cached timestamp string: updates at most once per second."""
        now_sec = int(time.time())
        if now_sec != self._last_ts_sec:
            self._last_ts_sec = now_sec
            self._cached_ts = time.strftime("%H:%M:%S")
        return self._cached_ts

    def append_log(self, text: str):
        """Append a single log string to the high-speed ring buffer."""
        if not text:
            return
        ts = self._get_timestamp()
        self._log_queue.append(f"[{ts}] {text}")

    def append_log_batch(self, lines: List[str]):
        """Append a batch of log strings directly without GUI thread lock."""
        if not lines:
            return
        ts = self._get_timestamp()
        formatted = [f"[{ts}] {line}" for line in lines if line]
        self._log_queue.extend(formatted)

    def _flush_buffer(self):
        """
        Batched renderer: flushes up to 800 lines into the QTextDocument in a single
        monolithic operation, bypassing individual line reflow and cursor reallocations.
        """
        if not self._log_queue:
            return

        # Throttle chunk size depending on whether the tab is currently visible
        max_chunk = 800 if self.isVisible() else 2500
        lines_to_render = []
        while self._log_queue and len(lines_to_render) < max_chunk:
            lines_to_render.append(self._log_queue.popleft())

        if lines_to_render:
            chunk_str = "\n".join(lines_to_render)
            self.terminal.appendPlainText(chunk_str)

            # Instant O(1) integer scrollbar assignment instead of heavy QTextCursor traversal
            if self.isVisible() and self.chk_autoscroll.isChecked():
                sb = self.terminal.verticalScrollBar()
                sb.setValue(sb.maximum())

    def showEvent(self, event):
        """When switching to Console tab, instantly flush all pending backlog and scroll down."""
        super().showEvent(event)
        self._flush_buffer()
        if self.chk_autoscroll.isChecked():
            sb = self.terminal.verticalScrollBar()
            sb.setValue(sb.maximum())

    def clear_console(self):
        """Instant clear of both buffer and terminal."""
        self._log_queue.clear()
        self.terminal.clear()

    def _send_command(self):
        cmd = self.edit_cmd.text().strip()
        if not cmd:
            return
        self.edit_cmd.clear()
        self.append_log(f"> {cmd}")
        self._flush_buffer()
        self.proc_mgr.execute_custom_cmd(cmd)

    def _save_log_file(self):
        # Flush any remaining buffer before exporting
        self._flush_buffer()
        lang = self.config.language
        path, _ = QFileDialog.getSaveFileName(
            self, t("save_log_title", lang), f"zomboid_log_{int(time.time())}.log",
            "Log Files (*.log *.txt)"
        )
        if path:
            try:
                with open(path, "w", encoding="utf-8") as f:
                    f.write(self.terminal.toPlainText())
                QMessageBox.information(self, t("log_saved_title", lang), t("log_saved_msg", lang, path=path))
            except Exception as e:
                QMessageBox.critical(self, t("error", lang), str(e))

    def _check_process_status(self):
        lang = self.config.language
        if self.proc_mgr.is_game_running():
            pid = self.proc_mgr.current_pid
            self.lbl_proc_indicator.setText(t("game_running", lang, pid=pid))
            self.lbl_proc_indicator.setStyleSheet(
                "color: #22c55e; font-size: 11px; font-weight: 700;"
            )
        else:
            self.lbl_proc_indicator.setText(t("game_not_running", lang))
            self.lbl_proc_indicator.setStyleSheet(
                "color: #737373; font-size: 11px; font-weight: 600;"
            )
