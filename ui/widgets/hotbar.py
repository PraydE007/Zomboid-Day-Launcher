"""
Zomboid Day Launcher — Left Hotbar Navigation Dock
A sleek, modern vertical gaming hotbar with high-DPI vector icons, active green glow,
smooth hover states, and quick actions.
"""
from pathlib import Path
from typing import Optional
import webbrowser

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QToolButton,
    QButtonGroup, QFrame, QLabel, QSizePolicy
)
from PyQt6.QtCore import Qt, pyqtSignal, QSize, QByteArray
from PyQt6.QtGui import QIcon, QPixmap, QPainter, QFont
from PyQt6.QtSvg import QSvgRenderer

from core.utils import get_resource_path
from core.i18n import t


def create_tinted_icon(svg_path: Path, size: int = 24) -> QIcon:
    """
    Render SVG with dynamic color states:
    - Normal/Off: cool silver-gray (#9ca3af)
    - Active/Hover: clean white (#f3f4f6)
    - Checked/On: vivid emerald green (#22c55e)
    """
    if not svg_path.exists():
        return QIcon()

    try:
        raw_svg = svg_path.read_text(encoding="utf-8")

        def render_svg_color(color_hex: str) -> QPixmap:
            tinted = raw_svg.replace("currentColor", color_hex)
            renderer = QSvgRenderer(QByteArray(tinted.encode("utf-8")))
            pm = QPixmap(size, size)
            pm.fill(Qt.GlobalColor.transparent)
            painter = QPainter(pm)
            renderer.render(painter)
            painter.end()
            return pm

        icon = QIcon()
        pm_off = render_svg_color("#9ca3af")
        pm_hov = render_svg_color("#f3f4f6")
        pm_on = render_svg_color("#22c55e")

        icon.addPixmap(pm_off, QIcon.Mode.Normal, QIcon.State.Off)
        icon.addPixmap(pm_hov, QIcon.Mode.Active, QIcon.State.Off)
        icon.addPixmap(pm_on, QIcon.Mode.Normal, QIcon.State.On)
        icon.addPixmap(pm_on, QIcon.Mode.Active, QIcon.State.On)
        return icon
    except Exception as e:
        print(f"[Hotbar] Error rendering icon {svg_path}: {e}")
        return QIcon(str(svg_path))


class HotbarDock(QWidget):
    """
    Vertical hotbar dock positioned on the left side of the launcher window.
    Features icon slots for Home, Settings, and Console tabs, plus quick utility actions.
    """
    sig_tab_changed = pyqtSignal(int)
    sig_steam_clicked = pyqtSignal()
    sig_diag_clicked = pyqtSignal()

    def __init__(self, config_manager, parent=None):
        super().__init__(parent)
        self.config = config_manager
        self.setObjectName("HotbarDock")
        self.setFixedWidth(78)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)

        self.btn_group = QButtonGroup(self)
        self.btn_group.setExclusive(True)
        self.slots = []

        self._init_ui()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(6, 12, 6, 12)
        layout.setSpacing(8)
        layout.setAlignment(Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignTop)

        lang = self.config.language

        # 1. Main Navigation Hotbar Slots
        icons_dir = get_resource_path("assets/icons")

        tab_defs = [
            (0, "home", icons_dir / "nav_home.svg", "hotbar_home", "nav_home"),
            (1, "settings", icons_dir / "nav_settings.svg", "hotbar_settings", "nav_settings"),
            (2, "console", icons_dir / "nav_console.svg", "hotbar_console", "nav_console"),
        ]

        for idx, tab_id, svg_file, label_key, full_key in tab_defs:
            btn = QToolButton(self)
            btn.setProperty("class", "HotbarSlot")
            btn.setCheckable(True)
            btn.setFixedSize(66, 62)
            btn.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextUnderIcon)
            btn.setIconSize(QSize(22, 22))

            icon = create_tinted_icon(svg_file, 22)
            btn.setIcon(icon)
            btn.setText(t(label_key, lang))
            btn.setToolTip(f"{t(full_key, lang)} [Ctrl+{idx+1}]")

            if idx == 0:
                btn.setChecked(True)

            self.btn_group.addButton(btn, idx)
            layout.addWidget(btn)
            self.slots.append((btn, label_key, full_key))

        # 2. Subtle Seam Separator
        layout.addSpacing(6)
        sep = QFrame(self)
        sep.setFrameShape(QFrame.Shape.HLine)
        sep.setFixedHeight(1)
        sep.setFixedWidth(44)
        sep.setStyleSheet("background-color: rgba(255, 255, 255, 0.08); border: none;")
        layout.addWidget(sep, alignment=Qt.AlignmentFlag.AlignHCenter)

        # 3. Flexible stretch to push utility actions to bottom
        layout.addStretch()

        # 4. Bottom Quick Actions: Steam Workshop Collection
        steam_svg = icons_dir / "steam.svg"
        self.btn_steam = QToolButton(self)
        self.btn_steam.setProperty("class", "HotbarQuickAction")
        self.btn_steam.setFixedSize(48, 38)
        self.btn_steam.setIconSize(QSize(20, 20))
        self.btn_steam.setIcon(create_tinted_icon(steam_svg, 20))
        self.btn_steam.setToolTip("Steam Workshop Collection / Колекція модів")
        self.btn_steam.clicked.connect(self._open_steam_workshop)
        layout.addWidget(self.btn_steam, alignment=Qt.AlignmentFlag.AlignHCenter)

        # 5. Quick Diagnostics Action
        self.btn_diag_shield = QToolButton(self)
        self.btn_diag_shield.setProperty("class", "HotbarQuickAction")
        self.btn_diag_shield.setFixedSize(48, 38)
        self.btn_diag_shield.setText("🛡️")
        self.btn_diag_shield.setToolTip("PZ-ModGuard & System Diagnostics / Діагностика системи")
        self.btn_diag_shield.clicked.connect(self.sig_diag_clicked.emit)
        layout.addWidget(self.btn_diag_shield, alignment=Qt.AlignmentFlag.AlignHCenter)

        # Signal connections
        self.btn_group.idClicked.connect(self.sig_tab_changed.emit)

    def _open_steam_workshop(self):
        webbrowser.open("https://steamcommunity.com/sharedfiles/filedetails/?id=3831192498")

    def set_current_tab(self, index: int):
        button = self.btn_group.button(index)
        if button:
            button.setChecked(True)

    def current_tab(self) -> int:
        return self.btn_group.checkedId()

    def retranslate_ui(self, lang: str):
        for idx, (btn, label_key, full_key) in enumerate(self.slots):
            btn.setText(t(label_key, lang))
            btn.setToolTip(f"{t(full_key, lang)} [Ctrl+{idx+1}]")
