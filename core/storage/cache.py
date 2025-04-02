# core/storage/cache.py
import logging
import asyncio
from typing import Dict, List
from datetime import datetime
from cachetools import TTLCache
from core.models.enums import MessageRole
from core.models.waba import WABAConfig
# from core.utils.config import WABAConfig

logger = logging.getLogger(__name__)


class MessageBufferManager:
    """Manages message buffering and thread locking for WhatsApp messages"""

    def __init__(self, buffer_ttl: int = 3600, lock_ttl: int = 300):
        self.buffer = TTLCache(maxsize=10000, ttl=buffer_ttl)
        self.thread_locks = TTLCache(maxsize=1000, ttl=lock_ttl)

    def _get_key(self, waba_conf: WABAConfig, sender: str) -> str:
        """Genera la clave para el buffer"""
        return f"{sender}_{waba_conf.waba_id}"

    def get_active_buffers(self) -> Dict[str, Dict]:
        """Obtiene los buffers activos antes de que se limpie la cache"""
        return {key: data for key, data in self.buffer.items()}

    def get_or_create_buffer(
        self, waba_conf: WABAConfig, sender: str, conversation_id: str
    ) -> str:
        """Get or create a buffer and return its key"""
        key = self._get_key(waba_conf, sender)
        if key not in self.buffer:
            self.buffer[key] = {
                "metadata": {
                    "sender": sender,
                    "waba_id": waba_conf.waba_id,
                    "waba_conf": waba_conf,
                    "conversation_id": conversation_id,
                },
                "messages": [],
            }
        return key

    async def add_message(self, key: str, message_data: Dict) -> None:
        """Add a message to the buffer identified by its key"""
        if key not in self.buffer:
            logger.warning(f"Buffer not found for key: {key}")
            return

        self.buffer[key]["messages"].append(
            {
                **message_data,
                "processed": False,
                "timestamp": datetime.now().isoformat(),
            }
        )

    def mark_messages_processed(self, key: str, message_ids: List[str]) -> None:
        if key in self.buffer:
            for message in self.buffer[key]["messages"]:
                if message.get("message", {}).get("id") in message_ids:
                    message["processed"] = True

    def get_unprocessed_messages(self, key: str) -> List[Dict]:
        """Get unprocessed messages from buffer"""
        if key not in self.buffer:
            return []
        return [
            msg
            for msg in self.buffer[key]["messages"]
            if not msg.get("processed", False)
        ]

    def is_locked(self, buffer_key: str) -> bool:
        """Check if a thread is currently locked"""
        return buffer_key in self.thread_locks

    def acquire_lock(self, buffer_key: str) -> bool:
        """
        Try to acquire a lock for a buffer key

        Returns:
            bool: True if lock was acquired, False if already locked
        """
        if self.is_locked(buffer_key):
            return False
        self.thread_locks[buffer_key] = True
        # logger.info(f"Lock acquired for {buffer_key}")
        return True

    def release_lock(self, buffer_key: str) -> None:
        """Release a lock for a buffer key"""
        if buffer_key in self.thread_locks:
            del self.thread_locks[buffer_key]
            # logger.info(f"Thread unlocked for {buffer_key}")

    class Lock:
        def __init__(self, manager, buffer_key: str, max_wait: int = 30):
            self.manager = manager
            self.buffer_key = buffer_key
            self.max_wait = max_wait

        async def __aenter__(self):
            start_time = datetime.now()
            while self.manager.is_locked(self.buffer_key):
                if (datetime.now() - start_time).seconds > self.max_wait:
                    raise TimeoutError(
                        f"Could not acquire lock for {self.buffer_key} after {self.max_wait} seconds"
                    )
                await asyncio.sleep(1)
            self.manager.acquire_lock(self.buffer_key)
            return self

        async def __aexit__(self, exc_type, exc_val, exc_tb):
            self.manager.release_lock(self.buffer_key)

    def with_lock(self, buffer_key: str, max_wait: int = 30):
        """
        Get async context manager for handling locks

        Usage:
            async with message_buffer_manager.with_lock(buffer_key):
                # do processing
        """
        return self.Lock(self, buffer_key, max_wait)

    def clear_conversation(self, buffer_key: str) -> bool:
        try:
            if buffer_key in self.buffer:
                del self.buffer[buffer_key]
                if buffer_key in self.thread_locks:
                    del self.thread_locks[buffer_key]
                logger.info(f"Cleared conversation for {buffer_key}")
                return True
            return False
        except Exception as e:
            logger.error(f"Error clearing conversation {buffer_key}: {str(e)}")
            return False

    def clear_all_conversations(self) -> None:
        try:
            self.buffer.clear()
            self.thread_locks.clear()
            logger.info("Cleared all conversations from buffer")
        except Exception as e:
            logger.error(f"Error clearing all conversations: {str(e)}")

    def get_active_conversations(self) -> List[str]:
        return list(self.buffer.keys())

    async def has_new_pending_messages(
        self, buffer_key: str, processing_message_ids: List[str]
    ) -> bool:
        if buffer_key not in self.buffer:
            return False

        unprocessed = self.get_unprocessed_messages(buffer_key)
        # Filtramos los mensajes que ya estamos procesando
        new_pending = [
            msg
            for msg in unprocessed
            if msg["message"]["id"] not in processing_message_ids
        ]
        return len(new_pending) > 0


