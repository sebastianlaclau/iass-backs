# clients/iass-back-emprendemy/helpers.py
from datetime import datetime
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
import logging
import smtplib
import httpx
import json
import html
from typing import Any, Dict, List

from core.models.waba import WABAConfig
from core.services.whatsapp import send_contact_message_to_wa
from .constants import EMPRENDEMY_CONTACT_INFO

from core.models.config import ClientConfig
from core.config import config_manager

# ------------------------------------------------------------------------
# TOOLS RELATED FUNCTIONS
# ------------------------------------------------------------------------

logger = logging.getLogger(__name__)


async def send_cta_to_signup(
    waba_conf: WABAConfig,
    to: str,
    curso: str,
    url_compra: str,
    catchy_phrase: str = "curso copado!",
    descuento: str = "55%",
) -> Dict[str, Any]:
    """
    Send CTA message via WhatsApp API for course purchase

    Args:
        waba_conf: WhatsApp Business API configuration
        to: Recipient's phone number
        curso: Course name (used as header)
        url_compra: Purchase URL
        catchy_phrase: Marketing phrase (default: "curso copado!")
        descuento: Discount percentage (default: "55%")

    Returns:
        Dict with status and response data

    Raises:
        ValueError: If required parameters are missing or invalid
        Exception: If API call fails
    """
    # Validate all required inputs
    if not all([to, curso, url_compra]):
        raise ValueError(
            "Missing required parameters: to, curso, and url_compra are required"
        )

    # Validate WhatsApp credentials
    if not waba_conf.phone_number_id or not waba_conf.permanent_token:
        raise ValueError(
            "Invalid WhatsApp configuration: missing phone_number_id or token"
        )

    try:
        # Construct the interactive object
        interactive_object = {
            "type": "cta_url",
            "action": {
                "name": "cta_url",
                "parameters": {"display_text": "Inscribirme!", "url": url_compra},
            },
            "header": {"type": "text", "text": curso[:60]},
            "body": {"text": catchy_phrase},
            "footer": {"text": f"Compra con el dto de {descuento}"},
        }

        # Prepare request payload
        request_payload = {
            "messaging_product": "whatsapp",
            "recipient_type": "individual",
            "to": to,
            "type": "interactive",
            "interactive": interactive_object,
        }

        # logger.info(f"Sending CTA message to {to}")
        logger.debug(f"Request payload: {json.dumps(request_payload, indent=2)}")

        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"https://graph.facebook.com/v20.0/{waba_conf.phone_number_id}/messages",
                params={"access_token": waba_conf.permanent_token},
                json=request_payload,
                headers={"Content-Type": "application/json"},
                timeout=30.0,
            )

            response_data = response.json()
            logger.debug(f"WhatsApp API response: {response_data}")

            response.raise_for_status()

            return {
                "status": response.status_code,
                "statusText": response.reason_phrase,
                "data": response_data,
            }

    except httpx.TimeoutException:
        logger.error("Timeout while sending CTA message")
        raise Exception("Timeout while sending CTA message")
    except httpx.RequestError as e:
        logger.error(f"Network error while sending CTA: {str(e)}")
        raise Exception(f"Network error while sending CTA: {str(e)}")
    except Exception as e:
        logger.error(f"Error sending CTA: {str(e)}", exc_info=True)
        raise


async def send_emprendemy_contact(to: str, waba_conf: WABAConfig) -> str:
    """
    Send Emprendemy contact info via WhatsApp API

    Args:
        to: Recipient's phone number
        waba_conf: WhatsApp Business API configuration

    Returns:
        str: Status message

    Raises:
        Exception: If sending fails
    """
    try:
        logger.info("Sending Emprendemy contact message")

        response = await send_contact_message_to_wa(
            EMPRENDEMY_CONTACT_INFO,
            to,
            waba_conf.phone_number_id,
            waba_conf.permanent_token,
        )

        # Check if response contains messaging_product and messages
        if (
            isinstance(response, dict)
            and response.get("messaging_product") == "whatsapp"
        ):
            messages = response.get("messages", [])
            if messages and isinstance(messages, list) and len(messages) > 0:
                # Successfully sent
                logger.info("Contact message sent successfully")
                return "Contact message sent successfully"

        # If we get here, log the actual response for debugging
        logger.warning(f"Unexpected response format from WhatsApp API: {response}")

        # Even if response format is unexpected, if we got here without an exception,
        # the message probably went through
        return "Contact message processed"

    except Exception as e:
        logger.error("Failed to send Contact Message:", exc_info=True)

        # Get error details if available
        if hasattr(e, "response"):
            try:
                error_details = e.response.json()
                logger.error(f"Error details: {error_details}")
            except Exception:
                logger.error("Error details: Could not parse response")
        else:
            logger.error("Error details: No response data")

        # Re-raise with more specific error message
        raise Exception(f"Error sending contact message: {str(e)}")


