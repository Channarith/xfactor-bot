#!/usr/bin/env python3
"""
Install XFactor Bot as a macOS launchd service.

This script creates a launchd plist that will:
- Start the bot service automatically on login
- Keep the service running (restart if it crashes)
- Log output to ~/Library/Logs/XFactorBot/

Usage:
    python scripts/install_service.py [install|uninstall|status|start|stop]
"""

import argparse
import os
import subprocess
import sys
from pathlib import Path


# Service configuration
SERVICE_NAME = "com.xfactor.botservice"
PLIST_PATH = Path.home() / "Library" / "LaunchAgents" / f"{SERVICE_NAME}.plist"
LOG_DIR = Path.home() / "Library" / "Logs" / "XFactorBot"
CONFIG_DIR = Path.home() / ".xfactor"

# Detect Python and project paths
PROJECT_ROOT = Path(__file__).parent.parent.absolute()
PYTHON_PATH = sys.executable


def get_plist_content() -> str:
    """Generate the launchd plist content."""
    return f"""<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>{SERVICE_NAME}</string>
    
    <key>ProgramArguments</key>
    <array>
        <string>{PYTHON_PATH}</string>
        <string>-m</string>
        <string>src.service.bot_service</string>
        <string>--port</string>
        <string>8765</string>
        <string>--config-dir</string>
        <string>{CONFIG_DIR}</string>
    </array>
    
    <key>WorkingDirectory</key>
    <string>{PROJECT_ROOT}</string>
    
    <key>EnvironmentVariables</key>
    <dict>
        <key>PYTHONPATH</key>
        <string>{PROJECT_ROOT}</string>
    </dict>
    
    <key>RunAtLoad</key>
    <true/>
    
    <key>KeepAlive</key>
    <dict>
        <key>SuccessfulExit</key>
        <false/>
    </dict>
    
    <key>ThrottleInterval</key>
    <integer>30</integer>
    
    <key>StandardOutPath</key>
    <string>{LOG_DIR}/service.log</string>
    
    <key>StandardErrorPath</key>
    <string>{LOG_DIR}/service_error.log</string>
    
    <key>ProcessType</key>
    <string>Background</string>
</dict>
</plist>
"""


def install_service():
    """Install the launchd service."""
    print(f"Installing XFactor Bot service...")
    print(f"  Service name: {SERVICE_NAME}")
    print(f"  Plist path: {PLIST_PATH}")
    print(f"  Project root: {PROJECT_ROOT}")
    print(f"  Python: {PYTHON_PATH}")
    print()
    
    # Create log directory
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    print(f"✓ Created log directory: {LOG_DIR}")
    
    # Create config directory
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    print(f"✓ Created config directory: {CONFIG_DIR}")
    
    # Create plist directory if needed
    PLIST_PATH.parent.mkdir(parents=True, exist_ok=True)
    
    # Unload existing service if present
    if PLIST_PATH.exists():
        print("  Unloading existing service...")
        subprocess.run(
            ["launchctl", "unload", str(PLIST_PATH)],
            capture_output=True,
        )
    
    # Write plist file
    plist_content = get_plist_content()
    PLIST_PATH.write_text(plist_content)
    print(f"✓ Created plist: {PLIST_PATH}")
    
    # Load the service
    result = subprocess.run(
        ["launchctl", "load", str(PLIST_PATH)],
        capture_output=True,
        text=True,
    )
    
    if result.returncode == 0:
        print(f"✓ Service loaded successfully")
        print()
        print("=" * 50)
        print("XFactor Bot Service Installed!")
        print("=" * 50)
        print()
        print("The service will:")
        print("  • Start automatically when you log in")
        print("  • Restart automatically if it crashes")
        print("  • Listen on http://127.0.0.1:8765")
        print()
        print("Logs are stored in:")
        print(f"  • {LOG_DIR}/service.log")
        print(f"  • {LOG_DIR}/service_error.log")
        print()
        print("Commands:")
        print("  • Check status: python scripts/install_service.py status")
        print("  • Stop service: python scripts/install_service.py stop")
        print("  • Start service: python scripts/install_service.py start")
        print("  • Uninstall: python scripts/install_service.py uninstall")
    else:
        print(f"✗ Failed to load service: {result.stderr}")
        return 1
    
    return 0


