# core/utils/helpers.py
import logging
import json
from typing import Any, Dict, List

from core.models.enums import MessageCategory
from core.models.waba import WABAConfig
from core.services.cache import WABAConfigCache
from core.services.supabase import upload_to_supabase_audio_bucket
from core.storage.cache import (
    ConversationContext,
    MessageBufferManager,
)
from core.storage.db import DBStorage

logger = logging.getLogger(__name__)


def log_messages(
    messages: List[Dict[str, str]],
    title: str = None,
    standard_length: int = 1000,
    system_length: int = 1000,
    preview_standard: bool = True,
    preview_system: bool = False,
) -> None:
    if title:
        logger.info(f"{title}:")

    # Debug
    logger.debug(f"Type of messages: {type(messages)}")
    if isinstance(messages, str):
        try:
            messages = eval(messages)  # Temporary fix to parse string back to list
        except:
            logger.error("Could not parse messages string")
            return

    for idx, msg in enumerate(messages):
        content = msg.get("content", "").strip()
        content = ". ".join(
            line.strip() for line in content.splitlines() if line.strip()
        )

        is_system = msg["role"] == "system"
        length = system_length if is_system else standard_length
        use_preview = preview_system if is_system else preview_standard

        if use_preview and len(content) > length:
            content = f"{content[:length]}..."

        logger.info(f"Message {idx + 1} - {msg['role']}: {content}")

        if msg["role"] == "function":
            logger.info(f"  Function: {msg.get('name', 'unknown')}")


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


def normalize_openai_response(response: str) -> str:
    """
    Normaliza cualquier respuesta de OpenAI para asegurar que sea un string válido para WhatsApp.

    Args:
        response: Respuesta cruda que podría ser JSON, dict como string, o texto plano

    Returns:
        String limpio y formateado para enviar por WhatsApp
    """
    try:
        if not response:
            return ""

        # Si es un string que parece un dict
        if isinstance(response, str) and response.strip().startswith("{"):
            try:
                data = json.loads(response)
                # Si es un formato de mensaje de chat
                if isinstance(data, dict):
                    if "content" in data:
                        return data["content"]
                    # Agregar otros casos específicos si son necesarios
                return str(data)
            except json.JSONDecodeError:
                pass

        # Si es un string normal, limpiarlo
        response = str(response).strip()

        # Remover cualquier "Output:" o prefijos similares
        if response.startswith("Output:"):
            response = response[7:].strip()

        return response

    except Exception as e:
        logger.error(f"Error normalizing OpenAI response: {str(e)}")
        return "Lo siento, hubo un error en el procesamiento de la respuesta."


def normalize_classification_response(content: str) -> List[MessageCategory]:
    """
    Normaliza la respuesta de clasificación del modelo.

    Args:
        content: Respuesta cruda del modelo, se espera en formato JSON: ["academic", "payment"]

    Returns:
        Lista de MessageCategory. Retorna [GENERAL] si hay algún error.
    """
    try:
        # Limpieza básica
        content = content.strip()
        if content.startswith("Output:"):
            content = content[7:].strip()

        # Parse JSON
        data = json.loads(content)

        # Normalizar estructura
        if isinstance(data, dict):
            categories = data.get("categories", [])
        elif isinstance(data, list):
            categories = data
        else:
            return [MessageCategory.GENERAL]

        # Validar y convertir categorías
        valid_categories = []
        for cat in categories:
            try:
                valid_categories.append(MessageCategory(cat.strip().lower()))
            except ValueError:
                logger.warning(f"Invalid category ignored: {cat}")

        return valid_categories if valid_categories else [MessageCategory.GENERAL]

    except Exception as e:
        logger.error(f"Error normalizing classification: {str(e)}")
        return [MessageCategory.GENERAL]


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


# ------------------------------------------------------------------------
# MESSAGES DELIVERABILITY AND QUALITY
# ------------------------------------------------------------------------


async def handle_status_update_case(statuses: List[Dict[str, Any]]) -> None:
    """Process message status updates and track template deliverability"""
    if not statuses:
        return

    for status in statuses:
        try:
            message_id = status.get("id")
            status_type = status.get("status")
            recipient_id = status.get("recipient_id")

            message_info = status.get("message", {})
            is_template = message_info.get("type") == "template"
            template_name = (
                message_info.get("template", {}).get("name") if is_template else ""
            )

            template_suffix = f" (Template: {template_name})" if is_template else ""
            base_msg = f"Message {message_id} to {recipient_id}{template_suffix}"

            if status_type != "failed":
                # logger.info(f"{base_msg}: {status_type}")
                continue

            errors = status.get("errors", [])
            if not errors:
                logger.error(f"{base_msg} failed without specific error details")
                continue

            error = errors[0]
            error_code = error.get("code")
            error_message = error.get("message")

            logger.error(
                f"{base_msg} failed. "
                f"Error code: {error_code}, "
                f"Title: {error.get('title')}, "
                f"Message: {error_message}"
            )

            if is_template:
                if error_code in ["131047", "131048"]:
                    logger.error(
                        f"Template '{template_name}' might need revision. Error: {error_message}"
                    )
                elif error_code == "131032":
                    logger.error(f"Template '{template_name}' not found or deleted")
                elif error_code == "132000":
                    logger.error(
                        f"Template '{template_name}' parameter count mismatch. Check template configuration"
                    )

        except Exception as e:
            logger.error(f"Error processing status update: {str(e)}", exc_info=True)


async def handle_template_quality_case(
    raw_body: Dict[str, Any], value: Dict[str, Any]
) -> None:
    """
    Handles the template quality update case of a Meta webhook.
    Processes and logs template quality score changes.
    """
    try:
        # Log template details
        template_name = value.get("message_template_name")
        old_score = value.get("previous_quality_score")
        new_score = value.get("new_quality_score")
        template_id = value.get("message_template_id")
        language = value.get("message_template_language")

        logger.info(
            f"Template quality update - {template_name} (ID: {template_id}): "
            f"{old_score} → {new_score} ({language})"
        )

        if old_score == "GREEN" and new_score in ["YELLOW", "RED"]:
            logger.warning(
                f"Template quality degraded: {template_name} "
                f"needs review (Score: {new_score})"
            )

    # TODO: Implement additional business logic here:
    # - Update template status in database
    # - Send notifications to relevant teams
    # - Trigger template revision workflow
    # - Track metrics for quality trends

    except Exception as e:
        logger.error(f"Error handling template quality case: {str(e)}", exc_info=True)
