import os
from pathlib import Path
from typing import Dict, Any, List, Optional
from core.manifest_parser import ManifestParser
from core.utils import get_app_dir
from core.i18n import t


class VersionStatus:
    UP_TO_DATE = "UP_TO_DATE"
    UPDATE_AVAILABLE = "UPDATE_AVAILABLE"
    NOT_INSTALLED = "NOT_INSTALLED"
    GAME_NOT_FOUND = "GAME_NOT_FOUND"
    INVALID_PLACEMENT = "INVALID_PLACEMENT"


class VersionChecker:
    def __init__(self, config_manager):
        self.config = config_manager

    def check_status(self, lang: Optional[str] = None) -> Dict[str, Any]:
        if lang is None:
            lang = self.config.language

        base_dir = Path(self.config.base_dir)

        # Resolve target manifest & repository version upfront
        target_manifest = None
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

        repo_version = "1.0.1"
        if target_manifest and target_manifest.exists():
            try:
                p = ManifestParser(target_manifest)
                repo_version = str(p.version or "1.0.1").lstrip("v")
            except Exception:
                pass

        saved_version = str(self.config.get("installed_version", "")).lstrip("v")

        # 0. Check launcher placement strictly: must be beside ProjectZomboid64.exe
        app_dir = get_app_dir()
        game_exe_beside = (app_dir / "ProjectZomboid64.exe").exists()
        if not game_exe_beside:
            return {
                "status": VersionStatus.INVALID_PLACEMENT,
                "version": repo_version,
                "repo_version": repo_version,
                "installed_version": saved_version,
                "text": t("status_invalid_placement", lang),
                "color": "#ef4444",
                "is_installed": False,
                "missing_files": [
                    t("chk_launcher_loc_fail", lang, app_dir=str(app_dir))
                ]
            }

        game_dir_str = self.config.game_dir
        if not game_dir_str or not Path(game_dir_str).exists():
            return {
                "status": VersionStatus.GAME_NOT_FOUND,
                "version": repo_version,
                "repo_version": repo_version,
                "installed_version": saved_version,
                "text": t("status_game_not_found", lang),
                "color": "#ef4444",  # Red
                "is_installed": False,
                "missing_files": ["Game folder does not exist"]
            }

        game_dir = Path(game_dir_str)
        user_dir = Path(self.config.user_zomboid_dir)

        context = {
            "GAME_DIR": str(game_dir),
            "USER_ZOMBOID_DIR": str(user_dir),
            "MODS_DIR": str(user_dir / "mods"),
            "LAUNCHER_DIR": str(base_dir)
        }

        if not target_manifest:
            standard_required = [
                game_dir / "ProjectZomboid64.bat",
                game_dir / "ProjectZomboid64ShowConsole.bat",
                game_dir / "ZombieBuddy.jar"
            ]
            missing = [str(f) for f in standard_required if not f.exists()]
            installed = len(missing) == 0
            installed_ver = str(self.config.get("installed_version", "") or ("1.0.1" if installed else "")).lstrip("v")

            if not installed:
                return {
                    "status": VersionStatus.NOT_INSTALLED,
                    "version": "",
                    "repo_version": "1.0.1",
                    "installed_version": "",
                    "text": t("status_not_installed", lang),
                    "color": "#ef4444",
                    "is_installed": False,
                    "missing_files": missing
                }
            return {
                "status": VersionStatus.UP_TO_DATE,
                "version": installed_ver,
                "repo_version": installed_ver,
                "installed_version": installed_ver,
                "text": t("status_up_to_date", lang),
                "color": "#22c55e",  # Green
                "is_installed": True,
                "missing_files": []
            }

        try:
            parser = ManifestParser(target_manifest, context)
            is_valid, missing = parser.validate_installation()
            manifest_version = str(parser.version or "1.0.1").lstrip("v")
            saved_version = str(self.config.get("installed_version", "")).lstrip("v")

            if not is_valid:
                return {
                    "status": VersionStatus.NOT_INSTALLED,
                    "version": manifest_version,
                    "repo_version": manifest_version,
                    "installed_version": saved_version,
                    "text": t("status_not_installed", lang),
                    "color": "#ef4444",
                    "is_installed": False,
                    "missing_files": missing
                }

            if saved_version and saved_version != manifest_version:
                return {
                    "status": VersionStatus.UPDATE_AVAILABLE,
                    "version": f"{saved_version} → {manifest_version}",
                    "repo_version": manifest_version,
                    "installed_version": saved_version,
                    "text": f"{t('status_update_available', lang)} (v{manifest_version})",
                    "color": "#f59e0b",  # Amber
                    "is_installed": True,
                    "missing_files": []
                }

            return {
                "status": VersionStatus.UP_TO_DATE,
                "version": manifest_version,
                "repo_version": manifest_version,
                "installed_version": saved_version or manifest_version,
                "text": t("status_up_to_date", lang),
                "color": "#22c55e",  # Green
                "is_installed": True,
                "missing_files": []
            }
        except Exception as e:
            return {
                "status": VersionStatus.NOT_INSTALLED,
                "version": "",
                "text": f"{t('error', lang)}: {e}",
                "color": "#ef4444",
                "is_installed": False,
                "missing_files": [str(e)]
            }
