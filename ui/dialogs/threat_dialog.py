"""
Threat Dialog — Security Warning & Threat Quarantine Modal.
Provides a fake terminal/console with selectable raw logs and 1-click
deletion/quarantine of malicious files and scripts detected by PZ-ModGuard.
"""

import os
import re
import subprocess
from pathlib import Path
from typing import List, Dict, Any, Optional

from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QPlainTextEdit, QScrollArea, QWidget, QFrame, QMessageBox,
    QApplication
)
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QFont, QColor

from core.i18n import t


class ThreatItemWidget(QFrame):
    """Card displaying a single detected threat file with deletion and open-folder actions."""
    sig_file_deleted = pyqtSignal(str)

    def __init__(self, file_path: Path, raw_threat: str, lang: str = "uk", parent=None):
        super().__init__(parent)
        self.file_path = file_path
        self.raw_threat = raw_threat
        self.lang = lang
        self._setup_ui()

    def _setup_ui(self):
        self.setStyleSheet("""
            QFrame {
                background-color: rgba(30, 10, 10, 0.75);
                border: 1px solid rgba(239, 68, 68, 0.35);
                border-radius: 8px;
                padding: 6px;
            }
            QFrame:hover {
                border-color: rgba(239, 68, 68, 0.7);
                background-color: rgba(45, 12, 12, 0.85);
            }
        """)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(10, 8, 10, 8)
        layout.setSpacing(12)

        # File Info Column
        info_col = QVBoxLayout()
        info_col.setSpacing(2)

        file_name = self.file_path.name if self.file_path else "Невідомий файл"
        lbl_name = QLabel(f"⚠️  {file_name}", self)
        lbl_name.setStyleSheet("color: #ef4444; font-size: 13px; font-weight: 800; background: transparent;")
        info_col.addWidget(lbl_name)

        lbl_path = QLabel(str(self.file_path), self)
        lbl_path.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        lbl_path.setStyleSheet("color: #a1a1aa; font-family: 'Consolas', monospace; font-size: 11px; background: transparent;")
        lbl_path.setWordWrap(True)
        info_col.addWidget(lbl_path)

        layout.addLayout(info_col, stretch=1)

        # Action Buttons
        self.btn_del = QPushButton("🗑  Видалити" if self.lang == "uk" else "🗑  Delete", self)
        self.btn_del.setStyleSheet("""
            QPushButton {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #ef4444, stop:1 #dc2626);
                color: #ffffff;
                font-weight: 700;
                font-size: 11px;
                border: none;
                border-radius: 5px;
                padding: 6px 14px;
            }
            QPushButton:hover {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #f87171, stop:1 #ef4444);
            }
            QPushButton:disabled {
                background: #27272a;
                color: #71717a;
            }
        """)
        self.btn_del.clicked.connect(self._handle_delete)
        layout.addWidget(self.btn_del)

        self.btn_open = QPushButton("📂", self)
        self.btn_open.setToolTip("Відкрити папку з файлом" if self.lang == "uk" else "Open containing folder")
        self.btn_open.setStyleSheet("""
            QPushButton {
                background: rgba(255, 255, 255, 0.08);
                color: #e4e4e7;
                font-size: 13px;
                border: 1px solid rgba(255, 255, 255, 0.15);
                border-radius: 5px;
                padding: 5px 10px;
            }
            QPushButton:hover {
                background: rgba(255, 255, 255, 0.16);
            }
        """)
        self.btn_open.clicked.connect(self._handle_open_folder)
        layout.addWidget(self.btn_open)

    def _handle_delete(self):
        if not self.file_path or not self.file_path.exists():
            self.btn_del.setEnabled(False)
            self.btn_del.setText("✓ Відсутній" if self.lang == "uk" else "✓ Missing")
            return

        try:
            self.file_path.unlink()
            self.btn_del.setEnabled(False)
            self.btn_del.setText("✓ Видалено" if self.lang == "uk" else "✓ Deleted")
            self.btn_del.setStyleSheet("background: #15803d; color: #ffffff; border-radius: 5px; padding: 6px 14px;")
            self.sig_file_deleted.emit(str(self.file_path))
        except Exception as e:
            QMessageBox.warning(self, "Помилка", f"Не вдалося видалити файл:\n{e}")

    def _handle_open_folder(self):
        if self.file_path:
            folder = self.file_path.parent
            if folder.exists():
                try:
                    subprocess.Popen(f'explorer.exe /select,"{str(self.file_path)}"')
                except Exception:
                    subprocess.Popen(f'explorer.exe "{str(folder)}"')


