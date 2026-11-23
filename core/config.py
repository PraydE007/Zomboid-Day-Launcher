import os
import sys
import json
import winreg
from pathlib import Path
from typing import Dict, Any, List, Optional
from core.utils import get_resource_path, get_app_dir, is_in_game_dir, get_zd_data_dir

CONFIG_FILE_NAME = "launcher_config.json"
LAUNCHER_FOLDER_NAME = "zd-launcher"

DEFAULT_REPOSITORIES = [
    {
        "id": "zomboid-day-files",
        "name": "Zomboid Day Core",
        "order": 1,
        "enabled": True,
        "source_type": "local_or_git",
        "local_path": r"C:\Users\user\Desktop\Zomboid-Day-Launcher-Files",
        "git_url": "https://github.com/PraydE007/Zomboid-Day-Launcher-Files.git",
        "branch": "main",
        "has_manifest": True,
        "description": "Core repository with manifest, JVM scripts, and ZombieBuddy"
    },
    {
        "id": "pz-modguard",
        "name": "PZ-ModGuard",
        "order": 2,
        "enabled": True,
        "source_type": "git",
        "local_path": "",
        "git_url": "https://github.com/KodeMannn/PZ-ModGuard.git",
        "branch": "main",
        "has_manifest": False,
        "description": "Standalone bytecode and security scanner for mods",
        "custom_steps": [
            {
                "order": 1,
                "type": "copy_file",
                "name": "PZ-ModGuard.bat script",
                "source": "PZ-ModGuard.bat",
                "destination": "{GAME_DIR}\\PZ-ModGuard.bat",
                "overwrite": True,
                "backup": False
            }
        ]
    }
]


def detect_steam_pz_path() -> str:
    """
    Game directory is strictly relative to launcher location.
    The launcher does not search external Steam registries or paths.
    """
    return str(get_app_dir())


def detect_user_zomboid_dir() -> str:
    """Detect Project Zomboid user profile directory (usually C:\\Users\\<user>\\Zomboid)."""
    home = Path(os.path.expanduser("~")) / "Zomboid"
    return str(home) if home.exists() else str(Path(os.path.expanduser("~")) / "Zomboid")


def get_default_hero_image() -> str:
    """Return default hero image path bundled directly inside launcher assets."""
    local_hero = get_resource_path("assets/hero.png")
    if local_hero.exists():
        return str(local_hero)
    app_hero = get_app_dir() / "assets" / "hero.png"
    if app_hero.exists():
        return str(app_hero)
    return str(local_hero)


def load_external_repositories() -> Optional[List[Dict[str, Any]]]:
    r"""
    Load repositories definition dynamically:
    1. First checks local repo files: C:\Users\user\Desktop\Zomboid-Day-Launcher-Files\repositories.json
    2. Then checks zd-launcher/cache/repos/zomboid-day-files/repositories.json or cache/repos/...
    3. Fallback to launcher dir repositories.json
    """
    candidates = [
        Path(r"C:\Users\user\Desktop\Zomboid-Day-Launcher-Files\repositories.json"),
        get_app_dir() / LAUNCHER_FOLDER_NAME / "cache" / "repos" / "zomboid-day-files" / "repositories.json",
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
        app_dir = get_app_dir()
        # Strictly relative: check if launcher is located inside the game directory
        self.is_valid_location = is_in_game_dir()

        if base_dir is not None:
            self.base_dir = base_dir
        elif self.is_valid_location:
            # Launcher is inside game folder: use dedicated zd-launcher subfolder
            self.base_dir = app_dir / LAUNCHER_FOLDER_NAME
            self.base_dir.mkdir(parents=True, exist_ok=True)
            self._migrate_legacy_data(app_dir, self.base_dir)
        else:
            # Outside game folder: NEVER create zd-launcher or write configs on disk
            self.base_dir = app_dir

        self.config_path = self.base_dir / CONFIG_FILE_NAME
        self.data: Dict[str, Any] = self._load()

    def _migrate_legacy_data(self, app_dir: Path, zd_dir: Path):
        import shutil
        # 1. launcher_config.json
        old_cfg = app_dir / CONFIG_FILE_NAME
        new_cfg = zd_dir / CONFIG_FILE_NAME
        if old_cfg.exists() and not new_cfg.exists():
            try:
                shutil.move(str(old_cfg), str(new_cfg))
            except Exception:
                pass
        # 2. cache
        old_cache = app_dir / "cache"
        new_cache = zd_dir / "cache"
        if old_cache.exists() and not new_cache.exists():
            try:
                shutil.move(str(old_cache), str(new_cache))
            except Exception:
                pass
        # 3. logs
        old_logs = app_dir / "logs"
        new_logs = zd_dir / "logs"
        if old_logs.exists() and not new_logs.exists():
            try:
                shutil.move(str(old_logs), str(new_logs))
            except Exception:
                pass

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
            if self.is_valid_location:
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
            if self.is_valid_location:
                self._save(defaults)
            return defaults

    def _save(self, data: Dict[str, Any]):
        if not self.is_valid_location:
            # Do NOT create zd-launcher or write configs to disk if misplaced
            return
        try:
            self.base_dir.mkdir(parents=True, exist_ok=True)
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
        # Launcher operates strictly relative to its location
        return str(get_app_dir())

    @game_dir.setter
    def game_dir(self, val: str):
        self.data["game_dir"] = str(get_app_dir())
        if self.is_valid_location:
            self.save()

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
        val = str(self.data.get("hero_image", ""))
        # Ignore external D:\Pictures or non-existent files and use bundled resource
        if val and Path(val).exists() and not val.lower().startswith("d:\\pictures"):
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
