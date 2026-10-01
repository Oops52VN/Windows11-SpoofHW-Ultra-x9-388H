import os
import json
import time
import winreg
from typing import Dict, Any, List
from .logger import Logger

class RegistrySnapshotManager:
    """
    Manages capturing and restoring registry state backups before applying overrides.
    """
    def __init__(self, backup_dir: str = "backups"):
        self.backup_dir = backup_dir
        os.makedirs(self.backup_dir, exist_ok=True)

    def save_snapshot(self, records: List[Dict[str, Any]]) -> str:
        """
        Saves a list of registry key value records to a timestamped backup JSON file.
        Each record has format:
        {
            "hive": "HKLM",
            "path": r"...",
            "view": "64" or "32" or "default",
            "value_name": "...",
            "type": winreg.REG_SZ,
            "data": "..."
        }
        """
        timestamp = time.strftime("%Y%m%d_%H%M%S")
        filepath = os.path.join(self.backup_dir, f"backup_{timestamp}.json")

        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(records, f, indent=4)

        Logger.info(f"Registry snapshot saved to: {filepath}")
        return filepath

    def get_latest_backup(self) -> str:
        """Returns the path to the most recent backup file."""
        files = [
            os.path.join(self.backup_dir, f)
            for f in os.listdir(self.backup_dir)
            if f.startswith("backup_") and f.endswith(".json")
        ]
        if not files:
            raise FileNotFoundError("No existing backup files found in backups directory.")
        files.sort(key=os.path.getmtime, reverse=True)
        return files[0]

    def restore_snapshot(self, filepath: str) -> int:
        """
        Restores registry values recorded in a snapshot file.
        """
        if not os.path.exists(filepath):
            raise FileNotFoundError(f"Backup file not found: {filepath}")

        with open(filepath, "r", encoding="utf-8") as f:
            records = json.load(f)

        restored_count = 0
        for item in records:
            sub_path = item.get("path")
            view_flag = item.get("view", "64")
            val_name = item.get("value_name")
            val_type = item.get("type", winreg.REG_SZ)
            data = item.get("data")

            # Determine view access mask
            access = winreg.KEY_SET_VALUE
            if view_flag == "64":
                access |= winreg.KEY_WOW64_64KEY
            elif view_flag == "32":
                access |= winreg.KEY_WOW64_32KEY

            try:
                with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, sub_path, 0, access) as key:
                    if data is None:
                        # Value did not exist originally, remove if present
                        try:
                            winreg.DeleteValue(key, val_name)
                            restored_count += 1
                        except FileNotFoundError:
                            pass
                    else:
                        winreg.SetValueEx(key, val_name, 0, val_type, data)
                        restored_count += 1
            except Exception as ex:
                Logger.warning(f"Could not restore {sub_path}\\{val_name}: {ex}")

        Logger.success(f"Restored {restored_count} registry value(s) from {filepath}")
        return restored_count
