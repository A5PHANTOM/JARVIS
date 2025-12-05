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

    if intent == "open_website":
        url = args.get("url", "https://google.com")
        return f'''
Run "chrome.exe {url}"
'''
    elif intent == "open_app":
        # Prefer a platform-agnostic app identifier if provided
        app = args.get("app_id") or args.get("app_name") or "notepad.exe"
        app_low = (str(app) or "").lower()

        # Special-case Visual Studio Code to use the 'code' CLI (common on Windows)
        if "code" in app_low or "vscode" in app_low or "visual studio" in app_low:
            # Try opening via the 'code' CLI; if not available, users can configure their PATH
            return f'''
Run "code"
'''

        # Default: run the provided app string directly
        return f'''
Run "{app}"
'''
    elif intent == "type_text":
        text = args.get("text", "Hello from Jarvis")
        # In AHK v2, Send is a function, not a command
        return f'''
Send("{text}")
'''
    else:
        return '''
MsgBox "Jarvis: Unknown intent on Windows."
'''


def generate_applescript(plan: Plan) -> str:
    intent = plan.intent
    args = plan.arguments

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
