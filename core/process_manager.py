import os
import sys
import time
import subprocess
import ctypes
import ctypes.wintypes
from pathlib import Path
from typing import Optional, Set
from PyQt6.QtCore import QThread, pyqtSignal, QObject

TH32CS_SNAPPROCESS = 0x00000002


class PROCESSENTRY32(ctypes.Structure):
    _fields_ = [
        ("dwSize", ctypes.wintypes.DWORD),
        ("cntUsage", ctypes.wintypes.DWORD),
        ("th32ProcessID", ctypes.wintypes.DWORD),
        ("th32DefaultHeapID", ctypes.c_size_t),
        ("th32ModuleID", ctypes.wintypes.DWORD),
        ("cntThreads", ctypes.wintypes.DWORD),
        ("th32ParentProcessID", ctypes.wintypes.DWORD),
        ("pcPriClassBase", ctypes.c_long),
        ("dwFlags", ctypes.wintypes.DWORD),
        ("szExeFile", ctypes.c_char * 260)
    ]


def _fast_find_process(target_names: Set[str]) -> Optional[int]:
    """Scan running processes via Windows Toolhelp32 snapshot (~10ms vs 1100ms psutil)."""
    h = ctypes.windll.kernel32.CreateToolhelp32Snapshot(TH32CS_SNAPPROCESS, 0)
    if h == -1 or h == 0xFFFFFFFF:
        return None

    entry = PROCESSENTRY32()
    entry.dwSize = ctypes.sizeof(PROCESSENTRY32)
    found_pid = None

    if ctypes.windll.kernel32.Process32First(h, ctypes.byref(entry)):
        while True:
            exe = entry.szExeFile.decode("ansi", errors="ignore").lower()
            if exe in target_names:
                found_pid = entry.th32ProcessID
                break
            if not ctypes.windll.kernel32.Process32Next(h, ctypes.byref(entry)):
                break

    ctypes.windll.kernel32.CloseHandle(h)
    return found_pid


def _is_pid_alive(pid: int) -> bool:
    """Check if a specific PID is still alive via OpenProcess (~0.005ms)."""
    PROCESS_QUERY_LIMITED_INFORMATION = 0x1000
    STILL_ACTIVE = 259
    h = ctypes.windll.kernel32.OpenProcess(PROCESS_QUERY_LIMITED_INFORMATION, False, pid)
    if not h:
        return False
    exit_code = ctypes.wintypes.DWORD()
    success = ctypes.windll.kernel32.GetExitCodeProcess(h, ctypes.byref(exit_code))
    ctypes.windll.kernel32.CloseHandle(h)
    return bool(success and exit_code.value == STILL_ACTIVE)


class LogWatcherThread(QThread):
    sig_new_line = pyqtSignal(str)

    def __init__(self, log_file: Path, parent=None):
        super().__init__(parent)
        self.log_file = Path(log_file)
        self._running = True

    def stop(self):
        self._running = False

    def run(self):
        start_wait = time.time()
        while not self.log_file.exists() and (time.time() - start_wait < 5):
            time.sleep(0.2)

        if not self.log_file.exists():
            return

        try:
            with open(self.log_file, "r", encoding="utf-8", errors="replace") as f:
                f.seek(0, os.SEEK_END)
                while self._running:
                    line = f.readline()
                    if line:
                        self.sig_new_line.emit(line.rstrip("\r\n"))
                    else:
                        time.sleep(0.25)
        except Exception as e:
            self.sig_new_line.emit(f"[LogWatcher помилка]: {e}")


