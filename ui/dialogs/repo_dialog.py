from pathlib import Path
from typing import Dict, Any, Optional
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
    QPushButton, QCheckBox, QComboBox, QFileDialog, QMessageBox, QFrame
)
from PyQt6.QtCore import Qt


class RepoEditDialog(QDialog):
    def __init__(self, repo_data: Optional[Dict[str, Any]] = None, parent=None):
        super().__init__(parent)
        self.repo_data = repo_data or {}
        self.setWindowTitle("Налаштування репозиторію" if repo_data else "Додати новий репозиторій")
        self.setMinimumWidth(540)
        self.setWindowFlags(self.windowFlags() & ~Qt.WindowType.WindowContextHelpButtonHint)

        self._setup_ui()
        self._populate_fields()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(14)

        card = QFrame(self)
        card.setProperty("class", "GlassCard")
        card_layout = QVBoxLayout(card)
        card_layout.setSpacing(12)

        # Name
        card_layout.addWidget(QLabel("Назва компонента / репозиторію:"))
        self.edit_name = QLineEdit(card)
        self.edit_name.setPlaceholderText("Наприклад: PZ-ModGuard або Zomboid Day Patches")
        card_layout.addWidget(self.edit_name)

        # ID
        card_layout.addWidget(QLabel("Унікальний ідентифікатор (ID):"))
        self.edit_id = QLineEdit(card)
        self.edit_id.setPlaceholderText("Наприклад: pz-modguard")
        card_layout.addWidget(self.edit_id)

        # Source Type
        card_layout.addWidget(QLabel("Тип джерела:"))
        self.combo_source_type = QComboBox(card)
        self.combo_source_type.addItems(["Git Репозиторій (URL)", "Локальна папка на диску", "Локальна папка або Git"])
        self.combo_source_type.currentIndexChanged.connect(self._on_source_type_changed)
        card_layout.addWidget(self.combo_source_type)

        # Git URL
        self.lbl_git_url = QLabel("Git URL репозиторію:")
        card_layout.addWidget(self.lbl_git_url)
        self.edit_git_url = QLineEdit(card)
        self.edit_git_url.setPlaceholderText("https://github.com/author/repository.git")
        card_layout.addWidget(self.edit_git_url)

        # Branch
        self.lbl_branch = QLabel("Гілка Git (Branch):")
        card_layout.addWidget(self.lbl_branch)
        self.edit_branch = QLineEdit(card)
        self.edit_branch.setText("main")
        card_layout.addWidget(self.edit_branch)

        # Local Path
        self.lbl_local_path = QLabel("Шлях до локальної папки:")
        card_layout.addWidget(self.lbl_local_path)
        loc_row = QHBoxLayout()
        self.edit_local_path = QLineEdit(card)
        self.edit_local_path.setPlaceholderText(r"C:\Users\...\MyRepo")
        loc_row.addWidget(self.edit_local_path)
        self.btn_browse_local = QPushButton("Огляд...", card)
        self.btn_browse_local.setProperty("class", "SecondaryButton")
        self.btn_browse_local.clicked.connect(self._browse_local_folder)
        loc_row.addWidget(self.btn_browse_local)
        card_layout.addLayout(loc_row)

        # Checkboxes
        self.chk_manifest = QCheckBox("Містить файл launcher-manifest.json (автоматичні кроки та валідація)", card)
        self.chk_manifest.setChecked(True)
        card_layout.addWidget(self.chk_manifest)

        self.chk_enabled = QCheckBox("Увімкнено для встановлення", card)
        self.chk_enabled.setChecked(True)
        card_layout.addWidget(self.chk_enabled)

        layout.addWidget(card)

        # Bottom Buttons
        btn_row = QHBoxLayout()
        btn_row.addStretch()

        btn_cancel = QPushButton("Скасувати", self)
        btn_cancel.setProperty("class", "SecondaryButton")
        btn_cancel.clicked.connect(self.reject)
        btn_row.addWidget(btn_cancel)

        btn_save = QPushButton("Зберегти", self)
        btn_save.setProperty("class", "PrimaryButton")
        btn_save.clicked.connect(self._validate_and_save)
        btn_row.addWidget(btn_save)

        layout.addLayout(btn_row)

    def _populate_fields(self):
        if not self.repo_data:
            return

        self.edit_name.setText(self.repo_data.get("name", ""))
        self.edit_id.setText(self.repo_data.get("id", ""))
        self.edit_git_url.setText(self.repo_data.get("git_url", ""))
        self.edit_branch.setText(self.repo_data.get("branch", "main"))
        self.edit_local_path.setText(self.repo_data.get("local_path", ""))
        self.chk_manifest.setChecked(self.repo_data.get("has_manifest", True))
        self.chk_enabled.setChecked(self.repo_data.get("enabled", True))

        stype = self.repo_data.get("source_type", "git")
        if stype == "local":
            self.combo_source_type.setCurrentIndex(1)
        elif stype == "local_or_git":
            self.combo_source_type.setCurrentIndex(2)
        else:
            self.combo_source_type.setCurrentIndex(0)
        self._on_source_type_changed()

    def _on_source_type_changed(self):
        idx = self.combo_source_type.currentIndex()
        if idx == 0:  # Git only
            self.lbl_git_url.setVisible(True)
            self.edit_git_url.setVisible(True)
            self.lbl_branch.setVisible(True)
            self.edit_branch.setVisible(True)
            self.lbl_local_path.setVisible(False)
            self.edit_local_path.setVisible(False)
            self.btn_browse_local.setVisible(False)
        elif idx == 1:  # Local only
            self.lbl_git_url.setVisible(False)
            self.edit_git_url.setVisible(False)
            self.lbl_branch.setVisible(False)
            self.edit_branch.setVisible(False)
            self.lbl_local_path.setVisible(True)
            self.edit_local_path.setVisible(True)
            self.btn_browse_local.setVisible(True)
        else:  # Local or Git
            self.lbl_git_url.setVisible(True)
            self.edit_git_url.setVisible(True)
            self.lbl_branch.setVisible(True)
            self.edit_branch.setVisible(True)
            self.lbl_local_path.setVisible(True)
            self.edit_local_path.setVisible(True)
            self.btn_browse_local.setVisible(True)

    def _browse_local_folder(self):
        folder = QFileDialog.getExistingDirectory(self, "Виберіть папку репозиторію")
        if folder:
            self.edit_local_path.setText(folder)
            if not self.edit_name.text():
                self.edit_name.setText(Path(folder).name)
            if not self.edit_id.text():
                self.edit_id.setText(Path(folder).name.lower().replace(" ", "-"))

    def _validate_and_save(self):
        name = self.edit_name.text().strip()
        rid = self.edit_id.text().strip()
        if not name:
            QMessageBox.warning(self, "Помилка", "Вкажіть назву репозиторію!")
            return
        if not rid:
            rid = name.lower().replace(" ", "-")

        idx = self.combo_source_type.currentIndex()
        stypes = ["git", "local", "local_or_git"]
        source_type = stypes[idx]

        git_url = self.edit_git_url.text().strip()
        local_path = self.edit_local_path.text().strip()

        if source_type in ["git", "local_or_git"] and not git_url and not local_path:
            QMessageBox.warning(self, "Помилка", "Вкажіть Git URL або локальний шлях!")
            return

        self.result_data = {
            "id": rid,
            "name": name,
            "source_type": source_type,
            "git_url": git_url,
            "branch": self.edit_branch.text().strip() or "main",
            "local_path": local_path,
            "has_manifest": self.chk_manifest.isChecked(),
            "enabled": self.chk_enabled.isChecked(),
            "order": self.repo_data.get("order", 999),
            "custom_steps": self.repo_data.get("custom_steps", [])
        }
        self.accept()
