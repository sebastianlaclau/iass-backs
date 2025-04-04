# clients/iass_back_emprendemy/services/openai_handler.py
import logging
import json
from typing import Dict, Any, List, Optional, Tuple

from core.services.openai_handler import OpenAIHandler as BaseOpenAIHandler
from core.models.enums import (
    InstructionsStrategy,
    MessageCategory,
    MessageRole,
    ResponseBehavior,
    ToolChoice,
)
from core.data.prompts import BASE_INSTRUCTIONS
from core.utils.logging import log_messages
from core.utils.normalization import normalize_classification_response

from ..prompts import CATEGORIZE_PROMPT

logger = logging.getLogger(__name__)


class OpenAIHandler(BaseOpenAIHandler):
    """
    Emprendemy-specific OpenAI handler with custom categorization and function processing
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Defer the FunctionsHandler import until needed
        self._functions_handler_initialized = False

    def _ensure_functions_handler(self):
        """Lazily initialize the functions handler when needed"""
        if not self._functions_handler_initialized:
            # Import here to avoid circular import issues during module loading
            from .functions_handler import FunctionsHandler

            self.functions_handler = FunctionsHandler(
                client_id=self.client_id,
                waba_conf=self.waba_conf,
                sender_phone=self.sender_phone,
                openai_handler=self,
                message_buffer_manager=self.service_container.message_buffer_manager,
                service_container=self.service_container,
            )
            self._functions_handler_initialized = True

    async def handle_openai_process(self) -> None:
        try:
            # Get conversation context
            context_messages = self.service_container.context.get_messages(
                self.waba_conf.waba_id, self.sender_phone
            )

            # Perform categorization if there's enough context
            category_info = None
            if (
                hasattr(self.waba_conf, "instructions_strategy")
                and self.waba_conf.instructions_strategy == "CLASSIFIED"
            ):
                category_info = await self.categorize_messages(context_messages)
                if category_info:
                    # Log category information
                    categories_str = " | ".join(
                        f"{cat.value}({conf:.2f})" for cat, conf in category_info
                    )
                    logger.info(
                        f"Conversation categories - messages analyzed: {len(context_messages)} - categories: {categories_str}"
                    )

                    log_messages(
                        context_messages,
                        title="Messages analyzed for categorization",
                        preview_standard=True,
                        standard_length=300,
                    )

                    # Update metadata for all current processing messages
                    categories_data = [
                        {"category": cat.value, "confidence": conf}
                        for cat, conf in category_info
                    ]

                    for message_id in self.current_processing_ids:
                        await self.service_container.db.update_message_metadata(
                            self.conversation_id,
                            message_id,
                            {"categories": categories_data},
                        )

            # Get instructions based on categories and strategy
            if (
                hasattr(self.waba_conf, "instructions_strategy")
                and self.waba_conf.instructions_strategy
                == InstructionsStrategy.CLASSIFIED
            ):
                if category_info:
                    categories = [cat for cat, _ in category_info]
                    instructions = self.waba_conf.get_instructions("base", *categories)
                    self.service_container.context.set_prefix_instructions(
                        self.waba_conf.waba_id, self.sender_phone, instructions
                    )
            else:
                # For other strategies, just get base instructions
                instructions = self.waba_conf.get_instructions("base")
                self.service_container.context.set_prefix_instructions(
                    self.waba_conf.waba_id, self.sender_phone, instructions
                )

            # Get full context for completion
            context_for_completion = self.service_container.context.get_full_context(
                self.waba_conf.waba_id, self.sender_phone
            )

            # Get completion and process response
            response, _ = await self.get_completion(
                context_for_completion,
                tool_choice=ToolChoice.AUTO,
                situation="handle_openai_process",
            )
            logger.info(
                f"OpenAI response received: content={bool(response.content)}, tool_calls={bool(response.tool_calls)}"
            )

            answer = response.content

            if not response.tool_calls:
                logger.debug("No tool calls in response, sending direct message")

                if answer:
                    await self.process_response(
                        to_send_message=answer,
                        to_db_message=answer,
                        to_context_message=answer,
                        to_db_role=MessageRole.ASSISTANT,
                        to_context_role=MessageRole.ASSISTANT,
                    )
                else:
                    logger.warning("Empty response content and no tool calls")
                return

            # Initialize functions handler if needed
            self._ensure_functions_handler()

            # Process tool calls
            await self._process_tool_calls(response.tool_calls)

        except Exception as e:
            logger.error(f"Error in handle_openai_process: {str(e)}", exc_info=True)
            if not hasattr(self, "_response_sent"):
                await self.process_response(
                    "Lo siento, hubo un error procesando tu solicitud. ¿Podrías repetirla?"
                )

    async def _process_tool_calls(self, tool_calls: List) -> Tuple[bool, List[Dict]]:
        # Initialize functions handler if needed
        self._ensure_functions_handler()

        needs_follow_up = False
        follow_up_instructions = []

        # Emprendemy-specific priority map
        priority_map = {
            "get_course_details": 1,  # First course info
            "get_course_price": 2,  # Then price
            "send_emprendemy_contact": 3,  # Then contact info
            "send_sign_up_message": 4,  # Then signup link
            "send_conversation_to_supervisor": 5,  # Lastly supervisor notifications
        }

        # Sort tool_calls by priority
        sorted_calls = sorted(
            tool_calls,
            key=lambda x: priority_map.get(x.function.name, 99),
        )

        for tool_call in sorted_calls:
            function_name = tool_call.function.name
            function_args = json.loads(tool_call.function.arguments)

            result = await self.functions_handler.execute_function(
                function_name,
                function_args,
            )

            if result.response_behavior == ResponseBehavior.REQUIRES_FOLLOW_UP:
                needs_follow_up = True
                follow_up_instructions.append(result.follow_up_instructions)
                logger.info(f"Function {function_name} requires follow up")

        if needs_follow_up:
            await self._handle_follow_up(follow_up_instructions)

        return needs_follow_up, follow_up_instructions

    async def _handle_follow_up(self, follow_up_instructions: List[str]) -> str:
        try:
            new_instructions = "\n\n".join(follow_up_instructions)

            combined_instructions = {
                "role": "system",
                "content": "Dale continuidad a la conversacion"
                + BASE_INSTRUCTIONS
                + new_instructions,
            }

            messages = self.service_container.context.get_messages(
                self.waba_conf.waba_id, self.sender_phone
            )
            context_messages = [combined_instructions] + messages

            response, _ = await self.get_completion(
                context_messages,
                tool_choice=ToolChoice.NONE,
                situation="handle_follow_up",
            )
            answer = response.content
            if answer:
                await self.process_response(
                    to_send_message=answer,
                )
                return answer
            return ""

        except Exception as e:
            logger.error(f"Error handling follow-up: {str(e)}")
            raise

    async def categorize_messages(
        self, messages: List[Dict[str, Any]]
    ) -> Optional[List[Tuple[MessageCategory, float]]]:
        try:
            categorization_prompt = CATEGORIZE_PROMPT.copy()

            conversation_text = "\n".join(
                [f"{m['role']}: {m['content']}" for m in messages]
            )

            categorization_prompt.append(
                {"role": "user", "content": f"####\n{conversation_text}\n####"}
            )
            log_messages(categorization_prompt, "MENSAJES A LA CATEGORIZACION")

            message, choice = await self.get_completion(
                messages=categorization_prompt,
                temperature=0,
                tool_choice=ToolChoice.NONE,
                max_tokens=50,
                log_context=False,
                situation="categorize_messages",
            )

            # Use the normalize function to get valid MessageCategory enums
            categories = normalize_classification_response(message.content)
            confidence = 1.0 if choice.finish_reason == "stop" else 0.8

            # Categories are already MessageCategory enums, just pair them with confidence
            return (
                [(category, confidence) for category in categories]
                if categories
                else None
            )

        except Exception as e:
            logger.error(f"Error in categorize_messages: {str(e)}", exc_info=True)
            return None


# class OpenAIHandler(BaseOpenAIHandler):
#     """
#     Emprendemy-specific OpenAI handler with custom categorization and function processing
#     """

