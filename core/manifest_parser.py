import json
import os
import hashlib
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
        """Replace placeholders like {GAME_DIR}, {USER_ZOMBOID_DIR}, {MODS_DIR}, {LAUNCHER_DIR}."""
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
        return self.data.get("project", {}).get("version", "1.1.1")

    @property
    def launcher_version(self) -> str:
        return self.data.get("project", {}).get("launcher_version", self.version)

    @property
    def description(self) -> str:
        return self.data.get("project", {}).get("description", "")

    @property
    def author(self) -> str:
        return self.data.get("project", {}).get("author", "")

    @staticmethod
    def compute_sha256(file_path: Path) -> str:
        """Calculate SHA-256 hex digest of a file in streaming chunks."""
        try:
            h = hashlib.sha256()
            with open(file_path, "rb") as f:
                while chunk := f.read(65536):
                    h.update(chunk)
            return h.hexdigest().lower()
        except Exception:
            return ""

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

    def validate_installation(self) -> Tuple[bool, List[str], List[str]]:
        """
        Check if all required files specified in validation.required_files exist
        and verify their cryptographic SHA-256 hashes.
        Returns:
            (is_valid, missing_files, outdated_or_corrupt_files)
        """
        validation_cfg = self.data.get("validation", {})
        required = validation_cfg.get("required_files", [])

        missing: List[str] = []
        outdated: List[str] = []

        for item in required:
            if isinstance(item, str):
                raw_path = item
                expected_hash = ""
                name = Path(item).name
            else:
                raw_path = item.get("path", "")
                expected_hash = str(item.get("sha256", "")).strip().lower()
                name = item.get("name", Path(raw_path).name)

            if not raw_path:
                continue

            resolved = Path(self.resolve_variables(raw_path))

            # Check alternative locations (e.g. game_dir vs launcher_dir for bat files)
            alt_resolved = None
            if not resolved.exists() and "LAUNCHER_DIR" in self.context and "GAME_DIR" in self.context:
                game_dir = Path(self.context["GAME_DIR"])
                launcher_dir = Path(self.context["LAUNCHER_DIR"])
                if resolved.parent == launcher_dir:
                    candidate = game_dir / resolved.name
                    if candidate.exists():
                        alt_resolved = candidate
                elif resolved.parent == game_dir:
                    candidate = launcher_dir / resolved.name
                    if candidate.exists():
                        alt_resolved = candidate

            target_path = alt_resolved if (alt_resolved and alt_resolved.exists()) else resolved

            if not target_path.exists():
                missing.append(f"{name} ({target_path})")
            elif expected_hash:
                actual_hash = self.compute_sha256(target_path)
                if actual_hash != expected_hash:
                    outdated.append(f"{name} [SHA-256 mismatch]")

        is_valid = (len(missing) == 0 and len(outdated) == 0)
        return is_valid, missing, outdated

    def get_launch_executables(self) -> Dict[str, str]:
        launch_cfg = self.data.get("launch", {})
        default_exe = launch_cfg.get("default_executable", "{GAME_DIR}/ProjectZomboid64.bat")
        debug_exe = launch_cfg.get("debug_executable", "{GAME_DIR}/ProjectZomboid64ShowConsole.bat")
        
        return {
            "default": self.resolve_variables(default_exe),
            "debug": self.resolve_variables(debug_exe)
        }
