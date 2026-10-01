import os
import sys
import argparse
from typing import List, Optional

from .config import HardwareProfile
from .logger import Logger, init_file_logger
from .elevation import is_administrator, relaunch_elevated
from .virtualizer import RegistryVirtualizer
from .snapshot import RegistrySnapshotManager
from .scheduler import TaskSchedulerService
from .watchdog import WatchdogDaemon

def display_banner() -> None:
    print("\033[96m====================================================================")
    print("        SPOOFHW - HARDWARE SPECIFICATION EMULATION ENGINE          ")
    print("        Enterprise Multi-Architecture Windows Systems Layer         ")
    print("====================================================================\033[0m\n")

def parse_args(argv: Optional[List[str]] = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        prog="spoofhw",
        description="High-performance, zero-dependency utility to emulate CPU, GPU, and NPU hardware specifications.",
        formatter_class=argparse.RawDescriptionHelpFormatter
    )

    parser.add_argument("-s", "--silent", "-a", "--autorun", action="store_true", help="Run silently without interactive prompts (for background tasks/logon)")
    parser.add_argument("-i", "--install", action="store_true", help="Apply hardware profile and register startup Task Scheduler task")
    parser.add_argument("-u", "--uninstall", action="store_true", help="Unregister and remove startup Task Scheduler task")
    parser.add_argument("-v", "--verify", action="store_true", help="Inspect and display active hardware registry values")
    parser.add_argument("-r", "--restore", nargs="?", const="latest", default=None, help="Restore registry from backup snapshot file (default: latest)")
    parser.add_argument("-w", "--watchdog", action="store_true", help="Run in continuous background watchdog mode to prevent OS reset")
    parser.add_argument("--interval", type=int, default=30, help="Watchdog check interval in seconds (default: 30)")
    parser.add_argument("--config", "-c", type=str, default=None, help="Path to custom JSON configuration profile")
    parser.add_argument("--save-config", type=str, default=None, help="Export current hardware profile settings to specified JSON file")
    parser.add_argument("--cpu", type=str, default=None, help="Override target CPU name")
    parser.add_argument("--gpu", type=str, default=None, help="Override target GPU name")
    parser.add_argument("--npu", type=str, default=None, help="Override target NPU name")

    return parser.parse_args(argv)

def run_cli(argv: Optional[List[str]] = None) -> int:
    init_file_logger()
    args = parse_args(argv)

    # 1. Load Hardware Profile
    profile = HardwareProfile()
    if args.config:
        try:
            profile = HardwareProfile.load_from_file(args.config)
        except Exception as ex:
            Logger.error(f"Failed to load config file: {ex}")
            return 1
    elif os.path.exists("profiles/default.json"):
        try:
            profile = HardwareProfile.load_from_file("profiles/default.json")
        except Exception:
            pass

    # CLI overrides
    if args.cpu:
        profile.cpu_name = args.cpu
    if args.gpu:
        profile.gpu_name = args.gpu
        profile.gpu_family = f"{args.gpu} Family"
    if args.npu:
        profile.npu_name = args.npu

    if args.save_config:
        try:
            profile.save_to_file(args.save_config)
            Logger.success(f"Configuration profile saved to {args.save_config}")
            return 0
        except Exception as ex:
            Logger.error(f"Failed to save profile: {ex}")
            return 1

    # 2. Read-Only Verification Mode
    if args.verify:
        print("====================================================================")
        print("            SPOOFHW - HARDWARE REGISTRY VERIFICATION               ")
        print("====================================================================")
        verifications = RegistryVirtualizer.verify_current(profile)
        for res in verifications:
            if res.success:
                Logger.success(f"{res.subsystem_name}: {res.message}")
            else:
                Logger.error(f"{res.subsystem_name}: {res.message}")
        return 0

    # 3. Elevation Guard for write operations
    if not is_administrator():
        raw_args = sys.argv[1:] if argv is None else argv
        if args.silent:
            relaunch_elevated(raw_args, silent=True)
            return 1

        Logger.warning("Administrator privileges required for registry hardware emulation.")
        Logger.info("Requesting elevated UAC token...")

        if relaunch_elevated(raw_args, silent=False):
            return 0

        Logger.error("Elevation request was declined or failed.")
        print("\nPlease right-click the script/executable and select 'Run as administrator'.")
        input("Press Enter to exit...")
        return 1

    snapshot_mgr = RegistrySnapshotManager()

    # 4. Registry Snapshot Restore Mode
    if args.restore is not None:
        target_file = args.restore
        if target_file == "latest":
            try:
                target_file = snapshot_mgr.get_latest_backup()
            except Exception as ex:
                Logger.error(str(ex))
                return 1

        Logger.info(f"Restoring registry snapshot from: {target_file}")
        try:
            snapshot_mgr.restore_snapshot(target_file)
            return 0
        except Exception as ex:
            Logger.error(f"Restore failed: {ex}")
            return 1

    # 5. Handle AutoRun Uninstallation
    if args.uninstall:
        uninstalled = TaskSchedulerService.uninstall_task(profile.task_name, args.silent)
        return 0 if uninstalled else 1

    # 6. Handle AutoRun Installation
    if args.install:
        RegistryVirtualizer.apply_all(profile, snapshot_mgr)
        installed = TaskSchedulerService.install_task(profile.task_name, args.silent)
        return 0 if installed else 1

    # 7. Watchdog Mode
    if args.watchdog:
        # First ensure applied
        RegistryVirtualizer.apply_all(profile, snapshot_mgr)
        daemon = WatchdogDaemon(profile, interval_seconds=args.interval)
        daemon.run()
        return 0

    # 8. Standard / Interactive Execution
    if not args.silent:
        display_banner()

    results = RegistryVirtualizer.apply_all(profile, snapshot_mgr)
    all_success = True

    for result in results:
        if not result.success:
            all_success = False
        if not args.silent:
            if result.success:
                Logger.success(f"{result.subsystem_name}: {result.message}")
            else:
                Logger.error(f"{result.subsystem_name}: {result.message}")

    if not args.silent:
        print("\n\033[96m====================================================================")
        print("\033[92m[STATUS] HARDWARE SPECIFICATION PROFILE APPLIED SUCCESSFULLY!\033[0m")
        print("Target Profile Configuration:")
        print(f"  * CPU : {profile.cpu_name}")
        print(f"  * GPU : {profile.gpu_name}")
        print(f"  * NPU : {profile.npu_name}")
        print("\033[96m====================================================================\033[0m\n")

        print("Startup Task Scheduler Options:")
        print("  [1] Install AutoRun Task (Launch automatically at Windows logon)")
        print("  [2] Remove AutoRun Task")
        print("  [3] Start Watchdog Daemon (Keep active in this window)")
        print("  [4] Exit")

        choice = input("\nEnter choice [1-4] (Default = 1): ").strip()
        if choice in ("", "1"):
            TaskSchedulerService.install_task(profile.task_name, silent=False)
        elif choice == "2":
            TaskSchedulerService.uninstall_task(profile.task_name, silent=False)
        elif choice == "3":
            daemon = WatchdogDaemon(profile, interval_seconds=30)
            daemon.run()

        input("\nExecution complete. Press Enter to exit...")

    return 0 if all_success else 1