#     def __init__(self, *args, **kwargs):
#         super().__init__(*args, **kwargs)

#         from .functions_handler import FunctionsHandler

#         # Override with Emprendemy-specific function handler
#         self.functions_handler = FunctionsHandler(
#             client_id=self.client_id,
#             waba_conf=self.waba_conf,
#             sender_phone=self.sender_phone,
#             openai_handler=self,
#             message_buffer_manager=self.service_container.message_buffer_manager,
#             service_container=self.service_container,
#         )

#     async def handle_openai_process(self) -> None:
#         try:
#             # Get conversation context
#             context_messages = self.service_container.context.get_messages(
#                 self.waba_conf.waba_id, self.sender_phone
#             )

#             # Perform categorization if there's enough context
#             category_info = None
#             if (
#                 hasattr(self.waba_conf, "instructions_strategy")
#                 and self.waba_conf.instructions_strategy == "CLASSIFIED"
#             ):
#                 category_info = await self.categorize_messages(context_messages)

#                 if category_info:
#                     # Log category information
#                     categories_str = " | ".join(
#                         f"{cat.value}({conf:.2f})" for cat, conf in category_info
#                     )
#                     logger.info(
#                         f"Conversation categories - messages analyzed: {len(context_messages)} - categories: {categories_str}"
#                     )

