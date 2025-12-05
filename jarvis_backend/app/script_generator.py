from datetime import datetime
import os
from .config import GENERATED_DIR
from .schemas import Plan

def generate_script(plan: Plan, target_platform: str) -> dict:
    if target_platform == "windows":
        script_content = generate_ahk_v2(plan)
        ext = ".ahk"
    elif target_platform == "mac":
        script_content = generate_applescript(plan)
        ext = ".scpt"
    else:
        return {"script_path": None}

    filename = f"cmd_{datetime.now().strftime('%Y%m%d_%H%M%S')}{ext}"
    script_path = os.path.join(GENERATED_DIR, filename)

    with open(script_path, "w", encoding="utf-8") as f:
        f.write(script_content)

    return {"script_path": script_path}


# ✅ AHK v2 syntax version
def generate_ahk_v2(plan: Plan) -> str:
    intent = plan.intent
    args = plan.arguments
    # Prefer hotkey-based actions if present. Emit AHK v1-style commands (Run, Sleep, SendRaw)
    hotkeys = args.get("hotkeys") if args else None
    if hotkeys and isinstance(hotkeys, list):
        script_lines = ["Sleep, 120"]
        for step in hotkeys:
            t = step.get("type")
            if t == "run" and step.get("cmd"):
                # run arbitrary command
                script_lines.append(f'Run, {step.get("cmd")}')
            elif t == "activate_app" and step.get("app"):
                # try to run the app by name
                script_lines.append(f'Run, {step.get("app")}')
            elif t == "open_url" and step.get("url"):
                # open URL; relying on system association
                script_lines.append(f'Run, {step.get("url")}')
        return "\n".join(script_lines)

    if intent == "open_website":
        url = args.get("url", "https://google.com")
        # try to open Chrome explicitly; otherwise open the URL
        return f"""
Sleep, 120
Run, chrome.exe "{url}"
If ErrorLevel
    Run, {url}
"""
    elif intent == "open_app":
        app = args.get("app_name", "notepad.exe")
        return f"""
Sleep, 120
Run, {app}
"""
    elif intent == "type_text":
        text = args.get("text", "Hello from Jarvis")
        return f"""
Sleep, 120
SendRaw, {text}
"""
    else:
        return """
MsgBox, Jarvis: Unknown intent on Windows.
"""


def generate_applescript(plan: Plan) -> str:
    intent = plan.intent
    args = plan.arguments

    # Prefer hotkey-based actions when available
    hotkeys = args.get("hotkeys") if args else None
    if hotkeys and isinstance(hotkeys, list):
        lines = []
        for step in hotkeys:
            t = step.get("type")
            if t == "activate_app":
                app = step.get("app", "Finder")
                lines.append(f'tell application "{app}"\n    activate\nend tell')
            elif t == "open_url":
                url = step.get("url")
                lines.append(f'tell application "Google Chrome"\n    activate\n    open location "{url}"\nend tell')
        if lines:
            return "\n\n".join(lines)

    if intent == "open_website":
        url = args.get("url", "https://google.com")
        return f'''
tell application "Google Chrome"
    activate
    open location "{url}"
end tell
'''
    elif intent == "open_app":
        app = args.get("app_name", "Notes")
        return f'''
tell application "{app}"
    activate
end tell
'''
    elif intent == "type_text":
        text = args.get("text", "Hello from Jarvis")
        return f'''
tell application "System Events"
    keystroke "{text}"
end tell
'''
    else:
        return '''
display dialog "Jarvis: Unknown intent on macOS."
'''
