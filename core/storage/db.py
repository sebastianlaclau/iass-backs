import datetime
import logging
from typing import Dict, List
import uuid

from pytz import timezone

from core.models.waba import WABAConfig

logger = logging.getLogger(__name__)


class DBStorage:
    def __init__(self, supabase_client):
        self.supabase = supabase_client

    def save_message(
        self, conversation_id: str, message_data: Dict, metadata: Dict = None
    ) -> None:
        """Save message with optional metadata"""
        if not self.supabase:
            return

        try:
            # Verificar si la conversación existe y está activa
            result = (
                self.supabase.table("conversations")
                .select("id")
                .eq("id", conversation_id)
                .eq("status", "active")
                .execute()
            )

            if not result.data:
                # Si la conversación no existe o no está activa, crear una nueva
                logger.warning(
                    f"Conversation {conversation_id} not found or not active, creating new one"
                )
                conversation_id = self._create_conversation(
                    message_data.get("waba_id"), message_data.get("sender")
                )

            message_insert = {
                "conversation_id": conversation_id,
                "message_id": message_data.get("message", {}).get("id"),
                "role": "user" if not message_data.get("is_response") else "assistant",
                "content": message_data.get("message", {})
                .get("text", {})
                .get("body", ""),
                "type": "text",  # PRUEBA
                "metadata": {
                    "type": message_data.get("type"),
                    "original_message": message_data.get("original_message"),
                },
            }

            if metadata:
                message_insert["metadata"].update(metadata)

            self.supabase.table("messages").insert(message_insert).execute()
            self._update_conversation_activity(conversation_id)

        except Exception as e:
            logger.error(f"Error saving message: {str(e)}")

    def _create_conversation(self, waba_id: str, phone_number: str) -> str:
        """Create new conversation and return its ID"""
        try:
            result = (
                self.supabase.table("conversations")
                .insert({"waba_id": waba_id, "phone_number": phone_number})
                .execute()
            )
            logger.info(f"Created new conversation for {phone_number}")
            return result.data[0]["id"]
        except Exception as e:
            logger.error(f"Error creating conversation: {str(e)}")
            raise

    def store_function_call(self, conversation_id: str, function_data: Dict) -> None:
        """Store function execution details"""
        try:
            function_message = {
                "message": {
                    "id": str(uuid.uuid4()),
                    "text": {"body": f"Function executed: {function_data['name']}"},
                },
                "is_response": True,
                "type": "function_call",
            }

            self.store_message(
                conversation_id=conversation_id,
                message_data=function_message,
                metadata={
                    "function_name": function_data["name"],
                    "arguments": function_data["args"],
                    "result": function_data["result"],
                    "timestamp": function_data["timestamp"],
                },
            )

        except Exception as e:
            logger.error(f"Error storing function call: {str(e)}", exc_info=True)
            raise

    def get_conversation_id(self, waba_conf: WABAConfig, sender: str) -> str:
        """Get existing conversation ID for this sender and WABA"""
        return self.get_or_create_conversation(waba_conf.waba_id, sender)

    def get_conversation_messages(
        self, conversation_id: str, include_metadata: bool = False
    ) -> List[Dict]:
        """Retrieve messages for a conversation"""
        try:
            query = (
                self.supabase.table("messages")
                .select(
                    "id, role, content, created_at"
                    + (", metadata" if include_metadata else "")
                )
                .eq("conversation_id", conversation_id)
                .order("created_at")
            )

            result = query.execute()
            return result.data

        except Exception as e:
            logger.error(
                f"Error retrieving conversation messages: {str(e)}", exc_info=True
            )
            return []

    def archive_conversation(self, conversation_id: str) -> None:
        """Archive a conversation"""
        self.supabase.table("conversations").update({"status": "archived"}).eq(
            "id", conversation_id
        ).execute()

    def get_or_create_conversation(self, waba_id: str, phone_number: str) -> str:
        if not self.supabase:
            return str(uuid.uuid4())

        try:
            result = (
                self.supabase.table("conversations")
                .select("id, last_activity_at")
                .eq("waba_id", waba_id)
                .eq("phone_number", phone_number)
                .eq("status", "active")
                .execute()
            )

            if not result.data:
                return self._create_conversation(waba_id, phone_number)

            conv = result.data[0]
            last_activity = datetime.strptime(
                conv["last_activity_at"].split(".")[0], "%Y-%m-%dT%H:%M:%S"
            ).replace(tzinfo=timezone.utc)

            if datetime.now(timezone.utc) - last_activity > datetime.timedelta(
                hours=24
            ):
                self.archive_conversation(conv["id"])
                return self._create_conversation(waba_id, phone_number)

            return conv["id"]

        except Exception as e:
            logger.error(f"Error in get_or_create_conversation: {str(e)}")
            return self._create_conversation(waba_id, phone_number)

    def store_message(
        self, conversation_id: str, message_data: Dict, metadata: Dict = None
    ) -> None:
        if not self.supabase:
            return

        try:
            message_insert = {
                "conversation_id": conversation_id,
                "message_id": message_data.get("message", {}).get("id"),
                "role": "user" if not message_data.get("is_response") else "assistant",
                "content": message_data.get("message", {})
                .get("text", {})
                .get("body", ""),
                "metadata": {
                    "type": message_data.get("type"),
                    "original_message": message_data.get("original_message"),
                },
            }

            if metadata:
                message_insert["metadata"].update(metadata)

            self.supabase.table("messages").insert(message_insert).execute()
            self._update_conversation_activity(conversation_id)

        except Exception as e:
            logger.error(f"Error storing message: {str(e)}", exc_info=True)

    def _message_exists(self, conversation_id: str, message: Dict) -> bool:
        """Check if message already exists in conversation"""
        result = (
            self.supabase.table("messages")
            .select("id")
            .eq("conversation_id", conversation_id)
            .eq("message_id", message.get("id"))
            .execute()
        )
        return bool(result.data)

    def _format_message_data(self, message: Dict) -> Dict:
        """Format message for storage"""
        return {
            "message": {
                "id": message.get("id", str(uuid.uuid4())),
                "text": {"body": message.get("content", "")},
            },
            "is_response": message.get("role") == "assistant",
            "type": message.get("type", "text"),
        }

    def _update_conversation_activity(self, conversation_id: str) -> None:
        self.supabase.table("conversations").update(
            {"last_activity_at": datetime.now(timezone.utc).isoformat()}
        ).eq("id", conversation_id).execute()

    async def update_message_metadata(
        self, conversation_id: str, message_id: str, metadata_update: Dict
    ) -> None:
        try:
            result = (
                self.supabase.table("messages")
                .select("metadata")
                .eq("conversation_id", conversation_id)
                .eq("message_id", message_id)
                .execute()
            )

            if result.data:
                current_metadata = result.data[0].get("metadata", {})
                # Merge current metadata with updates
                updated_metadata = {**current_metadata, **metadata_update}

                self.supabase.table("messages").update(
                    {"metadata": updated_metadata}
                ).eq("conversation_id", conversation_id).eq(
                    "message_id", message_id
                ).execute()

                logger.debug(
                    f"Updated metadata for message {message_id} in conversation {conversation_id}"
                )
            else:
                logger.warning(
                    f"Message {message_id} not found in conversation {conversation_id}"
                )

        except Exception as e:
            logger.error(f"Error updating message metadata: {str(e)}", exc_info=True)
