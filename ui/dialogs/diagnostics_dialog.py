"""
Zomboid Day Launcher — Diagnostics Dialog
Presents an in-depth system verification report:
- Launcher placement beside ProjectZomboid64.exe
- Game binary presence
- Optimized JVM scripts
- ZombieBuddy Java agent & zbNative.dll
- PZ-ModGuard security scanner
- User profile & saves directory
"""
from typing import Dict, Any
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QFrame, QScrollArea, QWidget
)
from PyQt6.QtCore import Qt
from core.i18n import t


class DiagnosticsDialog(QDialog):
    def __init__(self, diag_results: Dict[str, Any], lang: str = "en", parent=None):
        super().__init__(parent)
        self.results = diag_results
        self.lang = lang
        self.setWindowTitle(t("view_diagnostics", self.lang))
        self.setMinimumWidth(560)
        self.setMinimumHeight(440)
        self.setWindowFlags(self.windowFlags() & ~Qt.WindowType.WindowContextHelpButtonHint)
        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 20, 24, 20)
        layout.setSpacing(16)

        # Header
        top_row = QHBoxLayout()
        lbl_head = QLabel("SYSTEM VERIFICATION & DIAGNOSTICS", self)
        lbl_head.setStyleSheet("""
            color: #22c55e;
            font-family: 'Freckle Face', sans-serif;
            font-size: 20px;
            letter-spacing: 1px;
            background: transparent;
        """)
        top_row.addWidget(lbl_head)
        top_row.addStretch()

        passed = self.results.get("passed_count", 0)
        total = self.results.get("total_count", 0)
        score_color = "#22c55e" if passed == total else "#f59e0b"
        lbl_score = QLabel(f"{passed}/{total} Passed", self)
        lbl_score.setStyleSheet(f"""
            background-color: rgba(30, 30, 30, 0.8);
            color: {score_color};
            border: 1px solid {score_color};
            border-radius: 12px;
            padding: 2px 10px;
            font-size: 11px;
            font-weight: 700;
        """)
        top_row.addWidget(lbl_score)
        layout.addLayout(top_row)

        # Scroll area for items
        scroll = QScrollArea(self)
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setStyleSheet("QScrollArea{background: transparent; border: none;}")

        container = QWidget()
        c_layout = QVBoxLayout(container)
        c_layout.setContentsMargins(0, 0, 0, 0)
        c_layout.setSpacing(10)

        checks = self.results.get("checks", [])
        for chk in checks:
            status = chk.get("status", "ok")
            icon = "✓" if status == "ok" else ("⚠" if status == "warn" else "✗")
            color = "#22c55e" if status == "ok" else ("#f59e0b" if status == "warn" else "#ef4444")
            bg_color = "rgba(22, 22, 22, 0.9)" if status == "ok" else "rgba(35, 25, 10, 0.9)"

            card = QFrame(container)
            card.setStyleSheet(f"""
                background-color: {bg_color};
                border: 1px solid {color}40;
                border-left: 3px solid {color};
                border-radius: 6px;
                padding: 10px;
            """)
            card_layout = QVBoxLayout(card)
            card_layout.setContentsMargins(10, 8, 10, 8)
            card_layout.setSpacing(4)

            # Title row
            row_title = QHBoxLayout()
            lbl_icon = QLabel(f"{icon} {chk.get('title', '')}", card)
            lbl_icon.setStyleSheet(f"color: {color}; font-size: 13px; font-weight: 700; background: transparent;")
            row_title.addWidget(lbl_icon)
            row_title.addStretch()
            card_layout.addLayout(row_title)

            # Details
            lbl_detail = QLabel(chk.get("details", ""), card)
            lbl_detail.setStyleSheet("color: #a3a3a3; font-size: 11px; background: transparent;")
            lbl_detail.setWordWrap(True)
            card_layout.addWidget(lbl_detail)

            c_layout.addWidget(card)

        c_layout.addStretch()
        scroll.setWidget(container)
        layout.addWidget(scroll)

        # Bottom Close Button
        btn_row = QHBoxLayout()
        btn_row.addStretch()
        btn_close = QPushButton("OK", self)
        btn_close.setProperty("class", "PrimaryButton")
        btn_close.setMinimumWidth(100)
        btn_close.clicked.connect(self.accept)
        btn_row.addWidget(btn_close)
        layout.addLayout(btn_row)
