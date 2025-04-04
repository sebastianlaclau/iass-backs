# core/utils/helpers.py
import logging
from typing import Any, Dict, List
from core.models.waba import WABAConfig
from core.services.cache import WABAConfigCache
from core.services.supabase import upload_to_supabase_audio_bucket
from core.storage.cache import (
    ConversationContext,
    MessageBufferManager,
)
from core.storage.db import DBStorage

logger = logging.getLogger(__name__)


async def message_to_text_type(
    message: Dict[str, Any], from_: str, waba_conf: WABAConfig
) -> str:
    from core.services.openai import convert_audio_to_text
    from core.services.whatsapp import get_media_whatsapp_url

    """Convert any type of message to text format, maintaining original behavior"""
    # If message has a text field, it's a text message regardless of type field
    if message.get("text"):
        return message["text"].get("body", "")

    # For other types, check the type field
    message_type = message.get("type")

    if message_type in [
        "image",
    ]:
        return """Imagen enviada"""

    if message_type in ["video"]:
        return """Video enviado"""

    elif message_type == "audio":
        try:
            audio_msg_data = message.get("audio", {})
            logger.info(f"Received audio: {audio_msg_data}")

            meta_audio_url = await get_media_whatsapp_url(
                audio_msg_data, waba_conf.permanent_token
            )

            public_supabase_url = await upload_to_supabase_audio_bucket(
                meta_audio_url, waba_conf.permanent_token
            )

            logger.info(f"Public URL of uploaded audio: {public_supabase_url}")

            text_message = await convert_audio_to_text(public_supabase_url, waba_conf)

            logger.info(f"Transcribed text: {text_message}")

            return text_message

        except Exception as error:
            logger.error(f"Error processing audio message: {error}")
            return "Error processing audio message"

    else:
        logger.info(f"Unrecognized message structure: {message}")
        return "Unrecognized message type"


def format_duration(duration):
    if duration is not None and isinstance(duration, (int, float)):
        hours = duration // 60
        minutes = duration % 60
        formatted = (
            f"{hours} horas y {minutes} minutos" if minutes else f"{hours} horas"
        )
        return {"raw": duration, "formatted": formatted}
    return None


def format_searchable_fields(field_value) -> str:
    if isinstance(field_value, list):
        return " ".join(str(item) for item in field_value)
    return str(field_value) if field_value is not None else ""


def create_instances(supabase_client):
    """
    Crear todas las instancias globales necesarias.
    """
    global \
        db, \
        message_buffer_manager, \
        context, \
        courses_cache, \
        instructions_cache, \
        wabas_config_cache

    db = DBStorage(supabase_client)
    message_buffer_manager = MessageBufferManager()
    context = ConversationContext()
    # courses_cache = CoursesCache()
    # instructions_cache = InstructionsCache()
    wabas_config_cache = WABAConfigCache()
