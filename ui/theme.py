"""
Zomboid Day Launcher - UI Theme & Modern Gamer Stylesheet
"""

MODERN_DARK_THEME = """
/* ===== GLOBAL APPLICATION STYLES ===== */
QWidget {
    background-color: #0b0f19;
    color: #e2e8f0;
    font-family: 'Segoe UI', 'Ubuntu', 'Roboto', sans-serif;
    font-size: 13px;
    selection-background-color: #10b981;
    selection-color: #ffffff;
}

/* Scrollbars */
QScrollBar:vertical {
    border: none;
    background: #0b0f19;
    width: 8px;
    margin: 0px;
    border-radius: 4px;
}
QScrollBar::handle:vertical {
    background: #273142;
    min-height: 25px;
    border-radius: 4px;
}
QScrollBar::handle:vertical:hover {
    background: #3b475c;
}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
    height: 0px;
}

QScrollBar:horizontal {
    border: none;
    background: #0b0f19;
    height: 8px;
    margin: 0px;
    border-radius: 4px;
}
QScrollBar::handle:horizontal {
    background: #273142;
    min-width: 25px;
    border-radius: 4px;
}
QScrollBar::handle:horizontal:hover {
    background: #3b475c;
}

/* ===== TITLE BAR ===== */
#TitleBar {
    background-color: #080c14;
    border-bottom: 1px solid #1e2638;
}

#TitleLabel {
    color: #f8fafc;
    font-size: 13px;
    font-weight: 700;
    letter-spacing: 1px;
}

#TitleButton {
    background-color: transparent;
    color: #94a3b8;
    border: none;
    border-radius: 4px;
    font-size: 14px;
    padding: 6px 12px;
}
#TitleButton:hover {
    background-color: #1e293b;
    color: #f1f5f9;
}
#CloseButton:hover {
    background-color: #ef4444;
    color: #ffffff;
}

/* ===== NAVIGATION TAB BAR ===== */
#NavBar {
    background-color: #0d1322;
    border-bottom: 1px solid #1a2234;
    padding: 6px 12px;
}

QPushButton.NavTab {
    background-color: transparent;
    color: #94a3b8;
    border: none;
    border-radius: 8px;
    padding: 8px 18px;
    font-weight: 600;
    font-size: 13px;
    text-align: center;
}
QPushButton.NavTab:hover {
    background-color: #161f33;
    color: #f8fafc;
}
QPushButton.NavTab:checked {
    background-color: #1a253e;
    color: #38bdf8;
    border-bottom: 2px solid #38bdf8;
}

/* ===== CARDS & CONTAINERS ===== */
QFrame.GlassCard {
    background-color: #111726;
    border: 1px solid #1e293b;
    border-radius: 12px;
    padding: 16px;
}

QFrame.HeroOverlay {
    background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
        stop:0 rgba(11, 15, 25, 0.2),
        stop:0.6 rgba(11, 15, 25, 0.75),
        stop:1 rgba(11, 15, 25, 0.98));
    border-radius: 12px;
}

/* ===== BUTTONS ===== */
QPushButton.PrimaryButton {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #10b981, stop:1 #059669);
    color: #ffffff;
    border: none;
    border-radius: 10px;
    font-size: 15px;
    font-weight: 700;
    padding: 12px 28px;
    letter-spacing: 0.5px;
}
QPushButton.PrimaryButton:hover {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #34d399, stop:1 #10b981);
}
QPushButton.PrimaryButton:pressed {
    background: #047857;
}

QPushButton.DebugButton {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #6366f1, stop:1 #4f46e5);
    color: #ffffff;
    border: none;
    border-radius: 10px;
    font-size: 14px;
    font-weight: 700;
    padding: 12px 24px;
    letter-spacing: 0.5px;
}
QPushButton.DebugButton:hover {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #818cf8, stop:1 #6366f1);
}
QPushButton.DebugButton:pressed {
    background: #4338ca;
}

QPushButton.SecondaryButton {
    background-color: #1e293b;
    color: #e2e8f0;
    border: 1px solid #334155;
    border-radius: 8px;
    padding: 8px 16px;
    font-weight: 600;
    font-size: 12px;
}
QPushButton.SecondaryButton:hover {
    background-color: #334155;
    color: #ffffff;
    border-color: #475569;
}
QPushButton.SecondaryButton:pressed {
    background-color: #0f172a;
}

/* ===== INPUTS & CONTROLS ===== */
QLineEdit, QComboBox, QSpinBox {
    background-color: #090d16;
    border: 1px solid #1e293b;
    border-radius: 8px;
    color: #f1f5f9;
    padding: 8px 12px;
    selection-background-color: #10b981;
}
QLineEdit:focus, QComboBox:focus {
    border: 1px solid #38bdf8;
    background-color: #0d1322;
}

QComboBox::drop-down {
    border: none;
    padding-right: 8px;
}
QComboBox QAbstractItemView {
    background-color: #111726;
    border: 1px solid #1e293b;
    selection-background-color: #1e293b;
    color: #f1f5f9;
    padding: 4px;
}

QCheckBox {
    color: #cbd5e1;
    spacing: 8px;
    font-size: 13px;
}
QCheckBox::indicator {
    width: 18px;
    height: 18px;
    border: 1px solid #334155;
    border-radius: 4px;
    background-color: #0d1322;
}
QCheckBox::indicator:checked {
    background-color: #10b981;
    border-color: #10b981;
    image: none;
}

/* ===== PROGRESS BAR ===== */
QProgressBar {
    background-color: #090d16;
    border: 1px solid #1e293b;
    border-radius: 8px;
    text-align: center;
    color: #ffffff;
    font-weight: 600;
    font-size: 11px;
    height: 18px;
}
QProgressBar::chunk {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #10b981, stop:1 #38bdf8);
    border-radius: 7px;
}

/* ===== TABLES ===== */
QTableWidget {
    background-color: #0d1322;
    border: 1px solid #1e293b;
    border-radius: 8px;
    gridline-color: #161f33;
    color: #e2e8f0;
}
QTableWidget::item {
    padding: 8px;
    border-bottom: 1px solid #161f33;
}
QTableWidget::item:selected {
    background-color: #1e293b;
    color: #38bdf8;
}
QHeaderView::section {
    background-color: #090d16;
    color: #94a3b8;
    padding: 8px;
    border: none;
    border-bottom: 1px solid #1e293b;
    font-weight: 700;
}

/* ===== CONSOLE TERMINAL ===== */
QPlainTextEdit.TerminalView {
    background-color: #07090e;
    color: #34d399;
    font-family: 'Consolas', 'Courier New', 'Fira Code', monospace;
    font-size: 12px;
    line-height: 1.4;
    border: 1px solid #161f33;
    border-radius: 8px;
    padding: 10px;
}
"""
