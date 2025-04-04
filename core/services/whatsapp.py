# https://developers.facebook.com/docs/whatsapp/cloud-api/guides/send-message-templates/mpm-template-messages

import httpx
from typing import Dict, Any, List
from core.utils.helpers import WABAConfig
from core.services.waba import get_waba_config
import json
import aiohttp
import requests
import logging

logger = logging.getLogger(__name__)


# async def send_text_response_to_wa(answer: str, to: str, waba_conf: WABAConfig):
#     try:
#         # Log the parameters being used
#         # logger.info(f"Sending message to WhatsApp. To: {to}, Message: {answer}")

#         # Your existing send_text_response_to_wa logic here
#         url = f"https://graph.facebook.com/v12.0/{waba_conf.phone_number_id}/messages"
#         headers = {
#             "Authorization": f"Bearer {waba_conf.permanent_token}",
#             "Content-Type": "application/json",
#         }
#         payload = {
#             "messaging_product": "whatsapp",
#             "to": to,
#             "type": "text",
#             "text": {"body": answer},
#         }

#         async with aiohttp.ClientSession() as session:
#             async with session.post(url, headers=headers, json=payload) as response:
#                 if response.status == 200:
#                     # logger.info("Message sent successfully")
#                     pass
#                 else:
#                     error_text = await response.text()
#                     logger.error(
#                         f"Failed to send message. Status: {response.status}, Response: {error_text}"
#                     )
#                     raise Exception(f"WhatsApp API error: {error_text}")

#     except Exception as e:
#         logger.error(f"Error in send_text_response_to_wa: {str(e)}", exc_info=True)
#         raise  # Re-raise the exception after logging


async def send_text_response_to_wa(answer: str, to: str, waba_conf: WABAConfig):
    try:
        # Detailed logging
        logger.info(
            f"Sending message to WhatsApp. To: {to}, Phone ID: {waba_conf.phone_number_id}"
        )
        logger.debug(f"Message content (first 50 chars): {answer[:50]}...")

        url = f"https://graph.facebook.com/v17.0/{waba_conf.phone_number_id}/messages"
        logger.debug(f"WhatsApp API URL: {url}")

        headers = {
            "Authorization": f"Bearer {waba_conf.permanent_token}",
            "Content-Type": "application/json",
        }
        logger.debug(
            f"Using phone_number_id: {waba_conf.phone_number_id}, token length: {len(waba_conf.permanent_token)}"
        )

        payload = {
            "messaging_product": "whatsapp",
            "to": to,
            "type": "text",
            "text": {"body": answer},
        }
        logger.debug(
            f"Payload (without message body): {json.dumps({**payload, 'text': {'body': '...'}})}"
        )

        async with aiohttp.ClientSession() as session:
            async with session.post(url, headers=headers, json=payload) as response:
                status_code = response.status
                logger.info(f"WhatsApp API response status: {status_code}")

                if status_code == 200:
                    response_body = await response.text()
                    logger.info("Message sent successfully")
                    logger.debug(f"Response body: {response_body}")
                    return response_body
                else:
                    error_text = await response.text()
                    logger.error(
                        f"Failed to send message. Status: {status_code}, Response: {error_text}"
                    )
                    raise Exception(f"WhatsApp API error: {error_text}")

    except Exception as e:
        logger.error(f"Error in send_text_response_to_wa: {str(e)}", exc_info=True)
        raise  # Re-raise the exception after logging


async def send_url_response_to_wa(
    to: str, phone_number_id: str, fb_permanent_token: str, waba: str
):
    logger.info(f"Sending to wapp with phoneNumberId: {phone_number_id}")
    try:
        logger.info(f"Sending URL message to WhatsApp, to number: {to}")
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"https://graph.facebook.com/v20.0/{phone_number_id}/messages",
                params={"access_token": fb_permanent_token},
                json={
                    "messaging_product": "whatsapp",
                    "recipient_type": "individual",
                    "to": to,
                    "type": "text",
                    "text": {
                        "preview_url": True,
                        "body": "As requested, here's the link to our latest product: https://www.meta.com/quest/quest-3/",
                    },
                },
                headers={"Content-Type": "application/json"},
            )
        return response.json()
    except Exception as error:
        logger.info(f"Failed to send message to WhatsApp: {error}")


