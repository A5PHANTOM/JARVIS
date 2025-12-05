from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import platform as py_platform
import os
import requests
from dotenv import load_dotenv, find_dotenv
load_dotenv(find_dotenv(), override=True)
try:
    # optional imports for service-account auth in chat endpoint
    from google.oauth2 import service_account
    from google.auth.transport.requests import Request as GoogleRequest
    _HAS_GOOGLE_AUTH = True
except Exception:
    _HAS_GOOGLE_AUTH = False


from .schemas import CommandRequest, CommandResponse
from .gpt_client import get_plan
from .script_generator import generate_script
from .executor import execute_script
from .safety import is_safe

app = FastAPI(title="Jarvis-AI Backend (Gemini 1.5 Edition)")

# Allow all origins (for hackathon testing)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# 🩺 Health Check
@app.get("/health")
def health():
    return {"status": "ok"}


# 🧠 AUTOMATION ENDPOINT
@app.post("/command", response_model=CommandResponse)
def handle_command(req: CommandRequest):
    target_platform = req.platform
    if not target_platform:
        sys_name = py_platform.system().lower()
        if "windows" in sys_name:
            target_platform = "windows"
        elif "darwin" in sys_name:
            target_platform = "mac"
        else:
            target_platform = "unknown"

    # Get plan from Gemini-based automation planner
    plan = get_plan(req.text)

    # Quick override: if user asks to "start coding" treat as open_app -> Visual Studio Code
    # This helps when Gemini returns a chat reply for casual phrases like "let's start coding"
    try:
        user_low = (req.text or "").strip().lower()
        if plan.intent == "chat" and ("start coding" in user_low or "lets start coding" in user_low or "let's start coding" in user_low):
            # convert to an automation plan to open VS Code
            plan.intent = "open_app"
            plan.actions = ["Open Visual Studio Code"]
            # Provide both a platform app_name and a generic app_id so generators can pick the right command
            plan.arguments = {"app_name": "Visual Studio Code", "app_id": "vscode"}
    except Exception:
        # keep original plan on any unexpected error
        pass
    safe, reason = is_safe(plan)

    # 🚫 Safety check
    if not safe:
        return CommandResponse(
            message="Blocked potentially dangerous command.",
            platform=target_platform,
            actions=plan.actions,
            blocked=True,
            reason=reason,
        )

    # 💬 If it's a normal chat, just reply instead of automating
    if plan.intent == "chat":
        chat_text = plan.arguments.get("response", "I'm here to help you automate things!")
        return CommandResponse(
            message=chat_text,
            platform=target_platform,
            actions=["reply"],
            blocked=False,
            reason=None,
        )

    # 🧰 Otherwise → generate and execute automation script
    gen_info = generate_script(plan, target_platform)
    script_path = gen_info.get("script_path")

    if script_path:
        execute_script(script_path, target_platform)
        msg = "Command executed successfully."
    else:
        msg = "No script generated (unsupported platform)."

    return CommandResponse(
        message=msg,
        platform=target_platform,
        script_path=script_path,
        actions=plan.actions,
        blocked=False,
        reason=None,
    )


# 💬 NORMAL CHAT ENDPOINT (Gemini 1.5 or fallback)
@app.post("/chat")
def chat_endpoint(req: CommandRequest):
    """
    Basic chatbot endpoint using Gemini 1.5 Flash (with fallback logic).
    """
    user_text = req.text
    GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
    GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-flash-latest")

    # prefer service-account bearer token if available
    gemini_url = f"https://generativelanguage.googleapis.com/v1beta/models/{GEMINI_MODEL}:generateContent"

    google_creds_path = os.getenv("GOOGLE_APPLICATION_CREDENTIALS")
    headers = {"Content-Type": "application/json"}
    request_url = gemini_url
    used_bearer = False

    if google_creds_path and _HAS_GOOGLE_AUTH:
        try:
            creds = service_account.Credentials.from_service_account_file(
                google_creds_path,
                scopes=["https://www.googleapis.com/auth/cloud-platform"],
            )
            creds.refresh(GoogleRequest())
            headers["Authorization"] = f"Bearer {creds.token}"
            used_bearer = True
        except Exception as e:
            print("[chat] failed to obtain bearer token:", repr(e))

    if not used_bearer:
        if not GEMINI_API_KEY:
            # fall back to offline responses below
            GEMINI_API_KEY = ""
        else:
            request_url = f"{gemini_url}?key={GEMINI_API_KEY}"

    if used_bearer or GEMINI_API_KEY:
        try:
            response = requests.post(
                request_url,
                headers=headers,
                json={"contents": [{"parts": [{"text": user_text}]}]},
                timeout=20,
            )
            if response.status_code != 200:
                print(f"[chat] Gemini API returned status {response.status_code}: {response.text}")
            data = response.json()
            msg = (
                data.get("candidates", [{}])[0]
                .get("content", {})
                .get("parts", [{}])[0]
                .get("text", "I'm here to help you automate things!")
            )
            return {"message": msg.strip(), "from": "Jarvis"}
        except Exception as e:
            print("[chat] Gemini API error:", repr(e))
            # fallback below

    # 🧩 Fallback: simple offline responses
    fallback_responses = {
        "hi": "Hello! I'm Jarvis — ready to help you automate your system.",
        "hello": "Hey there! What can I do for you today?",
        "how are you": "I'm doing great — ready to open apps for you!",
        "who are you": "I'm Jarvis, your personal AI assistant.",
        "what can you do": "I can open websites, launch apps, and type messages for you.",
    }

    for key, val in fallback_responses.items():
        if key in user_text.lower():
            return {"message": val, "from": "Jarvis"}

    return {"message": "I'm Jarvis — say 'Open Chrome' or just chat with me!", "from": "Jarvis"}
