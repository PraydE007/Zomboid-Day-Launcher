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


def _get_process_image_path(pid: int) -> Optional[str]:
    """Retrieve full executable path of a process via Win32 API."""
    PROCESS_QUERY_LIMITED_INFORMATION = 0x1000
    h = ctypes.windll.kernel32.OpenProcess(PROCESS_QUERY_LIMITED_INFORMATION, False, pid)
    if not h:
        return None
    buf = ctypes.create_unicode_buffer(1024)
    size = ctypes.wintypes.DWORD(1024)
    ok = ctypes.windll.kernel32.QueryFullProcessImageNameW(h, 0, buf, ctypes.byref(size))
    ctypes.windll.kernel32.CloseHandle(h)
    if ok:
        return buf.value
    return None


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


def _is_actual_game_pid(pid: int, game_dir_str: str) -> bool:
    """Strict check: PID must be a real game executable (ProjectZomboid or Java), NEVER cmd.exe."""
    if not _is_pid_alive(pid):
        return False
    img = _get_process_image_path(pid)
    if not img:
        return False
    img_low = img.lower()
    if img_low.endswith("cmd.exe") or img_low.endswith("conhost.exe"):
        return False
    if "projectzomboid64.exe" in img_low or "projectzomboid32.exe" in img_low:
        return True
    if img_low.endswith("java.exe") or img_low.endswith("javaw.exe"):
        if (game_dir_str and game_dir_str.lower() in img_low) or "projectzomboid" in img_low:
            return True
    return False


def _fast_find_process(target_names: Set[str], game_dir: Optional[str] = None) -> Optional[int]:
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
            elif exe in ("java.exe", "javaw.exe"):
                img = _get_process_image_path(entry.th32ProcessID)
                if img:
                    img_low = img.lower()
                    if (game_dir and game_dir.lower() in img_low) or "projectzomboid" in img_low:
                        found_pid = entry.th32ProcessID
                        break
            if not ctypes.windll.kernel32.Process32Next(h, ctypes.byref(entry)):
                break

    ctypes.windll.kernel32.CloseHandle(h)
    return found_pid


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


class LaunchCrashWatcher(QThread):
    sig_launch_failed = pyqtSignal(str)
    sig_launch_succeeded = pyqtSignal(int)

    def __init__(self, process_manager, parent=None):
        super().__init__(parent)
        self.mgr = process_manager
        self._running = True

    def stop(self):
        self._running = False

    def run(self):
        start_time = time.time()
        fatal_patterns = [
            "could not find agent library",
            "error occurred during initialization of vm",
            "can't find dependent libraries",
            "fatal error in native method",
            "a fatal error has been detected",
            "exception in thread \"main\"",
            "failed to load",
            "noclassdeffounderror",
            "cannot find"
        ]

        found_game = False
        while self._running and (time.time() - start_time < 6.5):
            time.sleep(0.3)

            # 1. Scan session log for fatal errors
            if self.mgr.session_log_path.exists():
                try:
                    with open(self.mgr.session_log_path, "r", encoding="utf-8", errors="ignore") as f:
                        lines = f.readlines()
                    for i, line in enumerate(lines[-25:]):
                        l_low = line.lower()
                        for pat in fatal_patterns:
                            if pat in l_low:
                                err_line = line.strip()
                                # Include adjacent error line for full context if available
                                if i + 1 < len(lines[-25:]):
                                    next_line = lines[-25:][i + 1].strip()
                                    if any(p in next_line.lower() for p in fatal_patterns) or "error" in next_line.lower() or "exception" in next_line.lower():
                                        err_line = f"{err_line}\n{next_line}"
                                self.sig_launch_failed.emit(err_line)
                                return
                except Exception:
                    pass

            # 2. Check if real game PID has started
            if self.mgr.is_game_running():
                found_game = True
                self.sig_launch_succeeded.emit(self.mgr.current_pid or 0)

            # 3. If batch wrapper exited and game is not running -> premature exit
            if self.mgr.batch_proc and self.mgr.batch_proc.poll() is not None:
                if not self.mgr.is_game_running():
                    self.sig_launch_failed.emit("Процес гри завершився передчасно без старту.")
                    return

        # End of monitoring window: final check
        if not found_game and not self.mgr.is_game_running():
            self.sig_launch_failed.emit("Процес гри не виявлено (можливий збій запуску).")


