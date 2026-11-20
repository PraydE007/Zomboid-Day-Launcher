"""
Zomboid Day Launcher — Clean Dark Theme
Inspired by Epic Games / Riot launchers. No clutter, no noise.
"""

MODERN_DARK_THEME = """
/* ===== BASE ===== */
QWidget {
    background-color: #0a0e17;
    color: #c8d0dc;
    font-family: 'Segoe UI', sans-serif;
    font-size: 13px;
    selection-background-color: #22c55e;
    selection-color: #fff;
}

/* ===== SCROLLBARS — thin & invisible-ish ===== */
QScrollBar:vertical {
    border: none; background: transparent; width: 6px;
}
QScrollBar::handle:vertical {
    background: #1e293b; min-height: 30px; border-radius: 3px;
}
QScrollBar::handle:vertical:hover { background: #334155; }
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height: 0; }
QScrollBar:horizontal {
    border: none; background: transparent; height: 6px;
}
QScrollBar::handle:horizontal {
    background: #1e293b; min-width: 30px; border-radius: 3px;
}

/* ===== TITLE BAR ===== */
#TitleBar {
    background-color: #070a11;
    border-bottom: 1px solid #141a28;
}
#TitleLabel {
    color: #e2e8f0; font-size: 12px; font-weight: 600; letter-spacing: 0.5px;
}
#TitleButton {
    background: transparent; color: #64748b; border: none;
    border-radius: 3px; font-size: 13px; padding: 5px 10px;
}
#TitleButton:hover { background: #1e293b; color: #f1f5f9; }
#CloseButton:hover { background: #dc2626; color: #fff; }

/* ===== NAVIGATION ===== */
#NavBar {
    background-color: #070a11;
    border-bottom: 1px solid #141a28;
}
QPushButton.NavTab {
    background: transparent; color: #64748b; border: none;
    border-bottom: 2px solid transparent;
    border-radius: 0; padding: 10px 20px;
    font-weight: 600; font-size: 13px;
}
QPushButton.NavTab:hover { color: #e2e8f0; }
QPushButton.NavTab:checked {
    color: #f8fafc;
    border-bottom: 2px solid #22c55e;
}

/* ===== GLASS CARDS ===== */
QFrame.GlassCard {
    background-color: #0f1420;
    border: 1px solid #1a2030;
    border-radius: 10px;
}

/* ===== PRIMARY BUTTON — the big green PLAY ===== */
QPushButton.PrimaryButton {
    background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #22c55e, stop:1 #16a34a);
    color: #fff; border: none; border-radius: 6px;
    font-family: 'Freckle Face', 'Segoe UI', sans-serif;
    font-size: 18px; font-weight: 700; padding: 14px 40px;
    letter-spacing: 1.5px;
}
QPushButton.PrimaryButton:hover {
    background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #4ade80, stop:1 #22c55e);
}
QPushButton.PrimaryButton:pressed { background: #15803d; }
QPushButton.PrimaryButton:disabled {
    background: #1e293b; color: #475569;
}

/* ===== DEBUG BUTTON ===== */
QPushButton.DebugButton {
    background: transparent;
    color: #94a3b8;
    border: 1px solid #334155;
    border-radius: 6px;
    font-size: 13px; font-weight: 600;
    padding: 14px 24px;
}
QPushButton.DebugButton:hover {
    color: #e2e8f0; border-color: #475569; background: #111827;
}
QPushButton.DebugButton:pressed { background: #0f172a; }

/* ===== SECONDARY BUTTON ===== */
QPushButton.SecondaryButton {
    background: transparent; color: #94a3b8;
    border: 1px solid #1e293b; border-radius: 6px;
    padding: 7px 14px; font-weight: 500; font-size: 12px;
}
QPushButton.SecondaryButton:hover {
    color: #e2e8f0; border-color: #334155; background: rgba(30, 41, 59, 0.5);
}

/* ===== INPUTS ===== */
QLineEdit, QComboBox, QSpinBox {
    background-color: #0a0e17;
    border: 1px solid #1e293b; border-radius: 6px;
    color: #e2e8f0; padding: 7px 10px;
}
QLineEdit:focus, QComboBox:focus { border-color: #22c55e; }
QComboBox::drop-down { border: none; padding-right: 6px; }
QComboBox QAbstractItemView {
    background: #0f1420; border: 1px solid #1e293b;
    selection-background-color: #1e293b; color: #e2e8f0;
}

/* ===== CHECKBOX ===== */
QCheckBox { color: #94a3b8; spacing: 8px; font-size: 12px; }
QCheckBox::indicator {
    width: 16px; height: 16px;
    border: 1px solid #334155; border-radius: 3px;
    background: #0a0e17;
}
QCheckBox::indicator:checked {
    background: #22c55e; border-color: #22c55e;
}

/* ===== PROGRESS BAR ===== */
QProgressBar {
    background: #0a0e17; border: 1px solid #1e293b;
    border-radius: 4px; text-align: center;
    color: #e2e8f0; font-weight: 600; font-size: 11px; height: 14px;
}
QProgressBar::chunk {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #22c55e, stop:1 #38bdf8);
    border-radius: 3px;
}

/* ===== TABLES ===== */
QTableWidget {
    background: #0a0e17; border: 1px solid #1a2030;
    border-radius: 6px; gridline-color: #141a28; color: #c8d0dc;
}
QTableWidget::item { padding: 6px; border-bottom: 1px solid #141a28; }
QTableWidget::item:selected { background: #1e293b; color: #22c55e; }
QHeaderView::section {
    background: #070a11; color: #64748b; padding: 6px;
    border: none; border-bottom: 1px solid #1a2030; font-weight: 600; font-size: 11px;
}

/* ===== CONSOLE ===== */
QPlainTextEdit.TerminalView {
    background-color: #050710;
    color: #22c55e;
    font-family: 'Consolas', 'Courier New', monospace;
    font-size: 12px; border: 1px solid #141a28;
    border-radius: 6px; padding: 8px;
}
"""
