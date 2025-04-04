# core/handlers/status_handler.py
import logging
from typing import Any, Dict, List

logger = logging.getLogger(__name__)


# async def handle_status_update_case(
#     statuses: List[Dict[str, Any]], client_config, service_container
# ) -> None:
#     """Process message status updates and track template deliverability"""
#     if not statuses:
#         return

#     for status in statuses:
#         try:
#             message_id = status.get("id")
#             status_type = status.get("status")
#             recipient_id = status.get("recipient_id")

#             message_info = status.get("message", {})
#             is_template = message_info.get("type") == "template"
#             template_name = (
#                 message_info.get("template", {}).get("name") if is_template else ""
#             )

#             template_suffix = f" (Template: {template_name})" if is_template else ""
#             base_msg = f"Message {message_id} to {recipient_id}{template_suffix}"

#             if status_type != "failed":
#                 # logger.info(f"{base_msg}: {status_type}")
#                 continue

#             errors = status.get("errors", [])
#             if not errors:
#                 logger.error(f"{base_msg} failed without specific error details")
#                 continue

#             error = errors[0]
#             error_code = error.get("code")
#             error_message = error.get("message")

#             logger.error(
#                 f"{base_msg} failed. "
#                 f"Error code: {error_code}, "
#                 f"Title: {error.get('title')}, "
#                 f"Message: {error_message}"
#             )

#             if is_template:
#                 if error_code in ["131047", "131048"]:
#                     logger.error(
#                         f"Template '{template_name}' might need revision. Error: {error_message}"
#                     )
#                 elif error_code == "131032":
#                     logger.error(f"Template '{template_name}' not found or deleted")
#                 elif error_code == "132000":
#                     logger.error(
#                         f"Template '{template_name}' parameter count mismatch. Check template configuration"
#                     )

#         except Exception as e:
#             logger.error(f"Error processing status update: {str(e)}", exc_info=True)


# core/handlers/status_handler.py


async def handle_status_update_case(
    statuses: List[Dict[str, Any]], client_config, service_container
) -> None:
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

            # Log all status types
            logger.info(f"{base_msg}: {status_type}")

            # Special logging for delivered messages
            if status_type == "delivered":
                logger.info(f"✓ Message successfully delivered to {recipient_id}")
                continue

            if status_type != "failed":
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
