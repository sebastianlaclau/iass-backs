# core/routers/meta_webhooks/verification.py
import logging
from fastapi import APIRouter, Request, Response
from core.config import config_manager

logger = logging.getLogger(__name__)

router = APIRouter()


# TODO FUNCIONA PERO LA HICIMOS PARA CUANDO IBAMOS A MANEJAR DISTINTOS WEBHOOKS, AHORA NO TIENE SENTIDO POR EJEMPLO AGARRAR EL CLIEN ID, YA NO ESTA LLEGANDO.
@router.get("/webhook")
async def handle_webhook_verification(request: Request):
    # Extract client ID from path
    path_parts = request.url.path.split("/")
    # Path should be like /api/v1/client_id/webhook_verification
    client_id = path_parts[3] if len(path_parts) >= 4 else None
    params = request.query_params
    hub_mode = params.get("hub.mode")
    hub_challenge = params.get("hub.challenge")
    hub_verify_token = params.get("hub.verify_token")

    # Get client-specific configuration
    client_config = config_manager.get_client_config(client_id) if client_id else None

    logger.info(
        f"Received webhook GET request for client {client_id} with parameters: hub_mode={hub_mode}, hub_verify_token={hub_verify_token}"
    )

    # Get verification token from client config or fall back to project config
    verify_token = None
    if client_config:
        verify_token = client_config.waba_config.verification_token

    # If no client-specific token, use project default
    if not verify_token:
        project_config = config_manager.get_project_config()
        verify_token = project_config.FB_VERIFY_TOKEN

    if hub_mode == "subscribe" and hub_verify_token == verify_token:
        logger.info(
            f"Webhook verified for client {client_id}. Responding with hub_challenge: {hub_challenge}"
        )
        return Response(content=hub_challenge, media_type="text/plain", status_code=200)
    else:
        logger.warning(f"Webhook verification failed for client {client_id}")
        return Response(status_code=403)
