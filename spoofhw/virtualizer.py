import re
import winreg
from dataclasses import dataclass
from typing import List, Optional, Tuple, Dict, Any
from .config import HardwareProfile
from .logger import Logger
from .snapshot import RegistrySnapshotManager

@dataclass
class OperationResult:
    subsystem_name: str
    success: bool
    affected_items: int
    message: str

class RegistryVirtualizer:
    """
    High-performance registry virtualization and hardware specification override engine.
    Supports native 64-bit and 32-bit registry views to prevent WOW64 redirection flaws.
    """

    @classmethod
    def apply_all(cls, profile: HardwareProfile, snapshot_mgr: Optional[RegistrySnapshotManager] = None) -> List[OperationResult]:
        """
        Applies all hardware specification overrides across CPU, GPU, NPU, DirectX, WinSAT, and OEM caches.
        """
        backup_records: List[Dict[str, Any]] = []

        results = [
            cls.apply_cpu_override(profile, backup_records),
            cls.apply_pci_device_override(profile, backup_records),
            cls.apply_display_class_override(profile, backup_records),
            cls.apply_winsat_cache_override(profile, backup_records),
            cls.apply_directx_cache_override(profile, backup_records),
            cls.apply_oem_cache_override(profile, backup_records)
        ]

        if snapshot_mgr and backup_records:
            try:
                snapshot_mgr.save_snapshot(backup_records)
            except Exception as ex:
                Logger.warning(f"Failed to record registry backup snapshot: {ex}")

        return results

    @classmethod
    def verify_current(cls, profile: HardwareProfile) -> List[OperationResult]:
        """
        Verifies and inspects current registry values across hardware subsystems.
        """
        results: List[OperationResult] = []

        # 1. CPU Inspection
        try:
            path = r"HARDWARE\DESCRIPTION\System\CentralProcessor"
            with cls._open_hklm_key(path, writable=False) as cpu_base:
                if cpu_base:
                    sub_keys = cls._get_sub_key_names(cpu_base)
                    if sub_keys:
                        with winreg.OpenKey(cpu_base, sub_keys[0]) as core_key:
                            current_cpu, _ = winreg.QueryValueEx(core_key, "ProcessorNameString")
                            results.append(OperationResult(
                                "CPU ProcessorName",
                                True,
                                len(sub_keys),
                                f"Detected ({len(sub_keys)} cores): {current_cpu}"
                            ))
                    else:
                        results.append(OperationResult("CPU ProcessorName", False, 0, "No logical cores detected."))
                else:
                    results.append(OperationResult("CPU ProcessorName", False, 0, "CentralProcessor key not accessible."))
        except Exception as ex:
            results.append(OperationResult("CPU ProcessorName", False, 0, str(ex)))

        # 2. WinSAT Inspection
        try:
            path = r"SOFTWARE\Microsoft\Windows NT\CurrentVersion\WinSAT"
            with cls._open_hklm_key(path, writable=False, view="64") as winsat_key:
                if winsat_key:
                    try:
                        adapter, _ = winreg.QueryValueEx(winsat_key, "PrimaryAdapterString")
                    except FileNotFoundError:
                        adapter = "Not configured"
                    results.append(OperationResult("WinSAT PrimaryAdapter", True, 1, adapter))
                else:
                    results.append(OperationResult("WinSAT PrimaryAdapter", False, 0, "WinSAT key not present."))
        except Exception as ex:
            results.append(OperationResult("WinSAT PrimaryAdapter", False, 0, str(ex)))

        # 3. DirectX Cache Inspection
        try:
            dx_found = 0
            path = r"SOFTWARE\Microsoft\DirectX"
            with cls._open_hklm_key(path, writable=False, view="64") as dx_base:
                if dx_base:
                    sub_keys = cls._get_sub_key_names(dx_base)
                    for sub in sub_keys:
                        try:
                            with winreg.OpenKey(dx_base, sub) as dx_sub:
                                desc, _ = winreg.QueryValueEx(dx_sub, "Description")
                                results.append(OperationResult(
                                    f"DirectX Adapter Cache [{sub}]",
                                    True,
                                    1,
                                    str(desc)
                                ))
                                dx_found += 1
                        except FileNotFoundError:
                            pass
            if dx_found == 0:
                results.append(OperationResult("DirectX Adapter Cache", True, 0, "No DirectX cache entries detected."))
        except Exception as ex:
            results.append(OperationResult("DirectX Adapter Cache", False, 0, str(ex)))

        return results

    # =========================================================================
    # Subsystem Implementations
    # =========================================================================

    @classmethod
    def apply_cpu_override(cls, profile: HardwareProfile, backup: Optional[List[Dict[str, Any]]] = None) -> OperationResult:
        subsystem = "CPU CentralProcessor"
        core_count = 0
        base_path = r"HARDWARE\DESCRIPTION\System\CentralProcessor"

        try:
            with cls._open_hklm_key(base_path, writable=False) as cpu_base:
                if not cpu_base:
                    return OperationResult(subsystem, False, 0, "CentralProcessor registry branch not found.")

                sub_keys = cls._get_sub_key_names(cpu_base)
                for core_sub in sub_keys:
                    core_path = f"{base_path}\\{core_sub}"
                    with cls._open_hklm_key(core_path, writable=True) as core_key:
                        if core_key:
                            if backup is not None:
                                cls._record_backup(core_key, core_path, "ProcessorNameString", "default", backup)
                            winreg.SetValueEx(core_key, "ProcessorNameString", 0, winreg.REG_SZ, profile.cpu_name)
                            core_count += 1

            return OperationResult(
                subsystem,
                True,
                core_count,
                f"Overwrote {core_count} logical processor core(s) -> {profile.cpu_name}"
            )
        except Exception as ex:
            return OperationResult(subsystem, False, core_count, f"Exception: {ex}")

    @classmethod
    def apply_pci_device_override(cls, profile: HardwareProfile, backup: Optional[List[Dict[str, Any]]] = None) -> OperationResult:
        subsystem = "PCI Bus (GPU/NPU)"
        gpu_count = 0
        npu_count = 0
        pci_base_path = r"SYSTEM\CurrentControlSet\Enum\PCI"

        try:
            with cls._open_hklm_key(pci_base_path, writable=False) as pci_base:
                if not pci_base:
                    return OperationResult(subsystem, False, 0, "PCI registry branch not accessible.")

                vendor_keys = cls._get_sub_key_names(pci_base)
                for vendor in vendor_keys:
                    vendor_path = f"{pci_base_path}\\{vendor}"
                    with cls._open_hklm_key(vendor_path, writable=False) as v_key:
                        if not v_key:
                            continue
                        instances = cls._get_sub_key_names(v_key)
                        for inst in instances:
                            inst_path = f"{vendor_path}\\{inst}"
                            with cls._open_hklm_key(inst_path, writable=True) as inst_key:
                                if not inst_key:
                                    continue

                                class_guid = cls._safe_query_value(inst_key, "ClassGUID") or ""

                                # Display Adapter (GPU)
                                if class_guid.lower() == profile.GPU_CLASS_GUID.lower():
                                    if cls._has_value(inst_key, "DeviceDesc"):
                                        if backup is not None:
                                            cls._record_backup(inst_key, inst_path, "DeviceDesc", "default", backup)
                                        winreg.SetValueEx(inst_key, "DeviceDesc", 0, winreg.REG_SZ, profile.gpu_name)

                                    if cls._has_value(inst_key, "FriendlyName"):
                                        if backup is not None:
                                            cls._record_backup(inst_key, inst_path, "FriendlyName", "default", backup)
                                        winreg.SetValueEx(inst_key, "FriendlyName", 0, winreg.REG_SZ, profile.gpu_name)

                                    gpu_count += 1

                                # Compute Accelerator (NPU)
                                elif class_guid.lower() == profile.NPU_CLASS_GUID.lower():
                                    if cls._has_value(inst_key, "DeviceDesc"):
                                        if backup is not None:
                                            cls._record_backup(inst_key, inst_path, "DeviceDesc", "default", backup)
                                        winreg.SetValueEx(inst_key, "DeviceDesc", 0, winreg.REG_SZ, profile.npu_name)

                                    if cls._has_value(inst_key, "FriendlyName"):
                                        if backup is not None:
                                            cls._record_backup(inst_key, inst_path, "FriendlyName", "default", backup)
                                        winreg.SetValueEx(inst_key, "FriendlyName", 0, winreg.REG_SZ, profile.npu_name)

                                    npu_count += 1

            return OperationResult(
                subsystem,
                True,
                gpu_count + npu_count,
                f"Updated {gpu_count} GPU instance(s) -> {profile.gpu_name}, {npu_count} NPU instance(s) -> {profile.npu_name}"
            )
        except Exception as ex:
            return OperationResult(subsystem, False, gpu_count + npu_count, f"Exception: {ex}")

    @classmethod
    def apply_display_class_override(cls, profile: HardwareProfile, backup: Optional[List[Dict[str, Any]]] = None) -> OperationResult:
        subsystem = "Display Class Adapter"
        count = 0
        class_base_path = rf"SYSTEM\CurrentControlSet\Control\Class\{profile.GPU_CLASS_GUID}"

        try:
            with cls._open_hklm_key(class_base_path, writable=False) as class_base:
                if class_base:
                    sub_keys = cls._get_sub_key_names(class_base)
                    for sub in sub_keys:
                        # Display adapter subkeys are 4 digits: 0000, 0001, etc.
                        if re.match(r"^\d{4}$", sub):
                            sub_path = f"{class_base_path}\\{sub}"
                            with cls._open_hklm_key(sub_path, writable=True) as sub_key:
                                if sub_key:
                                    if cls._has_value(sub_key, "DriverDesc"):
                                        if backup is not None:
                                            cls._record_backup(sub_key, sub_path, "DriverDesc", "default", backup)
                                        winreg.SetValueEx(sub_key, "DriverDesc", 0, winreg.REG_SZ, profile.gpu_name)

                                    if cls._has_value(sub_key, "HardwareInformation.AdapterString"):
                                        if backup is not None:
                                            cls._record_backup(sub_key, sub_path, "HardwareInformation.AdapterString", "default", backup)
                                        winreg.SetValueEx(sub_key, "HardwareInformation.AdapterString", 0, winreg.REG_SZ, profile.gpu_name)

                                    if cls._has_value(sub_key, "HardwareInformation.ChipType"):
                                        if backup is not None:
                                            cls._record_backup(sub_key, sub_path, "HardwareInformation.ChipType", "default", backup)
                                        winreg.SetValueEx(sub_key, "HardwareInformation.ChipType", 0, winreg.REG_SZ, profile.gpu_family)

                                    count += 1

            return OperationResult(
                subsystem,
                True,
                count,
                f"Overwrote {count} Display Class entry/entries -> {profile.gpu_name}"
            )
        except Exception as ex:
            return OperationResult(subsystem, False, count, f"Exception: {ex}")

    @classmethod
    def apply_winsat_cache_override(cls, profile: HardwareProfile, backup: Optional[List[Dict[str, Any]]] = None) -> OperationResult:
        subsystem = "WinSAT System Rating Cache"
        winsat_path = r"SOFTWARE\Microsoft\Windows NT\CurrentVersion\WinSAT"

        try:
            with cls._open_hklm_key(winsat_path, writable=True, view="64") as winsat_key:
                if winsat_key:
                    if backup is not None:
                        cls._record_backup(winsat_key, winsat_path, "PrimaryAdapterString", "64", backup)
                    winreg.SetValueEx(winsat_key, "PrimaryAdapterString", 0, winreg.REG_SZ, profile.gpu_name)
                    return OperationResult(subsystem, True, 1, f"PrimaryAdapterString updated -> {profile.gpu_name}")

            return OperationResult(subsystem, False, 0, "WinSAT registry key not present.")
        except Exception as ex:
            return OperationResult(subsystem, False, 0, f"Exception: {ex}")

    @classmethod
    def apply_directx_cache_override(cls, profile: HardwareProfile, backup: Optional[List[Dict[str, Any]]] = None) -> OperationResult:
        subsystem = "DirectX Adapter Cache"
        count = 0
        base_path = r"SOFTWARE\Microsoft\DirectX"

        try:
            for view_flag in ["64", "32"]:
                with cls._open_hklm_key(base_path, writable=False, view=view_flag) as dx_base:
                    if not dx_base:
                        continue

                    sub_names = cls._get_sub_key_names(dx_base)
                    for sub in sub_names:
                        dx_sub_path = f"{base_path}\\{sub}"
                        with cls._open_hklm_key(dx_sub_path, writable=True, view=view_flag) as dx_key:
                            if not dx_key:
                                continue

                            desc = cls._safe_query_value(dx_key, "Description")
                            if desc and isinstance(desc, str):
                                # Skip basic software rasterizer descriptions
                                if "Basic Render" not in desc and "Basic Display" not in desc:
                                    if backup is not None:
                                        cls._record_backup(dx_key, dx_sub_path, "Description", view_flag, backup)
                                    winreg.SetValueEx(dx_key, "Description", 0, winreg.REG_SZ, profile.gpu_name)
                                    count += 1

            return OperationResult(
                subsystem,
                True,
                count,
                f"Overwrote {count} DirectX cache adapter descriptor(s) -> {profile.gpu_name}"
            )
        except Exception as ex:
            return OperationResult(subsystem, False, count, f"Exception: {ex}")

    @classmethod
    def apply_oem_cache_override(cls, profile: HardwareProfile, backup: Optional[List[Dict[str, Any]]] = None) -> OperationResult:
        subsystem = "OEM Analysis Interface (ASUS/Generic)"
        asus_path = r"SOFTWARE\ASUS\ASUS System Control Interface\AsusSystemAnalysis"

        try:
            with cls._open_hklm_key(asus_path, writable=True, view="64") as asus_key:
                if asus_key:
                    if backup is not None:
                        cls._record_backup(asus_key, asus_path, "graphic_card_model", "64", backup)
                        cls._record_backup(asus_key, asus_path, "cpu_info", "64", backup)
                    winreg.SetValueEx(asus_key, "graphic_card_model", 0, winreg.REG_SZ, profile.gpu_name)
                    winreg.SetValueEx(asus_key, "cpu_info", 0, winreg.REG_SZ, profile.cpu_name)
                    return OperationResult(subsystem, True, 2, "Updated ASUS OEM telemetry cache.")

            return OperationResult(subsystem, True, 0, "No active OEM telemetry hook detected (Bypassed safely).")
        except Exception as ex:
            return OperationResult(subsystem, False, 0, f"Exception: {ex}")

    # =========================================================================
    # Helpers
    # =========================================================================

    @staticmethod
    def _open_hklm_key(sub_key_path: str, writable: bool = False, view: str = "default"):
        access = winreg.KEY_READ
        if writable:
            access |= winreg.KEY_SET_VALUE

        if view == "64":
            access |= winreg.KEY_WOW64_64KEY
        elif view == "32":
            access |= winreg.KEY_WOW64_32KEY

        try:
            return winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, sub_key_path, 0, access)
        except FileNotFoundError:
            return None
        except PermissionError as pe:
            raise pe
        except Exception:
            return None

    @staticmethod
    def _get_sub_key_names(key) -> List[str]:
        names = []
        try:
            index = 0
            while True:
                name = winreg.EnumKey(key, index)
                names.append(name)
                index += 1
        except OSError:
            pass
        return names

    @staticmethod
    def _safe_query_value(key, value_name: str) -> Optional[Any]:
        try:
            val, _ = winreg.QueryValueEx(key, value_name)
            return val
        except FileNotFoundError:
            return None
        except Exception:
            return None

    @staticmethod
    def _has_value(key, value_name: str) -> bool:
        try:
            winreg.QueryValueEx(key, value_name)
            return True
        except FileNotFoundError:
            return False

    @staticmethod
    def _record_backup(key, path: str, value_name: str, view: str, records: List[Dict[str, Any]]) -> None:
        try:
            data, reg_type = winreg.QueryValueEx(key, value_name)
            records.append({
                "hive": "HKLM",
                "path": path,
                "view": view,
                "value_name": value_name,
                "type": reg_type,
                "data": data
            })
        except FileNotFoundError:
            records.append({
                "hive": "HKLM",
                "path": path,
                "view": view,
                "value_name": value_name,
                "type": winreg.REG_SZ,
                "data": None
            })