class ProcessManager(QObject):
    sig_log = pyqtSignal(str)
    sig_process_started = pyqtSignal(int, str)
    sig_process_stopped = pyqtSignal(int)

    def __init__(self, config_manager, parent=None):
        super().__init__(parent)
        self.config = config_manager
        self.current_pid: Optional[int] = None
        self.watcher: Optional[LogWatcherThread] = None
        self.session_log_path = Path(self.config.base_dir) / "logs" / "session_output.log"
        self.session_log_path.parent.mkdir(parents=True, exist_ok=True)
        self._last_check_time: float = 0
        self._last_status: bool = False

    def is_game_running(self) -> bool:
        """
        Instantaneous non-blocking check if Project Zomboid is running.
        1. Checks tracked PID directly (<0.01ms).
        2. Fallback to native Win32 Toolhelp snapshot (~10ms) cached for 2 seconds.
        """
        now = time.time()

        # 1. If we have a tracked PID, check it instantaneously
        if self.current_pid:
            if _is_pid_alive(self.current_pid):
                self._last_status = True
                return True
            else:
                self.current_pid = None

        # Cache check for 2 seconds to avoid unnecessary scanning
        if now - self._last_check_time < 2.0:
            return self._last_status

        self._last_check_time = now

        # 2. Fast Win32 snapshot check
        target_names = {"projectzomboid64.exe", "projectzomboid32.exe"}
        pid = _fast_find_process(target_names)
        if pid:
            self.current_pid = pid
            self._last_status = True
            return True

        self._last_status = False
        return False

    def launch_game(self, is_debug: bool = False, run_security_scan: bool = False) -> bool:
        game_dir = Path(self.config.game_dir)
        if not game_dir.exists():
            self.sig_log.emit(f"[Помилка]: Папка гри не існує: {game_dir}")
            return False

        if is_debug:
            bat_name = "ProjectZomboid64ShowConsole.bat"
            mode_name = "Дебаг запуск (-debug)"
        else:
            bat_name = "ProjectZomboid64.bat"
            mode_name = "Стандартний запуск"

        bat_path = game_dir / bat_name
        if not bat_path.exists():
            exe_path = game_dir / "ProjectZomboid64.exe"
            if exe_path.exists():
                bat_path = exe_path
            else:
                self.sig_log.emit(f"[Помилка]: Не знайдено {bat_name} або ProjectZomboid64.exe у {game_dir}")
                return False

        if run_security_scan:
            modguard_path = game_dir / "PZ-ModGuard.bat"
            if modguard_path.exists():
                self.sig_log.emit("Запуск швидкого сканування модів через PZ-ModGuard...")
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

        try:
            self.session_log_path.write_text(f"=== Сесія запуску {time.strftime('%Y-%m-%d %H:%M:%S')} [{mode_name}] ===\n", encoding="utf-8")
        except Exception:
            pass

        show_ext_cmd = self.config.show_external_cmd or is_debug
        creationflags = subprocess.CREATE_NEW_PROCESS_GROUP
        if show_ext_cmd:
            creationflags |= subprocess.CREATE_NEW_CONSOLE
        else:
            creationflags |= subprocess.CREATE_NO_WINDOW

        wrapper_cmd = f'cmd.exe /c "call "{bat_path}" >> "{self.session_log_path}" 2>&1"'

        self.sig_log.emit(f"Запуск гри: {bat_path.name} ({mode_name})")
        self.sig_log.emit(f"Папка виконання: {game_dir}")

        try:
            proc = subprocess.Popen(
                wrapper_cmd,
                cwd=str(game_dir),
                shell=False,
                creationflags=creationflags
            )
            self.current_pid = proc.pid
            self._last_status = True
            self.sig_log.emit(f"Процес успішно запущено (PID: {proc.pid})")
            self.sig_process_started.emit(proc.pid, bat_name)

            if self.watcher:
                self.watcher.stop()
                self.watcher.wait()

            self.watcher = LogWatcherThread(self.session_log_path)
            self.watcher.sig_new_line.connect(lambda line: self.sig_log.emit(line))
            self.watcher.start()

            user_console = Path(self.config.user_zomboid_dir) / "console.txt"
            if user_console.exists():
                self.sig_log.emit(f"Підключено стеження за консоллю Zomboid: {user_console}")

            return True

        except Exception as e:
            self.sig_log.emit(f"[Помилка запуску гри]: {e}")
            return False

    def execute_custom_cmd(self, cmd_text: str):
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
