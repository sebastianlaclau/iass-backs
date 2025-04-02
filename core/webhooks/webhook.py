# core/webhooks/webhook.py
import logging
from fastapi import APIRouter, Request, Response, HTTPException, BackgroundTasks
from core.services.waba import get_waba_config
from core.utils.supabase_client import supabase
from typing import Dict, Any
from core.webhooks.router import route_meta_webhook
from core.config import config_manager  # Add this import

logger = logging.getLogger(__name__)

router = APIRouter()


@router.post("/dialogs/{waba_id}/{phone_number}/new-conversation")
async def force_new_conversation(waba_id: str, phone_number: str):
    """Force start a new conversation and clear history"""
    """TODO: DO WE WANT TO ALLOW NEW EMPTY CONVERSATIONS? OTHERWISE THIS PROCESS SHOULD ALSO AUTOMATICALLY DELETE THE EMPTY ARCHIVED CONVERSATION"""
    try:
        buffer_key = f"{phone_number}_{waba_id}"
        waba_conf = get_waba_config(waba_id)

        # Acquire lock to prevent race conditions during conversation switch
        # async with message_buffer_manager.with_lock(buffer_key):
        #     # Find current active conversation
        #     current_conv = (
        #         supabase.table("conversations")
        #         .select("id, last_activity_at")
        #         .eq("waba_id", waba_id)
        #         .eq("phone_number", phone_number)
        #         .eq("status", "active")
        #         .execute()
        #     )

        #     logger.info(f"Found existing conversation: {current_conv.data}")

        #     if current_conv.data:
        #         # Archive the current conversation
        #         now = datetime.now(timezone.utc)
        #         supabase.table("conversations").update(
        #             {
        #                 "status": "archived",
        #                 "archived_at": now.isoformat(),
        #                 "last_activity_at": now.isoformat(),
        #                 "metadata": {
        #                     "archive_reason": "manual_split",
        #                     "archived_at": now.isoformat(),
        #                 },
        #             }
        #         ).eq("id", current_conv.data[0]["id"]).execute()

        #     logger.info(f"Archived conversation: {current_conv.data[0]['id']}")

        #     # Clear message buffer and pending responses
        #     message_buffer_manager.clear_conversation(buffer_key)
        #     logger.info(f"Cleared message buffer for: {buffer_key}")

        #     # Clear context cache
        #     context_key = context._get_key(waba_conf, phone_number)
        #     if context_key in context.contexts:
        #         del context.contexts[context_key]

        #     # Create new conversation
        #     new_conv = (
        #         supabase.table("conversations")
        #         .insert(
        #             {
        #                 "waba_id": waba_id,
        #                 "phone_number": phone_number,
        #                 "status": "active",
        #                 "metadata": {
        #                     "manually_split": True,
        #                     "split_from_conversation": current_conv.data[0]["id"]
        #                     if current_conv.data
        #                     else None,
        #                     "split_timestamp": datetime.now(timezone.utc).isoformat(),
        #                 },
        #             }
        #         )
        #         .execute()
        #     )

        #     logger.info(f"Created new conversation: {new_conv.data[0]['id']}")

        #     return {
        #         "message": "New conversation started",
        #         "old_conversation_id": current_conv.data[0]["id"]
        #         if current_conv.data
        #         else None,
        #         "new_conversation_id": new_conv.data[0]["id"],
        #     }

    except Exception as e:
        logger.error(f"Error creating new conversation: {str(e)}")
        raise HTTPException(
            status_code=500, detail=f"Error creating new conversation: {str(e)}"
        )


@router.delete("/dialogs/{waba_id}/conversation/{conversation_id}")
async def delete_conversation(waba_id: str, conversation_id: str):
    try:
        # Delete messages first
        supabase.table("messages").delete().eq(
            "conversation_id", conversation_id
        ).execute()
        # Then delete conversation
        supabase.table("conversations").delete().eq("id", conversation_id).execute()
        return {"message": "Conversation deleted successfully"}
    except Exception as e:
        logger.error(f"Error deleting conversation: {str(e)}")
        raise HTTPException(
            status_code=500, detail=f"Error deleting conversation: {str(e)}"
        )


# async def sync_development_conversations():
#     """
#     Sincroniza las conversaciones activas en cache local con la base de datos.
#     Solo archiva y recrea conversaciones que tienen mensajes.
#     """
#     logger.warning("🔄 INICIANDO SINCRONIZACIÓN DE CONVERSACIONES DE DESARROLLO 🔄")

