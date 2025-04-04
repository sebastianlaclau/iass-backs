# core/utils/normalization.py
from typing import Any, Dict, List
import logging
import json
from core.models.enums import MessageCategory

logger = logging.getLogger(__name__)


def normalize_webhook_payload(body: Dict[str, Any]) -> Dict[str, Any]:
    """
    Normaliza un payload de webhook a formato estándar.
    """
    # Si ya tiene el formato estándar, devolver tal cual
    if "object" in body and "entry" in body:
        return body

    # Si es un payload de prueba del dashboard de Meta, transformarlo
    if "field" in body and "value" in body:
        phone_number_id = (
            body.get("value", {}).get("metadata", {}).get("phone_number_id", "test_id")
        )
        return {
            "object": "whatsapp_business_account",
            "entry": [
                {
                    "id": phone_number_id,
                    "changes": [{"value": body["value"], "field": body["field"]}],
                }
            ],
        }

    raise ValueError("Invalid webhook payload structure")


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
