# core/handlers/message_handler.py

import logging
from typing import Any, Dict

from core.models.waba import WABAConfig
from core.services.message import initialize_message, process_buffered_messages
from core.utils.helpers import message_to_text_type

logger = logging.getLogger(__name__)


async def handle_message_case(
    message: Dict[str, Any],
    waba_id: str,
    sender: str,
    waba_config: WABAConfig,
    client_config,
    service_container,
) -> None:
    try:
        # Convertir mensaje a texto
        try:
            text_content = await message_to_text_type(message, sender, waba_config)
            if not text_content:
                logger.warning(f"Could not convert message to text from {sender}")
                return
        except Exception as e:
            logger.error(f"Error converting message to text: {str(e)}")
            return

        # Initialize message
        await initialize_message(
            message, sender, waba_config, text_content, service_container
        )
        # Process buffered messages
        await process_buffered_messages(
            waba_config,
            sender,
            service_container.message_buffer_manager,
            service_container,
        )

        logger.info(f"Completed message processing for {sender}")

    except Exception as e:
        logger.error(
            f"Error handling message case for sender {sender}: {str(e)}",
            exc_info=True,
        )
        raise
