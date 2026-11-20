import os
import shutil
import time
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple
from PyQt6.QtCore import QThread, pyqtSignal

from core.repo_manager import RepoManager
from core.manifest_parser import ManifestParser
from core.utils import get_app_dir
from core.i18n import t


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

            # Step 1: Open Steam Workshop Mod collection page
            lang = self.config.language
            steam_url = "steam://url/CommunityFilePage/3831192498"
            web_url = "https://steamcommunity.com/sharedfiles/filedetails/?id=3831192498"
            self.sig_progress.emit(2, t("step_steam_open", lang))
            self.sig_log.emit(f"🌐 [Крок 1] Відкриття сторінки модифікацій у Steam Workshop: {web_url}")

            steam_opened = False
            try:
                os.startfile(steam_url)
                steam_opened = True
                self.sig_log.emit("  → Надіслано запит на відкриття сторінки у клієнті Steam.")
            except Exception as e:
                self.sig_log.emit(f"  → Steam клієнт не відповів ({e}). Відкриваємо у веб-браузері...")

            if not steam_opened:
                try:
                    import webbrowser
                    webbrowser.open(web_url)
                    self.sig_log.emit("  → Сторінку відкрито у браузері за замовчуванням.")
                except Exception as ex:
                    self.sig_log.emit(f"  → Не вдалося відкрити посилання: {ex}")

            time.sleep(0.5)

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

                pct = int(40 + (idx / total_steps) * 55)
                self.sig_progress.emit(pct, f"Встановлення ({idx}/{total_steps}): {step_name}...")
                self.sig_log.emit(f"Виконання кроку #{step.get('order')}: {step_name} [{step_type}]")

                if step_type == "open_url":
                    url = step.get("url") or step.get("fallback_url", "")
                    if url:
                        try:
                            os.startfile(url)
                            self.sig_log.emit(f"  → Відкрито посилання: {url}")
                        except Exception:
                            try:
                                import webbrowser
                                webbrowser.open(step.get("fallback_url", url))
                            except Exception:
                                pass
                    continue

                source = Path(step.get("source")) if step.get("source") else Path("")
                destination = Path(step.get("destination")) if step.get("destination") else Path("")
                overwrite = step.get("overwrite", True)
                backup = step.get("backup", False)

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


def reinstall_step(step_id: str, config_manager, log_callback=None) -> Tuple[bool, str]:
    """
    Directly reinstall/execute a specific installation or verification step.
    Supports individual re-execution of:
      - 'jvm_scripts' / 'step_game_configs'
      - 'zombie_buddy' / 'step_zombie_buddy'
      - 'modguard' / 'step_modguard'
      - 'steam_workshop' / 'step_steam_workshop'
    """
    def log(msg: str):
        if log_callback:
            log_callback(msg)

    game_dir = Path(config_manager.game_dir)
    if not game_dir.exists():
        return False, f"Game folder not found: {game_dir}"

    base_dir = get_app_dir()

    # 1. JVM Startup Scripts
    if step_id in ("jvm_scripts", "step_game_configs"):
        candidates = [
            Path(r"C:\Users\user\Desktop\Zomboid-Day-Launcher-Files\game-configuration-files"),
            base_dir / "cache" / "repos" / "zomboid-day-files" / "game-configuration-files",
            base_dir / "game-configuration-files"
        ]
        source_dir = None
        for c in candidates:
            if c.exists() and (c / "ProjectZomboid64.bat").exists():
                source_dir = c
                break

        if not source_dir:
            return False, "Source files for JVM scripts not found."

        try:
            copied = []
            for item in source_dir.iterdir():
                if item.is_file():
                    target = game_dir / item.name
                    if target.exists():
                        try:
                            shutil.copy2(target, target.with_suffix(target.suffix + ".bak"))
                        except Exception:
                            pass
                    shutil.copy2(item, target)
                    copied.append(item.name)
            log(f"Reinstalled JVM scripts: {', '.join(copied)}")
            return True, f"Reinstalled: {', '.join(copied)}"
        except Exception as e:
            return False, f"Copy error: {e}"

    # 2. ZombieBuddy & zbNative DLL
    elif step_id in ("zombie_buddy", "step_zombie_buddy"):
        candidates = [
            Path(r"C:\Users\user\Desktop\Zomboid-Day-Launcher-Files\ZombieBuddy"),
            base_dir / "cache" / "repos" / "zomboid-day-files" / "ZombieBuddy",
            base_dir / "ZombieBuddy"
        ]
        source_dir = None
        for c in candidates:
            if c.exists() and (c / "ZombieBuddy.jar").exists():
                source_dir = c
                break

        if not source_dir:
            return False, "Source files for ZombieBuddy not found."

        try:
            copied = []
            for item in source_dir.iterdir():
                if item.is_file():
                    target = game_dir / item.name
                    if target.exists():
                        try:
                            shutil.copy2(target, target.with_suffix(target.suffix + ".bak"))
                        except Exception:
                            pass
                    shutil.copy2(item, target)
                    copied.append(item.name)
            log(f"Reinstalled ZombieBuddy: {', '.join(copied)}")
            return True, f"Reinstalled: {', '.join(copied)}"
        except Exception as e:
            return False, f"Copy error: {e}"

    # 3. PZ-ModGuard Security Scanner
    elif step_id in ("modguard", "step_modguard"):
        candidates = [
            base_dir / "cache" / "repos" / "pz-modguard" / "PZ-ModGuard.bat",
            Path(r"C:\Users\user\Desktop\Zomboid-Day-Launcher-Files\PZ-ModGuard.bat"),
            base_dir / "PZ-ModGuard.bat"
        ]
        source_bat = None
        for c in candidates:
            if c.exists():
                source_bat = c
                break

        if not source_bat:
            cache_dir = base_dir / "cache" / "repos"
            context = {"GAME_DIR": str(game_dir), "USER_ZOMBOID_DIR": str(config_manager.user_zomboid_dir)}
            repo_mgr = RepoManager(cache_dir, context)
            modguard_repo = config_manager.get_repo("pz-modguard")
            if modguard_repo:
                try:
                    repo_path = repo_mgr.sync_repository(modguard_repo)
                    if (repo_path / "PZ-ModGuard.bat").exists():
                        source_bat = repo_path / "PZ-ModGuard.bat"
                except Exception:
                    pass

        if not source_bat or not source_bat.exists():
            return False, "PZ-ModGuard.bat not found."

        try:
            target = game_dir / "PZ-ModGuard.bat"
            shutil.copy2(source_bat, target)
            log(f"Reinstalled PZ-ModGuard.bat into {target}")
            return True, "PZ-ModGuard.bat successfully reinstalled!"
        except Exception as e:
            return False, f"PZ-ModGuard copy error: {e}"

    # 4. Steam Workshop Collection
    elif step_id in ("steam_workshop", "step_steam_workshop"):
        try:
            os.startfile("steam://url/CommunityFilePage/3831192498")
        except Exception:
            import webbrowser
            webbrowser.open("https://steamcommunity.com/sharedfiles/filedetails/?id=3831192498")
        return True, "Opened Steam Workshop collection!"

    return False, f"Unknown step: {step_id}"
