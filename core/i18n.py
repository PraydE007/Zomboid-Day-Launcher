"""
Zomboid Day Launcher — Internationalization (i18n) Engine.
Loads locale definitions dynamically from JSON files in locales/ directory.
Provides reactive language switching, parameter interpolation, and robust fallback.
"""

import json
from pathlib import Path
from typing import Dict, Any, Optional, List, Tuple
from PyQt6.QtCore import QObject, pyqtSignal

from core.utils import get_resource_path


SUPPORTED_LANGUAGES: List[Tuple[str, str]] = [
    ("en", "English"),
    ("uk", "Українська")
]

DEFAULT_LANGUAGE = "en"


class I18nManager(QObject):
    """
    Centralized localization service.
    Loads JSON translations, caches them in memory, and provides reactive translation access.
    """
    sig_language_changed = pyqtSignal(str)

    def __init__(self, default_lang: str = DEFAULT_LANGUAGE):
        super().__init__()
        self._current_lang: str = default_lang
        self._locales_data: Dict[str, Dict[str, str]] = {}
        self._load_all_locales()

    def _get_locale_path(self, lang: str) -> Path:
        """Find the path to the locale JSON file."""
        # 1. Check bundled resource path (works in dev and PyInstaller)
        p = get_resource_path(f"locales/{lang}.json")
        if p.exists():
            return p
        # 2. Check direct project root fallback
        direct = Path(__file__).resolve().parent.parent / "locales" / f"{lang}.json"
        if direct.exists():
            return direct
        return p

    def _load_all_locales(self):
        """Load and cache translation dictionaries for all supported languages."""
        for code, _ in SUPPORTED_LANGUAGES:
            path = self._get_locale_path(code)
            if path.exists():
                try:
                    with open(path, "r", encoding="utf-8") as f:
                        data = json.load(f)
                        if isinstance(data, dict):
                            self._locales_data[code] = data
                except Exception as e:
                    print(f"[I18n] Error loading {path}: {e}")
                    self._locales_data[code] = {}
            else:
                self._locales_data[code] = {}

    def reload(self):
        """Force reload translation catalogs from disk."""
        self._load_all_locales()

    @property
    def current_language(self) -> str:
        return self._current_lang

    @current_language.setter
    def current_language(self, lang: str):
        self.set_language(lang)

    def set_language(self, lang: str):
        if lang not in [c for c, _ in SUPPORTED_LANGUAGES]:
            lang = DEFAULT_LANGUAGE
        if lang != self._current_lang:
            self._current_lang = lang
            self.sig_language_changed.emit(lang)

    def translate(self, key: str, lang: Optional[str] = None, **kwargs) -> str:
        """
        Translate a key.
        Fallback sequence:
        1. Requested language (or current_language)
        2. English ('en')
        3. Raw key
        Supports named kwargs formatting: e.g. t('game_running', pid=123)
        """
        target_lang = lang or self._current_lang

        # 1. Lookup in target language
        target_catalog = self._locales_data.get(target_lang, {})
        text = target_catalog.get(key)

        # 2. Fallback to English
        if text is None and target_lang != DEFAULT_LANGUAGE:
            en_catalog = self._locales_data.get(DEFAULT_LANGUAGE, {})
            text = en_catalog.get(key)

        # 3. Fallback to key itself
        if text is None:
            text = key

        # 4. Perform keyword interpolation safely
        if kwargs:
            try:
                return text.format(**kwargs)
            except Exception:
                return text
        return text


# Global singleton instance
i18n = I18nManager()


def t(key: str, lang: Optional[str] = None, **kwargs) -> str:
    """Convenient global translation function."""
    return i18n.translate(key, lang=lang, **kwargs)


def tr(key: str, **kwargs) -> str:
    """Standard Qt-style translation shortcut."""
    return i18n.translate(key, **kwargs)


def set_locale(lang: str):
    """Set the active application locale."""
    i18n.set_language(lang)


def get_locale() -> str:
    """Get the active application locale code."""
    return i18n.current_language


def get_available_locales() -> List[Tuple[str, str]]:
    """Return list of supported languages as (code, display_name)."""
    return SUPPORTED_LANGUAGES