async def process_buffered_messages(service_container):
    """Process all buffered messages across all active conversations"""
    try:
        # Obtenemos el message_buffer_manager del contenedor de servicios
        message_buffer_manager = service_container.message_buffer_manager

        buffer_keys = list(message_buffer_manager.buffer.keys())
        for buffer_key in buffer_keys:
            try:
                async with message_buffer_manager.with_lock(buffer_key):
                    buffer_data = message_buffer_manager.buffer[buffer_key]

                    # Get metadata and messages
                    metadata = buffer_data["metadata"]
                    waba_conf = metadata["waba_conf"]
                    sender = metadata["sender"]
                    conversation_id = metadata["conversation_id"]

                    # Get unprocessed messages
                    unprocessed_messages = [
                        msg
                        for msg in buffer_data["messages"]
                        if not msg.get("processed", False)
                    ]

                    if not unprocessed_messages:
                        logger.debug(
                            f"No unprocessed messages for buffer: {buffer_key}"
                        )
                        continue

                    # Get message IDs for processing
                    current_processing_ids = [
                        msg["message"]["id"] for msg in unprocessed_messages
                    ]

                    # Importamos OpenAIHandler y lo inicializamos con el service_container
                    from core.services.openai import OpenAIHandler

                    # Process messages with OpenAI
                    openai_handler = OpenAIHandler(
                        waba_conf,
                        sender,
                        conversation_id,
                        current_processing_ids,
                        service_container,  # Pasamos el contenedor de servicios
                    )
                    await openai_handler.handle_openai_process()

                    # Mark messages as processed
                    message_buffer_manager.mark_messages_processed(
                        buffer_key, current_processing_ids
                    )

            except Exception as e:
                logger.error(
                    f"Error processing buffer {buffer_key}: {str(e)}", exc_info=True
                )
                # Continue processing other buffers even if one fails
                continue

    except Exception as e:
        logger.error(f"Error in process_buffered_messages: {str(e)}", exc_info=True)
        raise


# class WABAConfigCache:
#     def __init__(self):
#         self._cache = {}

#     async def get_config(self, waba_id: str) -> WABAConfig:
#         logger.debug(f"Getting config for WABA {waba_id}")
#         try:
#             if waba_id in self._cache:
#                 logger.debug(f"Cache hit for WABA {waba_id}")
#                 return self._cache[waba_id]

#             logger.info(f"Cache miss for WABA {waba_id}, loading from DB")
#             config = await self._load_from_db(waba_id)
#             self._cache[waba_id] = config
#             return config

#         except Exception as e:
#             logger.error(
#                 f"Error getting config for WABA {waba_id}: {str(e)}", exc_info=True
#             )
#             raise

#     async def invalidate(self, waba_id: str):
#         if waba_id in self._cache:
#             del self._cache[waba_id]

#     async def _load_from_db(self, waba_id: str) -> WABAConfig:
#         logger.debug(f"Loading WABA {waba_id} config from DB")
#         try:
#             waba_data = (
#                 await supabase_client.from_("wabas")
#                 .select("*")
#                 .eq("waba_id", waba_id)
#                 .single()
#             )
#             logger.debug(f"DB data retrieved for WABA {waba_id}: {waba_data}")

