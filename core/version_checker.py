import os
import json
import time
import urllib.request
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple
from PyQt6.QtCore import QThread, pyqtSignal

from core.manifest_parser import ManifestParser
from core.utils import get_app_dir
from core.i18n import t

CURRENT_LAUNCHER_VERSION = "1.1.1"
REMOTE_MANIFEST_URL = "https://raw.githubusercontent.com/PraydE007/Zomboid-Day-Launcher-Files/main/launcher-manifest.json"
GITHUB_LATEST_RELEASE_API = "https://api.github.com/repos/PraydE007/Zomboid-Day-Launcher/releases/latest"


class VersionStatus:
    UP_TO_DATE = "UP_TO_DATE"
    UPDATE_AVAILABLE = "UPDATE_AVAILABLE"
    NOT_INSTALLED = "NOT_INSTALLED"
    GAME_NOT_FOUND = "GAME_NOT_FOUND"
    INVALID_PLACEMENT = "INVALID_PLACEMENT"


class RemoteUpdateCheckThread(QThread):
    """
    Background worker that silently checks for remote modpack manifest updates
    and launcher releases without blocking the UI.
    """
    sig_update_checked = pyqtSignal(dict)

    def __init__(self, version_checker, parent=None):
        super().__init__(parent)
        self.checker = version_checker

    def run(self):
        try:
            res = self.checker.fetch_remote_updates_sync(force=True)
            self.sig_update_checked.emit(res)
        except Exception:
            self.sig_update_checked.emit({})


