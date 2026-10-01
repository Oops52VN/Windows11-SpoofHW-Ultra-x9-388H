import os
import sys
import logging
from typing import Optional

# ANSI Color Codes
RESET = "\033[0m"
BOLD = "\033[1m"
RED = "\033[91m"
GREEN = "\033[92m"
YELLOW = "\033[93m"
CYAN = "\033[96m"

# Enable VT100 terminal escape sequences on Windows console
if os.name == "nt":
    import ctypes
    kernel32 = ctypes.windll.kernel32
    # STD_OUTPUT_HANDLE = -11
    h_out = kernel32.GetStdHandle(-11)
    mode = ctypes.c_ulong()
    if kernel32.GetConsoleMode(h_out, ctypes.byref(mode)):
        # ENABLE_VIRTUAL_TERMINAL_PROCESSING = 0x0004
        kernel32.SetConsoleMode(h_out, mode.value | 0x0004)

_file_logger: Optional[logging.Logger] = None

def init_file_logger(log_dir: str = "logs") -> logging.Logger:
    global _file_logger
    if _file_logger is not None:
        return _file_logger

    os.makedirs(log_dir, exist_ok=True)
    log_path = os.path.join(log_dir, "spoofhw.log")

    logger = logging.getLogger("SpoofHW")
    logger.setLevel(logging.DEBUG)

    file_handler = logging.FileHandler(log_path, encoding="utf-8")
    file_handler.setLevel(logging.DEBUG)
    formatter = logging.Formatter(
        "%(asctime)s [%(levelname)s] %(message)s", datefmt="%Y-%m-%d %H:%M:%S"
    )
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)

    _file_logger = logger
    return logger

class Logger:
    @staticmethod
    def success(message: str) -> None:
        print(f"{GREEN}[OK]{RESET} {message}")
        if _file_logger:
            _file_logger.info(f"[OK] {message}")

    @staticmethod
    def info(message: str) -> None:
        print(f"{CYAN}[*]{RESET} {message}")
        if _file_logger:
            _file_logger.info(f"[*] {message}")

    @staticmethod
    def warning(message: str) -> None:
        print(f"{YELLOW}[!]{RESET} {message}")
        if _file_logger:
            _file_logger.warning(f"[!] {message}")

    @staticmethod
    def error(message: str) -> None:
        print(f"{RED}[X]{RESET} {message}")
        if _file_logger:
            _file_logger.error(f"[X] {message}")
