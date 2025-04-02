# core/webhooks/router.py
import logging
from typing import Dict, Any
from core.utils.helpers import handle_status_update_case, handle_template_quality_case
from core.webhooks.message_handlers import handle_message_case

logger = logging.getLogger(__name__)


async def route_meta_webhook(body: Dict[str, Any]) -> None:
    """
    Routes incoming Meta webhooks to appropriate handlers based on type.
    """
    from core.webhooks.webhook import (
        normalize_webhook_payload,
    )  # Importación dentro de la función

    try:
        # Normalize and validate webhook payload
        try:
            normalized_body = await normalize_webhook_payload(body)
        except ValueError as e:
            logger.error(f"Invalid webhook structure: {str(e)}")
            return

        # Extract main webhook components
        entry = normalized_body.get("entry", [{}])[0]
        changes = entry.get("changes", [{}])[0]
        field = changes.get("field")
        value = changes.get("value", {})
        waba_id = entry.get("id")

        if not waba_id:
            logger.error("Missing WABA ID in webhook")
            return

        # Route webhook based on field type
        if field == "message_template_quality_update":
            await handle_template_quality_case(body, value)

        elif field == "messages":
            messages = value.get("messages", [])
            if messages:
                await handle_message_case(messages[0], waba_id)

        elif field == "statuses":
            statuses = value.get("statuses", [])
            if statuses:
                await handle_status_update_case(statuses)

        else:
            logger.warning(f"Unhandled webhook field type: {field}")

    except Exception as e:
        logger.error(f"Error routing Meta webhook: {str(e)}", exc_info=True)
