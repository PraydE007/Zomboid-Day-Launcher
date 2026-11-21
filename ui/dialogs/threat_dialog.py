"""
Threat Dialog — Security Warning & Threat Quarantine Modal.
Provides a fake terminal/console with selectable raw logs, 1-click
deletion/quarantine of malicious files and scripts, and saving trusted exceptions (pzmg_exceptions.json).
Fully localized using centralized i18n system.
"""

import os
import re
import json
import time
import hashlib
import subprocess
from pathlib import Path
from typing import List, Dict, Any, Optional

from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QPlainTextEdit, QScrollArea, QWidget, QFrame, QMessageBox,
    QApplication
)
from PyQt6.QtCore import Qt, pyqtSignal

from core.i18n import t


def get_file_sha256(path: Path) -> str:
    """Calculate SHA-256 hash of a file in lowercase hex."""
    h = hashlib.sha256()
    try:
        with open(path, "rb") as f:
            while chunk := f.read(65536):
                h.update(chunk)
        return h.hexdigest().lower()
    except Exception:
        return ""


def add_pzmg_exception(file_path: Path, game_dir: Optional[Path] = None) -> bool:
    """
    Register a trusted user exception for PZ-ModGuard in pzmg_exceptions.json.
    PZ-ModGuard natively parses pzmg_exceptions.json in the game root and in %LOCALAPPDATA%/PZ-ModGuard.
    """
    if not file_path or not file_path.exists():
        return False

    f_hash = get_file_sha256(file_path)
    if not f_hash:
        return False

    ext = file_path.suffix.lower()
    pattern = "native" if ext in (".dll", ".exe", ".ps1", ".bat", ".cmd", ".vbs", ".sh") else "*"

    entry = {
        "sha256": f_hash,
        "target": file_path.name,
        "entry": "*",
        "pattern": pattern,
        "comment": f"Allowed via Zomboid Day Launcher ({file_path.name})",
        "date_added": time.strftime("%Y-%m-%d %H:%M:%S")
    }

    targets = []
    if game_dir and game_dir.exists():
        targets.append(game_dir)
    local_app = os.environ.get("LOCALAPPDATA")
    if local_app:
        targets.append(Path(local_app) / "PZ-ModGuard")

    success = False
    for d in targets:
        try:
            d.mkdir(parents=True, exist_ok=True)
            target_json = d / "pzmg_exceptions.json"
            data = []
            if target_json.exists():
                try:
                    with open(target_json, "r", encoding="utf-8") as jf:
                        loaded = json.load(jf)
                        if isinstance(loaded, list):
                            data = loaded
                        elif isinstance(loaded, dict):
                            data = [loaded]
                except Exception:
                    data = []

            if not any(item.get("sha256", "").lower() == f_hash for item in data if isinstance(item, dict)):
                data.append(entry)
                with open(target_json, "w", encoding="utf-8") as jf:
                    json.dump(data, jf, indent=2, ensure_ascii=False)
            success = True
        except Exception as e:
            print(f"[ThreatDialog] Could not save exception to {d}: {e}")

    return success


