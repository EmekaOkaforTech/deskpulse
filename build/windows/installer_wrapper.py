"""
DeskPulse Windows Installer Wrapper.

One-click installer for end users:
- Extracts files to %LOCALAPPDATA%\DeskPulse
- Creates desktop and startup shortcuts
- Prompts for Raspberry Pi IP
- Launches DeskPulse automatically
"""

import os
import sys
import shutil
import zipfile
import tempfile
import ctypes
from pathlib import Path


def show_message(title, message):
    """Show message box."""
    ctypes.windll.user32.MessageBoxW(0, message, title, 0x0 | 0x2000 | 0x10000)


def get_pi_ip():
    """Prompt user for Raspberry Pi IP address."""
    # Create input dialog using VBScript
    vbs_script = os.path.join(tempfile.gettempdir(), 'get_pi_ip.vbs')
    with open(vbs_script, 'w') as f:
        f.write('Set objShell = CreateObject("WScript.Shell")\n')
        f.write('strIP = InputBox("Enter your Raspberry Pi IP address:" & vbCrLf & vbCrLf & "Example: 192.168.10.133", "DeskPulse Setup", "192.168.10.133")\n')
        f.write('If strIP <> "" Then\n')
        f.write('  WScript.Echo strIP\n')
        f.write('Else\n')
        f.write('  WScript.Quit 1\n')
        f.write('End If\n')

    # Run VBScript and capture output
    import subprocess
    try:
        result = subprocess.run(
            ['cscript', '//nologo', vbs_script],
            capture_output=True,
            text=True,
            timeout=60
        )
        os.remove(vbs_script)

        if result.returncode == 0:
            return result.stdout.strip()
        else:
            return None
    except Exception:
        return None


def main():
    """Main installer logic."""
    errors_log = []  # Track errors to show at the end

    # Show welcome message
    show_message(
        "DeskPulse Setup",
        "Welcome to DeskPulse!\n\n"
        "This will install DeskPulse to your computer.\n\n"
        "Click OK to continue."
    )

    # Get Pi IP
    pi_ip = get_pi_ip()
    if not pi_ip:
        show_message("Setup Cancelled", "Installation cancelled by user.")
        sys.exit(1)

    # Validate IP format
    parts = pi_ip.split('.')
    if len(parts) != 4 or not all(p.isdigit() and 0 <= int(p) <= 255 for p in parts):
        show_message(
            "Invalid IP",
            f"Invalid IP address: {pi_ip}\n\n"
            "Please use format: xxx.xxx.xxx.xxx"
        )
        sys.exit(1)

    # Installation directory
    install_dir = os.path.join(os.environ['LOCALAPPDATA'], 'DeskPulse')

    # Extract embedded data (PyInstaller will bundle payload.zip)
    try:
        # Get the directory where the installer is running
        if getattr(sys, 'frozen', False):
            # Running as compiled executable
            bundle_dir = sys._MEIPASS
        else:
            # Running as script
            bundle_dir = os.path.dirname(os.path.abspath(__file__))

        payload_zip = os.path.join(bundle_dir, 'payload.zip')

        # Create installation directory
        if os.path.exists(install_dir):
            shutil.rmtree(install_dir)
        os.makedirs(install_dir)

        # Extract payload
        with zipfile.ZipFile(payload_zip, 'r') as zip_ref:
            zip_ref.extractall(install_dir)

    except Exception as e:
        show_message(
            "Installation Failed",
            f"Failed to extract files.\n\n"
            f"Error: {str(e)}"
        )
        sys.exit(1)

    # Create config file
    try:
        config_content = f'{{"backend_url": "http://{pi_ip}:5000"}}'
        config_path = os.path.join(install_dir, 'config.json')

        # Write without BOM
        with open(config_path, 'w', encoding='utf-8') as f:
            f.write(config_content)

    except Exception as e:
        show_message(
            "Configuration Failed",
            f"Failed to create config file.\n\n"
            f"Error: {str(e)}"
        )
        sys.exit(1)

    # Create shortcuts using PowerShell (more reliable)
    shortcut_created = False
    try:
        import subprocess

        # Desktop shortcut
        desktop_ps = f"""
$WshShell = New-Object -ComObject WScript.Shell
$Desktop = [Environment]::GetFolderPath('Desktop')
if (-not (Test-Path $Desktop)) {{
    New-Item -ItemType Directory -Path $Desktop -Force | Out-Null
}}
$Shortcut = $WshShell.CreateShortcut("$Desktop\\DeskPulse.lnk")
$Shortcut.TargetPath = '{install_dir}\\start_deskpulse.vbs'
$Shortcut.WorkingDirectory = '{install_dir}'
$Shortcut.IconLocation = '{install_dir}\\assets\\windows\\icon_professional.ico'
$Shortcut.Description = 'DeskPulse - Posture Monitoring'
$Shortcut.Save()
Write-Output 'Desktop shortcut created'
"""
        result = subprocess.run(
            ['powershell', '-ExecutionPolicy', 'Bypass', '-Command', desktop_ps],
            capture_output=True,
            text=True,
            timeout=10
        )

        if result.returncode == 0:
            shortcut_created = True
        else:
            errors_log.append(f"Desktop shortcut failed: {result.stderr}")

        # Startup shortcut
        startup_ps = f"""
$WshShell = New-Object -ComObject WScript.Shell
$Startup = [Environment]::GetFolderPath('Startup')
$Shortcut = $WshShell.CreateShortcut("$Startup\\DeskPulse.lnk")
$Shortcut.TargetPath = '{install_dir}\\start_deskpulse.vbs'
$Shortcut.WorkingDirectory = '{install_dir}'
$Shortcut.IconLocation = '{install_dir}\\assets\\windows\\icon_professional.ico'
$Shortcut.Save()
Write-Output 'Startup shortcut created'
"""
        result = subprocess.run(
            ['powershell', '-ExecutionPolicy', 'Bypass', '-Command', startup_ps],
            capture_output=True,
            text=True,
            timeout=10
        )

        if result.returncode != 0:
            errors_log.append(f"Startup shortcut failed: {result.stderr}")

    except Exception as e:
        errors_log.append(f"Shortcut creation error: {str(e)}")

    # Launch DeskPulse
    tray_started = False
    try:
        import subprocess
        import time
        launch_script = os.path.join(install_dir, 'start_deskpulse.vbs')

        # Verify the launch script exists
        if not os.path.exists(launch_script):
            errors_log.append(f"Launch script not found: {launch_script}")
        else:
            # Launch and wait briefly to ensure it starts
            subprocess.Popen(['wscript', launch_script], cwd=install_dir)
            time.sleep(3)  # Give it time to start
            tray_started = True

    except Exception as e:
        errors_log.append(f"Launch failed: {str(e)}")

    # Show completion with status
    if errors_log:
        error_details = "\n".join(errors_log)
        show_message(
            "Installation Complete (with warnings)",
            f"DeskPulse has been installed to:\n{install_dir}\n\n"
            f"Backend: http://{pi_ip}:5000\n\n"
            f"WARNINGS:\n{error_details}\n\n"
            f"You can manually start DeskPulse by running:\n"
            f"{install_dir}\\start_deskpulse.vbs"
        )
    else:
        show_message(
            "Installation Complete",
            f"DeskPulse has been installed!\n\n"
            f"Location: {install_dir}\n"
            f"Backend: http://{pi_ip}:5000\n\n"
            f"DeskPulse is now running in your system tray.\n"
            f"Look for the teal icon in the bottom-right corner.\n\n"
            f"Desktop shortcut created for future use."
        )

    sys.exit(0)


if __name__ == '__main__':
    main()