#                     log_messages(
#                         context_messages,
#                         title="Messages analyzed for categorization",
#                         preview_standard=True,
#                         standard_length=300,
#                     )

#                     # Update metadata for all current processing messages
#                     categories_data = [
#                         {"category": cat.value, "confidence": conf}
#                         for cat, conf in category_info
#                     ]

#                     for message_id in self.current_processing_ids:
#                         await self.service_container.db.update_message_metadata(
#                             self.conversation_id,
#                             message_id,
#                             {"categories": categories_data},
#                         )

#             # Get instructions based on categories and strategy
#             if (
#                 hasattr(self.waba_conf, "instructions_strategy")
#                 and self.waba_conf.instructions_strategy == "CLASSIFIED"
#             ):
#                 if category_info:
#                     categories = [cat for cat, _ in category_info]
#                     instructions = self.waba_conf.get_instructions("base", *categories)
#                     self.service_container.context.set_prefix_instructions(
#                         self.waba_conf.waba_id, self.sender_phone, instructions
#                     )
#             else:
#                 # For other strategies, just get base instructions
#                 instructions = self.waba_conf.get_instructions("base")
#                 self.service_container.context.set_prefix_instructions(
#                     self.waba_conf.waba_id, self.sender_phone, instructions
#                 )

#             # Get full context for completion
#             context_for_completion = self.service_container.context.get_full_context(
#                 self.waba_conf.waba_id, self.sender_phone
#             )

#             # Get completion and process response
#             response, _ = await self.get_completion(
#                 context_for_completion,
#                 tool_choice=ToolChoice.AUTO,
#                 situation="handle_openai_process",
#             )

#             answer = response.content

#             if not response.tool_calls:
#                 if answer:
#                     await self.process_response(
#                         to_send_message=answer,
#                         to_db_message=answer,
#                         to_context_message=answer,
#                         to_db_role=MessageRole.ASSISTANT,
#                         to_context_role=MessageRole.ASSISTANT,
#                     )
#                 return

#             # Process tool calls
#             await self._process_tool_calls(response.tool_calls)

