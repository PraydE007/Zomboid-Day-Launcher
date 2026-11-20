"""
Zomboid Day Launcher - Automated Build Script
Builds standalone executable into release/ directory using PyInstaller.
"""

import os
import sys
import shutil
import subprocess
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
RELEASE_DIR = BASE_DIR / "release"
BUILD_DIR = BASE_DIR / "build"
ASSETS_DIR = BASE_DIR / "assets"
FONT_DIR = BASE_DIR / "font"
ICON_PATH = ASSETS_DIR / "icon.ico"


def build():
    print("=" * 60)
    print("  🚀 ZOMBOID DAY LAUNCHER — ЗБИРАННЯ RELEASE EXE")
    print("=" * 60)

    # 1. Ensure release and build directories
    RELEASE_DIR.mkdir(parents=True, exist_ok=True)
    
    # 2. Check prerequisites
    if not ICON_PATH.exists():
        print(f"[Попередження] Іконку {ICON_PATH} не знайдено.")

    main_script = BASE_DIR / "main.py"
    if not main_script.exists():
        print(f"[Помилка] Головний файл {main_script} не знайдено!")
        sys.exit(1)

    # 3. Construct PyInstaller command
    cmd = [
        sys.executable, "-m", "PyInstaller",
        "--name=Zomboid-Day-Launcher",
        "--noconsole",
        "--onefile",
        "--clean",
        f"--distpath={str(RELEASE_DIR)}",
        f"--workpath={str(BUILD_DIR)}",
        f"--specpath={str(BUILD_DIR)}",
        f"--icon={str(ICON_PATH)}",
        f"--add-data={str(ASSETS_DIR)};assets",
        f"--add-data={str(FONT_DIR)};font",
        "--hidden-import=PyQt6",
        "--hidden-import=PyQt6.QtCore",
        "--hidden-import=PyQt6.QtGui",
        "--hidden-import=PyQt6.QtWidgets",
        "--hidden-import=PyQt6.QtSvg",
        "--hidden-import=psutil",
        "--hidden-import=PIL",
        str(main_script)
    ]

    print("\n📦 Запуск PyInstaller...")
    print(f"Цільова папка: {RELEASE_DIR}")
    print(f"Конфігурація: Single-File Executable (--onefile, --noconsole)\n")

    try:
        proc = subprocess.run(cmd, cwd=str(BASE_DIR), check=True)
        exe_path = RELEASE_DIR / "Zomboid-Day-Launcher.exe"

        if exe_path.exists():
            size_mb = exe_path.stat().st_size / (1024 * 1024)
            print("\n" + "=" * 60)
            print("  ✅ ЗБИРАННЯ УСПІШНО ЗАВЕРШЕНО!")
            print(f"  📁 Виконуваний файл: {exe_path}")
            print(f"  📊 Розмір: {size_mb:.2f} MB")
            print("=" * 60 + "\n")
        else:
            print("\n[Увага] Файл не знайдено в папці release.")

    except subprocess.CalledProcessError as e:
        print(f"\n❌ [Помилка збирання]: PyInstaller завершився з кодом {e.returncode}")
        sys.exit(e.returncode)
    except Exception as e:
        print(f"\n❌ [Несподівана помилка]: {e}")
        sys.exit(1)


if __name__ == "__main__":
    build()
