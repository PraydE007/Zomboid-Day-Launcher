"""
Zomboid Day Launcher — Internationalization (i18n) Module
Supports English ('en') and Ukrainian ('uk').
Default is English ('en') unless saved otherwise in config.
"""
from typing import Dict, Any

TRANSLATIONS: Dict[str, Dict[str, str]] = {
    # Navigation & Window
    "nav_home": {
        "en": "Home",
        "uk": "Головна"
    },
    "nav_settings": {
        "en": "Settings",
        "uk": "Налаштування"
    },
    "nav_console": {
        "en": "Console",
        "uk": "Консоль"
    },
    "window_title": {
        "en": "Zomboid Day Launcher",
        "uk": "Zomboid Day Launcher"
    },

    # Home Tab
    "subtitle": {
        "en": "SURVIVAL CLIENT & MODPACK • BUILD 42+",
        "uk": "SURVIVAL CLIENT & MODPACK • BUILD 42+"
    },
    "checking_version": {
        "en": "Checking version...",
        "uk": "Перевірка версії..."
    },
    "btn_install": {
        "en": "INSTALL",
        "uk": "ВСТАНОВИТИ"
    },
    "btn_play": {
        "en": "PLAY",
        "uk": "ГРАТИ"
    },
    "btn_debug": {
        "en": "DEBUG",
        "uk": "DEBUG"
    },

    # Version Statuses
    "status_up_to_date": {
        "en": "Up to date",
        "uk": "Актуальна"
    },
    "status_update_available": {
        "en": "Update available",
        "uk": "Доступне оновлення"
    },
    "status_not_installed": {
        "en": "Not installed",
        "uk": "Не встановлено"
    },
    "status_game_not_found": {
        "en": "Game folder not found",
        "uk": "Папку гри не знайдено"
    },

    # Console Tab
    "game_running": {
        "en": "Game is running (PID: {pid})",
        "uk": "Гра працює (PID: {pid})"
    },
    "game_not_running": {
        "en": "Game is not running",
        "uk": "Гра не запущена"
    },
    "autoscroll": {
        "en": "Autoscroll",
        "uk": "Автоскрол"
    },
    "clear": {
        "en": "Clear",
        "uk": "Очистити"
    },
    "save": {
        "en": "Save",
        "uk": "Зберегти"
    },
    "execute": {
        "en": "Execute",
        "uk": "Виконати"
    },
    "cmd_placeholder": {
        "en": "Enter CMD command to execute...",
        "uk": "Введіть команду CMD для запуску..."
    },
    "console_ready": {
        "en": "Console ready. Processes run detached from launcher.",
        "uk": "Консоль готова. Процеси запускаються автономно."
    },

    # Settings Tab
    "sec_paths": {
        "en": "Paths",
        "uk": "Шляхи"
    },
    "sec_repos": {
        "en": "Repositories",
        "uk": "Репозиторії"
    },
    "sec_launch": {
        "en": "Launch",
        "uk": "Запуск"
    },
    "lbl_game_dir": {
        "en": "Project Zomboid folder:",
        "uk": "Папка Project Zomboid:"
    },
    "lbl_user_dir": {
        "en": "Zomboid user profile folder:",
        "uk": "Папка профілю Zomboid:"
    },
    "lbl_hero_image": {
        "en": "Hero banner image:",
        "uk": "Фонова картинка:"
    },
    "browse": {
        "en": "Browse",
        "uk": "Огляд"
    },
    "auto_detect": {
        "en": "Auto Detect",
        "uk": "Автопошук"
    },
    "reset": {
        "en": "Reset",
        "uk": "Скинути"
    },
    "move_up": {
        "en": "Up",
        "uk": "Вгору"
    },
    "move_down": {
        "en": "Down",
        "uk": "Вниз"
    },
    "add": {
        "en": "Add",
        "uk": "Додати"
    },
    "edit": {
        "en": "Edit",
        "uk": "Редагувати"
    },
    "delete": {
        "en": "Delete",
        "uk": "Видалити"
    },
    "opt_tray": {
        "en": "Minimize to tray when game starts",
        "uk": "Згортати в трей при старті гри"
    },
    "opt_show_cmd": {
        "en": "Show external CMD window",
        "uk": "Показувати зовнішнє вікно CMD"
    },
    "opt_modguard": {
        "en": "Scan mods before launch (ModGuard)",
        "uk": "Сканувати моди перед запуском (ModGuard)"
    },
    "saved_msg": {
        "en": "Settings saved successfully.",
        "uk": "Налаштування збережено."
    },

    # Tray Menu
    "tray_show": {
        "en": "Show Launcher",
        "uk": "Показати лаунчер"
    },
    "tray_start": {
        "en": "Launch Game",
        "uk": "Запустити гру"
    },
    "tray_debug": {
        "en": "Debug Launch",
        "uk": "Debug запуск"
    },
    "tray_exit": {
        "en": "Exit",
        "uk": "Вийти"
    },
    "tray_game_started_title": {
        "en": "Game launched",
        "uk": "Гру запущено"
    },
    "tray_game_started_msg": {
        "en": "{mode} launch complete. Launcher minimized to tray.",
        "uk": "{mode} запуск виконано. Лаунчер згорнуто."
    },

    # Popups / Statuses
    "info": {
        "en": "Information",
        "uk": "Інформація"
    },
    "error": {
        "en": "Error",
        "uk": "Помилка"
    },
    "done": {
        "en": "Done",
        "uk": "Готово"
    },
    "install_in_progress": {
        "en": "Installation is already running.",
        "uk": "Встановлення вже виконується."
    },
    "install_prep": {
        "en": "Preparing...",
        "uk": "Підготовка..."
    },
    "game_running_close_confirm": {
        "en": "Game is running in background. Minimize to tray?",
        "uk": "Гра працює у фоні. Згорнути в трей?"
    }
}


def t(key: str, lang: str = "en", **kwargs) -> str:
    """Retrieve localized string by key and language code."""
    data = TRANSLATIONS.get(key)
    if not data:
        return key

    text = data.get(lang) or data.get("en") or key
    if kwargs:
        try:
            return text.format(**kwargs)
        except Exception:
            return text
    return text