#         except Exception as e:
#             logger.error(f"Error in handle_openai_process: {str(e)}", exc_info=True)
#             if not hasattr(self, "_response_sent"):
#                 await self.process_response(
#                     "Lo siento, hubo un error procesando tu solicitud. ¿Podrías repetirla?"
#                 )

#     async def _process_tool_calls(self, tool_calls: List) -> Tuple[bool, List[Dict]]:
#         needs_follow_up = False
#         follow_up_instructions = []

#         # Emprendemy-specific priority map
#         priority_map = {
#             "get_course_details": 1,  # First course info
#             "get_course_price": 2,  # Then price
#             "send_emprendemy_contact": 3,  # Then contact info
#             "send_sign_up_message": 4,  # Then signup link
#             "send_conversation_to_supervisor": 5,  # Lastly supervisor notifications
#         }

#         # Sort tool_calls by priority
#         sorted_calls = sorted(
#             tool_calls,
#             key=lambda x: priority_map.get(x.function.name, 99),
#         )

#         for tool_call in sorted_calls:
#             function_name = tool_call.function.name
#             function_args = json.loads(tool_call.function.arguments)

#             result = await self.functions_handler.execute_function(
#                 function_name,
#                 function_args,
#             )

#             if result.response_behavior == ResponseBehavior.REQUIRES_FOLLOW_UP:
#                 needs_follow_up = True
#                 follow_up_instructions.append(result.follow_up_instructions)
#                 logger.info(f"Function {function_name} requires follow up")

#         if needs_follow_up:
#             await self._handle_follow_up(follow_up_instructions)

#         return needs_follow_up, follow_up_instructions

#     async def _handle_follow_up(self, follow_up_instructions: List[str]) -> str:
#         try:
#             new_instructions = "\n\n".join(follow_up_instructions)

#             combined_instructions = {
#                 "role": "system",
#                 "content": "Dale continuidad a la conversacion"
#                 + BASE_INSTRUCTIONS
#                 + new_instructions,
#             }

#             messages = self.service_container.context.get_messages(
#                 self.waba_conf.waba_id, self.sender_phone
#             )
#             context_messages = [combined_instructions] + messages

#             response, _ = await self.get_completion(
#                 context_messages,
#                 tool_choice=ToolChoice.NONE,
#                 situation="handle_follow_up",
#             )
#             answer = response.content
#             if answer:
#                 await self.process_response(
#                     to_send_message=answer,
#                 )
#                 return answer
#             return ""

#         except Exception as e:
#             logger.error(f"Error handling follow-up: {str(e)}")
#             raise

#     async def categorize_messages(
#         self, messages: List[Dict[str, Any]]
#     ) -> Optional[List[Tuple[MessageCategory, float]]]:
#         try:
#             categorization_prompt = CATEGORIZE_PROMPT.copy()

#             conversation_text = "\n".join(
#                 [f"{m['role']}: {m['content']}" for m in messages]
#             )

#             categorization_prompt.append(
#                 {"role": "user", "content": f"####\n{conversation_text}\n####"}
#             )
#             log_messages(categorization_prompt, "MENSAJES A LA CATEGORIZACION")

#             message, choice = await self.get_completion(
#                 messages=categorization_prompt,
#                 temperature=0,
#                 tool_choice=ToolChoice.NONE,
#                 max_tokens=50,
#                 log_context=False,
#                 situation="categorize_messages",
#             )

#             # Use the normalize function to get valid MessageCategory enums
#             categories = normalize_classification_response(message.content)
#             confidence = 1.0 if choice.finish_reason == "stop" else 0.8

#             # Categories are already MessageCategory enums, just pair them with confidence
#             return (
#                 [(category, confidence) for category in categories]
#                 if categories
#                 else None
#             )

#         except Exception as e:
#             logger.error(f"Error in categorize_messages: {str(e)}", exc_info=True)
#             return None