class ThreatDialog(QDialog):
    """
    Dedicated Security Alert Dialog with a fake console and threat file management.
    """
    sig_rescan_requested = pyqtSignal()

    def __init__(self, raw_logs: List[str], threats: List[str], lang: str = "uk", parent=None):
        super().__init__(parent)
        self.raw_logs = raw_logs
        self.threats = threats
        self.lang = lang
        self.threat_widgets: List[ThreatItemWidget] = []

        self.setWindowTitle("PZ-ModGuard Security Alert")
        self.setMinimumSize(780, 580)
        self.resize(820, 640)
        self._setup_ui()

    def _extract_threat_paths(self) -> List[Path]:
        found_paths = []
        seen = set()
        for t_line in self.threats:
            # Look for Windows file paths like C:\path\to\file.ext
            matches = re.findall(r'([A-Za-z]:\\[^:\r\n"\'<>|]+)', t_line)
            for m in matches:
                p_str = m.strip()
                # Clean trailing periods or commas
                p_str = p_str.rstrip('.,;)')
                p = Path(p_str)
                # Ignore self binaries
                lower = p.name.lower()
                if "zomboid-day-launcher" in lower or "pz-modguard" in lower:
                    continue
                if str(p).lower() not in seen:
                    seen.add(str(p).lower())
                    found_paths.append(p)
        return found_paths

    def _setup_ui(self):
        self.setStyleSheet("""
            QDialog {
                background-color: #0f0f11;
                border: 2px solid #ef4444;
                border-radius: 12px;
            }
        """)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 22, 24, 20)
        layout.setSpacing(14)

        # 1. Header Banner
        header = QHBoxLayout()
        header.setSpacing(14)

        lbl_icon = QLabel("🛡️⛔", self)
        lbl_icon.setStyleSheet("font-size: 34px; background: transparent;")
        header.addWidget(lbl_icon)

        title_col = QVBoxLayout()
        title_col.setSpacing(2)

        lbl_title = QLabel("ВИЯВЛЕНО КРИТИЧНІ ЗАГРОЗИ БЕЗПЕКИ МОДІВ" if self.lang == "uk" else "CRITICAL MOD SECURITY THREAT DETECTED", self)
        lbl_title.setStyleSheet("color: #ef4444; font-size: 17px; font-weight: 900; letter-spacing: 0.5px; background: transparent;")
        title_col.addWidget(lbl_title)

        lbl_desc = QLabel(
            "PZ-ModGuard виявив неавторизовані нативні бінарні файли або скрипти. Запуск гри скасовано!"
            if self.lang == "uk" else
            "PZ-ModGuard detected unauthorized native binaries or scripts. Game launch has been TERMINATED!",
            self
        )
        lbl_desc.setStyleSheet("color: #a1a1aa; font-size: 12px; background: transparent;")
        title_col.addWidget(lbl_desc)

        header.addLayout(title_col, stretch=1)
        layout.addLayout(header)

        # 2. Fake Console Section (Raw scan output with selectable text)
        console_box = QVBoxLayout()
        console_box.setSpacing(6)

        c_header = QHBoxLayout()
        lbl_console_title = QLabel("📟  ТЕРМІНАЛ СКАНОРА (PZ-MODGUARD REPORT):" if self.lang == "uk" else "📟  SCANNER TERMINAL REPORT:", self)
        lbl_console_title.setStyleSheet("color: #d4d4d8; font-size: 11px; font-weight: 700; background: transparent;")
        c_header.addWidget(lbl_console_title)

        c_header.addStretch()

        btn_copy = QPushButton("📋  Скопіювати звіт" if self.lang == "uk" else "📋  Copy Log", self)
        btn_copy.setStyleSheet("""
            QPushButton {
                background: rgba(255, 255, 255, 0.06);
                color: #e4e4e7;
                font-size: 11px;
                font-weight: 600;
                border: 1px solid rgba(255, 255, 255, 0.12);
                border-radius: 4px;
                padding: 4px 10px;
            }
            QPushButton:hover {
                background: rgba(255, 255, 255, 0.14);
            }
        """)
        btn_copy.clicked.connect(self._copy_console_text)
        c_header.addWidget(btn_copy)
        console_box.addLayout(c_header)

        self.txt_console = QPlainTextEdit(self)
        self.txt_console.setReadOnly(True)
        self.txt_console.setTextInteractionFlags(
            Qt.TextInteractionFlag.TextSelectableByMouse | Qt.TextInteractionFlag.TextSelectableByKeyboard
        )
        self.txt_console.setStyleSheet("""
            QPlainTextEdit {
                background-color: #09090b;
                color: #fca5a5;
                font-family: 'Consolas', 'Courier New', monospace;
                font-size: 11px;
                border: 1px solid rgba(239, 68, 68, 0.3);
                border-radius: 6px;
                padding: 8px;
            }
        """)
        self.txt_console.setFixedHeight(160)

        # Populate console text
        full_text = "\n".join(self.raw_logs) if self.raw_logs else "\n".join(self.threats)
        self.txt_console.setPlainText(full_text)
        console_box.addWidget(self.txt_console)

        layout.addLayout(console_box)

        # 3. Detected Threat Files & Deletion Action
        threat_paths = self._extract_threat_paths()

        lbl_files_header = QLabel(
            f"🎯  ФАЙЛИ ДЛЯ ВИДАЛЕННЯ ({len(threat_paths)}):" if self.lang == "uk" else f"🎯  FILES READY FOR REMOVAL ({len(threat_paths)}):",
            self
        )
        lbl_files_header.setStyleSheet("color: #ef4444; font-size: 12px; font-weight: 800; background: transparent;")
        layout.addWidget(lbl_files_header)

        scroll = QScrollArea(self)
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("""
            QScrollArea {
                background: transparent;
                border: 1px solid rgba(255, 255, 255, 0.06);
                border-radius: 8px;
            }
            QWidget#ThreatContainer {
                background: transparent;
            }
        """)
        scroll_content = QWidget()
        scroll_content.setObjectName("ThreatContainer")
        scroll_layout = QVBoxLayout(scroll_content)
        scroll_layout.setContentsMargins(8, 8, 8, 8)
        scroll_layout.setSpacing(8)

        if threat_paths:
            for p in threat_paths:
                item = ThreatItemWidget(p, "", self.lang, scroll_content)
                item.sig_file_deleted.connect(self._on_item_deleted)
                self.threat_widgets.append(item)
                scroll_layout.addWidget(item)
        else:
            lbl_none = QLabel("Не вдалося автоматично виокремити шляхи файлів. Перевірте звіт у консолі вище.", scroll_content)
            lbl_none.setStyleSheet("color: #71717a; font-size: 11px; padding: 10px;")
            scroll_layout.addWidget(lbl_none)

        scroll_layout.addStretch()
        scroll.setWidget(scroll_content)
        layout.addWidget(scroll, stretch=1)

        # 4. Bottom Action Buttons
        btn_row = QHBoxLayout()
        btn_row.setSpacing(10)

        self.btn_del_all = QPushButton("🗑  Видалити всі загрози" if self.lang == "uk" else "🗑  Delete All Threats", self)
        self.btn_del_all.setStyleSheet("""
            QPushButton {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #ef4444, stop:1 #dc2626);
                color: #ffffff;
                font-weight: 800;
                font-size: 13px;
                border: none;
                border-radius: 6px;
                padding: 10px 22px;
            }
            QPushButton:hover {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #f87171, stop:1 #ef4444);
            }
        """)
        self.btn_del_all.clicked.connect(self._delete_all_threats)
        btn_row.addWidget(self.btn_del_all)

        btn_rescan = QPushButton("⟳  Перевірити знову" if self.lang == "uk" else "⟳  Rescan Now", self)
        btn_rescan.setStyleSheet("""
            QPushButton {
                background: rgba(34, 197, 94, 0.15);
                color: #4ade80;
                font-weight: 700;
                font-size: 13px;
                border: 1px solid rgba(34, 197, 94, 0.4);
                border-radius: 6px;
                padding: 10px 18px;
            }
            QPushButton:hover {
                background: rgba(34, 197, 94, 0.28);
            }
        """)
        btn_rescan.clicked.connect(self._handle_rescan)
        btn_row.addWidget(btn_rescan)

        btn_row.addStretch()

        btn_close = QPushButton("✕  Закрити" if self.lang == "uk" else "✕  Close", self)
        btn_close.setStyleSheet("""
            QPushButton {
                background: rgba(255, 255, 255, 0.08);
                color: #a1a1aa;
                font-weight: 600;
                font-size: 13px;
                border: 1px solid rgba(255, 255, 255, 0.12);
                border-radius: 6px;
                padding: 10px 20px;
            }
            QPushButton:hover {
                color: #ffffff;
                background: rgba(255, 255, 255, 0.14);
            }
        """)
        btn_close.clicked.connect(self.reject)
        btn_row.addWidget(btn_close)

        layout.addLayout(btn_row)

    def _copy_console_text(self):
        cb = QApplication.clipboard()
        if cb:
            cb.setText(self.txt_console.toPlainText())
            QMessageBox.information(self, "Скопійовано", "Повний звіт скопійовано в буфер обміну!")

    def _on_item_deleted(self, file_path_str: str):
        self.txt_console.appendPlainText(f"\n[УСПІШНО]: Файл видалено з системи: {file_path_str}")

    def _delete_all_threats(self):
        deleted_count = 0
        for w in self.threat_widgets:
            if w.file_path and w.file_path.exists():
                try:
                    w.file_path.unlink()
                    w.btn_del.setEnabled(False)
                    w.btn_del.setText("✓ Видалено" if self.lang == "uk" else "✓ Deleted")
                    w.btn_del.setStyleSheet("background: #15803d; color: #ffffff; border-radius: 5px; padding: 6px 14px;")
                    self.txt_console.appendPlainText(f"[УСПІШНО]: Видалено файл: {w.file_path}")
                    deleted_count += 1
                except Exception as e:
                    self.txt_console.appendPlainText(f"[ПОМИЛКА]: Не вдалося видалити {w.file_path}: {e}")

        if deleted_count > 0:
            QMessageBox.information(
                self,
                "Успіх",
                f"Успішно видалено {deleted_count} небезпечних файлів!\nТепер можна запустити сканування знову."
            )
            self.btn_del_all.setEnabled(False)
            self.btn_del_all.setText("✓ Всі загрози видалено" if self.lang == "uk" else "✓ All Threats Removed")

    def _handle_rescan(self):
        self.accept()
        self.sig_rescan_requested.emit()
