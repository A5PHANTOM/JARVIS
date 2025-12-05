import json
from dotenv import load_dotenv, find_dotenv
load_dotenv(find_dotenv(), override=True)

import os
import requests
from .schemas import Plan
import re

# Optional google-auth imports for service-account / bearer-token flow
try:
    from google.oauth2 import service_account
    from google.auth.transport.requests import Request as GoogleRequest
    _HAS_GOOGLE_AUTH = True
except Exception:
    _HAS_GOOGLE_AUTH = False

# Load Gemini API key from environment
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
# default to the public 1.5 flash model used in main.py
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-flash-latest")

SYSTEM_PROMPT = """
You are an automation planner for a local desktop assistant called Jarvis-AI.

User gives a natural language command like:
- "Open Chrome and go to Gmail"
- "Type hello in the current window"

Your job:
- If it's a system action, output JSON describing what to do.
- If it's just chat (like "hi" or "how are you"), output a chat intent.

You MUST return ONLY valid JSON with these keys:
- intent: one of [open_website, open_app, type_text, chat]
- actions: list of human-readable steps
- arguments: key-value details

Examples:

Input: Open Chrome and go to Gmail
Output:
{
  "intent": "open_website",
  "actions": ["Open Chrome", "Go to https://mail.google.com"],
  "arguments": {"browser": "chrome", "url": "https://mail.google.com"}
}

Input: Type hello world in the current window
Output:
{
  "intent": "type_text",
  "actions": ["Focus current window", "Type 'hello world'"],
  "arguments": {"text": "hello world"}
}

Input: Hello, how are you?
Output:
{
  "intent": "chat",
  "actions": ["reply"],
  "arguments": {"response": "Hey there! I'm Jarvis — ready to help you automate things!"}
}

Return ONLY pure JSON — no explanations or code blocks.
"""

def _dummy_plan() -> Plan:
    """Fallback if API fails."""
    return Plan(
        intent="open_website",
        actions=["Open browser", "Go to https://mail.google.com"],
        arguments={"browser": "chrome", "url": "https://mail.google.com"},
    )


def get_plan(user_text: str) -> Plan:
    """Send user command to Gemini API and parse structured JSON plan."""
    if not GEMINI_API_KEY:
        print("[gpt_client] Missing GEMINI_API_KEY — using dummy plan.")
        return _dummy_plan()

    try:
        # Build endpoint and auth
        gemini_url = (
            f"https://generativelanguage.googleapis.com/v1beta/models/{GEMINI_MODEL}:generateContent"
        )

        payload = {
            "contents": [
                {
                    "parts": [
                        {"text": f"{SYSTEM_PROMPT}\nUser Input: {user_text}"}
                    ]
                }
            ]
        }

        # Choose auth method: service account (bearer) if GOOGLE_APPLICATION_CREDENTIALS present
        google_creds_path = os.getenv("GOOGLE_APPLICATION_CREDENTIALS")
        use_bearer = False
        headers = {"Content-Type": "application/json"}

        if google_creds_path and _HAS_GOOGLE_AUTH:
            try:
                creds = service_account.Credentials.from_service_account_file(
                    google_creds_path,
                    scopes=["https://www.googleapis.com/auth/cloud-platform"],
                )
                creds.refresh(GoogleRequest())
                headers["Authorization"] = f"Bearer {creds.token}"
                use_bearer = True
            except Exception as e:
                print("[gpt_client] Failed to obtain bearer token from service account:", repr(e))

        # If no bearer token, fall back to using API key in query param (if provided)
        request_url = gemini_url
        if not use_bearer:
            if not GEMINI_API_KEY:
                print("[gpt_client] Missing GEMINI_API_KEY and no service account available — using dummy plan.")
                return _dummy_plan()
            request_url = f"{gemini_url}?key={GEMINI_API_KEY}"

        response = requests.post(
            request_url,
            headers=headers,
            json=payload,
            timeout=20,
        )

        # Helpful debug information when things go wrong
        if response.status_code != 200:
            try:
                body = response.text
            except Exception:
                body = "<unreadable response body>"
            print(f"[gpt_client] Gemini API returned status {response.status_code}: {body}")
            return _dummy_plan()

        data = response.json()

        # Try to extract model response safely
        content = data.get("candidates", [{}])[0].get("content", {}).get("parts", [{}])[0].get("text", "")
        if not content:
            print("[gpt_client] Empty Gemini response, falling back to dummy plan.")
            return _dummy_plan()

        # Sanitize common wrappers (markdown fences, code blocks) and extract JSON object
        # Remove triple-backtick fences if present
        content_clean = re.sub(r"^```(?:json)?\s*", "", content.strip(), flags=re.IGNORECASE)
        content_clean = re.sub(r"\s*```$", "", content_clean)

        # If still not valid JSON, try to extract the first {...} object
        try:
            json_data = json.loads(content_clean)
            return Plan(**json_data)
        except json.JSONDecodeError:
            m = re.search(r"(\{[\s\S]*\})", content_clean)
            if m:
                try:
                    json_data = json.loads(m.group(1))
                    return Plan(**json_data)
                except Exception:
                    print("[gpt_client] Extracted block is not valid JSON — falling back.")
                    return _dummy_plan()
            else:
                print("[gpt_client] Invalid JSON from Gemini, falling back.")
                return _dummy_plan()

    except Exception as e:
        print("[gpt_client] Gemini API error:", repr(e))
        return _dummy_plan()
