# clients/iass_back_demo/services/openai_handler.py
import logging

from core.services.openai_handler import OpenAIHandler as BaseOpenAIHandler
from core.models.enums import MessageRole, ToolChoice

logger = logging.getLogger(__name__)


class OpenAIHandler(BaseOpenAIHandler):
    """
    Simple OpenAI handler for demo client with basic functionality
    """

    async def handle_openai_process(self) -> None:
        try:
            logger.info("estamos en el cliente demo")
            # Get conversation context
            context_messages = self.service_container.context.get_messages(
                self.waba_conf.waba_id, self.sender_phone
            )

            # Get base instructions for the demo client
            instructions = self.waba_conf.get_instructions("base")

            # Set instructions as prefix
            self.service_container.context.set_prefix_instructions(
                self.waba_conf.waba_id, self.sender_phone, instructions
            )

            # Get full context with instructions included
            context_for_completion = self.service_container.context.get_full_context(
                self.waba_conf.waba_id, self.sender_phone
            )

            # Get completion without tool choice
            response, _ = await self.get_completion(
                context_for_completion,
                tool_choice=ToolChoice.NONE,
                situation="handle_openai_process",
            )

            answer = response.content

            if answer:
                await self.process_response(
                    to_send_message=answer,
                    to_db_message=answer,
                    to_context_message=answer,
                    to_db_role=MessageRole.ASSISTANT,
                    to_context_role=MessageRole.ASSISTANT,
                )

        except Exception as e:
            logger.error(f"Error in handle_openai_process: {str(e)}", exc_info=True)
            await self.process_response(
                "Lo siento, hubo un error procesando tu solicitud. ¿Podrías repetirla?"
            )
