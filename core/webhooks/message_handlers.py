# core/webhooks/message_handlers.py
import logging
from typing import Any, Dict, Tuple, Union

from core.models.waba import WABAConfig
from core.services.message_service import initialize_message
from core.services.waba import get_waba_config
from core.storage.cache import process_buffered_messages
from core.utils.blocked_numbers import is_number_blocked
from core.utils.helpers import message_to_text_type

logger = logging.getLogger(__name__)


async def handle_message_case(
    message: Dict[str, Any], waba_id: str, service_container
) -> None:
    try:
        # Validate incoming message
        validation_result = await validate_incoming_message(
            message, waba_id, service_container
        )

        if not validation_result[0]:
            logger.info("Message validation failed, skipping processing")
            return

        sender, waba_conf, text_content = validation_result

        # Initialize message
        await initialize_message(
            message, sender, waba_conf, text_content, service_container
        )

        # Process buffered messages
        await process_buffered_messages(
            waba_conf, sender, service_container.message_buffer_manager
        )

        logger.info(f"Completed message processing for {sender}")

    except Exception as e:
        logger.error(
            f"Error handling message case for waba_id {waba_id}: {str(e)}",
            exc_info=True,
        )
        raise


async def validate_incoming_message(
    message: Dict[str, Any], waba_id: str
) -> Tuple[bool, str, Union[WABAConfig, None], str]:
    try:
        # Extract and validate sender
        sender = message.get("from")
        if not sender:
            logger.error("Missing sender phone number in message case")
            return False, None, None, None

        # Check if number is blocked
        if is_number_blocked(sender):
            logger.info(f"Blocked message from {sender}")
            return False, "", None, ""

        # Get and validate WABA configuration
        try:
            waba_conf = get_waba_config(waba_id)
        except Exception as e:
            logger.error(f"Invalid WABA configuration for {waba_id}: {str(e)}")
            return False, "", None, ""

        # Convert and validate message content
        try:
            text_content = await message_to_text_type(message, sender, waba_conf)
            if not text_content:
                logger.warning(f"Could not convert message to text from {sender}")
                return False, None, None, None
        except Exception as e:
            logger.error(f"Error converting message to text: {str(e)}")
            return False, "", None, ""

        return sender, waba_conf, text_content

    except Exception as e:
        logger.error(f"Error in message validation: {str(e)}", exc_info=True)
        return False, "", None, ""