def uninstall_service():
    """Uninstall the launchd service."""
    print(f"Uninstalling XFactor Bot service...")
    
    if not PLIST_PATH.exists():
        print("Service is not installed.")
        return 0
    
    # Unload the service
    result = subprocess.run(
        ["launchctl", "unload", str(PLIST_PATH)],
        capture_output=True,
        text=True,
    )
    
    # Remove plist file
    PLIST_PATH.unlink()
    print(f"✓ Removed plist: {PLIST_PATH}")
    
    print("✓ Service uninstalled")
    print()
    print("Note: Log files and config files have been preserved.")
    print(f"  • Logs: {LOG_DIR}")
    print(f"  • Config: {CONFIG_DIR}")
    
    return 0


def get_service_status():
    """Get the current status of the service."""
    print(f"XFactor Bot Service Status")
    print("=" * 40)
    
    if not PLIST_PATH.exists():
        print("Status: NOT INSTALLED")
        return 1
    
    # Check if service is running
    result = subprocess.run(
        ["launchctl", "list", SERVICE_NAME],
        capture_output=True,
        text=True,
    )
    
    if result.returncode == 0:
        # Parse the output
        lines = result.stdout.strip().split("\n")
        if len(lines) >= 1:
            parts = lines[0].split("\t")
            if len(parts) >= 3:
                pid = parts[0]
                exit_code = parts[1]
                label = parts[2]
                
                if pid == "-":
                    print("Status: STOPPED")
                    if exit_code != "-":
                        print(f"Last exit code: {exit_code}")
                else:
                    print(f"Status: RUNNING (PID: {pid})")
        
        print(f"Plist: {PLIST_PATH}")
        print(f"Log: {LOG_DIR}/service.log")
        print()
        
        # Check if API is responding
        try:
            import urllib.request
            req = urllib.request.urlopen("http://127.0.0.1:8765/health", timeout=2)
            data = req.read().decode()
            print("API Status: HEALTHY")
            print(f"API Response: {data}")
        except Exception as e:
            print(f"API Status: NOT RESPONDING ({e})")
    else:
        print("Status: REGISTERED (not running)")
    
    return 0


def start_service():
    """Start the service."""
    print("Starting XFactor Bot service...")
    
    if not PLIST_PATH.exists():
        print("Service is not installed. Run 'install' first.")
        return 1
    
    result = subprocess.run(
        ["launchctl", "start", SERVICE_NAME],
        capture_output=True,
        text=True,
    )
    
    if result.returncode == 0:
        print("✓ Service start command sent")
        print("  Check status with: python scripts/install_service.py status")
    else:
        print(f"✗ Failed to start service: {result.stderr}")
        return 1
    
    return 0


def stop_service():
    """Stop the service."""
    print("Stopping XFactor Bot service...")
    
    if not PLIST_PATH.exists():
        print("Service is not installed.")
        return 1
    
    result = subprocess.run(
        ["launchctl", "stop", SERVICE_NAME],
        capture_output=True,
        text=True,
    )
    
    if result.returncode == 0:
        print("✓ Service stopped")
    else:
        print(f"✗ Failed to stop service: {result.stderr}")
        return 1
    
    return 0


def main():
    parser = argparse.ArgumentParser(
        description="Install XFactor Bot as a macOS launchd service"
    )
    parser.add_argument(
        "command",
        choices=["install", "uninstall", "status", "start", "stop"],
        default="status",
        nargs="?",
        help="Command to run (default: status)",
    )
    
    args = parser.parse_args()
    
    # Check platform
    if sys.platform != "darwin":
        print("This script is for macOS only.")
        print("For Linux, use systemd. For Windows, use Task Scheduler.")
        return 1
    
    commands = {
        "install": install_service,
        "uninstall": uninstall_service,
        "status": get_service_status,
        "start": start_service,
        "stop": stop_service,
    }
    
    return commands[args.command]()


if __name__ == "__main__":
    sys.exit(main())