def generate_email_content(
    conversation_history: List[Dict[str, str]],
    sender_phone: str,
    notification_type: str,
    info: Dict[str, Any],
    waba_conf: WABAConfig,
) -> str:
    """Generate HTML content for email."""

    # Get conversation stats
    total_messages = len([m for m in conversation_history if m.get("role") != "system"])
    user_messages = len([m for m in conversation_history if m.get("role") == "user"])
    bot_messages = len(
        [m for m in conversation_history if m.get("role") == "assistant"]
    )

    # Format timestamp
    timestamp = datetime.now().strftime("%d/%m/%Y %H:%M:%S")

    # Create HTML content with additional environment info
    html_content = f"""
    <html>
    <head>
        <style>
            body {{
                font-family: Arial, sans-serif;
                max-width: 800px;
                margin: 20px auto;
                padding: 20px;
                background-color: #f5f5f5;
            }}
            .header {{
                background-color: #ffffff;
                padding: 20px;
                border-radius: 10px;
                margin-bottom: 20px;
                box-shadow: 0 2px 5px rgba(0,0,0,0.1);
            }}
            .env-info {{
                background-color: #e8f5e9;
                padding: 10px;
                border-radius: 5px;
                margin: 10px 0;
                font-size: 0.9em;
            }}
            .stats {{
                display: grid;
                grid-template-columns: repeat(3, 1fr);
                gap: 10px;
                margin: 15px 0;
            }}
            .stat-box {{
                background-color: #f8f9fa;
                padding: 10px;
                border-radius: 5px;
                text-align: center;
            }}
            .conversation {{
                background-color: #ffffff;
                padding: 20px;
                border-radius: 10px;
                box-shadow: 0 2px 5px rgba(0,0,0,0.1);
            }}
            .message {{
                margin: 10px 0;
                padding: 10px;
                border-radius: 5px;
            }}
            .user-message {{
                background-color: #e3f2fd;
                margin-left: 20px;
            }}
            .bot-message {{
                background-color: #f5f5f5;
                margin-right: 20px;
            }}
            .timestamp {{
                color: #666;
                font-size: 0.8em;
            }}
        </style>
    </head>
    <body>
        <div class="header">
            <h2>{info["prefix"]}</h2>
            <div class="env-info">
                <p>🏢 Account: {waba_conf.name}</p>
            </div>
            <p>👤 Usuario: +{sender_phone} (ID: {sender_phone[-4:]})</p>
            <p>⏰ Fecha y hora: {timestamp}</p>
            
            <div class="stats">
                <div class="stat-box">
                    📊 Total Mensajes<br><strong>{total_messages}</strong>
                </div>
                <div class="stat-box">
                    👤 Mensajes Usuario<br><strong>{user_messages}</strong>
                </div>
                <div class="stat-box">
                    🤖 Respuestas Bot<br><strong>{bot_messages}</strong>
                </div>
            </div>
        </div>
        
        <div class="conversation">
            <h3>💬 Historial de Conversación</h3>
    """

    # Add messages in reverse order
    # for msg in reversed(conversation_history):
    for msg in conversation_history:
        role = msg.get("role", "")
        content = msg.get("content", "")

        if role == "system":
            continue

        message_class = "user-message" if role == "user" else "bot-message"
        icon = "👤" if role == "user" else "🤖"

        html_content += f"""
            <div class="message {message_class}">
                <strong>{icon}</strong> {html.escape(content)}
            </div>
        """

    html_content += """
        </div>
    </body>
    </html>
    """

    return html_content


# def send_email(subject: str, html_content: str, settings: Settings) -> None:
def send_email(subject: str, html_content: str, client_config: ClientConfig) -> None:
    """Send email using SMTP with settings from project config."""
    # Get project-wide email settings
    project_config = config_manager.get_project_config()

    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"] = client_config.SENDER_EMAIL

    # Can use client-specific settings from client_config.settings if needed
    admin_email = client_config.settings.get("ADMIN_EMAIL", project_config.ADMIN_EMAIL)

    recipients = [
        admin_email,
        # "esteban.cosin@gmail.com",
    ]
    msg["To"] = ", ".join(recipients)

    html_part = MIMEText(html_content, "html")
    msg.attach(html_part)

    try:
        with smtplib.SMTP(
            project_config.SMTP_SERVER, project_config.SMTP_PORT
        ) as server:
            server.starttls()
            server.login(project_config.SENDER_EMAIL, project_config.EMAIL_PASSWORD)
            server.send_message(msg)
            logger.info(f"Email sent successfully to {admin_email}")

    except Exception as e:
        logger.error(f"Failed to send email: {str(e)}")
        raise
