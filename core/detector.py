"""
Zomboid Day Launcher — System Detector & Verification Engine
Performs in-depth diagnostics on game files, launcher placement, manifests,
ZombieBuddy Java agent, zbNative DLL, and PZ-ModGuard scanner.
"""
from pathlib import Path
from typing import Dict, Any, List, Optional
from core.utils import get_app_dir
from core.manifest_parser import ManifestParser
from core.i18n import t


class SystemDetector:
    def __init__(self, config_manager):
        self.config = config_manager

    def is_launcher_next_to_game(self) -> bool:
        """Check if launcher executable is running in the same directory as ProjectZomboid64.exe."""
        app_dir = get_app_dir()
        return (app_dir / "ProjectZomboid64.exe").exists()

    def run_diagnostics(self, lang: Optional[str] = None) -> Dict[str, Any]:
        """
        Run complete diagnostics checklist:
        1. Launcher placement beside ProjectZomboid64.exe
        2. Game directory & ProjectZomboid64.exe presence
        3. Optimized JVM launch scripts (bat & json)
        4. ZombieBuddy agent & zbNative.dll
        5. PZ-ModGuard security scanner
        6. User profile folder (Zomboid saves/mods)
        7. Manifest integrity & version match
        """
        if lang is None:
            lang = self.config.language

        app_dir = get_app_dir()
        game_dir_str = self.config.game_dir
        game_dir = Path(game_dir_str) if game_dir_str else Path("")
        user_dir = Path(self.config.user_zomboid_dir)

        checks: List[Dict[str, Any]] = []

        # 1. Launcher Location Check
        launcher_beside = self.is_launcher_next_to_game()
        checks.append({
            "id": "launcher_location",
            "title": t("chk_launcher_loc", lang),
            "status": "ok" if launcher_beside else "fail",
            "passed": launcher_beside,
            "details": (
                t("chk_launcher_loc_ok", lang)
                if launcher_beside else
                t("chk_launcher_loc_fail", lang, app_dir=str(app_dir))
            )
        })

        # 2. Game Executable Check
        game_exe = game_dir / "ProjectZomboid64.exe"
        game_exe_ok = game_dir.exists() and game_exe.exists()
        checks.append({
            "id": "game_exe",
            "title": t("chk_game_exe", lang),
            "status": "ok" if game_exe_ok else "fail",
            "passed": game_exe_ok,
            "details": (
                t("chk_game_exe_found", lang)
                if game_exe_ok else
                t("chk_game_exe_missing", lang)
            )
        })

        # 3. Optimized JVM Launch Scripts
        data_dir = Path(self.config.base_dir)
        bat_normal = data_dir / "ProjectZomboid64.bat" if (data_dir / "ProjectZomboid64.bat").exists() else game_dir / "ProjectZomboid64.bat"
        bat_debug = data_dir / "ProjectZomboid64ShowConsole.bat" if (data_dir / "ProjectZomboid64ShowConsole.bat").exists() else game_dir / "ProjectZomboid64ShowConsole.bat"
        jvm_ok = bat_normal.exists() and bat_debug.exists()
        checks.append({
            "id": "jvm_scripts",
            "title": t("chk_jvm_scripts", lang),
            "status": "ok" if jvm_ok else "fail",
            "passed": jvm_ok,
            "details": (
                t("chk_jvm_scripts_ok", lang)
                if jvm_ok else
                t("chk_jvm_scripts_missing", lang)
            )
        })

        # 4. ZombieBuddy Java Agent & zbNative.dll
        zb_jar = game_dir / "ZombieBuddy.jar"
        zb_dll = game_dir / "zbNative.dll"
        zb_ok = zb_jar.exists() and zb_dll.exists()
        checks.append({
            "id": "zombie_buddy",
            "title": t("chk_zombie_buddy", lang),
            "status": "ok" if zb_ok else "fail",
            "passed": zb_ok,
            "details": (
                t("chk_zombie_buddy_ok", lang)
                if zb_ok else
                t("chk_zombie_buddy_missing", lang)
            )
        })

        # 5. PZ-ModGuard Security Scanner
        modguard = game_dir / "PZ-ModGuard.bat"
        mg_ok = modguard.exists()
        checks.append({
            "id": "modguard",
            "title": t("chk_modguard", lang),
            "status": "ok" if mg_ok else "warn",
            "passed": mg_ok,
            "details": (
                t("chk_modguard_ok", lang)
                if mg_ok else
                t("chk_modguard_missing", lang)
            )
        })

        # 6. User Profile Folder
        user_ok = user_dir.exists()
        checks.append({
            "id": "user_profile",
            "title": t("chk_user_profile", lang),
            "status": "ok" if user_ok else "warn",
            "passed": user_ok,
            "details": (
                t("chk_user_profile_ok", lang, path=str(user_dir))
                if user_ok else
                t("chk_user_profile_missing", lang, path=str(user_dir))
            )
        })

        # 7. Modpack Manifest & Version Match (Repo vs Launcher)
        from core.version_checker import VersionChecker, VersionStatus
        vc = VersionChecker(self.config)
        ver_info = vc.check_status(lang)
        repo_v = ver_info.get("repo_version", "1.0.4")
        inst_v = ver_info.get("installed_version") or self.config.get("installed_version", "")
        ver_status = ver_info.get("status")
        v_ok = (ver_status == VersionStatus.UP_TO_DATE)

        checks.append({
            "id": "version_match",
            "title": t("chk_version_match", lang),
            "status": "ok" if v_ok else "warn",
            "passed": v_ok,
            "details": (
                t("chk_version_synced", lang, version=repo_v)
                if v_ok else
                t("chk_version_mismatch", lang, installed=inst_v or "—", repo=repo_v)
            )
        })

        # Calculate scores
        passed_count = sum(1 for c in checks if c["passed"])
        total_count = len(checks)
        all_ok = (passed_count == total_count)
        is_ready = launcher_beside and game_exe_ok and jvm_ok and zb_ok

        return {
            "checks": checks,
            "launcher_beside_game": launcher_beside,
            "passed_count": passed_count,
            "total_count": total_count,
            "all_passed": all_ok,
            "is_ready": is_ready,
            "game_dir": str(game_dir),
            "app_dir": str(app_dir),
        }
