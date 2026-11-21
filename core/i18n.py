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
    "hotbar_home": {
        "en": "HOME",
        "uk": "ГОЛОВНА"
    },
    "hotbar_settings": {
        "en": "SETTINGS",
        "uk": "НАЛАШТУВ."
    },
    "hotbar_console": {
        "en": "CONSOLE",
        "uk": "КОНСОЛЬ"
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
        "en": "DEBUG MODE",
        "uk": "DEBUG MODE"
    },
    "btn_refresh_tooltip": {
        "en": "Refresh status & run system diagnostics",
        "uk": "Оновити статус та виконати діагностику системи"
    },
    "btn_modguard_scan": {
        "en": "🛡️ MODGUARD SCAN",
        "uk": "🛡️ СКАНУВАННЯ МОДІВ"
    },
    "btn_modguard_scanning": {
        "en": "⏳ SCANNING...",
        "uk": "⏳ СКАНУВАННЯ..."
    },
    "btn_modguard_tooltip": {
        "en": "Run manual PZ-ModGuard security scan on installed mods",
        "uk": "Виконати ручне сканування безпеки модів через PZ-ModGuard"
    },
    "modguard_scan_running": {
        "en": "Running PZ-ModGuard security scan...",
        "uk": "Виконується сканування PZ-ModGuard..."
    },
    "modguard_scan_finished": {
        "en": "PZ-ModGuard scan complete. See Console tab.",
        "uk": "Сканування PZ-ModGuard завершено. Деталі в консолі."
    },
    "scan_profile_full": {
        "en": "Full Deep Scan",
        "uk": "Повний глибокий аудит"
    },
    "scan_profile_quick": {
        "en": "Quick Scan",
        "uk": "Швидка перевірка модів"
    },
    "scan_reason_first": {
        "en": "First launch (full security audit)",
        "uk": "Перший запуск (первинний аудит безпеки)"
    },
    "scan_reason_periodic": {
        "en": "Periodic 7-day security audit",
        "uk": "Плановий аудит (раз на 7 днів)"
    },
    "scan_reason_updated": {
        "en": "Game files or mods updated",
        "uk": "Виявлено оновлення або зміну файлів чи модів"
    },
    "scan_reason_routine": {
        "en": "Routine mods verification",
        "uk": "Експрес-перевірка встановлених модів"
    },
    "launching_game": {
        "en": "Starting Project Zomboid...",
        "uk": "Запуск Project Zomboid..."
    },
    "modguard_status_scanning": {
        "en": "PZ-ModGuard: {profile} in progress...",
        "uk": "PZ-ModGuard: виконується {profile}..."
    },
    "err_modguard_critical_title": {
        "en": "CRITICAL SECURITY THREAT DETECTED!",
        "uk": "КРИТИЧНА ЗАГРОЗА БЕЗПЕКИ!"
    },
    "err_modguard_critical_msg": {
        "en": "PZ-ModGuard detected critical security threats or malicious bytecode in your mods!\n\nGame launch has been TERMINATED to protect your system.\n\nDetails:\n{details}\n\nPlease check the Console tab for the full security report and remove malicious mods before restarting.",
        "uk": "PZ-ModGuard виявив критичні загрози безпеки або шкідливий байткод у встановлених модах!\n\nЗапуск гри СКАСОВАНО для захисту вашої системи та безпеки.\n\nДеталі:\n{details}\n\nБудь ласка, перегляньте детальний звіт на вкладці «Консоль» та видаліть шкідливі моди перед повторним запуском."
    },
    "banner_launcher_not_in_game": {
        "en": "⚠️ Launcher is not beside ProjectZomboid64.exe. For proper operation, place it in the game directory.",
        "uk": "⚠️ Лаунчер не лежить біля ProjectZomboid64.exe. Рекомендується помістити його в папку гри."
    },
    "banner_launch_prohibited": {
        "en": "🚫 LAUNCH PROHIBITED: Launcher is not in the game directory beside ProjectZomboid64.exe! Move the launcher into the game folder.",
        "uk": "🚫 ЗАПУСК ЗАБОРОНЕНО: Лаунчер знаходиться не в папці гри поруч із ProjectZomboid64.exe! Перемістіть лаунчер у папку гри."
    },
    "err_launch_prohibited_title": {
        "en": "Launch Prohibited",
        "uk": "Запуск заборонено"
    },
    "err_launch_prohibited_msg": {
        "en": "The launcher is not located in the Project Zomboid directory beside ProjectZomboid64.exe.\n\nCurrent location: {app_dir}\n\nRunning the game from an external location is prohibited.\nPlease move Zomboid-Day-Launcher.exe directly into the Project Zomboid game folder (beside ProjectZomboid64.exe) and launch it there!",
        "uk": "Лаунчер знаходиться не в папці гри поруч із ProjectZomboid64.exe.\n\nПоточне розміщення: {app_dir}\n\nЗапуск гри із зовнішнього розташування суворо заборонено!\nБудь ласка, перемістіть файл Zomboid-Day-Launcher.exe безпосередньо у папку гри Project Zomboid (поруч із ProjectZomboid64.exe) і запустіть його звідти!"
    },
    "err_launch_prohibited_tooltip": {
        "en": "Launch is blocked: Launcher must be in the game folder beside ProjectZomboid64.exe",
        "uk": "Запуск заблоковано: лаунчер має знаходитись у папці гри біля ProjectZomboid64.exe"
    },
    "step_steam_open": {
        "en": "Opening Steam Workshop mod collection...",
        "uk": "Відкриття збірки модифікацій у Steam Workshop..."
    },
    "chk_launcher_loc": {
        "en": "Launcher Directory Placement",
        "uk": "Розміщення лаунчера в папці гри"
    },
    "chk_launcher_loc_ok": {
        "en": "Located beside ProjectZomboid64.exe ({path})",
        "uk": "Знаходиться поруч із ProjectZomboid64.exe ({path})"
    },
    "chk_launcher_loc_warn": {
        "en": "Running from: {app_dir}. Game folder: {game_dir}",
        "uk": "Запущено з: {app_dir}. Папка гри: {game_dir}"
    },
    "chk_launcher_loc_fail": {
        "en": "Invalid location! Running from: {app_dir}. Must be placed directly in the game folder beside ProjectZomboid64.exe.",
        "uk": "Неправильне розміщення! Запущено з: {app_dir}. Має бути безпосередньо в папці гри біля ProjectZomboid64.exe."
    },
    "chk_game_exe": {
        "en": "Game Binary (ProjectZomboid64.exe)",
        "uk": "Виконуваний файл гри (ProjectZomboid64.exe)"
    },
    "chk_jvm_scripts": {
        "en": "Optimized JVM Startup Scripts",
        "uk": "Оптимізовані JVM скрипти запуску"
    },
    "chk_zombie_buddy": {
        "en": "ZombieBuddy & zbNative DLL",
        "uk": "ZombieBuddy та zbNative DLL"
    },
    "chk_modguard": {
        "en": "PZ-ModGuard Security Scanner",
        "uk": "PZ-ModGuard сканер безпеки"
    },
    "chk_version_match": {
        "en": "Target Version (Launcher vs Repository)",
        "uk": "Таргет версія (Лаунчер vs Репозиторій)"
    },
    "chk_user_profile": {
        "en": "User Zomboid Profile (Mods & Saves)",
        "uk": "Папка профілю Zomboid (Моди та збереження)"
    },
    "all_systems_verified": {
        "en": "All systems verified",
        "uk": "Всі системи перевірено"
    },
    "view_diagnostics": {
        "en": "Diagnostics",
        "uk": "Діагностика"
    },
    "diag_title": {
        "en": "System Diagnostics",
        "uk": "Діагностика системи"
    },
    "diag_header_title": {
        "en": "SYSTEM VERIFICATION & DIAGNOSTICS",
        "uk": "СИСТЕМНА ДІАГНОСТИКА ТА ПЕРЕВІРКА"
    },
    "btn_reinstall_step": {
        "en": "🔄 Reinstall",
        "uk": "🔄 Перевстановити"
    },
    "btn_reinstall_all": {
        "en": "🔄 Reinstall All",
        "uk": "🔄 Перевстановити все"
    },
    "btn_open_folder": {
        "en": "📂 Open Folder",
        "uk": "📂 Відкрити папку"
    },
    "btn_open_steam": {
        "en": "🌐 Open in Steam",
        "uk": "🌐 Відкрити в Steam"
    },
    "btn_refresh_diag": {
        "en": "⟳ Refresh",
        "uk": "⟳ Оновити"
    },
    "step_reinstalled_success": {
        "en": "Successfully reinstalled!",
        "uk": "Успішно перевстановлено!"
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
    "status_invalid_placement": {
        "en": "Incorrect Launcher Location",
        "uk": "Неправильне розміщення лаунчера"
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
