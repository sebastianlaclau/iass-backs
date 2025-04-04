# core/routers/webhook_processor.py
import logging
from typing import Dict, Any
from core.config import config_manager
from core.handlers.message_handler import handle_message_case
from core.handlers.status_handler import handle_status_update_case
from core.handlers.template_handler import handle_template_quality_case
from core.services.container import ServiceContainer
from core.utils.blocked_numbers import is_number_blocked
from core.utils.normalization import normalize_webhook_payload
from core.utils.supabase_client import supabase
from core.services.waba import get_waba_config
import json

logger = logging.getLogger(__name__)

# Mantener un diccionario global de containers por cliente
_client_containers = {}


async def process_meta_webhook(body: Dict[str, Any]) -> None:
    """
    Processes incoming Meta webhooks and routes to appropriate handlers.
    """
    # Logging original payload para depuración
    logger.info(f"Webhook raw payload: {json.dumps(body)}")

    try:
        # 1. Normalizar el payload primero
        try:
            normalized_body = normalize_webhook_payload(body)
        except ValueError as e:
            logger.error(f"Invalid webhook structure: {str(e)}")
            return

        # 2. Extraer componentes principales
        entry = normalized_body.get("entry", [{}])[0]
        changes = entry.get("changes", [{}])[0]
        value = changes.get("value", {})
        field = changes.get("field")

        # Log detallado del tipo de webhook
        logger.info(f"Webhook field type: {field}")

        # Si hay statuses, log especial
        if field == "messages" and "statuses" in value:
            statuses = value.get("statuses", [])
            if statuses:
                status_info = statuses[0]
                logger.info(
                    f"Status update received: {status_info.get('status')} for message {status_info.get('id')}"
                )

        # 3. Extraer identificadores
        waba_id = entry.get("id")
        phone_id = value.get("metadata", {}).get("phone_number_id")

        if not waba_id:
            logger.error("Missing WABA ID in webhook")
            return

        # 4. Identificar cliente (antes de obtener waba_config)
        client_id = None
        client_config = None
        for cid, config in config_manager._clients.items():
            if (
                config.waba_config.waba_id == waba_id
                or config.waba_config.phone_number_id == phone_id
            ):
                client_id = cid
                client_config = config
                break

        if not client_id:
            logger.warning(
                f"No client found for WABA ID: {waba_id} or Phone ID: {phone_id}"
            )
            return

        # 5. Obtener o crear service_container para este cliente
        if client_id not in _client_containers:
            _client_containers[client_id] = ServiceContainer(supabase, client_id)

        service_container = _client_containers[client_id]

        # 6. Obtener configuración WABA del service_container
        try:
            waba_config = await get_waba_config(service_container, client_id, waba_id)

        except Exception as e:
            logger.error(f"Invalid WABA configuration for {waba_id}: {str(e)}")
            return

        logger.info(f"Processing webhook for client: {client_id}")

        # 7. Enrutar según tipo de evento
        if field == "message_template_quality_update":
            await handle_template_quality_case(
                normalized_body, value, client_config, service_container
            )
        elif field == "messages":
            messages = value.get("messages", [])
            if messages:
                message = messages[0]

                # Extraer y validar sender
                sender = message.get("from")
                if not sender:
                    logger.error("Missing sender phone number in message")
                    return

                # Verificar si el número está bloqueado
                if is_number_blocked(sender):
                    logger.info(f"Blocked message from {sender}")
                    return

                await handle_message_case(
                    message,
                    waba_id,
                    sender,
                    waba_config,
                    client_config,
                    service_container,
                )
        elif field == "statuses":
            statuses = value.get("statuses", [])
            if statuses:
                await handle_status_update_case(
                    statuses, client_config, service_container
                )
        else:
            logger.warning(f"Unhandled webhook field type: {field}")

    except Exception as e:
        logger.error(f"Error processing Meta webhook: {str(e)}", exc_info=True)
