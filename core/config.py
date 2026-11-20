import os
import sys
import json
import winreg
from pathlib import Path
from typing import Dict, Any, List, Optional
from core.utils import get_resource_path, get_app_dir

CONFIG_FILE_NAME = "launcher_config.json"

DEFAULT_REPOSITORIES = [
    {
        "id": "zomboid-day-files",
        "name": "Zomboid Day Core (Конфіги, Патчі, ZombieBuddy)",
        "order": 1,
        "enabled": True,
        "source_type": "local_or_git",
        "local_path": r"C:\Users\user\Desktop\Zomboid-Day-Launcher-Files",
        "git_url": "https://github.com/PraydE007/Zomboid-Day-Launcher-Files.git",
        "branch": "main",
        "has_manifest": True,
        "description": "Основний репозиторій із маніфестом, оптимізованими JVM батниками та ZombieBuddy"
    },
    {
        "id": "pz-modguard",
        "name": "PZ-ModGuard (Сканер безпеки модів)",
        "order": 2,
        "enabled": True,
        "source_type": "git",
        "local_path": "",
        "git_url": "https://github.com/KodeMannn/PZ-ModGuard.git",
        "branch": "main",
        "has_manifest": False,
        "description": "Автономний сканер байткоду та безпеки Java/бінарних модів для Build 42+",
        "custom_steps": [
            {
                "order": 1,
                "type": "copy_file",
                "name": "Скрипт PZ-ModGuard.bat",
                "source": "PZ-ModGuard.bat",
                "destination": "{GAME_DIR}\\PZ-ModGuard.bat",
                "overwrite": True,
                "backup": False
            }
        ]
    }
]