async def send_wapp_document_res(
    to: str, phone_number_id: str, fb_permanent_token: str, waba: str
):
    logger.info(f"Sending Doc to wapp with phoneNumberId: {phone_number_id}")
    try:
        logger.info(f"Sending message to WhatsApp, to number: {to}")
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"https://graph.facebook.com/v20.0/{phone_number_id}/messages",
                params={"access_token": fb_permanent_token},
                json={
                    "messaging_product": "whatsapp",
                    "recipient_type": "individual",
                    "to": to,
                    "type": "document",
                    "document": {
                        "link": "https://drive.google.com/uc?export=download&id=1-yMKqbIJX-28VcGI0JkTpGYFcS8553DS",
                        "caption": "esta es la caption!",
                        "filename": "este es el file name!",
                    },
                },
                headers={"Content-Type": "application/json"},
            )
        return response.json()
    except Exception as error:
        logger.info(f"Failed to send message to WhatsApp: {error}")


# conf = {
#     "phone_number_id": "123456",
#     "fb_permanent_token": "ABC-123",
#     "curso": "Multiplica tus Ventas en Mercado Libre",
#     "url_compra": "https://emprendemy.com/curso/curso-ventas-en-mercado-libre/",
#     "catchy_phrase": "Aprovecha esta oportunidad y multiplica tus ventas en Mercado Libre!",
#     "descuento": "55%",
#     "to": "123456",
# }


async def send_interactive_list_to_wa(
    to: str,
    phone_number_id: str,
    fb_permanent_token: str,
    files: List[Dict],
    company_name: str,
):
    try:
        sections = []
        for i in range(0, len(files), 10):
            sections.append(
                {
                    "title": f"Documentos ({i // 10 + 1})",
                    "rows": [
                        {
                            "id": file["id"],
                            "title": company_name[:24],
                            "description": file["filename"][:72],
                        }
                        for file in files[i : i + 10]
                    ],
                }
            )

        for i, section in enumerate(sections):
            request_body = {
                "messaging_product": "whatsapp",
                "recipient_type": "individual",
                "to": to,
                "type": "interactive",
                "interactive": {
                    "type": "list",
                    "body": {"text": "Documentos disponibles"},
                    "action": {"button": "Ver Documentos", "sections": [section]},
                },
            }
            if i == 0:
                request_body["interactive"]["header"] = {
                    "type": "text",
                    "text": company_name[:60],
                }
            if len(sections) > 1:
                request_body["interactive"]["footer"] = {
                    "text": f"Parte {i + 1} de {len(sections)}"
                }

            logger.info(f"Request body for section {i + 1}: {request_body}")

            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"https://graph.facebook.com/v20.0/{phone_number_id}/messages",
                    params={"access_token": fb_permanent_token},
                    json=request_body,
                    headers={"Content-Type": "application/json"},
                )
            logger.info(
                f"Sent message {i + 1} of {len(sections)}. Response: {response.json()}"
            )

        return {
            "success": True,
            "message": f"Sent {len(sections)} messages with document lists.",
        }
    except Exception as error:
        logger.info(f"Failed to send list to WhatsApp: {error}")
        if hasattr(error, "response"):
            logger.info(f"Response data: {error.response.json()}")
        elif hasattr(error, "request"):
            logger.info(f"No response received: {error.request}")
        else:
            logger.info(f"Error message: {str(error)}")
        return {"success": False, "error": str(error)}