# CLASE ORIGINAL COMPLETA, LA GUARDO ACA HASTA QUE FUNCIONE EMPRENDEMY PORQUE ESTA CLASE TENIA MUCHA INTELIGENCIA DEL BOT DE EMPRENDEMY FUNCIONANDO.

# class OpenAIHandler:
#     def __init__(
#         self,
#         client_id: str,  # Add this parameter
#         conversation_id: str,
#         waba_conf: WABAConfig,
#         sender_phone: str,
#         current_processing_ids: List[str],
#         service_container,
#     ):
#         self.waba_conf = waba_conf
#         self.sender_phone = sender_phone
#         self.conversation_id = conversation_id
#         self.buffer_key = f"{sender_phone}_{waba_conf.waba_id}"
#         self.current_processing_ids = current_processing_ids
#         self.message_buffer_manager = service_container.message_buffer_manager
#         self.context = service_container.context
#         self.db = service_container.db
#         self.service_container = service_container
#         self.client_id = client_id

#         self.functions_handler = FunctionsHandler(
#             waba_conf=waba_conf,
#             sender_phone=sender_phone,
#             message_buffer_manager=message_buffer_manager,
#             openai_handler=self,
#             service_container=service_container,
#         )

#     async def handle_openai_process(self) -> None:
#         try:
#             # Get conversation context
#             context_messages = context.get_messages(
#                 self.waba_conf.waba_id, self.sender_phone
#             )

#             # Get last 6 messages (or all if less than 6) for categorization
#             # last_messages = (
#             #     context_messages[-6:]
#             #     if len(context_messages) >= 6
#             #     else context_messages
#             # )

#             # Perform categorization if there's enough context
#             category_info = None
#             if self.waba_conf.instructions_strategy == InstructionsStrategy.CLASSIFIED:
#                 # if last_messages:
#                 category_info = await self.categorize_messages(context_messages)

#                 if category_info:
#                     # Log category information
#                     categories_str = " | ".join(
#                         f"{cat.value}({conf:.2f})" for cat, conf in category_info
#                     )
#                     logger.info(
#                         f"Conversation categories - messages analyzed: {len(context_messages)} - categories: {categories_str}"
#                     )

#                     log_messages(
#                         context_messages,
#                         title="Messages analyzed for categorization",
#                         preview_standard=True,
#                         standard_length=300,
#                     )

#                     # Update metadata for all current processing messages
#                     categories_data = [
#                         {"category": cat.value, "confidence": conf}
#                         for cat, conf in category_info
#                     ]

#                     for message_id in self.current_processing_ids:
#                         await db.update_message_metadata(
#                             self.conversation_id,
#                             message_id,
#                             {"categories": categories_data},
#                         )

#             # Get instructions based on categories and strategy
#             if self.waba_conf.instructions_strategy == InstructionsStrategy.CLASSIFIED:
#                 if category_info:
#                     categories = [cat for cat, _ in category_info]
#                     instructions = self.waba_conf.get_instructions("base", *categories)
#                     context.set_prefix_instructions(
#                         self.waba_conf.waba_id, self.sender_phone, instructions
#                     )

#             else:
#                 # For other strategies, just get base instructions
#                 instructions = self.waba_conf.get_instructions("base")
#                 context.set_prefix_instructions(
#                     self.waba_conf.waba_id, self.sender_phone, instructions
#                 )

#             # Get full context for completion
#             context_for_completion = context.get_full_context(
#                 self.waba_conf.waba_id, self.sender_phone
#             )

#             # Get completion and process response
#             response, _ = await self.get_completion(
#                 context_for_completion,
#                 tool_choice=ToolChoice.AUTO,
#                 situation="handle_openai_process",
#             )

#             answer = response.content

#             if not response.tool_calls:
#                 if answer:
#                     await self.process_response(
#                         to_send_message=answer,
#                         to_db_message=answer,
#                         to_context_message=answer,
#                         to_db_role=MessageRole.ASSISTANT,
#                         to_context_role=MessageRole.ASSISTANT,
#                     )
#                 return

