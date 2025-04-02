# core/services/message_service.py
import logging
from typing import Any, Dict

from core.models.enums import MessageRole
from core.models.waba import WABAConfig

logger = logging.getLogger(__name__)


async def initialize_message(
    message: Dict[str, Any],
    sender: str,
    waba_conf: WABAConfig,
    text_content: str,
    service_container,
):
    try:
        # Obtener servicios del contenedor
        db = service_container.db
        message_buffer_manager = service_container.message_buffer_manager
        context = service_container.context  # Obtener el contexto del contenedor
        # Initialize conversation in DB
        conversation_id = db.get_or_create_conversation(waba_conf.waba_id, sender)

        buffer_key = message_buffer_manager.get_or_create_buffer(
            waba_conf, sender, conversation_id
        )

        # Prepare metadata
        metadata = {"strategy": waba_conf.instructions_strategy.value}

        # Prepare message data for storage
        message_data = {
            "type": message.get("type"),
            "message": {"id": message.get("id"), "text": {"body": text_content}},
            "processed": False,
            "sender": sender,
            "waba_id": waba_conf.waba_id,
            "waba_conf": waba_conf,
            "conversation_id": conversation_id,
        }

        # Save to database
        db.save_message(
            conversation_id,
            {**message_data, "original_message": message},
            metadata=metadata,
        )

        # Add message to buffer and context
        await message_buffer_manager.add_message(buffer_key, message_data)
        context.add_message(waba_conf.waba_id, sender, MessageRole.USER, text_content)

    except Exception as e:
        logger.error(f"Error initializing message: {str(e)}")
        raise
