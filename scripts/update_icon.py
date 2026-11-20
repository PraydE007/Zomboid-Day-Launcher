"""
Utility script to quickly set and update the launcher icon.
Usage:
    python scripts/update_icon.py                     # Updates icon.ico from assets/icon.png
    python scripts/update_icon.py path/to/image.png   # Sets new image as assets/icon.png and generates assets/icon.ico
"""

import sys
import shutil
from pathlib import Path
from PIL import Image

BASE_DIR = Path(__file__).resolve().parent.parent
ASSETS_DIR = BASE_DIR / "assets"
ICON_PNG = ASSETS_DIR / "icon.png"
ICON_ICO = ASSETS_DIR / "icon.ico"

ICON_SIZES = [(16, 16), (24, 24), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)]


def update_icon(source_path: Path = None):
    ASSETS_DIR.mkdir(parents=True, exist_ok=True)

    if source_path:
        source_path = Path(source_path).resolve()
        if not source_path.exists():
            print(f"[ПОМИЛКА] Файл не знайдено: {source_path}")
            return False
        print(f"-> Копіювання {source_path.name} в assets/icon.png ...")
        shutil.copy2(source_path, ICON_PNG)

    if not ICON_PNG.exists():
        print(f"[ПОМИЛКА] Файл {ICON_PNG} не знайдено!")
        return False

    print("-> Генерація Windows icon.ico з multi-resolution розмірами (16x16 ... 256x256)...")
    img = Image.open(ICON_PNG)
    img = img.convert("RGBA")
    img.save(ICON_ICO, format="ICO", sizes=ICON_SIZES)

    print("✅ Успішно оновлено:")
    print(f"   - {ICON_PNG}")
    print(f"   - {ICON_ICO}")
    print("\n💡 Тепер запустіть `python build.py` щоб зібрати новий .exe з цією іконкою.")
    return True


if __name__ == "__main__":
    src = sys.argv[1] if len(sys.argv) > 1 else None
    update_icon(src)