class ThreatItemWidget(QFrame):
    sig_file_deleted = pyqtSignal(str)
    sig_exception_added = pyqtSignal(str)

    def __init__(self, file_path: Path, raw_msg: str = "", game_dir: Optional[Path] = None, lang: str = "en", parent=None):
        super().__init__(parent)
        self.file_path = file_path
        self.raw_msg = raw_msg
        self.game_dir = game_dir
        self.lang = lang
        self.is_resolved = False

        self._setup_ui()

    def _setup_ui(self):
        self.setStyleSheet("""
            QFrame {
                background-color: rgba(25, 12, 12, 0.75);
                border: 1px solid rgba(239, 68, 68, 0.35);
                border-radius: 8px;
                padding: 6px;
            }
        """)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(10, 8, 10, 8)
        layout.setSpacing(10)

        info_col = QVBoxLayout()
        info_col.setSpacing(2)

        file_name = self.file_path.name if self.file_path else t("threat_unknown_file", self.lang)
        self.lbl_name = QLabel(f"⚠️  {file_name}", self)
        self.lbl_name.setStyleSheet("color: #ef4444; font-size: 13px; font-weight: 800; background: transparent;")
        info_col.addWidget(self.lbl_name)

        self.lbl_path = QLabel(str(self.file_path), self)
        self.lbl_path.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        self.lbl_path.setStyleSheet("color: #a1a1aa; font-family: 'Consolas', monospace; font-size: 11px; background: transparent;")
        self.lbl_path.setWordWrap(True)
        info_col.addWidget(self.lbl_path)

        layout.addLayout(info_col, stretch=1)

        # Allow / Add Exception button
        self.btn_allow = QPushButton(t("threat_btn_allow", self.lang), self)
        self.btn_allow.setToolTip(t("threat_tip_allow", self.lang))
        self.btn_allow.setStyleSheet("""
            QPushButton {
                background: rgba(34, 197, 94, 0.15);
                color: #4ade80;
                font-weight: 700;
                font-size: 11px;
                border: 1px solid rgba(34, 197, 94, 0.4);
                border-radius: 5px;
                padding: 6px 12px;
            }
            QPushButton:hover {
                background: rgba(34, 197, 94, 0.3);
            }
            QPushButton:disabled {
                background: #14532d;
                color: #86efac;
                border: none;
            }
        """)
        self.btn_allow.clicked.connect(self._handle_allow)
        layout.addWidget(self.btn_allow)

        # Delete button
        self.btn_del = QPushButton(t("threat_btn_delete", self.lang), self)
        self.btn_del.setStyleSheet("""
            QPushButton {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #ef4444, stop:1 #dc2626);
                color: #ffffff;
                font-weight: 700;
                font-size: 11px;
                border: none;
                border-radius: 5px;
                padding: 6px 12px;
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

        # Open folder button
        self.btn_open = QPushButton("📂", self)
        self.btn_open.setToolTip(t("threat_tip_open", self.lang))
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

    def _handle_allow(self):
        if not self.file_path or not self.file_path.exists():
            self.btn_allow.setEnabled(False)
            self.btn_allow.setText(t("threat_status_missing", self.lang))
            self.is_resolved = True
            self.sig_exception_added.emit(str(self.file_path))
            return

        ok = add_pzmg_exception(self.file_path, self.game_dir)
        if ok:
            self.is_resolved = True
            self.btn_allow.setEnabled(False)
            self.btn_allow.setText(t("threat_status_allowed", self.lang))
            self.btn_del.setEnabled(False)
            whitelisted_suffix = t("threat_status_whitelisted", self.lang)
            self.lbl_name.setText(f"🛡️  {self.file_path.name} {whitelisted_suffix}")
            self.lbl_name.setStyleSheet("color: #4ade80; font-size: 13px; font-weight: 800; background: transparent;")
            self.setStyleSheet("""
                QFrame {
                    background-color: rgba(10, 30, 15, 0.75);
                    border: 1px solid rgba(34, 197, 94, 0.4);
                    border-radius: 8px;
                    padding: 6px;
                }
            """)
            self.sig_exception_added.emit(str(self.file_path))
        else:
            QMessageBox.warning(self, t("error", self.lang), t("threat_err_save_exception", self.lang))

    def _handle_delete(self):
        if not self.file_path or not self.file_path.exists():
            self.is_resolved = True
            self.btn_del.setEnabled(False)
            self.btn_del.setText(t("threat_status_missing", self.lang))
            self.btn_allow.setEnabled(False)
            self.sig_file_deleted.emit(str(self.file_path))
            return

        try:
            self.file_path.unlink()
            self.is_resolved = True
            self.btn_del.setEnabled(False)
            self.btn_del.setText(t("threat_status_resolved", self.lang))
            self.btn_del.setStyleSheet("background: #15803d; color: #ffffff; border-radius: 5px; padding: 6px 12px;")
            self.btn_allow.setEnabled(False)
            deleted_suffix = t("threat_status_deleted", self.lang)
            self.lbl_name.setText(f"✓  {self.file_path.name} {deleted_suffix}")
            self.lbl_name.setStyleSheet("color: #10b981; font-size: 13px; font-weight: 800; background: transparent;")
            self.setStyleSheet("""
                QFrame {
                    background-color: rgba(15, 25, 15, 0.75);
                    border: 1px solid rgba(16, 185, 129, 0.35);
                    border-radius: 8px;
                    padding: 6px;
                }
            """)
            self.sig_file_deleted.emit(str(self.file_path))
        except Exception as e:
            QMessageBox.warning(self, t("error", self.lang), t("threat_err_delete_file", self.lang, error=str(e)))

    def _handle_open_folder(self):
        if self.file_path:
            folder = self.file_path.parent
            if folder.exists():
                try:
                    subprocess.Popen(f'explorer.exe /select,"{str(self.file_path)}"')
                except Exception:
                    subprocess.Popen(f'explorer.exe "{str(folder)}"')


class ThreatDialog(QDialog):
    sig_rescan_requested = pyqtSignal()
    sig_launch_approved = pyqtSignal()

    def __init__(self, raw_logs: List[str], threats: List[str], game_dir: Optional[Path] = None, lang: str = "en", parent=None):
        super().__init__(parent)
        self.raw_logs = raw_logs
        self.threats = threats
        self.game_dir = game_dir
        self.lang = lang
        self.threat_widgets: List[ThreatItemWidget] = []

        self.setWindowTitle(t("threat_dlg_title", self.lang))
        self.setMinimumSize(800, 600)
        self.resize(840, 660)
        self._setup_ui()
        self._check_resolution_state()

    def _extract_threat_paths(self) -> List[Path]:
        found_paths = []
        seen = set()
        for t_line in self.threats:
            matches = re.findall(r'([A-Za-z]:\\[^:\r\n"\'<>|]+)', t_line)
            for m in matches:
                p_str = m.strip().rstrip('.,;)')
                p = Path(p_str)
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

        self.lbl_icon = QLabel("🛡️⛔", self)
        self.lbl_icon.setStyleSheet("font-size: 34px; background: transparent;")
        header.addWidget(self.lbl_icon)

        title_col = QVBoxLayout()
        title_col.setSpacing(2)

        self.lbl_title = QLabel(t("threat_header_critical", self.lang), self)
        self.lbl_title.setStyleSheet("color: #ef4444; font-size: 17px; font-weight: 900; letter-spacing: 0.5px; background: transparent;")
        title_col.addWidget(self.lbl_title)

        self.lbl_desc = QLabel(t("threat_header_desc", self.lang), self)
        self.lbl_desc.setStyleSheet("color: #a1a1aa; font-size: 12px; background: transparent;")
        title_col.addWidget(self.lbl_desc)

        header.addLayout(title_col, stretch=1)
        layout.addLayout(header)

        # 2. Fake Console Section
        console_box = QVBoxLayout()
        console_box.setSpacing(6)

        c_header = QHBoxLayout()
        lbl_console_title = QLabel(t("threat_console_title", self.lang), self)
        lbl_console_title.setStyleSheet("color: #d4d4d8; font-size: 11px; font-weight: 700; background: transparent;")
        c_header.addWidget(lbl_console_title)

        c_header.addStretch()

        btn_copy = QPushButton(t("threat_btn_copy", self.lang), self)
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
        self.txt_console.setFixedHeight(150)

        full_text = "\n".join(self.raw_logs) if self.raw_logs else "\n".join(self.threats)
        self.txt_console.setPlainText(full_text)
        console_box.addWidget(self.txt_console)
        layout.addLayout(console_box)

        # 3. Detected Threat Files
        threat_paths = self._extract_threat_paths()

        self.lbl_files_header = QLabel(t("threat_files_count", self.lang, count=len(threat_paths)), self)
        self.lbl_files_header.setStyleSheet("color: #ef4444; font-size: 12px; font-weight: 800; background: transparent;")
        layout.addWidget(self.lbl_files_header)

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
                item = ThreatItemWidget(p, "", self.game_dir, self.lang, scroll_content)
                item.sig_file_deleted.connect(self._on_item_deleted)
                item.sig_exception_added.connect(self._on_item_allowed)
                self.threat_widgets.append(item)
                scroll_layout.addWidget(item)
        else:
            self.lbl_none = QLabel(t("threat_none_left", self.lang), scroll_content)
            self.lbl_none.setStyleSheet("color: #4ade80; font-size: 12px; font-weight: 600; padding: 12px;")
            scroll_layout.addWidget(self.lbl_none)

        scroll_layout.addStretch()
        scroll.setWidget(scroll_content)
        layout.addWidget(scroll, stretch=1)

        # 4. Bottom Action Buttons
        btn_row = QHBoxLayout()
        btn_row.setSpacing(10)

        self.btn_del_all = QPushButton(t("threat_btn_delete_all", self.lang), self)
        self.btn_del_all.setStyleSheet("""
            QPushButton {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #ef4444, stop:1 #dc2626);
                color: #ffffff;
                font-weight: 800;
                font-size: 12px;
                border: none;
                border-radius: 6px;
                padding: 10px 18px;
            }
            QPushButton:hover {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #f87171, stop:1 #ef4444);
            }
            QPushButton:disabled {
                background: #27272a;
                color: #71717a;
            }
        """)
        self.btn_del_all.clicked.connect(self._delete_all_threats)
        btn_row.addWidget(self.btn_del_all)

        self.btn_allow_all = QPushButton(t("threat_btn_allow_all", self.lang), self)
        self.btn_allow_all.setStyleSheet("""
            QPushButton {
                background: rgba(34, 197, 94, 0.15);
                color: #4ade80;
                font-weight: 700;
                font-size: 12px;
                border: 1px solid rgba(34, 197, 94, 0.4);
                border-radius: 6px;
                padding: 10px 18px;
            }
            QPushButton:hover {
                background: rgba(34, 197, 94, 0.3);
            }
            QPushButton:disabled {
                background: #14532d;
                color: #86efac;
                border: none;
            }
        """)
        self.btn_allow_all.clicked.connect(self._allow_all_threats)
        btn_row.addWidget(self.btn_allow_all)

        self.btn_rescan = QPushButton(t("threat_btn_rescan", self.lang), self)
        self.btn_rescan.setStyleSheet("""
            QPushButton {
                background: rgba(255, 255, 255, 0.08);
                color: #e4e4e7;
                font-weight: 700;
                font-size: 12px;
                border: 1px solid rgba(255, 255, 255, 0.15);
                border-radius: 6px;
                padding: 10px 16px;
            }
            QPushButton:hover {
                background: rgba(255, 255, 255, 0.16);
            }
        """)
        self.btn_rescan.clicked.connect(self._handle_rescan)
        btn_row.addWidget(self.btn_rescan)

        btn_row.addStretch()

        self.btn_play_or_close = QPushButton(t("threat_btn_cancel", self.lang), self)
        self.btn_play_or_close.setStyleSheet("""
            QPushButton {
                background: rgba(255, 255, 255, 0.08);
                color: #a1a1aa;
                font-weight: 600;
                font-size: 13px;
                border: 1px solid rgba(255, 255, 255, 0.12);
                border-radius: 6px;
                padding: 10px 22px;
            }
            QPushButton:hover {
                color: #ffffff;
                background: rgba(255, 255, 255, 0.14);
            }
        """)
        self.btn_play_or_close.clicked.connect(self.reject)
        btn_row.addWidget(self.btn_play_or_close)

        layout.addLayout(btn_row)

    def _copy_console_text(self):
        cb = QApplication.clipboard()
        if cb:
            cb.setText(self.txt_console.toPlainText())
            QMessageBox.information(self, t("copied", self.lang), t("threat_copy_success", self.lang))

    def _on_item_deleted(self, file_path_str: str):
        self.txt_console.appendPlainText(t("threat_log_deleted", self.lang, path=file_path_str))
        self._check_resolution_state()

    def _on_item_allowed(self, file_path_str: str):
        self.txt_console.appendPlainText(t("threat_log_allowed", self.lang, path=file_path_str))
        self._check_resolution_state()

    def _check_resolution_state(self):
        unresolved = [w for w in self.threat_widgets if not w.is_resolved and w.file_path.exists()]

        if len(unresolved) == 0:
            self.lbl_icon.setText("🛡️✅")
            self.lbl_title.setText(t("threat_resolved_title", self.lang))
            self.lbl_title.setStyleSheet("color: #22c55e; font-size: 17px; font-weight: 900; background: transparent;")
            self.lbl_desc.setText(t("threat_resolved_desc", self.lang))
            self.lbl_desc.setStyleSheet("color: #86efac; font-size: 12px; background: transparent;")

            self.btn_del_all.setEnabled(False)
            self.btn_allow_all.setEnabled(False)

            self.btn_play_or_close.setText(t("threat_btn_save_and_play", self.lang))
            self.btn_play_or_close.setStyleSheet("""
                QPushButton {
                    background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #22c55e, stop:1 #16a34a);
                    color: #ffffff;
                    font-weight: 900;
                    font-size: 13px;
                    border: none;
                    border-radius: 6px;
                    padding: 10px 24px;
                }
                QPushButton:hover {
                    background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #4ade80, stop:1 #22c55e);
                }
            """)
            try:
                self.btn_play_or_close.clicked.disconnect()
            except Exception:
                pass
            self.btn_play_or_close.clicked.connect(self._handle_save_and_play)

    def _handle_save_and_play(self):
        self.accept()
        self.sig_launch_approved.emit()

    def _delete_all_threats(self):
        deleted_count = 0
        for w in self.threat_widgets:
            if not w.is_resolved:
                w._handle_delete()
                deleted_count += 1

        self._check_resolution_state()
        if deleted_count > 0:
            QMessageBox.information(
                self,
                t("success", self.lang),
                t("threat_del_success", self.lang, count=deleted_count)
            )

    def _allow_all_threats(self):
        allowed_count = 0
        for w in self.threat_widgets:
            if not w.is_resolved:
                w._handle_allow()
                allowed_count += 1

        self._check_resolution_state()
        if allowed_count > 0:
            QMessageBox.information(
                self,
                t("success", self.lang),
                t("threat_allow_success", self.lang, count=allowed_count)
            )

    def _handle_rescan(self):
        self.accept()
        self.sig_rescan_requested.emit()
