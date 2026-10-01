import os
import sys
import subprocess
import tempfile
from .logger import Logger

class TaskSchedulerService:
    """
    Enterprise Windows Task Scheduler management service.
    Configures highest-privilege logon triggers with AC/battery power independence.
    """

    @classmethod
    def install_task(cls, task_name: str, silent: bool = False) -> bool:
        """
        Registers a startup Task Scheduler task executing with highest privileges upon user logon.
        """
        try:
            if getattr(sys, "frozen", False):
                current_exe = sys.executable
                exe_dir = os.path.dirname(os.path.abspath(current_exe))
                exec_command = current_exe
                exec_args = "--silent"
            else:
                # Running via python script
                current_exe = sys.executable
                main_script = os.path.abspath(sys.argv[0])
                exe_dir = os.path.dirname(main_script)
                exec_command = current_exe
                exec_args = f'"{main_script}" --silent'

            task_xml = f"""<?xml version="1.0" encoding="UTF-16"?>
<Task version="1.2" xmlns="http://schemas.microsoft.com/windows/2004/02/mit/task">
  <RegistrationInfo>
    <Description>SpoofHW Hardware Emulation Background Daemon</Description>
  </RegistrationInfo>
  <Triggers>
    <LogonTrigger>
      <Enabled>true</Enabled>
      <Delay>PT3S</Delay>
    </LogonTrigger>
  </Triggers>
  <Principals>
    <Principal id="Author">
      <LogonType>InteractiveToken</LogonType>
      <RunLevel>HighestAvailable</RunLevel>
    </Principal>
  </Principals>
  <Settings>
    <MultipleInstancesPolicy>IgnoreNew</MultipleInstancesPolicy>
    <DisallowStartIfOnBatteries>false</DisallowStartIfOnBatteries>
    <StopIfGoingOnBatteries>false</StopIfGoingOnBatteries>
    <AllowHardTerminate>true</AllowHardTerminate>
    <StartWhenAvailable>true</StartWhenAvailable>
    <RunOnlyIfNetworkAvailable>false</RunOnlyIfNetworkAvailable>
    <IdleSettings>
      <StopOnIdleEnd>false</StopOnIdleEnd>
      <RestartOnIdle>false</RestartOnIdle>
    </IdleSettings>
    <AllowStartOnDemand>true</AllowStartOnDemand>
    <Enabled>true</Enabled>
    <Hidden>false</Hidden>
    <RunOnlyIfIdle>false</RunOnlyIfIdle>
    <WakeToRun>false</WakeToRun>
    <ExecutionTimeLimit>PT1H</ExecutionTimeLimit>
    <Priority>4</Priority>
  </Settings>
  <Actions Context="Author">
    <Exec>
      <Command>{cls._escape_xml(exec_command)}</Command>
      <Arguments>{cls._escape_xml(exec_args)}</Arguments>
      <WorkingDirectory>{cls._escape_xml(exe_dir)}</WorkingDirectory>
    </Exec>
  </Actions>
</Task>"""

            temp_xml_fd, temp_xml_path = tempfile.mkstemp(prefix="SpoofHW_", suffix=".xml")
            try:
                with os.fdopen(temp_xml_fd, "w", encoding="utf-16") as f:
                    f.write(task_xml)

                # Purge prior task registration if present
                subprocess.run(
                    ["schtasks.exe", "/delete", "/tn", task_name, "/f"],
                    capture_output=True,
                    timeout=5
                )

                # Register task via XML
                create_res = subprocess.run(
                    ["schtasks.exe", "/create", "/tn", task_name, "/xml", temp_xml_path, "/f"],
                    capture_output=True,
                    text=True,
                    timeout=10
                )

                if create_res.returncode == 0:
                    if not silent:
                        Logger.success(f"Task Scheduler task '{task_name}' successfully registered.")
                        Logger.info("Configured to launch silently at logon on both AC and Battery power.")
                    return True
                else:
                    # Fallback to standard commandline create
                    tr_arg = f'"{exec_command}" {exec_args}'
                    fallback_res = subprocess.run(
                        ["schtasks.exe", "/create", "/tn", task_name, "/tr", tr_arg, "/sc", "onlogon", "/rl", "HIGHEST", "/f"],
                        capture_output=True,
                        text=True,
                        timeout=10
                    )
                    if fallback_res.returncode == 0:
                        if not silent:
                            Logger.success(f"Task '{task_name}' registered via standard fallback.")
                        return True

                if not silent:
                    Logger.error(f"Failed to register Task Scheduler task: {create_res.stderr.strip()}")
                return False

            finally:
                if os.path.exists(temp_xml_path):
                    try:
                        os.remove(temp_xml_path)
                    except OSError:
                        pass

        except Exception as ex:
            if not silent:
                Logger.error(f"Task installation error: {ex}")
            return False

    @classmethod
    def uninstall_task(cls, task_name: str, silent: bool = False) -> bool:
        """
        Unregisters and removes the startup Task Scheduler entry.
        """
        try:
            res = subprocess.run(
                ["schtasks.exe", "/delete", "/tn", task_name, "/f"],
                capture_output=True,
                text=True,
                timeout=8
            )
            if res.returncode == 0:
                if not silent:
                    Logger.success(f"Task '{task_name}' uninstalled successfully.")
                return True
            else:
                if not silent:
                    Logger.warning(f"Task '{task_name}' was not found or was previously removed.")
                return False
        except Exception as ex:
            if not silent:
                Logger.error(f"Task uninstallation error: {ex}")
            return False

    @staticmethod
    def _escape_xml(value: str) -> str:
        if not value:
            return ""
        return (
            value.replace("&", "&amp;")
            .replace("<", "&lt;")
            .replace(">", "&gt;")
            .replace('"', "&quot;")
            .replace("'", "&apos;")
        )