class VersionChecker:
    def __init__(self, config_manager):
        self.config = config_manager
        self._last_remote_check_time = 0.0
        self._cached_remote_result: Optional[Dict[str, Any]] = None

    def get_cache_dir(self) -> Path:
        base_dir = Path(self.config.base_dir)
        cache_dir = base_dir / "cache"
        cache_dir.mkdir(parents=True, exist_ok=True)
        return cache_dir

    def fetch_remote_updates_sync(self, force: bool = False, timeout: float = 3.0) -> Dict[str, Any]:
        """
        Check remote GitHub raw manifest and latest release.
        Saves downloaded remote manifest to cache/remote_manifest.json.
        """
        now = time.time()
        cache_dir = self.get_cache_dir()
        cached_manifest_file = cache_dir / "remote_manifest.json"

        # Return cached in-memory if fresh (< 120s) and not forced
        if not force and self._cached_remote_result and (now - self._last_remote_check_time < 120):
            return self._cached_remote_result

        remote_data: Dict[str, Any] = {
            "remote_manifest_version": "",
            "remote_launcher_version": "",
            "has_update": False,
            "manifest_path": None,
            "download_url": ""
        }

        # 1. Fetch remote manifest
        try:
            req = urllib.request.Request(
                REMOTE_MANIFEST_URL,
                headers={"User-Agent": "Zomboid-Day-Launcher"}
            )
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                content = resp.read().decode("utf-8")
                parsed_manifest = json.loads(content)
                with open(cached_manifest_file, "w", encoding="utf-8") as f:
                    f.write(content)
                remote_data["remote_manifest_version"] = str(parsed_manifest.get("project", {}).get("version", "")).lstrip("v")
                remote_data["manifest_path"] = cached_manifest_file
        except Exception:
            if cached_manifest_file.exists():
                try:
                    with open(cached_manifest_file, "r", encoding="utf-8") as f:
                        parsed_manifest = json.load(f)
                    remote_data["remote_manifest_version"] = str(parsed_manifest.get("project", {}).get("version", "")).lstrip("v")
                    remote_data["manifest_path"] = cached_manifest_file
                except Exception:
                    pass

        # 2. Fetch latest GitHub launcher release tag
        try:
            req_rel = urllib.request.Request(
                GITHUB_LATEST_RELEASE_API,
                headers={"User-Agent": "Zomboid-Day-Launcher"}
            )
            with urllib.request.urlopen(req_rel, timeout=timeout) as resp:
                rel_json = json.loads(resp.read().decode("utf-8"))
                tag = str(rel_json.get("tag_name", "")).lstrip("v")
                remote_data["remote_launcher_version"] = tag
                for asset in rel_json.get("assets", []):
                    if asset.get("name") == "Zomboid-Day-Launcher.exe":
                        remote_data["download_url"] = asset.get("browser_download_url", "")
                        break
        except Exception:
            pass

        self._last_remote_check_time = now
        self._cached_remote_result = remote_data
        return remote_data

    def check_status(self, lang: Optional[str] = None) -> Dict[str, Any]:
        if lang is None:
            lang = self.config.language

        base_dir = Path(self.config.base_dir)

        # 0. Check launcher placement strictly: must be beside ProjectZomboid64.exe
        app_dir = get_app_dir()
        game_exe_beside = (app_dir / "ProjectZomboid64.exe").exists()
        saved_version = str(self.config.get("installed_version", "")).lstrip("v")

        if not game_exe_beside:
            return {
                "status": VersionStatus.INVALID_PLACEMENT,
                "version": CURRENT_LAUNCHER_VERSION,
                "repo_version": CURRENT_LAUNCHER_VERSION,
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
                "version": CURRENT_LAUNCHER_VERSION,
                "repo_version": CURRENT_LAUNCHER_VERSION,
                "installed_version": saved_version,
                "text": t("status_game_not_found", lang),
                "color": "#ef4444",
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

        # Resolve target manifest:
        # Priority 1: local repository from config (for dev / local path)
        # Priority 2: cached repo manifest (zd-launcher/cache/repos/zomboid-day-files/launcher-manifest.json)
        # Priority 3: downloaded remote manifest (zd-launcher/cache/remote_manifest.json)
        # Priority 4: try fast network fetch if no manifest found yet
        target_manifest: Optional[Path] = None
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

        remote_manifest_cached = base_dir / "cache" / "remote_manifest.json"
        if not target_manifest and remote_manifest_cached.exists():
            target_manifest = remote_manifest_cached

        # On another PC without local/cached manifest, check remote manifest
        if not target_manifest and self.config.get("auto_check_updates", True):
            try:
                rem = self.fetch_remote_updates_sync(force=False, timeout=2.0)
                if rem.get("manifest_path") and Path(rem["manifest_path"]).exists():
                    target_manifest = Path(rem["manifest_path"])
            except Exception:
                pass

        repo_version = CURRENT_LAUNCHER_VERSION
        if target_manifest and target_manifest.exists():
            try:
                p = ManifestParser(target_manifest, context)
                repo_version = str(p.version or CURRENT_LAUNCHER_VERSION).lstrip("v")
            except Exception:
                pass

        # Check if remote version is known from cached check
        if self._cached_remote_result:
            rem_ver = self._cached_remote_result.get("remote_manifest_version")
            if rem_ver and rem_ver > repo_version:
                repo_version = rem_ver

        if not target_manifest or not target_manifest.exists():
            # Fallback when completely offline and no manifest ever downloaded
            standard_required = [
                (base_dir / "ProjectZomboid64.bat") if (base_dir / "ProjectZomboid64.bat").exists() else (game_dir / "ProjectZomboid64.bat"),
                (base_dir / "ProjectZomboid64ShowConsole.bat") if (base_dir / "ProjectZomboid64ShowConsole.bat").exists() else (game_dir / "ProjectZomboid64ShowConsole.bat"),
                game_dir / "ZombieBuddy.jar",
                game_dir / "zbNative.dll"
            ]
            missing = [str(f.name) for f in standard_required if not f.exists()]
            installed = len(missing) == 0
            installed_ver = str(self.config.get("installed_version", "") or (CURRENT_LAUNCHER_VERSION if installed else "")).lstrip("v")

            if not installed:
                return {
                    "status": VersionStatus.NOT_INSTALLED,
                    "version": "",
                    "repo_version": repo_version,
                    "installed_version": "",
                    "text": t("status_not_installed", lang),
                    "color": "#ef4444",
                    "is_installed": False,
                    "missing_files": missing
                }

            is_up = (installed_ver == repo_version)
            return {
                "status": VersionStatus.UP_TO_DATE if is_up else VersionStatus.UPDATE_AVAILABLE,
                "version": installed_ver if is_up else f"{installed_ver} → {repo_version}",
                "repo_version": repo_version,
                "installed_version": installed_ver,
                "text": t("status_up_to_date", lang) if is_up else f"{t('status_update_available', lang)} (v{repo_version})",
                "color": "#22c55e" if is_up else "#f59e0b",
                "is_installed": True,
                "missing_files": []
            }

        try:
            parser = ManifestParser(target_manifest, context)
            is_valid, missing, outdated = parser.validate_installation()
            manifest_version = str(parser.version or CURRENT_LAUNCHER_VERSION).lstrip("v")
            saved_version = str(self.config.get("installed_version", "")).lstrip("v")

            # 1. Missing required files -> Not Installed
            if missing:
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

            # 2. File hash mismatch (outdated / modified files) -> Update Available
            if outdated:
                return {
                    "status": VersionStatus.UPDATE_AVAILABLE,
                    "version": f"v{manifest_version}",
                    "repo_version": manifest_version,
                    "installed_version": saved_version or "unknown",
                    "text": f"{t('status_update_available', lang)} (v{manifest_version})",
                    "color": "#f59e0b",  # Amber
                    "is_installed": True,
                    "missing_files": outdated
                }

            # 3. Version mismatch between saved config and latest manifest -> Update Available
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

            # 4. Check if remote launcher executable version is newer
            if self._cached_remote_result:
                rem_launcher_v = self._cached_remote_result.get("remote_launcher_version", "")
                if rem_launcher_v and rem_launcher_v > CURRENT_LAUNCHER_VERSION:
                    return {
                        "status": VersionStatus.UPDATE_AVAILABLE,
                        "version": f"{CURRENT_LAUNCHER_VERSION} → {rem_launcher_v}",
                        "repo_version": rem_launcher_v,
                        "installed_version": CURRENT_LAUNCHER_VERSION,
                        "text": f"{t('status_update_available', lang)} (v{rem_launcher_v})",
                        "color": "#f59e0b",
                        "is_installed": True,
                        "missing_files": []
                    }

            # 5. Clean, verified installation with matching SHA-256 hashes
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
