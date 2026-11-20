"""
Settings Tab — Clean sectioned layout in neutral dark tones.
"""
from pathlib import Path
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
    QPushButton, QCheckBox, QComboBox, QFileDialog, QMessageBox,
    QFrame, QTableWidget, QTableWidgetItem, QHeaderView, QAbstractItemView,
    QScrollArea
)
from PyQt6.QtCore import Qt, pyqtSignal

from core.config import detect_steam_pz_path, detect_user_zomboid_dir, get_default_hero_image
from ui.dialogs.repo_dialog import RepoEditDialog


class _SectionHeader(QLabel):
    """Clean uppercase section label."""
    def __init__(self, text: str, parent=None):
        super().__init__(text.upper(), parent)
        self.setStyleSheet(
            "color: #737373; font-size: 11px; font-weight: 700; letter-spacing: 1px;"
            "padding: 0; margin: 0; background: transparent;"
        )


class SettingsTab(QWidget):
    sig_settings_saved = pyqtSignal()
    sig_hero_image_changed = pyqtSignal(str)

    def __init__(self, config_manager, parent=None):
        super().__init__(parent)
        self.config = config_manager
        self.repos_cache = [r.copy() for r in self.config.repositories]
        self._setup_ui()
        self._load_settings()

    def _setup_ui(self):
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)

        scroll = QScrollArea(self)
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setStyleSheet("QScrollArea{background: transparent; border: none;}")

        content = QWidget()
        main = QVBoxLayout(content)
        main.setContentsMargins(24, 20, 24, 24)
        main.setSpacing(18)

        # ============================================================ Paths
        card_paths = QFrame(content)
        card_paths.setProperty("class", "GlassCard")
        lp = QVBoxLayout(card_paths)
        lp.setContentsMargins(18, 16, 18, 16)
        lp.setSpacing(10)

        lp.addWidget(_SectionHeader("Шляхи", card_paths))

        lp.addWidget(QLabel("Папка Project Zomboid:", card_paths))
        row_gd = QHBoxLayout()
        self.edit_game_dir = QLineEdit(card_paths)
        row_gd.addWidget(self.edit_game_dir)
        btn_br_g = QPushButton("Огляд", card_paths)
        btn_br_g.setProperty("class", "SecondaryButton")
        btn_br_g.clicked.connect(self._browse_game_dir)
        row_gd.addWidget(btn_br_g)
        btn_auto = QPushButton("Автопошук", card_paths)
        btn_auto.setProperty("class", "SecondaryButton")
        btn_auto.clicked.connect(self._auto_detect_game_dir)
        row_gd.addWidget(btn_auto)
        lp.addLayout(row_gd)

        lp.addWidget(QLabel("Папка профілю Zomboid:", card_paths))
        row_ud = QHBoxLayout()
        self.edit_user_dir = QLineEdit(card_paths)
        row_ud.addWidget(self.edit_user_dir)
        btn_br_u = QPushButton("Огляд", card_paths)
        btn_br_u.setProperty("class", "SecondaryButton")
        btn_br_u.clicked.connect(self._browse_user_dir)
        row_ud.addWidget(btn_br_u)
        lp.addLayout(row_ud)

        lp.addWidget(QLabel("Фонова картинка:", card_paths))
        row_h = QHBoxLayout()
        self.edit_hero = QLineEdit(card_paths)
        row_h.addWidget(self.edit_hero)
        btn_br_h = QPushButton("Огляд", card_paths)
        btn_br_h.setProperty("class", "SecondaryButton")
        btn_br_h.clicked.connect(self._browse_hero_image)
        row_h.addWidget(btn_br_h)
        btn_rst = QPushButton("Скинути", card_paths)
        btn_rst.setProperty("class", "SecondaryButton")
        btn_rst.clicked.connect(self._reset_hero_image)
        row_h.addWidget(btn_rst)
        lp.addLayout(row_h)

        main.addWidget(card_paths)

        # ============================================================ Repos
        card_repos = QFrame(content)
        card_repos.setProperty("class", "GlassCard")
        lr = QVBoxLayout(card_repos)
        lr.setContentsMargins(18, 16, 18, 16)
        lr.setSpacing(10)

        lr.addWidget(_SectionHeader("Репозиторії", card_repos))

        self.table_repos = QTableWidget(card_repos)
        self.table_repos.setColumnCount(5)
        self.table_repos.setHorizontalHeaderLabels(["#", "On", "Назва", "Тип", "Шлях / URL"])
        self.table_repos.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        self.table_repos.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        self.table_repos.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.Interactive)
        self.table_repos.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)
        self.table_repos.horizontalHeader().setSectionResizeMode(4, QHeaderView.ResizeMode.Stretch)
        self.table_repos.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table_repos.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.table_repos.setMinimumHeight(140)
        lr.addWidget(self.table_repos)

        repo_btns = QHBoxLayout()
        repo_btns.setSpacing(6)
        for label, slot in [
            ("Вгору", self._move_repo_up),
            ("Вниз", self._move_repo_down),
        ]:
            b = QPushButton(label, card_repos)
            b.setProperty("class", "SecondaryButton")
            b.clicked.connect(slot)
            repo_btns.addWidget(b)

        repo_btns.addSpacing(16)

        for label, slot in [
            ("Додати", self._add_repo),
            ("Редагувати", self._edit_repo),
            ("Видалити", self._delete_repo),
        ]:
            b = QPushButton(label, card_repos)
            b.setProperty("class", "SecondaryButton")
            b.clicked.connect(slot)
            repo_btns.addWidget(b)

        repo_btns.addStretch()
        lr.addLayout(repo_btns)
        main.addWidget(card_repos)

        # ============================================================ Launch
        card_launch = QFrame(content)
        card_launch.setProperty("class", "GlassCard")
        ll = QVBoxLayout(card_launch)
        ll.setContentsMargins(18, 16, 18, 16)
        ll.setSpacing(10)

        ll.addWidget(_SectionHeader("Запуск", card_launch))

        row_ram = QHBoxLayout()
        row_ram.addWidget(QLabel("RAM:", card_launch))
        self.combo_ram = QComboBox(card_launch)
        self.combo_ram.addItems([
            "4 GB", "8 GB", "12 GB (рекомендовано)", "16 GB"
        ])
        self.combo_ram.setCurrentIndex(2)
        row_ram.addWidget(self.combo_ram)
        row_ram.addStretch()
        ll.addLayout(row_ram)

        self.chk_tray_on_start = QCheckBox("Згортати в трей при старті гри", card_launch)
        ll.addWidget(self.chk_tray_on_start)

        self.chk_show_cmd = QCheckBox("Показувати зовнішнє вікно CMD", card_launch)
        ll.addWidget(self.chk_show_cmd)

        self.chk_scan_modguard = QCheckBox("Сканувати моди перед запуском (ModGuard)", card_launch)
        ll.addWidget(self.chk_scan_modguard)

        main.addWidget(card_launch)

        # ============================================================ Save
        row_save = QHBoxLayout()
        row_save.addStretch()
        self.btn_save = QPushButton("Зберегти", content)
        self.btn_save.setProperty("class", "PrimaryButton")
        self.btn_save.setMinimumHeight(42)
        self.btn_save.setMinimumWidth(160)
        self.btn_save.clicked.connect(self._save_settings)
        row_save.addWidget(self.btn_save)
        main.addLayout(row_save)

        main.addStretch()

        scroll.setWidget(content)
        outer.addWidget(scroll)

    def _load_settings(self):
        self.edit_game_dir.setText(self.config.game_dir)
        self.edit_user_dir.setText(self.config.user_zomboid_dir)
        self.edit_hero.setText(self.config.hero_image)
        self.chk_tray_on_start.setChecked(self.config.hide_to_tray_on_start)
        self.chk_show_cmd.setChecked(self.config.show_external_cmd)
        self.chk_scan_modguard.setChecked(self.config.get("scan_modguard_before_launch", False))

        ram_xmx = self.config.get("ram_xmx", "12288m")
        if "6144m" in ram_xmx:
            self.combo_ram.setCurrentIndex(0)
        elif "8192m" in ram_xmx:
            self.combo_ram.setCurrentIndex(1)
        elif "16384m" in ram_xmx:
            self.combo_ram.setCurrentIndex(3)
        else:
            self.combo_ram.setCurrentIndex(2)

        self._refresh_repos_table()

    def _refresh_repos_table(self):
        self.table_repos.setRowCount(0)
        for i, r in enumerate(self.repos_cache):
            self.table_repos.insertRow(i)

            item_order = QTableWidgetItem(str(i + 1))
            item_order.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self.table_repos.setItem(i, 0, item_order)

            chk = QCheckBox()
            chk.setChecked(r.get("enabled", True))
            chk.stateChanged.connect(lambda state, idx=i: self._toggle_repo(idx, state))
            w = QWidget()
            lo = QHBoxLayout(w)
            lo.addWidget(chk)
            lo.setAlignment(Qt.AlignmentFlag.AlignCenter)
            lo.setContentsMargins(0, 0, 0, 0)
            self.table_repos.setCellWidget(i, 1, w)

            self.table_repos.setItem(i, 2, QTableWidgetItem(r.get("name", "")))

            stype = r.get("source_type", "git")
            self.table_repos.setItem(i, 3, QTableWidgetItem(
                "Local" if stype == "local" else "Git" if stype == "git" else "Local/Git"
            ))

            loc = r.get("local_path") or r.get("git_url") or ""
            self.table_repos.setItem(i, 4, QTableWidgetItem(loc))

    def _toggle_repo(self, index, state):
        if 0 <= index < len(self.repos_cache):
            self.repos_cache[index]["enabled"] = (state == 2 or state == Qt.CheckState.Checked.value)

    def _move_repo_up(self):
        row = self.table_repos.currentRow()
        if row > 0:
            self.repos_cache[row], self.repos_cache[row - 1] = self.repos_cache[row - 1], self.repos_cache[row]
            self._refresh_repos_table()
            self.table_repos.selectRow(row - 1)

    def _move_repo_down(self):
        row = self.table_repos.currentRow()
        if 0 <= row < len(self.repos_cache) - 1:
            self.repos_cache[row], self.repos_cache[row + 1] = self.repos_cache[row + 1], self.repos_cache[row]
            self._refresh_repos_table()
            self.table_repos.selectRow(row + 1)

    def _add_repo(self):
        dlg = RepoEditDialog(parent=self)
        if dlg.exec():
            new = dlg.result_data
            new["order"] = len(self.repos_cache) + 1
            self.repos_cache.append(new)
            self._refresh_repos_table()

    def _edit_repo(self):
        row = self.table_repos.currentRow()
        if 0 <= row < len(self.repos_cache):
            dlg = RepoEditDialog(repo_data=self.repos_cache[row], parent=self)
            if dlg.exec():
                self.repos_cache[row] = dlg.result_data
                self._refresh_repos_table()
                self.table_repos.selectRow(row)

    def _delete_repo(self):
        row = self.table_repos.currentRow()
        if 0 <= row < len(self.repos_cache):
            name = self.repos_cache[row].get("name", "")
            if QMessageBox.question(
                self, "Видалення", f"Видалити '{name}'?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
            ) == QMessageBox.StandardButton.Yes:
                self.repos_cache.pop(row)
                self._refresh_repos_table()

    def _browse_game_dir(self):
        f = QFileDialog.getExistingDirectory(self, "Папка Project Zomboid", self.edit_game_dir.text())
        if f:
            self.edit_game_dir.setText(f)

    def _auto_detect_game_dir(self):
        found = detect_steam_pz_path()
        if found:
            self.edit_game_dir.setText(found)
            QMessageBox.information(self, "Знайдено", f"Project Zomboid:\n{found}")
        else:
            QMessageBox.warning(self, "Не знайдено", "Не вдалося знайти Project Zomboid.")

    def _browse_user_dir(self):
        f = QFileDialog.getExistingDirectory(self, "Папка профілю", self.edit_user_dir.text())
        if f:
            self.edit_user_dir.setText(f)

    def _browse_hero_image(self):
        f, _ = QFileDialog.getOpenFileName(self, "Картинка банера", "", "Images (*.png *.jpg *.jpeg *.webp)")
        if f:
            self.edit_hero.setText(f)
            self.sig_hero_image_changed.emit(f)

    def _reset_hero_image(self):
        d = get_default_hero_image()
        self.edit_hero.setText(d)
        self.sig_hero_image_changed.emit(d)

    def _save_settings(self):
        self.config.set("game_dir", self.edit_game_dir.text().strip())
        self.config.set("user_zomboid_dir", self.edit_user_dir.text().strip())
        self.config.set("hero_image", self.edit_hero.text().strip())
        self.config.set("hide_to_tray_on_start", self.chk_tray_on_start.isChecked())
        self.config.set("show_external_cmd", self.chk_show_cmd.isChecked())
        self.config.set("scan_modguard_before_launch", self.chk_scan_modguard.isChecked())

        ram_configs = [
            ("4096m", "6144m"),
            ("6144m", "8192m"),
            ("8192m", "12288m"),
            ("12288m", "16384m"),
        ]
        xms, xmx = ram_configs[self.combo_ram.currentIndex()]
        self.config.set("ram_xms", xms)
        self.config.set("ram_xmx", xmx)

        self.config.update_repositories(self.repos_cache)
        QMessageBox.information(self, "Збережено", "Налаштування збережено.")
        self.sig_settings_saved.emit()
