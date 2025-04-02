from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional, Dict
from typing import List, Any
from .enums import MessageRole, InformationType, ConversationStatus


@dataclass
class Message:
    id: str
    conversation_id: str
    role: MessageRole
    content: str
    whatsapp_message_id: Optional[str] = None
    metadata: Optional[Dict] = None
    created_at: datetime = field(default_factory=datetime.now)
    function_called: Optional[str] = None
    function_args: Optional[Dict] = None
    info_type: InformationType = InformationType.UNSPECIFIED
    processed: bool = False


@dataclass
class ConversationMetadata:
    user_name: Optional[str] = None
    user_email: Optional[str] = None


@dataclass
class Conversation:
    id: str
    waba_id: str
    phone_number: str
    last_activity_at: datetime
    status: ConversationStatus = ConversationStatus.ACTIVE
    messages: List[Message] = field(default_factory=list)
    metadata: ConversationMetadata = field(default_factory=ConversationMetadata)
    custom_data: Dict[str, Any] = field(default_factory=dict)

    def update_metadata(self, key: str, value: Any) -> None:
        self.custom_data[key] = value

    def set_user_info(
        self, name: Optional[str] = None, email: Optional[str] = None
    ) -> None:
        if name:
            self.metadata.user_name = name
        if email:
            self.metadata.user_email = email