async def send_template_response_to_wa(
    to: str, phone_number_id: str, fb_permanent_token: str, waba: str
) -> Dict[str, Any]:
    logger.info(f"Sending Template to wapp with phoneNumberId: {phone_number_id}")

    try:
        logger.info(f"Sending message to WhatsApp, to number: {to}")

        async with aiohttp.ClientSession() as session:
            async with session.post(
                f"https://graph.facebook.com/v20.0/{phone_number_id}/messages",
                params={"access_token": fb_permanent_token},
                json={
                    "messaging_product": "whatsapp",
                    "recipient_type": "individual",
                    "to": to,
                    "type": "template",
                    "template": {
                        "name": "hello_world",
                        "language": {"code": "en_US"},
                        "components": [
                            {
                                "type": "header",
                                "parameters": [
                                    {
                                        "type": "image",
                                        "image": {
                                            "link": "https://dfstudio-d420.kxcdn.com/wordpress/wp-content/uploads/2019/06/digital_camera_photo-980x653.jpg"
                                        },
                                    }
                                ],
                            },
                            {
                                "type": "body",
                                "parameters": [
                                    {"type": "text", "text": "hola text"},
                                    {
                                        "type": "currency",
                                        "currency": {
                                            "fallback_value": "VALUE",
                                            "code": "USD",
                                            "amount_1000": "NUMBER",
                                        },
                                    },
                                    {
                                        "type": "date_time",
                                        "date_time": {
                                            "fallback_value": "MONTH DAY, YEAR"
                                        },
                                    },
                                ],
                            },
                            {
                                "type": "button",
                                "sub_type": "quick_reply",
                                "index": "0",
                                "parameters": [
                                    {"type": "payload", "payload": "PAYLOAD"}
                                ],
                            },
                            {
                                "type": "button",
                                "sub_type": "quick_reply",
                                "index": "1",
                                "parameters": [
                                    {"type": "payload", "payload": "PAYLOAD"}
                                ],
                            },
                        ],
                    },
                },
            ) as response:
                return await response.json()
    except Exception as error:
        logger.info(f"Failed to send message to WhatsApp: {error}")


async def get_media_whatsapp_url(audio_data: Dict[str, Any], access_token: str) -> str:
    try:
        media_id = audio_data["id"]
        media_url = f"https://graph.facebook.com/v20.0/{media_id}/"

        async with aiohttp.ClientSession() as session:
            async with session.get(
                media_url, headers={"Authorization": f"Bearer {access_token}"}
            ) as response:
                media_response = await response.json()

        download_url = media_response["url"]
        logger.info(f"This is the downloadUrl: {download_url}")
        return download_url
    except Exception as error:
        logger.info(f"Error fetching audio file: {error}")
        raise


async def send_audio_response(
    audio_buffer_res: bytes, to: str, phone_number_id: str, fb_permanent_token: str
) -> Dict[str, Any]:
    try:
        logger.info(f"Sending audio to WhatsApp, to number: {to}")

        form = aiohttp.FormData()
        form.add_field("messaging_product", "whatsapp")
        form.add_field("to", to)
        form.add_field("type", "audio")
        form.add_field(
            "audio", audio_buffer_res, filename="audio.mp3", content_type="audio/mpeg"
        )

        async with aiohttp.ClientSession() as session:
            async with session.post(
                f"https://graph.facebook.com/v18.0/{phone_number_id}/messages",
                data=form,
                headers={"Authorization": f"Bearer {fb_permanent_token}"},
            ) as response:
                result = await response.json()
                logger.info(f"Audio sent to WhatsApp with response: {result}")
                return result
    except Exception as error:
        logger.info(f"Failed to send message to WhatsApp: {error}")


async def get_wa_templates(waba: str, fb_permanent_token: str) -> List[Dict[str, Any]]:
    api_url = f"https://graph.facebook.com/v20.0/{waba}/message_templates"

    async with aiohttp.ClientSession() as session:
        async with session.get(
            api_url, headers={"Authorization": f"Bearer {fb_permanent_token}"}
        ) as response:
            data = await response.json()
            templates = data.get("data", [])
            logger.info(f"Approved templates: {templates}")
            return templates


async def log_wabas_quality() -> str:
    waba_ids = [
        "333741499822026",
        "372629852590402",
        # Add any other WABA IDs to check
    ]

    for waba_id in waba_ids:
        company_vars = get_waba_config(waba_id)
        permanent_token = company_vars["permanent_token"]

        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    f"https://graph.facebook.com/v20.0/{waba_id}/phone_numbers",
                    params={"access_token": permanent_token},
                ) as response:
                    data = await response.json()
                    phone_numbers = data.get("data", [])

            for phone_number in phone_numbers:
                logger.info(
                    f"WABA ID: {waba_id}, Phone Number ID: {phone_number['id']}, Quality: {phone_number['quality_status']}"
                )
        except Exception as error:
            logger.info(f"Error fetching WABA quality for {waba_id}: {error}")

    return "WABA quality check completed"


