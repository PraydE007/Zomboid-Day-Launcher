import sys
import os
from pathlib import Path
from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFontDatabase

# Ensure root dir is in sys.path
BASE_DIR = Path(__file__).resolve().parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from core.config import ConfigManager
from core.utils import get_resource_path, get_app_dir
from ui.main_window import MainWindow


def main():
    # Set Windows App User Model ID so the taskbar and process show our custom icon
    if sys.platform == "win32":
        try:
            import ctypes
            ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID("zomboidday.launcher.app.1.0")
        except Exception:
            pass

    # Enable High DPI scaling
    os.environ["QT_AUTO_SCREEN_SCALE_FACTOR"] = "1"
    
    app = QApplication(sys.argv)
    app.setApplicationName("Zomboid Day Launcher")
    app.setApplicationDisplayName("Zomboid Day Launcher")
    app.setOrganizationName("ZomboidDay")

    # Set application icon globally for the whole process
    for icon_name in ("assets/icon.ico", "assets/icon.png"):
        p = get_resource_path(icon_name)
        if p.exists():
            from PyQt6.QtGui import QIcon
            app.setWindowIcon(QIcon(str(p)))
            break

    # Load custom Project Zomboid font if available
    font_path = get_resource_path("font/FreckleFaceRegular.ttf")
    if font_path.exists():
        QFontDatabase.addApplicationFont(str(font_path))

    # Initialize configuration (loads zd-launcher if placed next to ProjectZomboid64.exe)
    config = ConfigManager()

    # Synchronize i18n engine with saved user preference
    from core.i18n import set_locale
    set_locale(config.language)

    # Launch Main Window
    window = MainWindow(config)
    window.show()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