def detect_steam_pz_path() -> str:
    """Auto-detect Project Zomboid installation directory via Steam registry, local folder, and common paths."""
    # 0. Check if launcher is located right inside Project Zomboid directory
    app_dir = get_app_dir()
    if (app_dir / "ProjectZomboid64.exe").exists():
        return str(app_dir)

    candidates = []

    # 1. Check Windows Registry for Steam install path
    for hkey, subkey in [
        (winreg.HKEY_CURRENT_USER, r"Software\Valve\Steam"),
        (winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\WOW6432Node\Valve\Steam"),
        (winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\Valve\Steam"),
    ]:
        try:
            with winreg.OpenKey(hkey, subkey) as key:
                val, _ = winreg.QueryValueEx(key, "SteamPath")
                if val:
                    steam_path = Path(val.replace("/", "\\"))
                    candidates.append(steam_path / "steamapps" / "common" / "ProjectZomboid")

                    # Also check libraryfolders.vdf
                    vdf_file = steam_path / "steamapps" / "libraryfolders.vdf"
                    if vdf_file.exists():
                        try:
                            content = vdf_file.read_text(encoding="utf-8", errors="ignore")
                            import re
                            for m in re.finditer(r'"path"\s+"([^"]+)"', content):
                                lib_path = Path(m.group(1).replace("\\\\", "\\"))
                                candidates.append(lib_path / "steamapps" / "common" / "ProjectZomboid")
                        except Exception:
                            pass
        except Exception:
            pass

    # 2. Common manual drive locations
    for drive in ["C:", "D:", "E:", "F:", "G:"]:
        candidates.append(Path(f"{drive}\\Program Files (x86)\\Steam\\steamapps\\common\\ProjectZomboid"))
        candidates.append(Path(f"{drive}\\SteamLibrary\\steamapps\\common\\ProjectZomboid"))
        candidates.append(Path(f"{drive}\\Games\\ProjectZomboid"))

    for c in candidates:
        if c.exists() and (c / "ProjectZomboid64.exe").exists():
            return str(c)

    # Fallback to standard Steam default
    default_pz = Path(r"C:\Program Files (x86)\Steam\steamapps\common\ProjectZomboid")
    if default_pz.exists():
        return str(default_pz)

    return ""


def detect_user_zomboid_dir() -> str:
    """Detect Project Zomboid user profile directory (usually C:\\Users\\<user>\\Zomboid)."""
    home = Path(os.path.expanduser("~")) / "Zomboid"
    return str(home) if home.exists() else str(Path(os.path.expanduser("~")) / "Zomboid")


def get_default_hero_image() -> str:
    """Return default hero image path."""
    preferred = Path(r"D:\Pictures\Anime Zomboid Day.png")
    if preferred.exists():
        return str(preferred)
    local_hero = get_resource_path("assets/hero.png")
    if local_hero.exists():
        return str(local_hero)
    return str(preferred)


def load_external_repositories() -> Optional[List[Dict[str, Any]]]:
    r"""
    Load repositories definition dynamically:
    1. First checks local repo files: C:\Users\user\Desktop\Zomboid-Day-Launcher-Files\repositories.json
    2. Then checks cache/repos/zomboid-day-files/repositories.json
    3. Fallback to launcher dir repositories.json
    """
    candidates = [
        Path(r"C:\Users\user\Desktop\Zomboid-Day-Launcher-Files\repositories.json"),
        get_app_dir() / "cache" / "repos" / "zomboid-day-files" / "repositories.json",
        get_app_dir() / "repositories.json"
    ]
    for c in candidates:
        if c.exists():
            try:
                with open(c, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    if isinstance(data, list) and len(data) > 0:
                        return data
            except Exception as e:
                print(f"[Config] Error loading {c}: {e}")
    return None


class ConfigManager:
    def __init__(self, base_dir: Optional[Path] = None):
        if base_dir is None:
            self.base_dir = get_app_dir()
        else:
            self.base_dir = base_dir

        self.config_path = self.base_dir / CONFIG_FILE_NAME
        self.data: Dict[str, Any] = self._load()

    def _default_config(self) -> Dict[str, Any]:
        return {
            "game_dir": detect_steam_pz_path(),
            "user_zomboid_dir": detect_user_zomboid_dir(),
            "hero_image": get_default_hero_image(),
            "language": "en",                    # Default English if not saved
            "hide_to_tray_on_start": True,       # Minimizes launcher to tray by default
            "show_external_cmd": False,           # Keeps cmd detached without external cmd window, logs to launcher
            "auto_check_updates": True,
            "installed_version": "",
            "last_sync_time": "",
            "ram_xms": "8192m",
            "ram_xmx": "12288m",
            "extra_jvm_args": "",
            "scan_modguard_before_launch": True,
            "repositories": [repo.copy() for repo in DEFAULT_REPOSITORIES]
        }

    def _load(self) -> Dict[str, Any]:
        defaults = self._default_config()
        if not self.config_path.exists():
            self._save(defaults)
            return defaults

        try:
            with open(self.config_path, "r", encoding="utf-8") as f:
                loaded = json.load(f)
            # Merge loaded with defaults for any missing keys
            for k, v in defaults.items():
                if k not in loaded:
                    loaded[k] = v
            return loaded
        except Exception as e:
            print(f"[ConfigManager] Error reading {self.config_path}: {e}. Resetting to defaults.")
            self._save(defaults)
            return defaults

    def _save(self, data: Dict[str, Any]):
        try:
            with open(self.config_path, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
        except Exception as e:
            print(f"[ConfigManager] Error saving config: {e}")

    def save(self):
        self._save(self.data)

    def get(self, key: str, default: Any = None) -> Any:
        return self.data.get(key, default)

    def set(self, key: str, value: Any):
        self.data[key] = value
        self.save()

    @property
    def game_dir(self) -> str:
        return self.data.get("game_dir", "")

    @game_dir.setter
    def game_dir(self, val: str):
        self.set("game_dir", val)

    @property
    def user_zomboid_dir(self) -> str:
        return self.data.get("user_zomboid_dir", "")

    @property
    def language(self) -> str:
        return self.data.get("language", "en")

    @language.setter
    def language(self, val: str):
        self.set("language", val)

    @property
    def hero_image(self) -> str:
        val = self.data.get("hero_image", "")
        if val and Path(val).exists():
            return val
        return get_default_hero_image()

    @property
    def hide_to_tray_on_start(self) -> bool:
        return self.data.get("hide_to_tray_on_start", True)

    @property
    def show_external_cmd(self) -> bool:
        return self.data.get("show_external_cmd", False)

    @property
    def repositories(self) -> List[Dict[str, Any]]:
        external = load_external_repositories()
        if external is not None:
            return sorted(external, key=lambda x: x.get("order", 999))
        repos = self.data.get("repositories", DEFAULT_REPOSITORIES)
        return sorted(repos, key=lambda x: x.get("order", 999))

    def update_repositories(self, repos: List[Dict[str, Any]]):
        # Normalize order
        for idx, r in enumerate(repos, start=1):
            r["order"] = idx
        self.data["repositories"] = repos
        self.save()

    def get_repo(self, repo_id: str) -> Optional[Dict[str, Any]]:
        for r in self.repositories:
            if r.get("id") == repo_id:
                return r
        return None
