"""
Zomboid Day Launcher — Pure Neutral Dark Theme
Minimalist, high contrast, pitch-black & graphite tones. No blue hues.
"""

MODERN_DARK_THEME = """
/* ===== BASE ===== */
QWidget {
    background-color: #121212;
    color: #d4d4d4;
    font-family: 'Segoe UI', -apple-system, BlinkMacSystemFont, sans-serif;
    font-size: 13px;
    selection-background-color: #22c55e;
    selection-color: #000000;
}

/* Ensure all labels have transparent backgrounds by default */
QLabel {
    background: transparent;
    background-color: transparent;
}

/* ===== MAIN SHELL (ROUNDED WINDOW) ===== */
#MainShell {
    background-color: #121212;
    border: 1px solid #262626;
    border-radius: 14px;
}

/* ===== SCROLLBARS ===== */
QScrollBar:vertical {
    border: none;
    background: transparent;
    width: 6px;
    margin: 2px 0 2px 0;
}
QScrollBar::handle:vertical {
    background: #262626;
    min-height: 30px;
    border-radius: 3px;
}
QScrollBar::handle:vertical:hover {
    background: #3a3a3a;
}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
    height: 0;
}
QScrollBar:horizontal {
    border: none;
    background: transparent;
    height: 6px;
}
QScrollBar::handle:horizontal {
    background: #262626;
    min-width: 30px;
    border-radius: 3px;
}

/* ===== TITLE BAR ===== */
#TitleBar {
    background-color: #151515;
    border-top-left-radius: 13px;
    border-top-right-radius: 13px;
    border-bottom: 1px solid #222222;
}
#TitleLabel {
    color: #e5e5e5;
    font-size: 12px;
    font-weight: 600;
    background: transparent;
}
#TitleButton {
    background: transparent;
    color: #737373;
    border: none;
    border-radius: 4px;
    font-size: 13px;
    padding: 4px 8px;
}
#TitleButton:hover {
    background: #242424;
    color: #f5f5f5;
}
#CloseButton {
    background: transparent;
    color: #737373;
    border: none;
    border-top-right-radius: 13px;
    border-bottom-right-radius: 0;
    font-size: 13px;
    padding: 4px 10px;
}
#CloseButton:hover {
    background: #dc2626;
    color: #ffffff;
}

/* ===== NAVIGATION BAR ===== */
#NavBar {
    background-color: #151515;
    border-bottom: 1px solid #222222;
}
QPushButton.NavTab {
    background: transparent;
    color: #737373;
    border: none;
    border-bottom: 2px solid transparent;
    border-radius: 0;
    padding: 8px 18px;
    font-weight: 600;
    font-size: 13px;
}
QPushButton.NavTab:hover {
    color: #e5e5e5;
}
QPushButton.NavTab:checked {
    color: #ffffff;
    border-bottom: 2px solid #22c55e;
}

/* ===== CARDS & CONTAINERS ===== */
QFrame.GlassCard {
    background-color: #171717;
    border: 1px solid #242424;
    border-radius: 8px;
}

/* ===== ACTION BUTTONS (STABLE CYRILLIC FONTS & NO WRAPPING) ===== */
QPushButton.PrimaryButton {
    background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #22c55e, stop:1 #16a34a);
    color: #ffffff;
    border: none;
    border-radius: 6px;
    font-family: 'Segoe UI', -apple-system, sans-serif;
    font-size: 15px;
    font-weight: 800;
    padding: 12px 30px;
    text-align: center;
}
QPushButton.PrimaryButton:hover {
    background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #4ade80, stop:1 #22c55e);
}
QPushButton.PrimaryButton:pressed {
    background: #15803d;
}
QPushButton.PrimaryButton:disabled {
    background: #262626;
    color: #525252;
}

QPushButton.DebugButton {
    background: rgba(22, 22, 22, 0.7);
    color: #d4d4d4;
    border: 1px solid #383838;
    border-radius: 6px;
    font-family: 'Segoe UI', -apple-system, sans-serif;
    font-size: 13px;
    font-weight: 700;
    padding: 12px 24px;
    text-align: center;
}
QPushButton.DebugButton:hover {
    color: #ffffff;
    border-color: #555555;
    background: rgba(38, 38, 38, 0.85);
}
QPushButton.DebugButton:pressed {
    background: #141414;
}

QPushButton.SecondaryButton {
    background: #1a1a1a;
    color: #a3a3a3;
    border: 1px solid #282828;
    border-radius: 5px;
    padding: 6px 14px;
    font-family: 'Segoe UI', -apple-system, sans-serif;
    font-weight: 600;
    font-size: 12px;
}
QPushButton.SecondaryButton:hover {
    color: #f5f5f5;
    border-color: #404040;
    background: #242424;
}
QPushButton.SecondaryButton:pressed {
    background: #171717;
}

/* ===== FORM CONTROLS ===== */
QLineEdit, QComboBox, QSpinBox {
    background-color: #171717;
    border: 1px solid #282828;
    border-radius: 5px;
    color: #f5f5f5;
    padding: 6px 10px;
    font-size: 12px;
}
QLineEdit:focus, QComboBox:focus {
    border-color: #444444;
}
QComboBox::drop-down {
    border: none;
    padding-right: 8px;
}
QComboBox QAbstractItemView {
    background-color: #181818;
    border: 1px solid #282828;
    selection-background-color: #262626;
    selection-color: #ffffff;
    color: #f5f5f5;
    padding: 4px;
}

QCheckBox {
    color: #a3a3a3;
    spacing: 8px;
    font-size: 12px;
    background: transparent;
}
QCheckBox::indicator {
    width: 15px;
    height: 15px;
    border: 1px solid #333333;
    border-radius: 3px;
    background: #171717;
}
QCheckBox::indicator:hover {
    border-color: #525252;
}
QCheckBox::indicator:checked {
    background: #22c55e;
    border-color: #22c55e;
}

/* ===== PROGRESS BAR ===== */
QProgressBar {
    background: #171717;
    border: 1px solid #262626;
    border-radius: 4px;
    text-align: center;
    color: #f5f5f5;
    font-weight: 600;
    font-size: 11px;
    height: 12px;
}
QProgressBar::chunk {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #16a34a, stop:1 #22c55e);
    border-radius: 3px;
}

/* ===== TABLES ===== */
QTableWidget {
    background: #141414;
    border: 1px solid #242424;
    border-radius: 6px;
    gridline-color: #1f1f1f;
    color: #d4d4d4;
}
QTableWidget::item {
    padding: 6px;
    border-bottom: 1px solid #1c1c1c;
}
QTableWidget::item:selected {
    background: #222222;
    color: #22c55e;
}
QHeaderView::section {
    background: #181818;
    color: #737373;
    padding: 6px;
    border: none;
    border-bottom: 1px solid #242424;
    font-weight: 600;
    font-size: 11px;
}

/* ===== CONSOLE / TERMINAL ===== */
QPlainTextEdit.TerminalView {
    background-color: #0b0b0b;
    color: #22c55e;
    font-family: 'Consolas', 'Courier New', monospace;
    font-size: 12px;
    border: 1px solid #1f1f1f;
    border-radius: 6px;
    padding: 8px;
}
"""
