import time
import winreg
from typing import Optional
from .config import HardwareProfile
from .virtualizer import RegistryVirtualizer
from .logger import Logger

class WatchdogDaemon:
    """
    Continuous background monitor daemon to detect and correct registry hardware specification resets
    caused by Windows updates, power state transitions (sleep/wake), or driver restarts.
    """
    def __init__(self, profile: HardwareProfile, interval_seconds: int = 30):
        self.profile = profile
        self.interval_seconds = interval_seconds
        self._running = False

    def run(self) -> None:
        """
        Starts the watchdog monitoring loop.
        """
        self._running = True
        Logger.info(f"Starting SpoofHW Watchdog Daemon (Interval: {self.interval_seconds}s)...")
        Logger.info(f"Target CPU: {self.profile.cpu_name}")
        Logger.info(f"Target GPU: {self.profile.gpu_name}")

        try:
            while self._running:
                if self._needs_reapplication():
                    Logger.warning("Hardware specification drift detected! Reapplying virtualization profile...")
                    RegistryVirtualizer.apply_all(self.profile)
                    Logger.success("Profile reapplied successfully.")
                time.sleep(self.interval_seconds)
        except KeyboardInterrupt:
            Logger.info("Watchdog daemon stopped by user.")
        except Exception as ex:
            Logger.error(f"Watchdog daemon error: {ex}")

    def stop(self) -> None:
        self._running = False

    def _needs_reapplication(self) -> bool:
        """
        Checks critical keys (such as CPU CentralProcessor core 0) to verify if values were reverted by the OS.
        """
        try:
            with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, r"HARDWARE\DESCRIPTION\System\CentralProcessor\0", 0, winreg.KEY_READ) as key:
                current_cpu, _ = winreg.QueryValueEx(key, "ProcessorNameString")
                if current_cpu != self.profile.cpu_name:
                    return True
        except Exception:
            return True

        # Check WinSAT primary adapter
        try:
            with winreg.OpenKey(
                winreg.HKEY_LOCAL_MACHINE,
                r"SOFTWARE\Microsoft\Windows NT\CurrentVersion\WinSAT",
                0,
                winreg.KEY_READ | winreg.KEY_WOW64_64KEY
            ) as key:
                current_adapter, _ = winreg.QueryValueEx(key, "PrimaryAdapterString")
                if current_adapter != self.profile.gpu_name:
                    return True
        except Exception:
            pass

        return False