async def send_jellinek_doc_msg(
    recipient: str,
    message: Dict[str, str],
    file: Dict[str, Any],
    access_token: str,
    phone_number_id: str,
) -> Dict[str, Any]:
    logger.info(f"🚀 ~ send_jellinek_doc_msg ~ access_token: {access_token}")
    logger.info(f"🚀 ~ send_jellinek_doc_msg ~ phone_number_id: {phone_number_id}")

    try:
        if file and file.get("content"):
            media_id = await get_whatsapp_upload_url(
                phone_number_id, access_token, file
            )
            logger.info(f"🚀 ~ send_jellinek_doc_msg ~ media_id: {media_id}")
        else:
            raise ValueError("File content is missing")

        payload = {
            "messaging_product": "whatsapp",
            "recipient_type": "individual",
            "to": recipient,
            "type": "document",
            "document": {
                "id": media_id,
                "filename": file["name"],
                "caption": message["caption"],
            },
        }

        logger.info(f"🚀 ~ send_jellinek_doc_msg ~ payload: {payload}")

        async with aiohttp.ClientSession() as session:
            async with session.post(
                f"https://graph.facebook.com/v20.0/{phone_number_id}/messages",
                json=payload,
                headers={
                    "Authorization": f"Bearer {access_token}",
                    "Content-Type": "application/json",
                },
            ) as response:
                result = await response.json()
                logger.info(f"🚀 ~ send_jellinek_doc_msg ~ send_response: {result}")
                return result
    except Exception as error:
        logger.info(f"Error sending WhatsApp message: {error}")
        raise


async def get_whatsapp_upload_url(
    phone_number_id: str, access_token: str, file: Dict[str, Any]
) -> str:
    try:
        form = aiohttp.FormData()
        form.add_field("messaging_product", "whatsapp")
        form.add_field(
            "file",
            file["content"],
            filename=file["name"],
            content_type=file["mimeType"],
        )

        async with aiohttp.ClientSession() as session:
            async with session.post(
                f"https://graph.facebook.com/v20.0/{phone_number_id}/media",
                data=form,
                headers={"Authorization": f"Bearer {access_token}"},
            ) as response:
                result = await response.json()
                logger.info(f"🚀 ~ get_whatsapp_upload_url ~ response: {result}")

                if result and "id" in result:
                    return result["id"]
                else:
                    raise ValueError("Failed to upload media to WhatsApp API")
    except Exception as error:
        logger.info(f"Error uploading media to WhatsApp: {error}")
        raise


async def send_contact_message_to_wa(
    contact_info: Dict[str, Any], to: str, phone_number_id: str, fb_permanent_token: str
) -> Dict[str, Any]:
    # logger.info(f"Sending Contact to WhatsApp with phoneNumberId: {phone_number_id}")

    try:
        # logger.info(f"Sending contact message to WhatsApp, to number: {to}")

        async with aiohttp.ClientSession() as session:
            async with session.post(
                f"https://graph.facebook.com/v20.0/{phone_number_id}/messages",
                params={"access_token": fb_permanent_token},
                json={
                    "messaging_product": "whatsapp",
                    "to": to,
                    "type": "contacts",
                    "contacts": [contact_info],
                },
            ) as response:
                return await response.json()
    except Exception as error:
        logger.info(f"Failed to send contact message to WhatsApp: {error}")


