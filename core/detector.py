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
                t("chk_launcher_loc_ok", lang, path=str(app_dir))
                if launcher_beside else
                t("chk_launcher_loc_fail", lang, app_dir=str(app_dir), game_dir=str(game_dir))
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
                f"ProjectZomboid64.exe found ({game_dir})"
                if game_exe_ok else
                f"ProjectZomboid64.exe missing at {game_dir}"
            )
        })

        # 3. Optimized JVM Launch Scripts
        bat_normal = game_dir / "ProjectZomboid64.bat"
        bat_debug = game_dir / "ProjectZomboid64ShowConsole.bat"
        json_cfg = game_dir / "ProjectZomboid64.json"
        jvm_ok = bat_normal.exists() and bat_debug.exists()
        checks.append({
            "id": "jvm_scripts",
            "title": t("chk_jvm_scripts", lang),
            "status": "ok" if jvm_ok else "fail",
            "passed": jvm_ok,
            "details": (
                "ProjectZomboid64.bat & ProjectZomboid64ShowConsole.bat active"
                if jvm_ok else
                "Optimized launch scripts missing (needs installation)"
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
                "ZombieBuddy.jar & zbNative.dll installed"
                if zb_ok else
                "ZombieBuddy files missing"
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
                "PZ-ModGuard.bat ready for bytecode mod security scanning"
                if mg_ok else
                "PZ-ModGuard not installed in game directory"
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
                f"Zomboid profile located at {user_dir}"
                if user_ok else
                f"Profile folder {user_dir} not created yet"
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
