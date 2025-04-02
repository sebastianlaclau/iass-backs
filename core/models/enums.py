from enum import Enum


class InformationType(str, Enum):
    BRIEF = "brief"
    FULL = "full"
    SPECIFIC = "specific"
    UNSPECIFIED = "unspecified"


class ConversationStatus(str, Enum):
    ACTIVE = "active"
    ARCHIVED = "archived"
    BLOCKED = "blocked"


class ResponseBehavior(str, Enum):
    NO_FOLLOW_UP = "no_follow_up"
    REQUIRES_FOLLOW_UP = "requires_follow_up"
    CUSTOM = "custom"


class MessageRole(Enum):
    USER = "user"
    ASSISTANT = "assistant"
    SYSTEM = "system"


class MessageCategory(Enum):
    INITIAL = "initial"
    ACADEMIC = "academic"
    PAYMENT = "payment"
    OPERATIONAL = "operational"
    INSTITUTIONAL = "institutional"
    GENERAL = "general"


class ToolChoice(Enum):
    AUTO = "auto"
    NONE = "none"


__all__ = [
    "InformationType",
    "ConversationStatus",
    "ResponseBehavior",
    "MessageRole",
    "MessageCategory",
    "ToolChoice",
]
