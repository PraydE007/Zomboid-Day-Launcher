"""
Zomboid Day Launcher — Diagnostics & System Verification Dialog
Presents an in-depth system verification report with interactive 1-click
reinstallation/repair actions for each individual step.
"""
import os
from pathlib import Path
from typing import Dict, Any, Optional

from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QFrame, QScrollArea, QWidget, QMessageBox
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QColor

from core.i18n import t
from core.installer import reinstall_step


class DiagnosticsDialog(QDialog):
    def __init__(self, detector_or_results, config_manager=None, lang: str = "en", parent=None):
        super().__init__(parent)
        self.lang = lang
        self.config = config_manager

        if hasattr(detector_or_results, "run_diagnostics"):
            self.detector = detector_or_results
            self.results = self.detector.run_diagnostics(self.lang)
            if self.config is None and hasattr(self.detector, "config"):
                self.config = self.detector.config
        else:
            self.detector = None
            self.results = detector_or_results

        self.setWindowTitle(t("diag_title", self.lang))
        self.setMinimumWidth(620)
        self.setMinimumHeight(480)
        self.setWindowFlags(self.windowFlags() & ~Qt.WindowType.WindowContextHelpButtonHint)

        self.setStyleSheet("""
            QDialog {
                background-color: #121212;
                color: #e5e5e5;
            }
            QScrollArea {
                background: transparent;
                border: none;
            }
            QPushButton.CardAction {
                background-color: rgba(255, 255, 255, 0.06);
                color: #e5e5e5;
                border: 1px solid rgba(255, 255, 255, 0.12);
                border-radius: 6px;
                font-size: 11px;
                font-weight: 700;
                padding: 4px 12px;
            }
            QPushButton.CardAction:hover {
                background-color: rgba(34, 197, 94, 0.18);
                border-color: rgba(34, 197, 94, 0.50);
                color: #4ade80;
            }
            QPushButton.CardAction:pressed {
                background-color: rgba(34, 197, 94, 0.30);
            }
        """)

        self._setup_ui()

    def _setup_ui(self):
        # Clear layout if rebuilding
        if self.layout() is not None:
            QWidget().setLayout(self.layout())

        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 20, 24, 20)
        layout.setSpacing(14)

        # 1. Header Row
        top_row = QHBoxLayout()
        top_row.setSpacing(10)

        self.lbl_head = QLabel(t("diag_header_title", self.lang), self)
        self.lbl_head.setStyleSheet("""
            color: #22c55e;
            font-family: 'Freckle Face', sans-serif;
            font-size: 18px;
            font-weight: 800;
            letter-spacing: 0.5px;
            background: transparent;
        """)
        top_row.addWidget(self.lbl_head)
        top_row.addStretch()

        passed = self.results.get("passed_count", 0)
        total = self.results.get("total_count", 0)
        score_color = "#22c55e" if passed == total else "#f59e0b"

        passed_text = t("diag_score_passed", self.lang)
        self.lbl_score = QLabel(f"{passed}/{total} {passed_text}", self)
        self.lbl_score.setStyleSheet(f"""
            background-color: rgba(30, 30, 30, 0.85);
            color: {score_color};
            border: 1px solid {score_color};
            border-radius: 12px;
            padding: 3px 12px;
            font-size: 11px;
            font-weight: 700;
        """)
        top_row.addWidget(self.lbl_score)
        layout.addLayout(top_row)

        # 2. Scroll Area for checklist cards
        scroll = QScrollArea(self)
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)

        container = QWidget()
        c_layout = QVBoxLayout(container)
        c_layout.setContentsMargins(0, 0, 0, 0)
        c_layout.setSpacing(10)

        checks = self.results.get("checks", [])
        for chk in checks:
            card = self._create_check_card(chk)
            c_layout.addWidget(card)

        c_layout.addStretch()
        scroll.setWidget(container)
        layout.addWidget(scroll)

        # 3. Bottom Action Controls
        bottom_row = QHBoxLayout()
        bottom_row.setSpacing(10)

        # Reinstall All Steps Button
        btn_reinstall_all = QPushButton(t("btn_reinstall_all", self.lang), self)
        btn_reinstall_all.setProperty("class", "SecondaryButton")
        btn_reinstall_all.setFixedHeight(34)
        btn_reinstall_all.clicked.connect(self._handle_reinstall_all)
        bottom_row.addWidget(btn_reinstall_all)

        # Refresh Diagnostics Button
        btn_refresh = QPushButton(t("btn_refresh_diag", self.lang), self)
        btn_refresh.setProperty("class", "SecondaryButton")
        btn_refresh.setFixedHeight(34)
        btn_refresh.clicked.connect(self.refresh_diagnostics)
        bottom_row.addWidget(btn_refresh)

        bottom_row.addStretch()

        # OK / Close Button
        btn_close = QPushButton("OK", self)
        btn_close.setProperty("class", "PrimaryButton")
        btn_close.setMinimumWidth(110)
        btn_close.setFixedHeight(34)
        btn_close.clicked.connect(self.accept)
        bottom_row.addWidget(btn_close)

        layout.addLayout(bottom_row)

    def _create_check_card(self, chk: Dict[str, Any]) -> QFrame:
        chk_id = chk.get("id", "")
        status = chk.get("status", "ok")
        icon = "✓" if status == "ok" else ("⚠" if status == "warn" else "✗")
        color = "#22c55e" if status == "ok" else ("#f59e0b" if status == "warn" else "#ef4444")
        bg_color = "rgba(22, 22, 22, 0.9)" if status == "ok" else "rgba(35, 25, 10, 0.9)"

        card = QFrame()
        card.setStyleSheet(f"""
            QFrame {{
                background-color: {bg_color};
                border: 1px solid {color}40;
                border-left: 3px solid {color};
                border-radius: 6px;
                padding: 10px;
            }}
        """)
        card_layout = QVBoxLayout(card)
        card_layout.setContentsMargins(12, 10, 12, 10)
        card_layout.setSpacing(6)

        # Top line: Icon + Title + Action Button
        row_title = QHBoxLayout()
        lbl_icon = QLabel(f"{icon}  {chk.get('title', '')}", card)
        lbl_icon.setStyleSheet(f"color: {color}; font-size: 13px; font-weight: 700; background: transparent;")
        row_title.addWidget(lbl_icon)
        row_title.addStretch()

        # Action button for this specific step
        btn_action = self._create_step_action_button(chk_id, card)
        if btn_action:
            row_title.addWidget(btn_action)

        card_layout.addLayout(row_title)

        # Details
        lbl_detail = QLabel(chk.get("details", ""), card)
        lbl_detail.setStyleSheet("color: #a3a3a3; font-size: 11px; background: transparent;")
        lbl_detail.setWordWrap(True)
        card_layout.addWidget(lbl_detail)

        return card

    def _create_step_action_button(self, chk_id: str, parent: QWidget) -> Optional[QPushButton]:
        lang = self.lang

        if chk_id in ("jvm_scripts", "zombie_buddy", "modguard"):
            btn = QPushButton(t("btn_reinstall_step", lang), parent)
            btn.setProperty("class", "CardAction")
            btn.clicked.connect(lambda: self._execute_reinstall_step(chk_id, btn))
            return btn
        elif chk_id == "launcher_location":
            btn = QPushButton(t("btn_open_folder", lang), parent)
            btn.setProperty("class", "CardAction")
            btn.clicked.connect(self._open_game_folder)
            return btn
        elif chk_id == "user_profile":
            btn = QPushButton(t("btn_open_folder", lang), parent)
            btn.setProperty("class", "CardAction")
            btn.clicked.connect(self._open_user_profile)
            return btn
        elif chk_id == "manifest":
            btn = QPushButton(t("btn_refresh_diag", lang), parent)
            btn.setProperty("class", "CardAction")
            btn.clicked.connect(self.refresh_diagnostics)
            return btn

        return None

    def _execute_reinstall_step(self, chk_id: str, btn: QPushButton):
        if not self.config:
            return

        btn.setEnabled(False)
        btn.setText("⏳ ...")
        ok, msg = reinstall_step(chk_id, self.config)

        if ok:
            btn.setText("✓ " + (t("step_reinstalled_success", self.lang)))
            self.refresh_diagnostics()
        else:
            btn.setEnabled(True)
            btn.setText(t("btn_reinstall_step", self.lang))
            err_title = "Помилка" if self.lang == "uk" else "Error"
            QMessageBox.warning(self, err_title, msg)

    def _handle_reinstall_all(self):
        if not self.config:
            return

        reinstall_step("jvm_scripts", self.config)
        reinstall_step("zombie_buddy", self.config)
        reinstall_step("modguard", self.config)
        self.refresh_diagnostics()
        QMessageBox.information(
            self,
            t("info", self.lang),
            t("all_reinstalled_msg", self.lang)
        )

    def _open_game_folder(self):
        if self.config:
            p = Path(self.config.game_dir)
            if p.exists():
                os.startfile(str(p))

    def _open_user_profile(self):
        if self.config:
            p = Path(self.config.user_zomboid_dir)
            if p.exists():
                os.startfile(str(p))

    def refresh_diagnostics(self):
        if self.detector:
            self.results = self.detector.run_diagnostics(self.lang)
            self._setup_ui()