async def send_MPM(waba_conf, to, results, query):
    TEMPLATE_NAME = "mpm_template_4"
    TEMPLATE_LANGUAGE = "en"

    # waba = get_waba_config(waba)

    def format_product_id(product_id):
        product_id = str(product_id).strip()
        return product_id.zfill(7)[:7]

    product_items = [
        format_product_id(result["id"]) for result in results if result.get("id")
    ]

    if not product_items:
        logger.error("No valid product IDs found in the results array.")
        return {"status": "error", "message": "No valid product IDs to send."}

    logger.info(f"Product IDs: {product_items}")

    url = f"https://graph.facebook.com/v20.0/{waba_conf.phone_number_id}/messages"
    headers = {
        "Authorization": f"Bearer {waba_conf.permanent_token}",
        "Content-Type": "application/json",
    }

    payload = {
        "messaging_product": "whatsapp",
        "recipient_type": "individual",
        "to": to,
        "type": "template",
        "template": {
            "name": TEMPLATE_NAME,
            "language": {"code": TEMPLATE_LANGUAGE},
            "components": [
                {
                    "type": "body",
                    "parameters": [{"type": "text", "text": f"{query}"}],
                },
                {
                    "type": "button",
                    "sub_type": "MPM",
                    "index": 0,
                    "parameters": [
                        {
                            "type": "action",
                            "action": {
                                "sections": [
                                    {
                                        "title": "Featured Products",
                                        "product_items": [
                                            {"product_retailer_id": item}
                                            for item in product_items
                                        ],
                                    }
                                ]
                            },
                        }
                    ],
                },
            ],
        },
    }

    async with aiohttp.ClientSession() as session:
        try:
            async with session.post(url, headers=headers, json=payload) as response:
                response_text = await response.text()
                logger.info(f"Response Status: {response.status}")
                logger.info(f"Response text: {response_text}")

                response.raise_for_status()
                logger.info("Message sent successfully")
                return {"status": "success", "response": response_text}
        except aiohttp.ClientResponseError as e:
            logger.error(f"Error sending message: {e}")
            logger.error(f"Response content: {response_text}")
            return {
                "status": "error",
                "error": str(e),
                "response": response_text,
            }


