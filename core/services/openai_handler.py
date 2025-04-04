# core/services/openai_handler.py
import logging
import uuid
from typing import Dict, Any, List, Optional, Union, Tuple

from core.models.enums import MessageRole, ToolChoice
from core.models.tool import ToolChoiceType
from core.services.whatsapp import send_text_response_to_wa
from core.utils.logging import log_messages

logger = logging.getLogger(__name__)


class OpenAIHandler:
    """
    Base OpenAI handler providing core LLM interaction functionality
    """

    def __init__(
        self,
        client_id: str,
        waba_conf,
        sender_phone: str,
        conversation_id: str,
        current_processing_ids: List[str],
        service_container,
    ):
        self.waba_conf = waba_conf
        self.sender_phone = sender_phone
        self.conversation_id = conversation_id
        self.current_processing_ids = current_processing_ids
        self.service_container = service_container
        self.client_id = client_id

        # Generate buffer key - should match how MessageBufferManager creates keys
        # This key format must match what's used in MessageBufferManager._get_key
        self.buffer_key = f"{sender_phone}_{waba_conf.waba_id}"

        # Default empty functions handler - should be overridden by subclasses
        self.functions_handler = None

    async def handle_openai_process(self) -> None:
        """
        Base method for processing messages with OpenAI
        Should be implemented by subclasses
        """
        raise NotImplementedError("Subclasses must implement handle_openai_process")

    async def get_completion(
        self,
        messages: List[Dict[str, str]],
        tool_choice: ToolChoiceType = ToolChoice.AUTO,
        temperature: Optional[float] = None,
        tools: Optional[List] = None,
        model: Optional[str] = None,
        max_tokens: Optional[int] = None,
        log_context: bool = True,
        situation: Optional[str] = "completion",
    ) -> Tuple:
        """
        Core method to interact with OpenAI API
        """
        try:
            if log_context:
                log_messages(
                    messages,
                    title=f"Context sent to OpenAI ({tool_choice}) from {situation}",
                )

            create_params = {
                "messages": messages,
                "model": model or self.waba_conf.model,
                "temperature": temperature or self.waba_conf.temperature,
            }

            if max_tokens is not None:
                create_params["max_tokens"] = max_tokens

            if tools or (tool_choice != ToolChoice.NONE and self.waba_conf.tools):
                create_params["tools"] = tools or self.waba_conf.tools
                create_params["tool_choice"] = tool_choice.value

            api_response = await self.waba_conf.openai_client.chat.completions.create(
                **create_params
            )

            choice = api_response.choices[0]
            assistant_msg = choice.message

            if log_context:
                if assistant_msg.content:
                    content = ". ".join(
                        line.strip()
                        for line in assistant_msg.content.splitlines()
                        if line.strip()
                    )
                    content_preview = (
                        content[:100] + "..." if len(content) > 100 else content
                    )
                    logger.info(f"OpenAI Response: {content_preview}")

                if assistant_msg.tool_calls:
                    tool_calls_info = " | ".join(
                        f"Function: {call.function.name}, args: {call.function.arguments.replace(chr(10), ' ')}"
                        for call in assistant_msg.tool_calls
                    )
                    logger.info(
                        f"Tool calls: {len(assistant_msg.tool_calls)} | {tool_calls_info}"
                    )

            return assistant_msg, choice

        except Exception as e:
            logger.error(f"Error getting completion from OpenAI: {str(e)}")
            raise

    async def process_response(
        self,
        to_send_message: Union[str, None],
        to_db_message: Union[str, None] = None,
        to_db_role: MessageRole = MessageRole.ASSISTANT,
        to_context_message: Union[str, None] = None,
        to_context_role: MessageRole = MessageRole.ASSISTANT,
    ) -> None:
        """
        Process and send a response to the user
        """
        try:
            # Check if new messages arrived while processing this one
            message_buffer_manager = self.service_container.message_buffer_manager
            if hasattr(message_buffer_manager, "has_new_pending_messages"):
                if await message_buffer_manager.has_new_pending_messages(
                    self.buffer_key, self.current_processing_ids
                ):
                    logger.info(
                        f"Canceling response processing due to new pending messages for {self.sender_phone}"
                    )
                    return

            # Send message to WhatsApp if provided
            if to_send_message is not None:
                wa_sending = await send_text_response_to_wa(
                    to_send_message, self.sender_phone, self.waba_conf
                )
                logger.info(f"wa_sending:{wa_sending}")

            # Save to DB if there's a message (either specific DB message or fallback to send message)
            db_message = to_db_message if to_db_message is not None else to_send_message
            if db_message is not None:
                self.service_container.db.save_message(
                    conversation_id=self.conversation_id,
                    message_data={
                        "message": {
                            "id": str(uuid.uuid4()),
                            "text": {"body": db_message},
                        },
                        "type": "text",
                        "is_response": True,
                    },
                )

            # Add to context if there's a message
            context_message = (
                to_context_message
                if to_context_message is not None
                else (db_message if db_message is not None else (to_send_message or ""))
            )

            self.service_container.context.add_message(
                self.waba_conf.waba_id,
                self.sender_phone,
                to_context_role,
                context_message,
            )

        except Exception as e:
            logger.error(f"Error processing response: {str(e)}")
            raise
