import json
import os
from pathlib import Path
from typing import Dict, Any, List, Tuple, Optional


class ManifestParser:
    def __init__(self, manifest_path: Path, context: Dict[str, str]):
        self.manifest_path = Path(manifest_path)
        self.context = context
        self.data: Dict[str, Any] = {}
        self._load()

    def _load(self):
        if not self.manifest_path.exists():
            raise FileNotFoundError(f"Manifest file not found: {self.manifest_path}")

        with open(self.manifest_path, "r", encoding="utf-8") as f:
            self.data = json.load(f)

    def resolve_variables(self, text: str) -> str:
        """Replace placeholders like {GAME_DIR}, {USER_ZOMBOID_DIR}, {MODS_DIR}."""
        result = text
        for k, v in self.context.items():
            result = result.replace(f"{{{k}}}", v)
        # Normalize slashes for Windows
        return str(Path(result))

    @property
    def project_name(self) -> str:
        return self.data.get("project", {}).get("name", "Project Zomboid Modpack")

    @property
    def version(self) -> str:
        return self.data.get("project", {}).get("version", "1.0.0")

    @property
    def description(self) -> str:
        return self.data.get("project", {}).get("description", "")

    @property
    def author(self) -> str:
        return self.data.get("project", {}).get("author", "")

    def get_install_steps(self, repo_root: Path) -> List[Dict[str, Any]]:
        raw_steps = self.data.get("install_steps", [])
        resolved_steps = []

        for step in sorted(raw_steps, key=lambda s: s.get("order", 999)):
            stype = step.get("type", "copy_file")
            source = step.get("source", "")
            raw_dest = step.get("destination", "")
            dest = self.resolve_variables(raw_dest) if raw_dest else ""
            
            # Resolve full source path relative to repo_root
            full_source = (repo_root / source).resolve() if source else Path("")

            resolved_steps.append({
                "id": step.get("id", f"step_{step.get('order', 1)}"),
                "order": step.get("order", 1),
                "name": step.get("name", step.get("id", "Unnamed Step")),
                "description": step.get("description", ""),
                "type": stype,
                "url": step.get("url", ""),
                "fallback_url": step.get("fallback_url", ""),
                "source": full_source,
                "destination": Path(dest) if dest else Path(""),
                "files": step.get("files", []),
                "overwrite": step.get("overwrite", True),
                "backup": step.get("backup", True)
            })

        return resolved_steps

    def validate_installation(self) -> Tuple[bool, List[str]]:
        """
        Check if all required files specified in validation.required_files exist.
        Returns (is_valid, list_of_missing_files).
        """
        validation_cfg = self.data.get("validation", {})
        required = validation_cfg.get("required_files", [])
        
        # Support both simple list of paths or list of objects
        missing = []
        for item in required:
            raw_path = item if isinstance(item, str) else item.get("path", "")
            if not raw_path:
                continue
            resolved = Path(self.resolve_variables(raw_path))
            if not resolved.exists():
                missing.append(str(resolved))

        return len(missing) == 0, missing

    def get_launch_executables(self) -> Dict[str, str]:
        launch_cfg = self.data.get("launch", {})
        default_exe = launch_cfg.get("default_executable", "{GAME_DIR}/ProjectZomboid64.bat")
        debug_exe = launch_cfg.get("debug_executable", "{GAME_DIR}/ProjectZomboid64ShowConsole.bat")
        
        return {
            "default": self.resolve_variables(default_exe),
            "debug": self.resolve_variables(debug_exe)
        }
