import json
import os
from dataclasses import dataclass, asdict
from typing import Optional

@dataclass
class HardwareProfile:
    """
    Encapsulates the hardware emulation configuration profile.
    """
    cpu_name: str = "Intel(R) Core(TM) Ultra X9 388H"
    gpu_name: str = "Intel(R) Arc(TM) B390 (16 GB)"
    gpu_family: str = "Intel(R) Arc(TM) B390 Family"
    npu_name: str = "Intel NPU AI 8GB"
    task_name: str = "SpoofHW_AutoRun"

    # Well-known Windows Device Setup Class GUIDs
    GPU_CLASS_GUID: str = "{4d36e968-e325-11ce-bfc1-08002be10318}"
    NPU_CLASS_GUID: str = "{f01a9d53-3ff6-48d2-9f97-c8a7004be10c}"

    @classmethod
    def load_from_file(cls, filepath: str) -> "HardwareProfile":
        """Loads hardware specification profile from a JSON configuration file."""
        if not os.path.exists(filepath):
            raise FileNotFoundError(f"Configuration file not found: {filepath}")

        with open(filepath, "r", encoding="utf-8") as f:
            data = json.load(f)

        profile = cls()
        if "cpu_name" in data:
            profile.cpu_name = data["cpu_name"]
        if "gpu_name" in data:
            profile.gpu_name = data["gpu_name"]
            profile.gpu_family = data.get("gpu_family", f"{data['gpu_name']} Family")
        if "gpu_family" in data:
            profile.gpu_family = data["gpu_family"]
        if "npu_name" in data:
            profile.npu_name = data["npu_name"]
        if "task_name" in data:
            profile.task_name = data["task_name"]
        return profile

    def save_to_file(self, filepath: str) -> None:
        """Saves current configuration profile to a JSON file."""
        os.makedirs(os.path.dirname(os.path.abspath(filepath)), exist_ok=True)
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(asdict(self), f, indent=4)
