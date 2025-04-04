# core/routers/meta_webhooks/messages.py
import logging
from fastapi import APIRouter, Request, Response, BackgroundTasks
from core.routers.webhook_processor import process_meta_webhook

logger = logging.getLogger(__name__)

router = APIRouter()


@router.post("/webhook")
async def handle_meta_webhook(request: Request, background_tasks: BackgroundTasks):
    """
    Receives and validates incoming WhatsApp webhook messages.
    Delegates actual processing to background task.
    """
    try:
        body = await request.json()
        if not body.get("object"):
            return Response(content="No object found in request", status_code=200)

        background_tasks.add_task(process_meta_webhook, body)

        return Response(status_code=200)

    except Exception as e:
        logger.error(f"Error in webhook handler: {str(e)}")
        return Response(content="Error processing webhook", status_code=500)
