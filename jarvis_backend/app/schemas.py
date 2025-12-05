from pydantic import BaseModel
from typing import List, Optional

class CommandRequest(BaseModel):
    text: str
    platform: Optional[str] = None
    # When false, backend should generate a plan and return it but NOT execute scripts.
    execute: Optional[bool] = True

class CommandResponse(BaseModel):
    message: str
    platform: str
    script_path: Optional[str] = None
    actions: List[str] = []
    blocked: bool = False
    reason: Optional[str] = None

class Plan(BaseModel):
    intent: str
    actions: List[str]
    arguments: dict
