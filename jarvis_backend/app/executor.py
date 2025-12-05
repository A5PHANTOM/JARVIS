import subprocess, os


def execute_script(path: str, target_platform: str):
    if not path or not os.path.exists(path):
        print("Script not found:", path)
        return

    if target_platform == "windows":
        # try common AutoHotkey locations, otherwise fall back to start
        possible = [
            r"C:\Program Files\AutoHotkey\AutoHotkey.exe",
            r"C:\Program Files\AutoHotkey\AutoHotkey64.exe",
            r"D:\AutoHotkey\v2\AutoHotkey64.exe",
        ]
        ahk = None
        for p in possible:
            if os.path.exists(p):
                ahk = p
                break

        try:
            if ahk:
                subprocess.Popen([ahk, path])
            else:
                # fallback: try os.startfile (will use file association) then PowerShell start as a last resort
                try:
                    os.startfile(path)
                except Exception:
                    try:
                        subprocess.Popen(["powershell", "-Command", "Start-Process", f'\"{path}\"'])
                    except Exception as e:
                        print("Failed to open script via start/powershell:", e)
        except Exception as e:
            print("Failed to execute AHK script:", e)
    elif target_platform == "mac":
        try:
            subprocess.Popen(["osascript", path])
        except Exception as e:
            print("Failed to run osascript:", e)
    else:
        print("Unknown platform, not executing script.")
