# core/routers/threads.py
from core.utils.supabase_client import supabase
import logging
from fastapi import APIRouter, HTTPException
from core.services.waba import get_waba_config

logger = logging.getLogger(__name__)

router = APIRouter()


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
        #         now = datetime.now(datetime.datetime.datetime.datetime.datetime.timezone.utc)
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
        #                     "split_timestamp": datetime.now(datetime.datetime.timezone.utc).isoformat(),
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
