# core/services/message_service.py
import logging
from typing import Any, Dict

from core.models.enums import MessageRole
from core.services.openai_handler import OpenAIHandler

logger = logging.getLogger(__name__)


async def initialize_message(
    message: Dict[str, Any],
    sender: str,
    waba_config,
    text_content: str,
    service_container,
):
    """Inicializa un mensaje en la base de datos y buffers"""
    try:
        # Extraer servicios necesarios del contenedor
        db = service_container.db
        message_buffer_manager = service_container.message_buffer_manager
        context = service_container.context

        # Inicializar conversación en DB
        conversation_id = db.get_or_create_conversation(waba_config.waba_id, sender)

        # Crear o obtener buffer para esta conversación
        buffer_key = message_buffer_manager.get_or_create_buffer(
            waba_config, sender, conversation_id
        )

        # Preparar metadatos para almacenamiento
        metadata = {"strategy": waba_config.instructions_strategy.value}

        # Datos del mensaje
        message_data = {
            "type": message.get("type"),
            "message": {"id": message.get("id"), "text": {"body": text_content}},
            "processed": False,
            "sender": sender,
            "waba_id": waba_config.waba_id,
            "conversation_id": conversation_id,
        }

        # Guardar en base de datos
        db.save_message(
            conversation_id,
            {**message_data, "original_message": message},
            metadata=metadata,
        )

        # Añadir a buffer y contexto
        await message_buffer_manager.add_message(buffer_key, message_data)
        context.add_message(waba_config.waba_id, sender, MessageRole.USER, text_content)

        return conversation_id, buffer_key

    except Exception as e:
        logger.error(f"Error initializing message: {str(e)}")
        raise


async def process_buffered_messages(
    waba_config, sender, message_buffer_manager, service_container=None
):
    """Process buffered messages for a specific sender"""
    try:
        buffer_key = message_buffer_manager._get_key(waba_config, sender)

        if buffer_key not in message_buffer_manager.buffer:
            logger.debug(f"No buffer found for sender {sender}")
            return

        async with message_buffer_manager.with_lock(buffer_key):
            buffer_data = message_buffer_manager.buffer[buffer_key]

            # Get metadata
            metadata = buffer_data["metadata"]
            conversation_id = metadata["conversation_id"]

            # Extract data from metadata
            waba_conf = metadata["waba_conf"]
            sender = metadata["sender"]
            conversation_id = metadata["conversation_id"]
            # client_id = service_container.client_id

            # Get unprocessed messages
            unprocessed_messages = [
                msg
                for msg in buffer_data["messages"]
                if not msg.get("processed", False)
            ]

            if not unprocessed_messages:
                logger.debug(f"No unprocessed messages for buffer: {buffer_key}")
                return

            # Get message IDs for processing
            current_processing_ids = [
                msg["message"]["id"] for msg in unprocessed_messages
            ]
            openai_handler = service_container.create_openai_handler(
                waba_conf, sender, conversation_id, current_processing_ids
            )

            await openai_handler.handle_openai_process()

            # Mark messages as processed
            message_buffer_manager.mark_messages_processed(
                buffer_key, current_processing_ids
            )

    except Exception as e:
        logger.error(f"Error processing buffer for {sender}: {str(e)}", exc_info=True)
