from dataclasses import dataclass
from typing import Optional, Dict, Any
from .enums import ResponseBehavior


@dataclass
class FunctionResponse:
    success: bool
    data: Optional[Dict[str, Any]] = None
    content: Optional[str] = None
    conversation_entry: Optional[Dict[str, str]] = None
    response_behavior: ResponseBehavior = ResponseBehavior.NO_FOLLOW_UP
    template_response: Optional[str] = None
    error: Optional[str] = None
    follow_up_context: Optional[Dict[str, Any]] = None
    follow_up_instructions: Optional[Dict[str, Any]] = None