#             # Caso con tool_calls
#             await self._process_tool_calls(
#                 response.tool_calls,
#             )

#         except Exception as e:
#             logger.error(f"Error in handle_openai_process: {str(e)}", exc_info=True)
#             if not hasattr(self, "_response_sent"):
#                 await self.process_response(
#                     "Lo siento, hubo un error procesando tu solicitud. ¿Podrías repetirla?"
#                 )

#     async def get_completion(
#         self,
#         messages: List[Dict[str, str]],
#         tool_choice: ToolChoiceType = ToolChoice.AUTO,
#         temperature: Optional[float] = None,
#         tools: Optional[List] = None,
#         model: Optional[str] = None,
#         max_tokens: Optional[int] = None,
#         log_context: bool = True,
#         situation: Optional[str] = "completion",
#     ) -> ChatCompletionMessage:
#         try:
#             if log_context:
#                 log_messages(
#                     messages,
#                     title=f"Context sent to OpenAI ({tool_choice}) from {situation}",
#                 )

#             create_params = {
#                 "messages": messages,
#                 "model": model or self.waba_conf.model,
#                 "temperature": temperature or self.waba_conf.temperature,
#             }

#             if max_tokens is not None:
#                 create_params["max_tokens"] = max_tokens

#             if tools or (tool_choice != ToolChoice.NONE and self.waba_conf.tools):
#                 create_params["tools"] = tools or self.waba_conf.tools
#                 create_params["tool_choice"] = tool_choice.value

#             api_response = await self.waba_conf.openai_client.chat.completions.create(
#                 **create_params
#             )

#             choice = api_response.choices[0]
#             assistant_msg = choice.message

#             if log_context:
#                 if assistant_msg.content:
#                     content = ". ".join(
#                         line.strip()
#                         for line in assistant_msg.content.splitlines()
#                         if line.strip()
#                     )
#                     content_preview = (
#                         content[:100] + "..." if len(content) > 100 else content
#                     )
#                     logger.info(f"OpenAI Response: {content_preview}")

#                 if assistant_msg.tool_calls:
#                     tool_calls_info = " | ".join(
#                         f"Function: {call.function.name}, args: {call.function.arguments.replace(chr(10), ' ')}"
#                         for call in assistant_msg.tool_calls
#                     )
#                     logger.info(
#                         f"Tool calls: {len(assistant_msg.tool_calls)} | {tool_calls_info}"
#                     )

#             return assistant_msg, choice

#         except Exception as e:
#             logger.error(f"Error getting completion from OpenAI: {str(e)}")
#             raise

#     async def _process_tool_calls(
#         self,
#         tool_calls: List,
#     ) -> Tuple[bool, List[Dict]]:
#         needs_follow_up = False
#         follow_up_instructions = []

#         # Mapa de prioridades basado en el flujo lógico de la conversación
#         priority_map = {
#             "get_course_details": 1,  # Primero info del curso
#             "get_course_price": 2,  # Luego el precio
#             "send_emprendemy_contact": 3,  # Después datos de contacto
#             "send_sign_up_message": 4,  # Luego link de inscripción
#             "send_conversation_to_supervisor": 5,  # Al final notificaciones a supervisor
#         }

#         # Ordenar tool_calls basado en prioridades
#         sorted_calls = sorted(
#             tool_calls,
#             key=lambda x: priority_map.get(
#                 x.function.name, 99
#             ),  # Funciones sin prioridad definida van al final
#         )

#         for tool_call in sorted_calls:
#             function_name = tool_call.function.name
#             function_args = json.loads(tool_call.function.arguments)

#             result = await self.functions_handler.execute_function(
#                 function_name,
#                 function_args,
#             )

#             if result.response_behavior == ResponseBehavior.REQUIRES_FOLLOW_UP:
#                 needs_follow_up = True
#                 follow_up_instructions.append(result.follow_up_instructions)
#                 logger.info(f"Function {function_name} requires follow up")