async def send_carousel(waba_conf, to):
    # TEMPLATE_NAME = "carousel_template_1"
    TEMPLATE_NAME = "carousel_product_template_1"
    TEMPLATE_LANGUAGE = "en"

    BODY_PARAM_1 = "15OFF"
    BODY_PARAM_2 = "15%"

    IMAGE_URL_1 = "https://mishkaobjetos.com/imagenes/productos/0108238-1.jpg"
    IMAGE_URL_2 = "https://mishkaobjetos.com/imagenes/productos/0101096-1.jpg"
    IMAGE_URL_3 = "https://mishkaobjetos.com/imagenes/productos/0106H26-1.jpg"

    url = f"https://graph.facebook.com/v20.0/{waba_conf.phone_number_id}/messages"

    headers = {
        "Authorization": f"Bearer {waba_conf.permanent_token}",
        "Content-Type": "application/json",
    }

    payload = {
        "messaging_product": "whatsapp",
        "recipient_type": "individual",
        "to": to,
        "type": "template",
        "template": {
            "name": TEMPLATE_NAME,
            "language": {"code": TEMPLATE_LANGUAGE},
            "components": [
                {
                    "type": "BODY",
                    "parameters": [
                        {"type": "TEXT", "text": BODY_PARAM_1},
                        {"type": "TEXT", "text": BODY_PARAM_2},
                    ],
                },
                {
                    "type": "CAROUSEL",
                    "cards": [
                        {
                            "card_index": 0,
                            "components": [
                                {
                                    "type": "HEADER",
                                    "parameters": [
                                        {
                                            "type": "IMAGE",
                                            "image": {"link": IMAGE_URL_1},
                                        }
                                    ],
                                },
                                {
                                    "type": "BODY",
                                    "parameters": [
                                        {"type": "TEXT", "text": "15OFF"},
                                        {"type": "TEXT", "text": "15%"},
                                    ],
                                },
                                {
                                    "type": "BUTTON",
                                    "sub_type": "QUICK_REPLY",
                                    "index": 0,
                                    "parameters": [
                                        {
                                            "type": "PAYLOAD",
                                            "payload": "send_more_like_this",
                                        }
                                    ],
                                },
                                {
                                    "type": "BUTTON",
                                    "sub_type": "URL",
                                    "index": 1,
                                    "parameters": [
                                        {"type": "TEXT", "text": "summer_lemons_2023"}
                                    ],
                                },
                            ],
                        },
                        {
                            "card_index": 1,
                            "components": [
                                {
                                    "type": "HEADER",
                                    "parameters": [
                                        {
                                            "type": "IMAGE",
                                            "image": {"link": IMAGE_URL_2},
                                        }
                                    ],
                                },
                                {
                                    "type": "BODY",
                                    "parameters": [
                                        {"type": "TEXT", "text": "15OFF"},
                                        {"type": "TEXT", "text": "15%"},
                                    ],
                                },
                                {
                                    "type": "BUTTON",
                                    "sub_type": "QUICK_REPLY",
                                    "index": 0,
                                    "parameters": [
                                        {
                                            "type": "PAYLOAD",
                                            "payload": "send_more_like_this",
                                        }
                                    ],
                                },
                                {
                                    "type": "BUTTON",
                                    "sub_type": "URL",
                                    "index": 1,
                                    "parameters": [
                                        {"type": "TEXT", "text": "summer_lemons_2023"}
                                    ],
                                },
                            ],
                        },
                        {
                            "card_index": 2,
                            "components": [
                                {
                                    "type": "HEADER",
                                    "parameters": [
                                        {
                                            "type": "IMAGE",
                                            "image": {"link": IMAGE_URL_3},
                                        }
                                    ],
                                },
                                {
                                    "type": "BODY",
                                    "parameters": [
                                        {"type": "TEXT", "text": "15OFF"},
                                        {"type": "TEXT", "text": "15%"},
                                    ],
                                },
                                {
                                    "type": "BUTTON",
                                    "sub_type": "QUICK_REPLY",
                                    "index": 0,
                                    "parameters": [
                                        {
                                            "type": "PAYLOAD",
                                            "payload": "send_more_like_this",
                                        }
                                    ],
                                },
                                {
                                    "type": "BUTTON",
                                    "sub_type": "URL",
                                    "index": 1,
                                    "parameters": [
                                        {"type": "TEXT", "text": "summer_lemons_2023"}
                                    ],
                                },
                            ],
                        },  # ... (repeat similar structure for cards 1 and 2, using IMAGE_URL_2 and IMAGE_URL_3)
                    ],
                },
            ],
        },
    }

    async with aiohttp.ClientSession() as session:
        try:
            async with session.post(url, headers=headers, json=payload) as response:
                if response.status == 200:
                    result = await response.json()
                    logger.info("Message sent successfully!")
                    logger.info(f"Response: {result}")
                    return result
                else:
                    error_text = await response.text()
                    logger.error(
                        f"Failed to send message. Status code: {response.status}"
                    )
                    logger.error(f"Response: {error_text}")
                    return {
                        "error": f"Failed to send message. Status code: {response.status}"
                    }
        except aiohttp.ClientError as e:
            logger.error(f"Request failed: {str(e)}")
            return {"error": f"Request failed: {str(e)}"}