#     if not settings.should_sync_conversations:
#         logger.warning("❌ Sincronización deshabilitada o no en ambiente de desarrollo")
#         return

#     try:
#         # Obtener TODAS las conversaciones activas de los números habilitados
#         enabled_phones = settings.sync_enabled_phones
#         if not enabled_phones:
#             logger.warning("⚠️ No hay teléfonos habilitados para sincronización")
#             return

#         logger.warning(f"📱 Procesando teléfonos: {enabled_phones}")

#         now = datetime.now(timezone.utc)

#         for phone in enabled_phones:
#             # Buscar todas las conversaciones activas para este número
#             current_convs = (
#                 supabase.table("conversations")
#                 .select("id, waba_id")
#                 .eq("phone_number", phone)
#                 .eq("status", "active")
#                 .execute()
#             )

#             logger.warning(
#                 f"📱 Encontradas {len(current_convs.data)} conversaciones activas para {phone}"
#             )

#             for conv in current_convs.data:
#                 # Verificar si la conversación tiene mensajes
#                 messages = (
#                     supabase.table("messages")
#                     .select("id")
#                     .eq("conversation_id", conv["id"])
#                     .limit(1)
#                     .execute()
#                 )

#                 if not messages.data:
#                     logger.warning(
#                         f"⏭️ Manteniendo conversación sin mensajes: {conv['id']}"
#                     )
#                     continue

#                 # Proceder con archivado y creación solo si hay mensajes
#                 conv_id = conv["id"]
#                 waba_id = conv["waba_id"]

#                 logger.warning(f"📁 Archivando conversación: {conv_id}")

#                 # Archivar conversación actual
#                 supabase.table("conversations").update(
#                     {
#                         "status": "archived",
#                         "archived_at": now.isoformat(),
#                         "last_activity_at": now.isoformat(),
#                         "metadata": {
#                             "archive_reason": "development_reset",
#                             "archived_at": now.isoformat(),
#                         },
#                     }
#                 ).eq("id", conv_id).execute()

#                 # Crear nueva conversación
#                 new_conv = (
#                     supabase.table("conversations")
#                     .insert(
#                         {
#                             "waba_id": waba_id,
#                             "phone_number": phone,
#                             "status": "active",
#                             "metadata": {
#                                 "created_by": "development_reset",
#                                 "created_at": now.isoformat(),
#                                 "previous_conversation": conv_id,
#                             },
#                         }
#                     )
#                     .execute()
#                 )

#                 new_conv_id = new_conv.data[0]["id"]
#                 logger.warning(f"✨ Nueva conversación creada: {new_conv_id}")

#         logger.warning("✅ SINCRONIZACIÓN COMPLETADA")

#     except Exception as e:
#         logger.error(f"❌ Error en sincronización: {str(e)}", exc_info=True)


# ------------------------------------------------------------------------
# MANAGES WABA CONFIG ()
# ------------------------------------------------------------------------


@router.post("/wabas/{waba_id}/reload-config")
async def reload_waba_config(waba_id: str):
    logger.info(f"Received reload config request for WABA {waba_id}")
    try:
        logger.debug(f"Invalidating cache for WABA {waba_id}")
        # await wabas_config_cache.invalidate(waba_id)

        logger.debug(f"Loading new config from DB for WABA {waba_id}")
        # config = await wabas_config_cache.get_config(waba_id)

        # logger.info(f"Successfully reloaded config for WABA {config.name}")
        return {
            "success": True,
            # "message": f"WABA {config.name} configuration reloaded",
        }

    except Exception as e:
        logger.error(
            f"Failed to reload config for WABA {waba_id}: {str(e)}", exc_info=True
        )
        raise HTTPException(status_code=400, detail=str(e))


# ------------------------------------------------------------------------
# WEBHOOK HANDLING
# ------------------------------------------------------------------------


async def normalize_webhook_payload(body: Dict[str, Any]) -> Dict[str, Any]:
    """Normalize webhook payload to standard format."""
    # If it's already in the standard format, return as is
    if "object" in body and "entry" in body:
        return body

    # If it's a test payload from Meta dashboard, transform it
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

        background_tasks.add_task(route_meta_webhook, body)

        return Response(status_code=200)

    except Exception as e:
        logger.error(f"Error in webhook handler: {str(e)}")
        return Response(content="Error processing webhook", status_code=500)