#         if needs_follow_up:
#             await self._handle_follow_up(follow_up_instructions)

#     async def _handle_follow_up(self, follow_up_instructions: List[str]) -> str:
#         try:
#             new_instructions = "\n\n".join(follow_up_instructions)

#             combined_instructions = {
#                 "role": "system",
#                 "content": "Dale continuidad a la conversacion"
#                 + BASE_INSTRUCTIONS
#                 + new_instructions,
#             }

#             messages = context.get_messages(self.waba_conf.waba_id, self.sender_phone)
#             context_messages = [combined_instructions] + messages

#             response, _ = await self.get_completion(
#                 context_messages,
#                 tool_choice=ToolChoice.NONE,
#                 situation="handle_follow_up",
#             )
#             answer = response.content
#             if answer:
#                 await self.process_response(
#                     to_send_message=answer,
#                 )
#                 return answer
#             return ""

#         except Exception as e:
#             logger.error(f"Error handling follow-up: {str(e)}")
#             raise

#     async def process_response(
#         self,
#         to_send_message: Union[str, None],
#         to_db_message: Union[str, None] = None,
#         to_db_role: MessageRole = MessageRole.ASSISTANT,
#         to_context_message: Union[str, None] = None,
#         to_context_role: MessageRole = MessageRole.ASSISTANT,
#     ) -> None:
#         if await message_buffer_manager.has_new_pending_messages(
#             self.buffer_key, self.current_processing_ids
#         ):
#             logger.info(
#                 f"Canceling response processing due to new pending messages for {self.sender_phone}"
#             )
#             return

#         # Send message to WhatsApp if provided
#         if to_send_message is not None:
#             await send_text_response_to_wa(
#                 to_send_message, self.sender_phone, self.waba_conf
#             )

#         # Save to DB if there's a message (either specific DB message or fallback to send message)
#         db_message = to_db_message if to_db_message is not None else to_send_message
#         if db_message is not None:
#             db.save_message(
#                 conversation_id=self.conversation_id,
#                 message_data={
#                     "message": {
#                         "id": str(uuid.uuid4()),
#                         "text": {"body": db_message},
#                     },
#                     "type": "text",
#                     "is_response": True,
#                 },
#             )

#         # Add to context if there's a message
#         context_message = (
#             to_context_message
#             if to_context_message is not None
#             else (db_message if db_message is not None else (to_send_message or ""))
#         )

#         context.add_message(
#             self.waba_conf.waba_id,
#             self.sender_phone,
#             to_context_role,
#             context_message,
#         )

#     async def categorize_messages(
#         self,
#         messages: List[Dict[str, Any]],
#     ) -> Optional[List[Tuple[MessageCategory, float]]]:
#         try:
#             categorization_prompt = CATEGORIZE_PROMPT.copy()

#             conversation_text = "\n".join(
#                 [f"{m['role']}: {m['content']}" for m in messages]
#             )

#             categorization_prompt.append(
#                 {"role": "user", "content": f"####\n{conversation_text}\n####"}
#             )
#             log_messages(categorization_prompt, "MENSAJES A LA CATEGORIZACION")

#             message, choice = await self.get_completion(
#                 messages=categorization_prompt,
#                 temperature=0,
#                 tool_choice=ToolChoice.NONE,
#                 max_tokens=50,
#                 log_context=False,
#                 situation="categorize_messages",
#             )

#             # Use the normalize function to get valid MessageCategory enums
#             categories = normalize_classification_response(message.content)
#             confidence = 1.0 if choice.finish_reason == "stop" else 0.8

#             # Categories are already MessageCategory enums, just pair them with confidence
#             return (
#                 [(category, confidence) for category in categories]
#                 if categories
#                 else None
#             )

#         except Exception as e:
#             logger.error(f"Error in categorize_messages: {str(e)}", exc_info=True)
#             return None
