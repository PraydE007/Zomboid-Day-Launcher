import os
import shutil
import subprocess
import urllib.request
import zipfile
from pathlib import Path
from typing import Dict, Any, List, Optional, Callable

from core.manifest_parser import ManifestParser


class RepoManager:
    def __init__(self, cache_dir: Path, context: Dict[str, str], log_callback: Optional[Callable[[str], None]] = None):
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.context = context
        self.log = log_callback or (lambda msg: print(f"[RepoManager] {msg}"))

    def sync_repository(self, repo_info: Dict[str, Any]) -> Path:
        """
        Sync repository:
        1. If local_path is specified and exists, use it.
        2. Else, clone/pull from git_url into cache/repos/<repo_id>.
        Returns path to the repository directory.
        """
        repo_id = repo_info.get("id", "unknown_repo")
        local_path = repo_info.get("local_path", "").strip()

        if local_path and Path(local_path).exists():
            self.log(f"Using local repository for {repo_info.get('name')}")
            return Path(local_path)

        git_url = repo_info.get("git_url", "").strip()
        if not git_url:
            raise ValueError(f"Repository {repo_id} has neither local path nor Git URL!")

        target_dir = self.cache_dir / repo_id
        target_dir.mkdir(parents=True, exist_ok=True)

        branch = repo_info.get("branch", "main")
        self.log(f"Synchronizing repository {repo_info.get('name')}...")

        if (target_dir / ".git").exists():
            # Git pull
            try:
                self.log(f"Updating {repo_id} via git pull...")
                proc = subprocess.run(
                    ["git", "pull", "origin", branch],
                    cwd=str(target_dir),
                    capture_output=True,
                    text=True,
                    check=True
                )
                self.log(f"Git pull successful: {proc.stdout.strip()}")
                return target_dir
            except Exception as e:
                self.log(f"Git pull warning: {e}. Continuing with existing files.")
                return target_dir
        else:
            # Git clone
            try:
                self.log(f"Cloning {repo_id} (branch {branch})...")
                # Remove if empty or failed before
                if target_dir.exists():
                    shutil.rmtree(target_dir, ignore_errors=True)
                target_dir.mkdir(parents=True, exist_ok=True)

                proc = subprocess.run(
                    ["git", "clone", "--depth", "1", "--branch", branch, git_url, str(target_dir)],
                    capture_output=True,
                    text=True,
                    check=True
                )
                self.log("Cloning completed successfully.")
                return target_dir
            except Exception as e:
                self.log(f"Git clone error: {e}. Attempting download as ZIP archive...")
                return self._download_github_zip(git_url, branch, target_dir)

    def _download_github_zip(self, git_url: str, branch: str, target_dir: Path) -> Path:
        """Fallback to downloading GitHub zip if git command fails."""
        clean_url = git_url.removesuffix(".git")
        zip_url = f"{clean_url}/archive/refs/heads/{branch}.zip"
        zip_path = self.cache_dir / f"{target_dir.name}.zip"

        self.log(f"Downloading repository archive ({branch})...")
        urllib.request.urlretrieve(zip_url, str(zip_path))

        self.log("Extracting repository archive...")
        extract_tmp = self.cache_dir / f"{target_dir.name}_tmp"
        if extract_tmp.exists():
            shutil.rmtree(extract_tmp, ignore_errors=True)

        with zipfile.ZipFile(zip_path, 'r') as zip_ref:
            zip_ref.extractall(extract_tmp)

        # Move root folder from zip to target_dir
        extracted_roots = list(extract_tmp.iterdir())
        if extracted_roots:
            first_root = extracted_roots[0]
            if target_dir.exists():
                shutil.rmtree(target_dir, ignore_errors=True)
            shutil.move(str(first_root), str(target_dir))

        shutil.rmtree(extract_tmp, ignore_errors=True)
        if zip_path.exists():
            zip_path.unlink()

        self.log("Repository archive successfully unpacked.")
        return target_dir

    def get_repo_steps(self, repo_info: Dict[str, Any], repo_path: Path) -> List[Dict[str, Any]]:
        """
        Extract installation steps from repo:
        - If has_manifest is True or launcher-manifest.json exists: parse manifest.
        - Else: use custom_steps defined in repo_info.
        """
        manifest_file = repo_path / "launcher-manifest.json"
        if manifest_file.exists():
            self.log("Found project manifest: launcher-manifest.json")
            parser = ManifestParser(manifest_file, self.context)
            return parser.get_install_steps(repo_path)

        # Check for custom steps in repo_info
        custom_steps = repo_info.get("custom_steps", [])
        resolved = []
        for s in custom_steps:
            stype = s.get("type", "copy_file")
            raw_dest = s.get("destination", "{GAME_DIR}")
            dest = self._resolve_vars(raw_dest)
            source = (repo_path / s.get("source", "")).resolve()

            resolved.append({
                "id": f"{repo_info.get('id')}_{s.get('order', 1)}",
                "order": s.get("order", 1),
                "name": s.get("name", s.get("source", "Custom step")),
                "description": s.get("description", ""),
                "type": stype,
                "source": source,
                "destination": Path(dest),
                "overwrite": s.get("overwrite", True),
                "backup": s.get("backup", False)
            })
        return resolved

    def _resolve_vars(self, path_str: str) -> str:
        res = path_str
        for k, v in self.context.items():
            res = res.replace(f"{{{k}}}", v)
        return str(Path(res))
