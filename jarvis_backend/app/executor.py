import subprocess, os

def execute_script(path: str, target_platform: str):
    if not path or not os.path.exists(path):
        print("Script not found:", path)
        return

    if target_platform == "windows":
        # Try to execute the AHK script. Prefer using AutoHotkey executable if present,
        # otherwise fall back to 'start' which will use file associations on Windows.
        try:
            ahk_path = r"D:\AutoHotkey\v2\AutoHotkey64.exe"
            if os.path.exists(ahk_path):
                subprocess.Popen([ahk_path, path])
            else:
                # Use cmd start to launch the script by association
                subprocess.Popen(["cmd", "/c", "start", "", path])
        except Exception as e:
            print("Failed to execute Windows script:", repr(e))
    elif target_platform == "mac":
        subprocess.Popen(["osascript", path])
    else:
        print("Unknown platform, not executing script.")
