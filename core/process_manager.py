import os
import sys
import time
import subprocess
import ctypes
import ctypes.wintypes
from pathlib import Path
from typing import Optional, Set, Tuple, List
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


def determine_modguard_scan_profile(config) -> Tuple[int, str, str]:
    """
    Decide whether to run Profile 2 (Full Deep Scan) or Profile 1 (Quick Scan).
    Returns (profile_id, profile_title_key, scan_reason_key).

    Profile 2 (Full Deep Scan):
      1. First scan ever (config "modguard_full_scan_done" is False).
      2. Base game engine was updated (projectzomboid.jar or ProjectZomboid64.exe mtime changed).
      3. Periodic audit (7+ days since last full scan).

    Profile 1 (Quick Scan, ~1.5s):
      - Routine launches when no engine changes and recent full scan exists.
    """
    game_dir = Path(config.game_dir)
    full_done = config.get("modguard_full_scan_done", False)
    if not full_done:
        return 2, "scan_profile_full", "scan_reason_first"

    # Check 7-day periodic audit
    last_full_ts = float(config.get("modguard_last_full_scan_time", 0.0))
    now = time.time()
    if now - last_full_ts > (7 * 86400):
        return 2, "scan_profile_full", "scan_reason_periodic"

    # Check engine file modification times
    current_engine_mtime = 0.0
    for engine_file in ["projectzomboid.jar", "ProjectZomboid64.exe", "ProjectZomboid64.json"]:
        p = game_dir / engine_file
        if p.exists():
            try:
                m = p.stat().st_mtime
                if m > current_engine_mtime:
                    current_engine_mtime = m
            except Exception:
                pass

    last_engine_mtime = float(config.get("modguard_last_engine_mtime", 0.0))
    if current_engine_mtime > 0 and current_engine_mtime > last_engine_mtime:
        return 2, "scan_profile_full", "scan_reason_updated"

    # Routine quick scan
    return 1, "scan_profile_quick", "scan_reason_routine"


class ModGuardScanThread(QThread):
    sig_log = pyqtSignal(str)
    sig_finished = pyqtSignal(bool, int, str, list)  # (is_clean, exit_code, summary, critical_threats)

    def __init__(self, game_dir: Path, profile_id: int = 1, parent=None):
        super().__init__(parent)
        self.game_dir = Path(game_dir)
        self.profile_id = profile_id

    def run(self):
        modguard_path = self.game_dir / "PZ-ModGuard.bat"
        if not modguard_path.exists():
            self.sig_log.emit(f"[PZ-ModGuard помилка]: Скрипт {modguard_path} не знайдено.")
            self.sig_finished.emit(False, -1, f"PZ-ModGuard.bat not found in {self.game_dir}", ["PZ-ModGuard.bat not found"])
            return

        profile_label = "Full Deep Scan (2)" if self.profile_id == 2 else "Quick Scan (1)"
        self.sig_log.emit(f"🛡️ [PZ-ModGuard]: Початок сканування безпеки модів ({profile_label})...")
        self.sig_log.emit(f"  → Робоча папка: {self.game_dir}")

        critical_threats: List[str] = []
        try:
            env = os.environ.copy()
            env["PZMG_PROFILE"] = str(self.profile_id)
            env["PZMG_SELF"] = str(modguard_path)

            ps_cmd = [
                "powershell.exe",
                "-NoProfile",
                "-ExecutionPolicy", "Bypass",
                "-Command",
                f"$env:PZMG_SELF='{str(modguard_path)}'; "
                f"$env:PZMG_PROFILE='{self.profile_id}'; "
                f"$src = [System.IO.File]::ReadAllText('{str(modguard_path)}'); "
                f"if ($src -notmatch 'Zomboid-Day-Launcher') {{ "
                f"    $src = $src.Replace('$stockPzExes = @(', '$stockPzExes = @(''Zomboid-Day-Launcher.exe'', '); "
                f"    $src = $src.Replace('$stockPzScripts = @(', '$stockPzScripts = @(''PZ-ModGuard.bat'', '); "
                f"}} "
                f"Invoke-Expression $src"
            ]

            proc = subprocess.Popen(
                ps_cmd,
                cwd=str(self.game_dir),
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                env=env,
                creationflags=subprocess.CREATE_NO_WINDOW
            )
            for line in iter(proc.stdout.readline, ''):
                if line:
                    clean_line = line.rstrip()
                    self.sig_log.emit(f"[PZ-ModGuard]: {clean_line}")
                    lower = clean_line.lower()
                    # Filter out false-positives for our own launcher binaries and modguard script
                    if "zomboid-day-launcher" in lower or "pz-modguard" in lower:
                        continue
                    if "[critical]" in lower or "critical:" in lower or "[threat]" in lower or "danger!" in lower or "critical threat(s) detected" in lower:
                        critical_threats.append(clean_line)

            proc.stdout.close()
            code = proc.wait()
            # If no critical non-self threats detected, scan is considered clean!
            is_clean = len(critical_threats) == 0
            if not is_clean:
                self.sig_log.emit(f"🛡️ [PZ-ModGuard]: ⛔ ВИЯВЛЕНО КРИТИЧНІ ЗАГРОЗИ! Код: {code}, Загроз: {len(critical_threats)}")
                self.sig_finished.emit(False, code, f"Critical threats detected ({len(critical_threats)})", critical_threats)
            else:
                self.sig_log.emit(f"🛡️ [PZ-ModGuard]: ✅ Сканування завершено успішно (загроз: 0).")
                self.sig_finished.emit(True, 0, "Scan complete.", [])
        except Exception as e:
            self.sig_log.emit(f"[PZ-ModGuard виняток]: {e}")
            self.sig_finished.emit(False, -1, str(e), [str(e)])


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
        if getattr(self.config, "is_valid_location", True):
            try:
                self.session_log_path.parent.mkdir(parents=True, exist_ok=True)
            except Exception:
                pass
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
                self.sig_log.emit("🛡️ [PZ-ModGuard]: Запуск перевірки безпеки модів перед стартом гри...")
                try:
                    proc = subprocess.Popen(
                        ["cmd.exe", "/c", str(modguard_path)],
                        cwd=str(game_dir),
                        stdout=subprocess.PIPE,
                        stderr=subprocess.STDOUT,
                        text=True,
                        creationflags=subprocess.CREATE_NO_WINDOW
                    )
                    for line in iter(proc.stdout.readline, ''):
                        if line:
                            self.sig_log.emit(f"[PZ-ModGuard]: {line.rstrip()}")
                    proc.stdout.close()
                    proc.wait()
                    self.sig_log.emit("🛡️ [PZ-ModGuard]: Перевірку безпеки модів успішно завершено.")
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

    def run_modguard_scan_async(self, profile_id: int = 1, on_log=None, on_finished=None) -> ModGuardScanThread:
        """Run PZ-ModGuard scan asynchronously in a background thread."""
        game_dir = Path(self.config.game_dir)
        worker = ModGuardScanThread(game_dir, profile_id=profile_id, parent=self)
        if on_log:
            worker.sig_log.connect(on_log)
        if on_finished:
            worker.sig_finished.connect(on_finished)
        worker.sig_log.connect(lambda msg: self.sig_log.emit(msg))
        worker.start()
        return worker
