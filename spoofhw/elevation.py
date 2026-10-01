import os
import sys
import ctypes
from typing import List

def is_administrator() -> bool:
    """
    Checks whether the current process execution context holds Administrator privileges.
    """
    if os.name != "nt":
        return False
    try:
        return ctypes.windll.shell32.IsUserAnAdmin() != 0
    except Exception:
        return False

def relaunch_elevated(args: List[str], silent: bool = False) -> bool:
    """
    Relaunches the current script or executable with elevated Administrator privileges via UAC prompt.
    """
    if os.name != "nt":
        return False

    try:
        # Determine if running as a bundled PyInstaller binary or Python script
        if getattr(sys, "frozen", False):
            target_exe = sys.executable
            target_args = " ".join([f'"{a}"' if " " in a else a for a in args])
        else:
            target_exe = sys.executable
            script_path = os.path.abspath(sys.argv[0])
            all_args = [f'"{script_path}"'] + [f'"{a}"' if " " in a else a for a in args]
            target_args = " ".join(all_args)

        # SW_HIDE = 0, SW_SHOWNORMAL = 1
        n_show_cmd = 0 if silent else 1

        result = ctypes.windll.shell32.ShellExecuteW(
            None,
            "runas",
            target_exe,
            target_args,
            None,
            n_show_cmd
        )

        # HINSTANCE > 32 indicates success
        return result > 32
    except Exception:
        return False
