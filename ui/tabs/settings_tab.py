from pathlib import Path
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
    QPushButton, QCheckBox, QComboBox, QFileDialog, QMessageBox,
    QFrame, QTableWidget, QTableWidgetItem, QHeaderView, QAbstractItemView
)
from PyQt6.QtCore import Qt, pyqtSignal

from core.config import detect_steam_pz_path, detect_user_zomboid_dir, get_default_hero_image
from ui.dialogs.repo_dialog import RepoEditDialog


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
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(20, 16, 20, 20)
        main_layout.setSpacing(16)

        # 1. Game Paths Card
        card_paths = QFrame(self)
        card_paths.setProperty("class", "GlassCard")
        l_paths = QVBoxLayout(card_paths)
        l_paths.setSpacing(10)

        lbl_paths_header = QLabel("📁 ШЛЯХИ ТА ПАПКИ ГРИ", card_paths)
        lbl_paths_header.setStyleSheet("color: #38bdf8; font-size: 13px; font-weight: 700; letter-spacing: 0.5px;")
        l_paths.addWidget(lbl_paths_header)

        # Game Dir
        l_paths.addWidget(QLabel("Папка встановлення Project Zomboid (Steam/Standalone):", card_paths))
        row_game_dir = QHBoxLayout()
        self.edit_game_dir = QLineEdit(card_paths)
        row_game_dir.addWidget(self.edit_game_dir)
        btn_browse_game = QPushButton("Огляд...", card_paths)
        btn_browse_game.setProperty("class", "SecondaryButton")
        btn_browse_game.clicked.connect(self._browse_game_dir)
        row_game_dir.addWidget(btn_browse_game)
        btn_auto_game = QPushButton("🔍 Автопошук", card_paths)
        btn_auto_game.setProperty("class", "SecondaryButton")
        btn_auto_game.clicked.connect(self._auto_detect_game_dir)
        row_game_dir.addWidget(btn_auto_game)
        l_paths.addLayout(row_game_dir)

        # User Dir
        l_paths.addWidget(QLabel("Папка профілю Zomboid (Saves, Mods, Logs):", card_paths))
        row_user_dir = QHBoxLayout()
        self.edit_user_dir = QLineEdit(card_paths)
        row_user_dir.addWidget(self.edit_user_dir)
        btn_browse_user = QPushButton("Огляд...", card_paths)
        btn_browse_user.setProperty("class", "SecondaryButton")
        btn_browse_user.clicked.connect(self._browse_user_dir)
        row_user_dir.addWidget(btn_browse_user)
        l_paths.addLayout(row_user_dir)

        # Hero Image
        l_paths.addWidget(QLabel("Фонова картинка банера лаунчера:", card_paths))
        row_hero = QHBoxLayout()
        self.edit_hero = QLineEdit(card_paths)
        row_hero.addWidget(self.edit_hero)
        btn_browse_hero = QPushButton("Огляд...", card_paths)
        btn_browse_hero.setProperty("class", "SecondaryButton")
        btn_browse_hero.clicked.connect(self._browse_hero_image)
        row_hero.addWidget(btn_browse_hero)
        btn_reset_hero = QPushButton("За замовчуванням", card_paths)
        btn_reset_hero.setProperty("class", "SecondaryButton")
        btn_reset_hero.clicked.connect(self._reset_hero_image)
        row_hero.addWidget(btn_reset_hero)
        l_paths.addLayout(row_hero)

        main_layout.addWidget(card_paths)

        # 2. Repositories & Install Queue Card
        card_repos = QFrame(self)
        card_repos.setProperty("class", "GlassCard")
        l_repos = QVBoxLayout(card_repos)
        l_repos.setSpacing(10)

        header_repo_row = QHBoxLayout()
        lbl_repo_header = QLabel("📦 РЕПОЗИТОРІЇ ТА ЧЕРГА ВСТАНОВЛЕННЯ", card_repos)
        lbl_repo_header.setStyleSheet("color: #38bdf8; font-size: 13px; font-weight: 700; letter-spacing: 0.5px;")
        header_repo_row.addWidget(lbl_repo_header)
        header_repo_row.addStretch()
        lbl_repo_hint = QLabel("Порядок встановлення регулюється кнопками Вгору/Вниз", card_repos)
        lbl_repo_hint.setStyleSheet("color: #64748b; font-size: 11px;")
        header_repo_row.addWidget(lbl_repo_hint)
        l_repos.addLayout(header_repo_row)

        # Repos Table
        self.table_repos = QTableWidget(card_repos)
        self.table_repos.setColumnCount(5)
        self.table_repos.setHorizontalHeaderLabels(["Черга", "Активний", "Назва компонента", "Тип джерела", "Шлях / URL"])
        self.table_repos.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        self.table_repos.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        self.table_repos.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.Interactive)
        self.table_repos.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)
        self.table_repos.horizontalHeader().setSectionResizeMode(4, QHeaderView.ResizeMode.Stretch)
        self.table_repos.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table_repos.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.table_repos.setMinimumHeight(160)
        l_repos.addWidget(self.table_repos)

        # Table Control Buttons
        repo_btn_row = QHBoxLayout()
        self.btn_move_up = QPushButton("▲ Вгору", card_repos)
        self.btn_move_up.setProperty("class", "SecondaryButton")
        self.btn_move_up.clicked.connect(self._move_repo_up)
        repo_btn_row.addWidget(self.btn_move_up)

        self.btn_move_down = QPushButton("▼ Вниз", card_repos)
        self.btn_move_down.setProperty("class", "SecondaryButton")
        self.btn_move_down.clicked.connect(self._move_repo_down)
        repo_btn_row.addWidget(self.btn_move_down)

        repo_btn_row.addSpacing(20)

        self.btn_add_repo = QPushButton("➕ Додати репозиторій", card_repos)
        self.btn_add_repo.setProperty("class", "SecondaryButton")
        self.btn_add_repo.clicked.connect(self._add_repo)
        repo_btn_row.addWidget(self.btn_add_repo)

        self.btn_edit_repo = QPushButton("✏️ Редагувати", card_repos)
        self.btn_edit_repo.setProperty("class", "SecondaryButton")
        self.btn_edit_repo.clicked.connect(self._edit_repo)
        repo_btn_row.addWidget(self.btn_edit_repo)

        self.btn_delete_repo = QPushButton("🗑️ Видалити", card_repos)
        self.btn_delete_repo.setProperty("class", "SecondaryButton")
        self.btn_delete_repo.clicked.connect(self._delete_repo)
        repo_btn_row.addWidget(self.btn_delete_repo)

        repo_btn_row.addStretch()
        l_repos.addLayout(repo_btn_row)

        main_layout.addWidget(card_repos)

        # 3. Launch & Memory Settings Card
        card_launch = QFrame(self)
        card_launch.setProperty("class", "GlassCard")
        l_launch = QVBoxLayout(card_launch)
        l_launch.setSpacing(10)

        lbl_launch_header = QLabel("⚙️ ПАРАМЕТРИ ЗАПУСКУ ТА ПОВЕДІНКИ", card_launch)
        lbl_launch_header.setStyleSheet("color: #38bdf8; font-size: 13px; font-weight: 700; letter-spacing: 0.5px;")
        l_launch.addWidget(lbl_launch_header)

        row_ram = QHBoxLayout()
        row_ram.addWidget(QLabel("Виділена оперативна пам'ять (RAM):", card_launch))
        self.combo_ram = QComboBox(card_launch)
        self.combo_ram.addItems(["4 GB (-Xms4096m -Xmx6144m)", "8 GB (-Xms6144m -Xmx8192m)", "12 GB (-Xms8192m -Xmx12288m) [Рекомендовано]", "16 GB (-Xms12288m -Xmx16384m)"])
        self.combo_ram.setCurrentIndex(2)
        row_ram.addWidget(self.combo_ram)
        row_ram.addStretch()
        l_launch.addLayout(row_ram)

        # Checkboxes
        self.chk_tray_on_start = QCheckBox("Ховати лаунчер в системний трей при запуску гри (рекомендовано)", card_launch)
        l_launch.addWidget(self.chk_tray_on_start)

        self.chk_show_cmd = QCheckBox("Показувати окреме зовнішнє вікно Windows CMD для консолі гри", card_launch)
        l_launch.addWidget(self.chk_show_cmd)

        self.chk_scan_modguard = QCheckBox("Автоматично перевіряти моди через PZ-ModGuard перед кожним запуском", card_launch)
        l_launch.addWidget(self.chk_scan_modguard)

        main_layout.addWidget(card_launch)

        # 4. Save Button Row
        row_bottom = QHBoxLayout()
        row_bottom.addStretch()
        self.btn_save = QPushButton("💾 ЗБЕРЕГТИ ВСІ НАЛАШТУВАННЯ", self)
        self.btn_save.setProperty("class", "PrimaryButton")
        self.btn_save.setMinimumHeight(44)
        self.btn_save.clicked.connect(self._save_settings)
        row_bottom.addWidget(self.btn_save)
        main_layout.addLayout(row_bottom)

        main_layout.addStretch()

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
        for row_idx, r in enumerate(self.repos_cache):
            self.table_repos.insertRow(row_idx)

            # Order
            item_order = QTableWidgetItem(f"#{row_idx + 1}")
            item_order.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self.table_repos.setItem(row_idx, 0, item_order)

            # Enabled Checkbox
            chk_widget = QCheckBox()
            chk_widget.setChecked(r.get("enabled", True))
            chk_widget.stateChanged.connect(lambda state, idx=row_idx: self._toggle_repo(idx, state))
            cell_chk = QWidget()
            cell_layout = QHBoxLayout(cell_chk)
            cell_layout.addWidget(chk_widget)
            cell_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
            cell_layout.setContentsMargins(0, 0, 0, 0)
            self.table_repos.setCellWidget(row_idx, 1, cell_chk)

            # Name
            item_name = QTableWidgetItem(r.get("name", ""))
            self.table_repos.setItem(row_idx, 2, item_name)

            # Source Type
            stype = r.get("source_type", "git")
            item_type = QTableWidgetItem("Локальна" if stype == "local" else ("Локальна / Git" if stype == "local_or_git" else "Git"))
            self.table_repos.setItem(row_idx, 3, item_type)

            # Path / URL
            loc = r.get("local_path") or r.get("git_url") or ""
            item_src = QTableWidgetItem(loc)
            self.table_repos.setItem(row_idx, 4, item_src)

    def _toggle_repo(self, index: int, state: int):
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
            new_repo = dlg.result_data
            new_repo["order"] = len(self.repos_cache) + 1
            self.repos_cache.append(new_repo)
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
            ans = QMessageBox.question(
                self, "Видалення",
                f"Видалити репозиторій '{name}' зі списку встановлення?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
            )
            if ans == QMessageBox.StandardButton.Yes:
                self.repos_cache.pop(row)
                self._refresh_repos_table()

    def _browse_game_dir(self):
        folder = QFileDialog.getExistingDirectory(self, "Виберіть папку Project Zomboid", self.edit_game_dir.text())
        if folder:
            self.edit_game_dir.setText(folder)

    def _auto_detect_game_dir(self):
        found = detect_steam_pz_path()
        if found:
            self.edit_game_dir.setText(found)
            QMessageBox.information(self, "Знайдено", f"Знайдено Project Zomboid:\n{found}")
        else:
            QMessageBox.warning(self, "Не знайдено", "Не вдалося автоматично знайти папку Project Zomboid у Steam.")

    def _browse_user_dir(self):
        folder = QFileDialog.getExistingDirectory(self, "Виберіть папку профілю Zomboid", self.edit_user_dir.text())
        if folder:
            self.edit_user_dir.setText(folder)

    def _browse_hero_image(self):
        file, _ = QFileDialog.getOpenFileName(self, "Виберіть картинку банера", "", "Зображення (*.png *.jpg *.jpeg *.webp)")
        if file:
            self.edit_hero.setText(file)
            self.sig_hero_image_changed.emit(file)

    def _reset_hero_image(self):
        def_img = get_default_hero_image()
        self.edit_hero.setText(def_img)
        self.sig_hero_image_changed.emit(def_img)

    def _save_settings(self):
        gdir = self.edit_game_dir.text().strip()
        udir = self.edit_user_dir.text().strip()
        himg = self.edit_hero.text().strip()

        self.config.set("game_dir", gdir)
        self.config.set("user_zomboid_dir", udir)
        self.config.set("hero_image", himg)
        self.config.set("hide_to_tray_on_start", self.chk_tray_on_start.isChecked())
        self.config.set("show_external_cmd", self.chk_show_cmd.isChecked())
        self.config.set("scan_modguard_before_launch", self.chk_scan_modguard.isChecked())

        # RAM
        ram_idx = self.combo_ram.currentIndex()
        ram_configs = [
            ("4096m", "6144m"),
            ("6144m", "8192m"),
            ("8192m", "12288m"),
            ("12288m", "16384m")
        ]
        xms, xmx = ram_configs[ram_idx]
        self.config.set("ram_xms", xms)
        self.config.set("ram_xmx", xmx)

        # Repositories
        self.config.update_repositories(self.repos_cache)

        QMessageBox.information(self, "Збережено", "Всі налаштування лаунчера успішно збережено!")
        self.sig_settings_saved.emit()