class ProcessManager(QObject):
    sig_log = pyqtSignal(str)
    sig_process_started = pyqtSignal(int, str)
    sig_process_stopped = pyqtSignal(int)
    sig_game_crashed = pyqtSignal(str)

    def __init__(self, config_manager, parent=None):
        super().__init__(parent)
        self.config = config_manager
        self.current_pid: Optional[int] = None
        self.batch_proc: Optional[subprocess.Popen] = None
        self.launch_watcher: Optional[LaunchCrashWatcher] = None
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
        1. Checks tracked game PID directly (<0.01ms), strictly excluding cmd.exe.
        2. Fallback to native Win32 Toolhelp snapshot (~10ms) cached for 1.5 seconds.
        """
        now = time.time()
        game_dir_str = self.config.game_dir

        # 1. If we have a tracked game PID, check it instantaneously
        if self.current_pid:
            if _is_actual_game_pid(self.current_pid, game_dir_str):
                self._last_status = True
                return True
            else:
                self.current_pid = None

        # Cache check for 1.5 seconds to avoid unnecessary scanning
        if now - self._last_check_time < 1.5:
            return self._last_status

        self._last_check_time = now

        # 2. Fast Win32 snapshot check
        target_names = {"projectzomboid64.exe", "projectzomboid32.exe"}
        pid = _fast_find_process(target_names, game_dir=game_dir_str)
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

        data_dir = Path(self.config.base_dir)
        bat_path = data_dir / bat_name
        if not bat_path.exists():
            bat_path = game_dir / bat_name
            if not bat_path.exists():
                exe_path = game_dir / "ProjectZomboid64.exe"
                if exe_path.exists():
                    bat_path = exe_path
                else:
                    self.sig_log.emit(f"[Помилка]: Не знайдено {bat_name} у {data_dir} або {game_dir}")
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

        # Setup environment with jre64\bin, win64, and game root on PATH
        env = os.environ.copy()
        env["PATH"] = f"{str(game_dir)};{str(game_dir / 'jre64' / 'bin')};{str(game_dir / 'win64')};" + env.get("PATH", "")

        show_ext_cmd = self.config.show_external_cmd or is_debug
        creationflags = subprocess.CREATE_NEW_PROCESS_GROUP
        if show_ext_cmd:
            creationflags |= subprocess.CREATE_NEW_CONSOLE
        else:
            creationflags |= subprocess.CREATE_NO_WINDOW

        # Add '< nul' to ensure batch files never hang on PAUSE
        wrapper_cmd = f'cmd.exe /c "call "{bat_path}" < nul >> "{self.session_log_path}" 2>&1"'

        self.sig_log.emit(f"Запуск гри: {bat_path.name} ({mode_name})")
        self.sig_log.emit(f"Папка виконання: {game_dir}")

        try:
            self.batch_proc = subprocess.Popen(
                wrapper_cmd,
                cwd=str(game_dir),
                env=env,
                shell=False,
                creationflags=creationflags
            )
            self.current_pid = None
            self._last_status = True
            self.sig_log.emit(f"Процес запущено (батнік PID: {self.batch_proc.pid})")

            if self.watcher:
                self.watcher.stop()
                self.watcher.wait()

            self.watcher = LogWatcherThread(self.session_log_path)
            self.watcher.sig_new_line.connect(lambda line: self.sig_log.emit(line))
            self.watcher.start()

            # Start launch crash watcher
            if self.launch_watcher:
                self.launch_watcher.stop()
                self.launch_watcher.wait()

            self.launch_watcher = LaunchCrashWatcher(self)
            self.launch_watcher.sig_launch_failed.connect(self._on_launch_failed)
            self.launch_watcher.sig_launch_succeeded.connect(self._on_launch_succeeded)
            self.launch_watcher.start()

            user_console = Path(self.config.user_zomboid_dir) / "console.txt"
            if user_console.exists():
                self.sig_log.emit(f"Підключено стеження за консоллю Zomboid: {user_console}")

            return True

        except Exception as e:
            self.sig_log.emit(f"[Помилка запуску гри]: {e}")
            return False

    def _on_launch_failed(self, error_line: str):
        self._last_status = False
        self.current_pid = None
        if self.batch_proc:
            try:
                self.batch_proc.kill()
            except Exception:
                pass
            self.batch_proc = None
        self.sig_log.emit(f"⛔ [НЕВДАЛИЙ ЗАПУСК ГРИ]: {error_line}")
        self.sig_process_stopped.emit(-1)
        self.sig_game_crashed.emit(error_line)

    def _on_launch_succeeded(self, pid: int):
        self.sig_log.emit(f"✅ [ГРУ УСПІШНО ЗАПУЩЕНО]: PID {pid}")
        self.sig_process_started.emit(pid, "Project Zomboid")

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