#             # Combinar datos de DB con settings
#             config = WABAConfig(
#                 name=waba_data["name"],
#                 phone_number=waba_data["phone_number"],
#                 phone_number_id=waba_data["phone_number_id"],
#                 permanent_token=waba_data["permanent_token"],
#                 assistant_id=settings.OPENAI_ASSIST_ID_DEFAULT,
#                 openai_key=settings.OPENAI_API_KEY_DEFAULT,
#                 model=settings.OPENAI_MODEL_DEFAULT,
#                 tools=DEMO_RUN_TOOLS_DEFINITION_EMPRENDEMY,
#                 instructions_strategy=InstructionsStrategy.SINGLE,
#                 pinecone_key=settings.PINECONE_KEY_DEFAULT,
#                 temperature=0.3,
#                 vector_store="",
#                 waba_id=waba_id,
#                 smtp_server=settings.SMTP_SERVER,
#                 smtp_port=settings.SMTP_PORT,
#                 sender_email=settings.SENDER_EMAIL,
#                 admin_email=settings.ADMIN_EMAIL,
#                 email_password=settings.EMAIL_PASSWORD,
#             )

#             logger.info(f"Successfully created WABAConfig for {waba_id}")
#             return config

#         except Exception as e:
#             logger.error(
#                 f"Failed to load WABA {waba_id} from DB: {str(e)}", exc_info=True
#             )
#             raise


class ConversationContext:
    def __init__(self, context_ttl: int = 3600):
        self.contexts = TTLCache(maxsize=10000, ttl=context_ttl)

    def _get_key(self, waba_id: str, sender: str) -> str:
        return f"{sender}_{waba_id}"

    def _get_or_create_context(self, waba_id: str, sender: str) -> Dict:
        """Get or create context structure for a conversation"""
        key = self._get_key(waba_id, sender)
        if key not in self.contexts:
            self.contexts[key] = {
                "prefix_instructions": [],
                "messages": [],
                "temp_context": [],
            }
        return self.contexts[key]

    def set_prefix_instructions(
        self, waba_id: str, sender: str, instructions: List[Dict[str, str]]
    ) -> None:
        """Set instructions that should appear at the start of the context"""
        context = self._get_or_create_context(waba_id, sender)
        context["prefix_instructions"] = instructions

    def add_message(
        self, waba_id: str, sender: str, role: MessageRole, content: str
    ) -> None:
        """Add a message to the conversation history"""
        context = self._get_or_create_context(waba_id, sender)
        role_str = role.value if hasattr(role, "value") else str(role)
        context["messages"].append({"role": role_str, "content": content})

    def add_temp_context(
        self,
        waba_id: str,
        sender: str,
        content: str,
        role: MessageRole = MessageRole.SYSTEM,
    ) -> None:
        """Add a temporary context item"""
        context = self._get_or_create_context(waba_id, sender)
        role_str = role.value if hasattr(role, "value") else str(role)
        context["temp_context"].append({"role": role_str, "content": content})

    def get_messages(self, waba_id: str, sender: str) -> List[Dict[str, str]]:
        """Get conversation history messages only"""
        context = self._get_or_create_context(waba_id, sender)
        return context["messages"]

    def get_full_context(self, waba_id: str, sender: str) -> List[Dict[str, str]]:
        """Get complete context including all instructions and messages in proper order"""
        context = self._get_or_create_context(waba_id, sender)
        return (
            context["prefix_instructions"]
            + context["temp_context"]
            + context["messages"]
        )

    def clear_temp_context(self, waba_id: str, sender: str) -> None:
        """Clear temporary context items only"""
        context = self._get_or_create_context(waba_id, sender)
        context["temp_context"].clear()

    def clear_prefix_instructions(self, waba_id: str, sender: str) -> None:
        """Clear prefix instructions only"""
        context = self._get_or_create_context(waba_id, sender)
        context["prefix_instructions"].clear()

    def reset_conversation(self, waba_id: str, sender: str) -> None:
        """Clear everything - complete reset"""
        key = self._get_key(waba_id, sender)
        if key in self.contexts:
            del self.contexts[key]
