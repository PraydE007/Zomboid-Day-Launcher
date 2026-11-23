"""
Threat Dialog — Security Warning & Threat Quarantine Modal.
Provides a comprehensive scanner terminal, detailed categorization of all detected
security threats (not just file paths), 1-click deletion/quarantine, and saving
trusted exceptions (pzmg_exceptions.json).
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


def add_pzmg_exception(file_path: Path, game_dir: Optional[Path] = None, comment: str = "") -> bool:
    """
    Register a trusted user exception for PZ-ModGuard in pzmg_exceptions.json.
    PZ-ModGuard natively parses pzmg_exceptions.json in the game root and in %LOCALAPPDATA%/PZ-ModGuard.
    """
    if not file_path:
        return False

    f_hash = get_file_sha256(file_path) if file_path.exists() else ""
    if not f_hash:
        # Fallback pseudo-hash based on filename if file is missing/virtual
        f_hash = hashlib.sha256(file_path.name.encode("utf-8")).hexdigest().lower()

    ext = file_path.suffix.lower()
    pattern = "native" if ext in (".dll", ".exe", ".ps1", ".bat", ".cmd", ".vbs", ".sh") else "*"

    entry = {
        "sha256": f_hash,
        "target": file_path.name,
        "entry": "*",
        "pattern": pattern,
        "comment": comment or f"Allowed via Zomboid Day Launcher ({file_path.name})",
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


class ThreatEntry:
    """Structured representation of a detected threat from PZ-ModGuard."""
    def __init__(self, raw_line: str, game_dir: Optional[Path] = None):
        self.raw_line = raw_line.strip()
        self.game_dir = game_dir
        self.category_key = "threat_category_generic"
        self.fallback_title = "Security Threat Finding"
        self.detail = ""
        self.file_path: Optional[Path] = None
        self._parse()

    def _parse(self):
        line = self.raw_line
        lower = line.lower()

        if "unauthorized native binary" in lower:
            self.category_key = "threat_category_native"
            self.fallback_title = "Unauthorized Native Binary (.exe / .dll)"
        elif "unauthorized jvm agent" in lower:
            self.category_key = "threat_category_agent"
            self.fallback_title = "Unauthorized JVM Agent Injection"
        elif "boot classpath override" in lower:
            self.category_key = "threat_category_boot"
            self.fallback_title = "Boot Classpath Override (-Xbootclasspath)"
        elif "compromised native framework" in lower:
            self.category_key = "threat_category_compromised"
            self.fallback_title = "Compromised Native Framework Hook"
        elif "hijacked mainclass" in lower:
            self.category_key = "threat_category_mainclass"
            self.fallback_title = "Hijacked Game MainClass"
        elif "game folder class changed" in lower or "class override" in lower:
            self.category_key = "threat_category_class"
            self.fallback_title = "Modified Game Engine Class Override"
        else:
            self.category_key = "threat_category_generic"
            self.fallback_title = "Security Threat Finding"

        # 1. Try finding absolute Windows drive path (e.g. C:\...)
        m = re.search(r'([A-Za-z]:\\[^:\r\n"\'<>|]+)', line)
        if m:
            cand = Path(m.group(1).strip().rstrip('.,;)'))
            self.file_path = cand

        # 2. Try finding relative filename if no drive path
        if not self.file_path and self.game_dir:
            m2 = re.search(r'in\s+([\w\.-]+\.(?:bat|json|jar|dll|exe|class))', line, re.IGNORECASE)
            if m2:
                cand2 = self.game_dir / m2.group(1)
                if cand2.exists():
                    self.file_path = cand2

        # 3. Clean up display detail
        clean = re.sub(r'^\[(critical|warning|threat|danger)[^\]]*\]\s*', '', line, flags=re.IGNORECASE)
        self.detail = clean.strip() or line


class ThreatItemWidget(QFrame):
    sig_file_deleted = pyqtSignal(str)
    sig_exception_added = pyqtSignal(str)

    def __init__(self, entry: ThreatEntry, game_dir: Optional[Path] = None, lang: str = "en", parent=None):
        super().__init__(parent)
        self.entry = entry
        self.file_path = entry.file_path
        self.raw_msg = entry.raw_line
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
                padding: 8px;
            }
        """)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 10, 12, 10)
        layout.setSpacing(6)

        # Top row: Title + Action buttons
        top_row = QHBoxLayout()
        top_row.setSpacing(10)

        category_title = t(self.entry.category_key, self.lang)
        if not category_title or category_title == self.entry.category_key:
            category_title = self.entry.fallback_title

        self.lbl_title = QLabel(f"⚠️  {category_title}", self)
        self.lbl_title.setStyleSheet("color: #ef4444; font-size: 13px; font-weight: 800; background: transparent;")
        top_row.addWidget(self.lbl_title, stretch=1)

        # Action Buttons
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
                padding: 5px 12px;
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
        top_row.addWidget(self.btn_allow)

        if self.file_path and self.file_path.exists() and self.file_path.is_file():
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
                    padding: 5px 12px;
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
            top_row.addWidget(self.btn_del)
        else:
            self.btn_del = None

        # Open / Explore button
        self.btn_open = QPushButton("📂", self)
        self.btn_open.setToolTip(t("threat_tip_open", self.lang))
        self.btn_open.setStyleSheet("""
            QPushButton {
                background: rgba(255, 255, 255, 0.08);
                color: #e4e4e7;
                font-size: 12px;
                border: 1px solid rgba(255, 255, 255, 0.15);
                border-radius: 5px;
                padding: 5px 10px;
            }
            QPushButton:hover {
                background: rgba(255, 255, 255, 0.16);
            }
        """)
        self.btn_open.clicked.connect(self._handle_open_folder)
        top_row.addWidget(self.btn_open)

        layout.addLayout(top_row)

        # Detail line / finding message
        self.lbl_detail = QLabel(self.entry.detail, self)
        self.lbl_detail.setStyleSheet("color: #e4e4e7; font-size: 12px; background: transparent;")
        self.lbl_detail.setWordWrap(True)
        self.lbl_detail.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        layout.addWidget(self.lbl_detail)

        # Path line (if available)
        if self.file_path:
            self.lbl_path = QLabel(f"📍 {str(self.file_path)}", self)
            self.lbl_path.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
            self.lbl_path.setStyleSheet("color: #a1a1aa; font-family: 'Consolas', monospace; font-size: 11px; background: transparent;")
            self.lbl_path.setWordWrap(True)
            layout.addWidget(self.lbl_path)

    def _handle_allow(self):
        target_path = self.file_path or (self.game_dir / "mod_threat") if self.game_dir else None
        ok = add_pzmg_exception(target_path, self.game_dir, comment=self.entry.raw_line[:120]) if target_path else True

        self.is_resolved = True
        self.btn_allow.setEnabled(False)
        self.btn_allow.setText(t("threat_status_allowed", self.lang))
        if self.btn_del:
            self.btn_del.setEnabled(False)

        whitelisted_suffix = t("threat_status_whitelisted", self.lang)
        self.lbl_title.setText(f"🛡️  {t(self.entry.category_key, self.lang)} {whitelisted_suffix}")
        self.lbl_title.setStyleSheet("color: #4ade80; font-size: 13px; font-weight: 800; background: transparent;")
        self.setStyleSheet("""
            QFrame {
                background-color: rgba(10, 30, 15, 0.75);
                border: 1px solid rgba(34, 197, 94, 0.4);
                border-radius: 8px;
                padding: 8px;
            }
        """)
        self.sig_exception_added.emit(str(self.file_path or self.entry.detail))

    def _handle_delete(self):
        if not self.file_path or not self.file_path.exists():
            self.is_resolved = True
            if self.btn_del:
                self.btn_del.setEnabled(False)
                self.btn_del.setText(t("threat_status_missing", self.lang))
            self.btn_allow.setEnabled(False)
            self.sig_file_deleted.emit(str(self.file_path or self.entry.detail))
            return

        try:
            if self.file_path.is_file():
                self.file_path.unlink()
            elif self.file_path.is_dir():
                import shutil
                shutil.rmtree(self.file_path, ignore_errors=True)

            self.is_resolved = True
            if self.btn_del:
                self.btn_del.setEnabled(False)
                self.btn_del.setText(t("threat_status_resolved", self.lang))
                self.btn_del.setStyleSheet("background: #15803d; color: #ffffff; border-radius: 5px; padding: 5px 12px;")
            self.btn_allow.setEnabled(False)
            deleted_suffix = t("threat_status_deleted", self.lang)
            self.lbl_title.setText(f"✓  {t(self.entry.category_key, self.lang)} {deleted_suffix}")
            self.lbl_title.setStyleSheet("color: #10b981; font-size: 13px; font-weight: 800; background: transparent;")
            self.setStyleSheet("""
                QFrame {
                    background-color: rgba(15, 25, 15, 0.75);
                    border: 1px solid rgba(16, 185, 129, 0.35);
                    border-radius: 8px;
                    padding: 8px;
                }
            """)
            self.sig_file_deleted.emit(str(self.file_path))
        except Exception as e:
            QMessageBox.warning(self, t("error", self.lang), t("threat_err_delete_file", self.lang, error=str(e)))

    def _handle_open_folder(self):
        target = self.file_path or self.game_dir
        if target:
            if target.is_file() and target.exists():
                try:
                    subprocess.Popen(f'explorer.exe /select,"{str(target)}"')
                    return
                except Exception:
                    pass
            folder = target if target.is_dir() else target.parent
            if folder.exists():
                try:
                    subprocess.Popen(f'explorer.exe "{str(folder)}"')
                except Exception:
                    pass


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
        self.threat_entries: List[ThreatEntry] = []

        self._parse_threats()

        self.setWindowTitle(t("threat_dlg_title", self.lang))
        self.setMinimumSize(820, 620)
        self.resize(860, 680)
        self._setup_ui()
        self._check_resolution_state()

    def _parse_threats(self):
        """Parse raw threat lines into rich structured ThreatEntry objects."""
        seen_keys = set()
        for t_line in self.threats:
            clean = t_line.strip()
            if not clean:
                continue
            lower = clean.lower()
            # Skip summary lines
            if "result:" in lower and ("danger" in lower or "caution" in lower or "threat" in lower or "clean" in lower):
                continue
            if "critical threat(s) detected" in lower and "result" in lower:
                continue

            entry = ThreatEntry(clean, self.game_dir)
            key = (entry.category_key, str(entry.file_path or entry.detail))
            if key not in seen_keys:
                seen_keys.add(key)
                self.threat_entries.append(entry)

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

        # 2. Fake Scanner Terminal Output
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
        self.txt_console.setFixedHeight(130)

        full_text = "\n".join(self.raw_logs) if self.raw_logs else "\n".join(self.threats)
        self.txt_console.setPlainText(full_text)
        console_box.addWidget(self.txt_console)
        layout.addLayout(console_box)

        # 3. Detected Threats List
        self.lbl_threats_header = QLabel(
            t("threat_items_count", self.lang, count=len(self.threat_entries)), self
        )
        self.lbl_threats_header.setStyleSheet("color: #ef4444; font-size: 12px; font-weight: 800; background: transparent;")
        layout.addWidget(self.lbl_threats_header)

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

        if self.threat_entries:
            for entry in self.threat_entries:
                item = ThreatItemWidget(entry, self.game_dir, self.lang, scroll_content)
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
        unresolved = [w for w in self.threat_widgets if not w.is_resolved]

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
