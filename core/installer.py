import os
import shutil
import time
from pathlib import Path
from typing import Dict, Any, List, Optional
from PyQt6.QtCore import QThread, pyqtSignal

from core.repo_manager import RepoManager
from core.manifest_parser import ManifestParser


class InstallWorker(QThread):
    sig_progress = pyqtSignal(int, str)       # progress (0-100), message
    sig_log = pyqtSignal(str)                 # log string
    sig_finished = pyqtSignal(bool, str)      # success, result summary
    sig_version = pyqtSignal(str)             # detected version

    def __init__(self, config_manager, parent=None):
        super().__init__(parent)
        self.config = config_manager
        self._is_cancelled = False

    def cancel(self):
        self._is_cancelled = True

    def run(self):
        try:
            self.sig_log.emit("=== ПОЧАТОК ПРОЦЕСУ ВСТАНОВЛЕННЯ ТА НАЛАШТУВАННЯ ===")
            game_dir = Path(self.config.game_dir)
            user_dir = Path(self.config.user_zomboid_dir)
            base_dir = Path(self.config.base_dir)
            cache_dir = base_dir / "cache" / "repos"

            if not game_dir.exists():
                self.sig_finished.emit(False, f"Папку Project Zomboid не знайдено: {game_dir}")
                return

            context = {
                "GAME_DIR": str(game_dir),
                "USER_ZOMBOID_DIR": str(user_dir),
                "MODS_DIR": str(user_dir / "mods"),
                "LAUNCHER_DIR": str(base_dir)
            }

            repo_mgr = RepoManager(cache_dir, context, log_callback=lambda msg: self.sig_log.emit(msg))

            repos = self.config.repositories
            enabled_repos = [r for r in repos if r.get("enabled", True)]
            total_repos = len(enabled_repos)

            if total_repos == 0:
                self.sig_finished.emit(False, "Не вибрано жодного активного репозиторію для встановлення!")
                return

            self.sig_progress.emit(5, "Синхронізація репозиторіїв...")
            all_steps = []
            detected_version = "1.0.0"

            # Step 1: Sync all repositories in order
            for i, repo_info in enumerate(enabled_repos, start=1):
                if self._is_cancelled:
                    self.sig_finished.emit(False, "Операцію скасовано користувачем.")
                    return

                repo_name = repo_info.get("name", repo_info.get("id"))
                self.sig_log.emit(f"[{i}/{total_repos}] Підготовка репозиторію: {repo_name} (Черга #{repo_info.get('order')})")
                self.sig_progress.emit(int(5 + (i / total_repos) * 35), f"Синхронізація: {repo_name}...")

                repo_path = repo_mgr.sync_repository(repo_info)

                # Check if this repository contains project manifest to grab version
                manifest_path = repo_path / "launcher-manifest.json"
                if manifest_path.exists():
                    try:
                        parser = ManifestParser(manifest_path, context)
                        detected_version = parser.version
                        self.sig_version.emit(detected_version)
                        self.sig_log.emit(f"  → Зчитано версію проєкту з маніфесту: v{detected_version}")
                    except Exception as e:
                        self.sig_log.emit(f"  → Помилка зчитування маніфесту: {e}")

                steps = repo_mgr.get_repo_steps(repo_info, repo_path)
                all_steps.extend(steps)

            # Step 2: Sort all install steps by order
            all_steps.sort(key=lambda s: s.get("order", 999))
            total_steps = len(all_steps)
            self.sig_log.emit(f"Всього кроків для встановлення: {total_steps}")

            if total_steps == 0:
                self.sig_finished.emit(True, "Репозиторії синхронізовано, кроків копіювання немає.")
                return

            # Step 3: Execute installation steps
            for idx, step in enumerate(all_steps, start=1):
                if self._is_cancelled:
                    self.sig_finished.emit(False, "Операцію скасовано користувачем.")
                    return

                step_name = step.get("name", f"Крок {idx}")
                step_type = step.get("type", "copy_file")
                source = Path(step.get("source"))
                destination = Path(step.get("destination"))
                overwrite = step.get("overwrite", True)
                backup = step.get("backup", False)

                pct = int(40 + (idx / total_steps) * 55)
                self.sig_progress.emit(pct, f"Встановлення ({idx}/{total_steps}): {step_name}...")
                self.sig_log.emit(f"Виконання кроку #{step.get('order')}: {step_name} [{step_type}]")

                if step_type == "copy_dir_contents":
                    if not source.exists() or not source.is_dir():
                        self.sig_log.emit(f"  [Помилка] Папку-джерело не знайдено: {source}")
                        continue

                    destination.mkdir(parents=True, exist_ok=True)
                    for item in source.iterdir():
                        target_file = destination / item.name
                        if target_file.exists() and backup and not target_file.suffix == ".bak":
                            bak_file = target_file.with_suffix(target_file.suffix + ".bak")
                            try:
                                shutil.copy2(target_file, bak_file)
                                self.sig_log.emit(f"    Резервна копія: {bak_file.name}")
                            except Exception:
                                pass

                        if item.is_dir():
                            shutil.copytree(item, target_file, dirs_exist_ok=True)
                            self.sig_log.emit(f"    Скопійовано папку: {item.name} -> {target_file}")
                        else:
                            shutil.copy2(item, target_file)
                            self.sig_log.emit(f"    Встановлено файл: {item.name}")

                elif step_type == "copy_file":
                    if not source.exists():
                        self.sig_log.emit(f"  [Помилка] Файл не знайдено: {source}")
                        continue

                    destination_path = destination
                    if destination.is_dir() or not destination.suffix:
                        destination.mkdir(parents=True, exist_ok=True)
                        destination_path = destination / source.name

                    if destination_path.exists() and backup:
                        bak_file = destination_path.with_suffix(destination_path.suffix + ".bak")
                        try:
                            shutil.copy2(destination_path, bak_file)
                            self.sig_log.emit(f"    Резервна копія: {bak_file.name}")
                        except Exception:
                            pass

                    destination_path.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copy2(source, destination_path)
                    self.sig_log.emit(f"    Встановлено: {source.name} -> {destination_path}")

            # Save version and timestamp
            self.config.set("installed_version", detected_version)
            self.config.set("last_sync_time", time.strftime("%Y-%m-%d %H:%M:%S"))

            self.sig_progress.emit(100, "Встановлення завершено успішно!")
            self.sig_log.emit("=== ВСІ КОМПОНЕНТИ ТА ПАТЧІ ВСТАНОВЛЕНО УСПІШНО! ===")
            self.sig_finished.emit(True, f"Успішно встановлено Zomboid Day v{detected_version}")

        except Exception as e:
            import traceback
            err_details = traceback.format_exc()
            self.sig_log.emit(f"[Критична помилка встановлення]:\n{err_details}")
            self.sig_finished.emit(False, f"Помилка встановлення: {str(e)}")
