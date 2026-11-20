import os
import sys
import time
import subprocess
from pathlib import Path
from typing import Optional, Callable
import psutil
from PyQt6.QtCore import QThread, pyqtSignal, QObject


class LogWatcherThread(QThread):
    sig_new_line = pyqtSignal(str)

    def __init__(self, log_file: Path, parent=None):
        super().__init__(parent)
        self.log_file = Path(log_file)
        self._running = True

    def stop(self):
        self._running = False

    def run(self):
        # Wait until file exists
        start_wait = time.time()
        while not self.log_file.exists() and (time.time() - start_wait < 5):
            time.sleep(0.2)

        if not self.log_file.exists():
            return

        try:
            with open(self.log_file, "r", encoding="utf-8", errors="replace") as f:
                # Seek to end or read recent lines
                f.seek(0, os.SEEK_END)
                while self._running:
                    line = f.readline()
                    if line:
                        self.sig_new_line.emit(line.rstrip("\r\n"))
                    else:
                        time.sleep(0.15)
        except Exception as e:
            self.sig_new_line.emit(f"[LogWatcher помилка]: {e}")


class ProcessManager(QObject):
    sig_log = pyqtSignal(str)
    sig_process_started = pyqtSignal(int, str)  # pid, executable
    sig_process_stopped = pyqtSignal(int)

    def __init__(self, config_manager, parent=None):
        super().__init__(parent)
        self.config = config_manager
        self.current_pid: Optional[int] = None
        self.watcher: Optional[LogWatcherThread] = None
        self.session_log_path = Path(self.config.base_dir) / "logs" / "session_output.log"
        self.session_log_path.parent.mkdir(parents=True, exist_ok=True)

    def is_game_running(self) -> bool:
        """Check if Project Zomboid (or our spawned process) is currently running."""
        if self.current_pid:
            try:
                p = psutil.Process(self.current_pid)
                if p.is_running() and p.status() != psutil.STATUS_ZOMBIE:
                    return True
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                self.current_pid = None

        # Check by process names
        target_names = ["ProjectZomboid64.exe", "ProjectZomboid32.exe"]
        for p in psutil.process_iter(['pid', 'name', 'cmdline']):
            try:
                name = p.info.get('name') or ''
                if name in target_names:
                    self.current_pid = p.pid
                    return True
                # Check java with zomboid in cmdline
                if "java" in name.lower():
                    cmdline = " ".join(p.info.get('cmdline') or [])
                    if "zombie.gameStates.MainScreenState" in cmdline or "projectzomboid" in cmdline.lower():
                        self.current_pid = p.pid
                        return True
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                continue

        return False

    def launch_game(self, is_debug: bool = False, run_security_scan: bool = False) -> bool:
        """
        Launch Project Zomboid as an independent, detached process.
        When launcher exits, the game process continues running!
        """
        game_dir = Path(self.config.game_dir)
        if not game_dir.exists():
            self.sig_log.emit(f"[Помилка]: Папка гри не існує: {game_dir}")
            return False

        # Determine bat file
        if is_debug:
            bat_name = "ProjectZomboid64ShowConsole.bat"
            mode_name = "Дебаг запуск (-debug)"
        else:
            bat_name = "ProjectZomboid64.bat"
            mode_name = "Стандартний запуск"

        bat_path = game_dir / bat_name
        if not bat_path.exists():
            # Fallback to exe
            exe_path = game_dir / "ProjectZomboid64.exe"
            if exe_path.exists():
                bat_path = exe_path
            else:
                self.sig_log.emit(f"[Помилка]: Не знайдено {bat_name} або ProjectZomboid64.exe у {game_dir}")
                return False

        # Check PZ-ModGuard if requested
        if run_security_scan:
            modguard_path = game_dir / "PZ-ModGuard.bat"
            if modguard_path.exists():
                self.sig_log.emit("🔍 Запуск швидкого сканування модів через PZ-ModGuard...")
                try:
                    res = subprocess.run(
                        ["cmd.exe", "/c", str(modguard_path)],
                        cwd=str(game_dir),
                        capture_output=True,
                        text=True,
                        timeout=30
                    )
                    self.sig_log.emit(f"[PZ-ModGuard]: {res.stdout.strip()}")
                except Exception as e:
                    self.sig_log.emit(f"[PZ-ModGuard попередження]: {e}")

        # Prepare log redirection wrapper
        # Clear previous session log
        try:
            self.session_log_path.write_text(f"=== Сесія запуску {time.strftime('%Y-%m-%d %H:%M:%S')} [{mode_name}] ===\n", encoding="utf-8")
        except Exception:
            pass

        show_ext_cmd = self.config.show_external_cmd or is_debug

        # Construct independent command
        # Using cmd.exe /c with tee/redirection
        # Notice: To guarantee process survives when launcher terminates,
        # we pass CREATE_NEW_PROCESS_GROUP and either CREATE_NEW_CONSOLE (if visible)
        # or CREATE_NO_WINDOW (if hidden).
        creationflags = subprocess.CREATE_NEW_PROCESS_GROUP
        if show_ext_cmd:
            creationflags |= subprocess.CREATE_NEW_CONSOLE
        else:
            creationflags |= subprocess.CREATE_NO_WINDOW

        # Launch command that writes to session_log_path as well as running the bat
        # PowerShell or cmd redirection
        wrapper_cmd = f'cmd.exe /c "call "{bat_path}" >> "{self.session_log_path}" 2>&1"'

        self.sig_log.emit(f"🚀 Запуск гри: {bat_path.name} ({mode_name})")
        self.sig_log.emit(f"Папка виконання: {game_dir}")
        self.sig_log.emit(f"Прапорці процесу: CREATE_NEW_PROCESS_GROUP (процес повністю автономний від лаунчера)")

        try:
            proc = subprocess.Popen(
                wrapper_cmd,
                cwd=str(game_dir),
                shell=False,
                creationflags=creationflags
            )
            self.current_pid = proc.pid
            self.sig_log.emit(f"✅ Процес успішно запущено (PID: {proc.pid})")
            self.sig_process_started.emit(proc.pid, bat_name)

            # Start watching session log
            if self.watcher:
                self.watcher.stop()
                self.watcher.wait()

            self.watcher = LogWatcherThread(self.session_log_path)
            self.watcher.sig_new_line.connect(lambda line: self.sig_log.emit(line))
            self.watcher.start()

            # Also watch Zomboid user console.txt if exists
            user_console = Path(self.config.user_zomboid_dir) / "console.txt"
            if user_console.exists():
                self.sig_log.emit(f"Підключено стеження за системним логом Zomboid: {user_console}")

            return True

        except Exception as e:
            self.sig_log.emit(f"[Помилка запуску гри]: {e}")
            return False

    def execute_custom_cmd(self, cmd_text: str):
        """Execute custom arbitrary command in game or launcher context."""
        game_dir = Path(self.config.game_dir)
        cwd = str(game_dir) if game_dir.exists() else str(self.config.base_dir)

        self.sig_log.emit(f"> {cmd_text}")
        try:
            proc = subprocess.Popen(
                f'cmd.exe /c "{cmd_text}"',
                cwd=cwd,
                shell=False,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                creationflags=subprocess.CREATE_NEW_PROCESS_GROUP
            )
            out, _ = proc.communicate(timeout=60)
            for line in out.splitlines():
                self.sig_log.emit(line)
        except Exception as e:
            self.sig_log.emit(f"[Помилка виконання команди]: {e}")
