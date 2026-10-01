"""
SpoofHW - Hardware Specification Emulation & Registry Virtualization Suite
Enterprise-grade Python engine for Windows 10 / 11.
"""

__version__ = "2.0.0"
__author__ = "SpoofHW Development Team"

from .config import HardwareProfile
from .virtualizer import RegistryVirtualizer
from .snapshot import RegistrySnapshotManager
from .scheduler import TaskSchedulerService
from .watchdog import WatchdogDaemon

__all__ = [
    "HardwareProfile",
    "RegistryVirtualizer",
    "RegistrySnapshotManager",
    "TaskSchedulerService",
    "WatchdogDaemon",
]
