import os
from pathlib import Path
from typing import Dict, Any, List, Optional
from core.manifest_parser import ManifestParser


class VersionStatus:
    UP_TO_DATE = "UP_TO_DATE"
    UPDATE_AVAILABLE = "UPDATE_AVAILABLE"
    NOT_INSTALLED = "NOT_INSTALLED"
    GAME_NOT_FOUND = "GAME_NOT_FOUND"


class VersionChecker:
    def __init__(self, config_manager):
        self.config = config_manager

    def check_status(self) -> Dict[str, Any]:
        game_dir_str = self.config.game_dir
        if not game_dir_str or not Path(game_dir_str).exists():
            return {
                "status": VersionStatus.GAME_NOT_FOUND,
                "version": "—",
                "text": "Папку гри не знайдено",
                "color": "#ef4444",  # Red
                "is_installed": False,
                "missing_files": ["Папка гри не існує"]
            }

        game_dir = Path(game_dir_str)
        user_dir = Path(self.config.user_zomboid_dir)
        base_dir = Path(self.config.base_dir)

        context = {
            "GAME_DIR": str(game_dir),
            "USER_ZOMBOID_DIR": str(user_dir),
            "MODS_DIR": str(user_dir / "mods"),
            "LAUNCHER_DIR": str(base_dir)
        }

        # Check main repo manifest for required files & version
        target_manifest = None

        # Check local path of first repo or cached repo
        repos = self.config.repositories
        for r in repos:
            if r.get("has_manifest"):
                local_p = Path(r.get("local_path", ""))
                if local_p.exists() and (local_p / "launcher-manifest.json").exists():
                    target_manifest = local_p / "launcher-manifest.json"
                    break
                cached_p = base_dir / "cache" / "repos" / r.get("id", "") / "launcher-manifest.json"
                if cached_p.exists():
                    target_manifest = cached_p
                    break

        if not target_manifest:
            # Fallback check standard files
            standard_required = [
                game_dir / "ProjectZomboid64.bat",
                game_dir / "ProjectZomboid64ShowConsole.bat",
                game_dir / "ZombieBuddy.jar"
            ]
            missing = [str(f) for f in standard_required if not f.exists()]
            installed = len(missing) == 0
            installed_ver = self.config.get("installed_version", "") or ("1.0.0" if installed else "")

            if not installed:
                return {
                    "status": VersionStatus.NOT_INSTALLED,
                    "version": "Не встановлено",
                    "text": "Не встановлено",
                    "color": "#ef4444",
                    "is_installed": False,
                    "missing_files": missing
                }
            return {
                "status": VersionStatus.UP_TO_DATE,
                "version": f"v{installed_ver}",
                "text": "Актуальна",
                "color": "#10b981",  # Green
                "is_installed": True,
                "missing_files": []
            }

        # Validate with manifest
        try:
            parser = ManifestParser(target_manifest, context)
            is_valid, missing = parser.validate_installation()
            manifest_version = parser.version
            saved_version = self.config.get("installed_version", "")

            if not is_valid:
                return {
                    "status": VersionStatus.NOT_INSTALLED,
                    "version": f"v{manifest_version}",
                    "text": "Не встановлено",
                    "color": "#ef4444",
                    "is_installed": False,
                    "missing_files": missing
                }

            if saved_version and saved_version != manifest_version:
                return {
                    "status": VersionStatus.UPDATE_AVAILABLE,
                    "version": f"v{manifest_version}",
                    "text": f"Доступне оновлення (v{manifest_version})",
                    "color": "#f59e0b",  # Amber
                    "is_installed": True,
                    "missing_files": []
                }

            return {
                "status": VersionStatus.UP_TO_DATE,
                "version": f"v{manifest_version}",
                "text": "Актуальна",
                "color": "#10b981",  # Green
                "is_installed": True,
                "missing_files": []
            }
        except Exception as e:
            return {
                "status": VersionStatus.NOT_INSTALLED,
                "version": "Помилка",
                "text": f"Помилка маніфесту: {e}",
                "color": "#ef4444",
                "is_installed": False,
                "missing_files": [str(e)]
            }
