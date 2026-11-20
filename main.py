import sys
import os
from pathlib import Path
from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import Qt

# Ensure root dir is in sys.path
BASE_DIR = Path(__file__).resolve().parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from core.config import ConfigManager
from ui.main_window import MainWindow


def main():
    # Enable High DPI scaling
    os.environ["QT_AUTO_SCREEN_SCALE_FACTOR"] = "1"
    
    app = QApplication(sys.argv)
    app.setApplicationName("Zomboid Day Launcher")
    app.setApplicationDisplayName("Zomboid Day Launcher")
    app.setOrganizationName("ZomboidDay")

    # Initialize configuration
    config = ConfigManager(base_dir=BASE_DIR)

    # Launch Main Window
    window = MainWindow(config)
    window.show()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