async def send_carousel_product(token, phone_id, to):
    TEMPLATE_LANGUAGE = "en"

    ACCESS_TOKEN = "EAAQ6zvJxZBbQBO91st0ZClDjZCtu5bS680eI3xRaEJPVObnfZBnWksxaSwsZCyaCZCBn57JNMN0bcxYPHzxmwZCU5rKbNtDCZAGGmWVPiDu6keBqZBMKlE27B3Sga117fqRhlZAByDNvqGYiu9RToZCK35hOxvl3H9IrZAJs7QyXWTYp8JxdKIRVxZBKYybUgpY6iZCtuvwgZDZD"
    PHONE_NUMBER_ID = "361534797044013"  # iassistance demo de alianza business
    CATALOG_ID = "1542166406375180"
    TEMPLATE_NAME = "carousel_product_template_1"

    RECIPIENT_PHONE_NUMBER = "5491135568298"

    url = f"https://graph.facebook.com/v20.0/{PHONE_NUMBER_ID}/messages"

    headers = {
        "Authorization": f"Bearer {ACCESS_TOKEN}",
        "Content-Type": "application/json",
    }

    payload = {
        "messaging_product": "whatsapp",
        "recipient_type": "individual",
        "to": RECIPIENT_PHONE_NUMBER,
        "type": "template",
        "template": {
            "name": TEMPLATE_NAME,
            "language": {"code": TEMPLATE_LANGUAGE},
            "components": [
                {
                    "type": "BODY",
                    "parameters": [
                        {"type": "TEXT", "text": "15OFF"},
                        {"type": "TEXT", "text": "15%"},
                    ],
                },
                {
                    "type": "CAROUSEL",
                    "cards": [
                        {
                            "card_index": 0,
                            "components": [
                                {
                                    "type": "HEADER",
                                    "parameters": [
                                        {
                                            "type": "product",
                                            "product": {
                                                "product_retailer_id": "0503114",
                                                "catalog_id": CATALOG_ID,
                                            },
                                        }
                                    ],
                                },
                            ],
                        },
                        {
                            "card_index": 1,
                            "components": [
                                {
                                    "type": "HEADER",
                                    "parameters": [
                                        {
                                            "type": "product",
                                            "product": {
                                                "product_retailer_id": "0131118",
                                                "catalog_id": CATALOG_ID,
                                            },
                                        }
                                    ],
                                },
                            ],
                        },
                        {
                            "card_index": 2,
                            "components": [
                                {
                                    "type": "HEADER",
                                    "parameters": [
                                        {
                                            "type": "product",
                                            "product": {
                                                "product_retailer_id": "0101836",
                                                "catalog_id": CATALOG_ID,
                                            },
                                        }
                                    ],
                                },
                            ],
                        },
                    ],
                },
            ],
        },
    }

    # logger.info(f"Payload: {json.dumps(payload, indent=2)}")

    # try:
    #     response = requests.post(url, headers=headers, json=payload)
    #     response.raise_for_status()
    # except requests.exceptions.RequestException as e:
    #     logger.error(f"Request failed: {e}")
    #     if response is not None:
    #         logger.error(f"Response content: {response.text}")
    #     raise

    # if response.status_code == 200:
    #     logger.info("Message sent successfully!")
    #     logger.info(f"Response: {response.json()}")
    # else:
    #     logger.error(f"Failed to send message. Status code: {response.status_code}")
    #     logger.error(f"Response: {response.text}")

    async with aiohttp.ClientSession() as session:
        try:
            async with session.post(url, headers=headers, json=payload) as response:
                if response.status == 200:
                    result = await response.json()
                    logger.info("Message sent successfully!")
                    logger.info(f"Response: {result}")
                    return result
                else:
                    error_text = await response.text()
                    logger.error(
                        f"Failed to send message. Status code: {response.status}"
                    )
                    logger.error(f"Response: {error_text}")
                    return {
                        "error": f"Failed to send message. Status code: {response.status}"
                    }
        except aiohttp.ClientError as e:
            logger.error(f"Request failed: {str(e)}")
            return {"error": f"Request failed: {str(e)}"}


async def send_catalog_response_to_wa(fb_token, phone_number_id, to):
    url = f"https://graph.facebook.com/v20.0/{phone_number_id}/messages"

    headers = {
        "Authorization": f"Bearer {fb_token}",
        "Content-Type": "application/json",
    }

    payload = {
        "messaging_product": "whatsapp",
        "recipient_type": "individual",
        "to": to,
        "type": "interactive",
        "interactive": {
            "type": "catalog_message",
            "body": {"text": "body text"},
            "action": {
                "name": "catalog_message",
            },
        },
    }

    # logger.info(f"Payload: {json.dumps(payload, indent=2)}")

    try:
        response = requests.post(url, headers=headers, json=payload)
        response.raise_for_status()
    except requests.exceptions.RequestException as e:
        logger.error(f"Request failed: {e}")
        if response is not None:
            logger.error(f"Response content: {response.text}")
        raise

    if response.status_code == 200:
        logger.info("Message sent successfully!")
        logger.info(f"Response: {response.json()}")
    else:
        logger.error(f"Failed to send message. Status code: {response.status_code}")
        logger.error(f"Response: {response.text}")
