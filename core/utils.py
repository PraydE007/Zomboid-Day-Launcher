import sys
from pathlib import Path


def get_resource_path(relative_path: str = "") -> Path:
    """
    Get absolute path to resource, works for dev and for PyInstaller.
    PyInstaller creates a temp folder and stores path in _MEIPASS.
    """
    if getattr(sys, "frozen", False) and hasattr(sys, "_MEIPASS"):
        base_path = Path(sys._MEIPASS)
    else:
        base_path = Path(__file__).resolve().parent.parent

    if relative_path:
        return (base_path / relative_path).resolve()
    return base_path.resolve()


def get_app_dir() -> Path:
    """
    Get the directory where the application/executable is running from.
    Used for writable data like configs, logs, and caches.
    """
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parent.parent
