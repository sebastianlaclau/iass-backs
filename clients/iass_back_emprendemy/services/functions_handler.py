# clients/iass_back_emprendemy/services/functions_handler.py
import logging
import json
from typing import Dict, Any

from core.services.functions_handler import FunctionsHandler as BaseFunctionsHandler
from core.models.enums import MessageRole, ResponseBehavior, ToolChoice
from core.models.responses import FunctionResponse

from ..constants import COURSES_INFO, PRICES_DATA, SUPERVISOR_NOTIFICATION_TYPE
from ..prompts import (
    PRICE_MESSAGE_TEMPLATE_PROMPT,
    COURSE_GENERAL_INFO_PROMPT,
    COURSE_SPECIFIC_DETAILS_PROMPT,
    COURSE_SEMANTIC_SEARCH_PROMPT,
)
from ..helpers import (
    generate_email_content,
    send_cta_to_signup,
    send_email,
    send_emprendemy_contact,
)
from core.utils.helpers import format_duration, format_searchable_fields

logger = logging.getLogger(__name__)


class FunctionsHandler(BaseFunctionsHandler):
    """Emprendemy-specific implementation of FunctionsHandler"""

    async def execute_function(
        self, name: str, args: Dict[str, Any]
    ) -> FunctionResponse:
        """Override to handle Emprendemy-specific functions"""
        try:
            if name == "get_course_price":
                return await self._handle_get_course_price(args)
            elif name == "get_course_details":
                return await self._handle_get_course_details(args)
            elif name == "send_emprendemy_contact":
                return await self._handle_send_contact(args)
            elif name == "send_sign_up_message":
                return await self._handle_send_sign_up(args)
            elif name == "send_conversation_to_supervisor":
                return await self._handle_send_conversation_to_supervisor(args)
            else:
                return await super().execute_function(name, args)
        except Exception as e:
            logger.error(f"Error executing function {name}: {str(e)}", exc_info=True)
            return FunctionResponse(
                success=False,
                data={},
                error=f"Error executing {name}: {str(e)}",
                response_behavior=ResponseBehavior.NO_FOLLOW_UP,
            )

    async def _handle_get_course_price(self, args: Dict[str, Any]) -> FunctionResponse:
        try:
            # Log function execution
            await self.save_function_execution_message("get_course_price", args)

            # Get country-specific pricing, default to OTHER if not found
            country = args.get("country_code", "").upper()
            if country not in PRICES_DATA:
                country = "OTHER"
            pricing = PRICES_DATA[country]

            # Create pricing prompt using context messages
            conversation_messages = self.service_container.context.get_messages(
                self.waba_conf.waba_id, self.sender_phone
            )

            price_message_context = [
                {
                    "role": "system",
                    "content": PRICE_MESSAGE_TEMPLATE_PROMPT.substitute(
                        symbol=pricing.symbol,
                        price=f"{pricing.price:,.0f}",
                        currency=pricing.currency,
                        final_price=f"{pricing.final_price:,.0f}",
                        messages=f"{conversation_messages}",
                    ),
                }
            ]

            # Generate natural pricing message
            message, _ = await self.openai_handler.get_completion(
                messages=price_message_context,
                temperature=0.1,
                tool_choice=ToolChoice.NONE,
                situation="handle_get_course_price",
            )

            if not message.content:
                return FunctionResponse(
                    success=False,
                    data={},
                    error="No message content generated",
                    response_behavior=ResponseBehavior.NO_FOLLOW_UP,
                )

            # Send response and update conversation context
            await self.openai_handler.process_response(
                to_send_message=message.content,
            )

            # Return success with follow-up context for conversation flow
            return FunctionResponse(
                success=True,
                data={},
                follow_up_instructions="IMPORTANTE: ya has enviado los precios",
                response_behavior=ResponseBehavior.REQUIRES_FOLLOW_UP,
            )

        except Exception as e:
            logger.error(f"Error in get_course_price: {str(e)}", exc_info=True)
            return FunctionResponse(
                success=False,
                data={},
                error=str(e),
                response_behavior=ResponseBehavior.NO_FOLLOW_UP,
            )

    async def _handle_get_course_details(
        self, args: Dict[str, Any]
    ) -> FunctionResponse:
        try:
            # Log function execution
            await self.save_function_execution_message("get_course_details", args)

            # Extract and validate basic parameters
            course_id = args.get("course_id")
            info_type = args.get("info_type", "brief")
            specific_info = args.get("specific_info", [])

            # Get course data - handle possible missing courses_cache
            course_data = None
            if (
                hasattr(self.service_container, "courses_cache")
                and self.service_container.courses_cache
            ):
                courses_cache = self.service_container.courses_cache
                course_data = courses_cache.get_course(
                    self.waba_conf.waba_id, course_id
                )
            else:
                # Fallback if courses_cache is not available
                from ..constants import COURSES_INFO

                course_data = COURSES_INFO.get(course_id, {})
                logger.warning(
                    f"Using fallback COURSES_INFO for {course_id} - courses_cache not available"
                )

            if not course_data:
                return FunctionResponse(
                    success=False,
                    data={},
                    error="Course not found",
                    response_behavior=ResponseBehavior.NO_FOLLOW_UP,
                )

            conversation_messages = self.service_container.context.get_messages(
                self.waba_conf.waba_id, self.sender_phone
            )

            to_send_message = None

            # Process based on information type
            if info_type == "general":
                instructions = [
                    {
                        "role": "system",
                        "content": COURSE_GENERAL_INFO_PROMPT.substitute(
                            course_title=course_data["title"],
                            selling_description=course_data.get(
                                "selling_description", ""
                            ),
                            messages="\n".join(
                                [
                                    f"{m['role']}: {m['content']}"
                                    for m in conversation_messages
                                ]
                            ),
                        ),
                    }
                ]

                response, _ = await self.openai_handler.get_completion(
                    messages=instructions,
                    temperature=0.3,
                    tool_choice=ToolChoice.NONE,
                    situation="handle_get_course_details_general",
                )

                to_send_message = response.content

            elif info_type == "specific":
                # Get and format specific requested fields
                specific_data = {k: course_data.get(k, "") for k in specific_info}

                # Special formatting for duration field if present
                if "duration" in specific_info:
                    duration = specific_data.get("duration")
                    specific_data["duration"] = format_duration(duration)

                # Prepare data for prompt
                formatted_course_data = json.dumps(
                    specific_data, indent=2, ensure_ascii=False
                )

                instructions_with_conversation_messages = [
                    {
                        "role": "system",
                        "content": COURSE_SPECIFIC_DETAILS_PROMPT.substitute(
                            course_data=formatted_course_data,
                            messages=conversation_messages,
                        ),
                    }
                ]

                response, _ = await self.openai_handler.get_completion(
                    messages=instructions_with_conversation_messages,
                    temperature=0.2,
                    tool_choice=ToolChoice.NONE,
                    situation="handle_get_course_details",
                )
                to_send_message = response.content

            elif info_type == "semantic":
                searchable_fields = [
                    "description",
                    "units",
                    "objectives",
                    "requirements",
                    "selling_description",
                ]
                searcheable_content = " ".join(
                    format_searchable_fields(course_data.get(field, ""))
                    for field in searchable_fields
                )

                search_prompt = [
                    {
                        "role": "system",
                        "content": COURSE_SEMANTIC_SEARCH_PROMPT.substitute(
                            course_title=course_data["title"],
                            course_content=searcheable_content,
                            messages=conversation_messages,
                        ),
                    }
                ]

                message, _ = await self.openai_handler.get_completion(
                    messages=search_prompt,
                    temperature=0.3,
                    tool_choice=ToolChoice.NONE,
                    situation="handle_get_course_details",
                )

                to_send_message = message.content

            # Process and send response if content was generated
            if to_send_message:
                await self.openai_handler.process_response(
                    to_send_message=to_send_message,
                )

                return FunctionResponse(
                    success=True,
                    data={},
                    follow_up_instructions="IMPORTANTE: la consulta sobre el curso ya ha sido contestada",
                    response_behavior=ResponseBehavior.REQUIRES_FOLLOW_UP,
                )

            return FunctionResponse(
                success=False,
                data={},
                error="No response generated for course details",
                response_behavior=ResponseBehavior.NO_FOLLOW_UP,
            )

        except Exception as e:
            logger.error(
                f"Error in _handle_get_course_details: {str(e)}", exc_info=True
            )
            return FunctionResponse(
                success=False,
                data={},
                error=str(e),
                response_behavior=ResponseBehavior.NO_FOLLOW_UP,
            )

    async def _handle_send_contact(self, args: Dict[str, Any]) -> FunctionResponse:
        try:
            # Log function execution
            await self.save_function_execution_message(
                "enviar contacto de emprendemy", args
            )

            # Send contact (atomic action)
            await send_emprendemy_contact(self.sender_phone, self.waba_conf)

            await self.openai_handler.process_response(
                to_send_message=None,
                to_context_message="Mensaje de Whatsapp con contacto de Emprendemy enviado.",
                to_context_role=MessageRole.SYSTEM,
            )

            return FunctionResponse(
                success=True,
                data={},
                follow_up_instructions="IMPORTANTE: YA HAS ENVIADO EL CONTACTO PEDIDO.",
                response_behavior=ResponseBehavior.REQUIRES_FOLLOW_UP,
            )

        except Exception as e:
            logger.error(f"Error in send_contact: {str(e)}", exc_info=True)
            return FunctionResponse(
                success=False,
                data={},
                error=str(e),
                response_behavior=ResponseBehavior.NO_FOLLOW_UP,
            )

    async def _handle_send_sign_up(self, args: Dict[str, Any]) -> FunctionResponse:
        try:
            # Log function execution
            await self.save_function_execution_message("send_cta_to_signup", args)

            # Get course information
            course_id = args.get("course_id")
            course_info = COURSES_INFO.get(course_id, {})

            if not course_info:
                logger.error(f"Course info not found for ID: {course_id}")
                return FunctionResponse(
                    success=False,
                    data={},
                    error="Course not found",
                    response_behavior=ResponseBehavior.NO_FOLLOW_UP,
                )

            # Send CTA (atomic action)
            await send_cta_to_signup(
                waba_conf=self.waba_conf,
                to=self.sender_phone,
                curso=course_info["name"],
                url_compra=course_info["url"],
                catchy_phrase=args.get("catchy_phrase", "Tremendo curso!"),
                descuento="55%",
            )

            await self.openai_handler.process_response(
                to_send_message=None,
                to_context_message=f"Se envió link de inscripción para el curso '{course_info['name']}'",
                to_context_role=MessageRole.SYSTEM,
            )

            return FunctionResponse(
                success=True,
                data={},
                follow_up_instructions="IMPORTANTE: YA HAS ENVIADO EL LINK DE INSCRIPCION.",
                response_behavior=ResponseBehavior.REQUIRES_FOLLOW_UP,
            )

        except Exception as e:
            logger.error(f"Error in send_cta: {str(e)}", exc_info=True)
            return FunctionResponse(
                success=False,
                data={},
                error=str(e),
                response_behavior=ResponseBehavior.NO_FOLLOW_UP,
            )

    async def _handle_send_conversation_to_supervisor(
        self, args: Dict[str, Any]
    ) -> FunctionResponse:
        try:
            # Log function execution
            await self.save_function_execution_message(
                "send_conversation_to_supervisor", args
            )

            # Validate notification type
            notification_type = args.get("notification_type")
            if notification_type not in SUPERVISOR_NOTIFICATION_TYPE:
                return FunctionResponse(
                    success=False,
                    data={},
                    error=f"Invalid notification type: {notification_type}",
                    response_behavior=ResponseBehavior.NO_FOLLOW_UP,
                )

            info = SUPERVISOR_NOTIFICATION_TYPE[notification_type]

            # Get conversation messages
            conversation_messages = self.service_container.context.get_messages(
                self.waba_conf.waba_id, self.sender_phone
            )

            # Get client config from config manager
            from core.config import config_manager

            client_config = config_manager.get_client_config(self.client_id)

            # Generate and send email
            html_content = generate_email_content(
                conversation_history=conversation_messages,
                sender_phone=self.sender_phone,
                notification_type=notification_type,
                info=info,
                waba_conf=self.waba_conf,
            )

            send_email(
                subject=f"{info['subject_prefix']} - Usuario {self.sender_phone[-4:]}",
                html_content=html_content,
                client_config=client_config,
            )

            await self.openai_handler.process_response(
                to_send_message=None,
                to_context_message=f"Se envio mail al supervisor sobre {notification_type}",
                to_context_role=MessageRole.SYSTEM,
            )

            return FunctionResponse(
                success=True,
                data={},
                follow_up_instructions="IMPORTANTE: EL MAIL SE HA ENVIADO, MENCIONALO",
                response_behavior=ResponseBehavior.REQUIRES_FOLLOW_UP,
            )

        except Exception as e:
            logger.error(f"Error in supervisor notification: {str(e)}", exc_info=True)
            return FunctionResponse(
                success=False,
                data={},
                error=str(e),
                response_behavior=ResponseBehavior.NO_FOLLOW_UP,
            )


# GUARDO ACA EL HANDLER VIEJO PORQUE TIENE MUCHA LOGICA QUE TIENE QEU VER CON EL PRODUCTO DE EMPRENDEMY, HASTA QUE HAGA FUNCIONAR BIEN ESTA NUEVA VERSION

# import logging
# import json
# from typing import Dict, Any
# import uuid
# from fastapi import APIRouter
# from .constants import COURSES_INFO, PRICES_DATA, SUPERVISOR_NOTIFICATION_TYPE
# from .prompts import (
#     CATEGORIZE_PROMPT,
#     COURSE_SPECIFIC_DETAILS_PROMPT,
#     PRICE_MESSAGE_TEMPLATE_PROMPT,
#     COURSE_GENERAL_INFO_PROMPT,
#     COURSE_SEMANTIC_SEARCH_PROMPT,
# )
# from .helpers import (
#     generate_email_content,
#     send_cta_to_signup,
#     send_email,
#     send_emprendemy_contact,
# )
# from core.utils.helpers import (
#     WABAConfig,
#     format_duration,
#     format_searchable_fields,
# )
# from core.services.openai import OpenAIHandler

# from core.models.enums import MessageRole, ResponseBehavior, ToolChoice
# from core.models.responses import FunctionResponse
# from core.storage.cache import MessageBufferManager

# logger = logging.getLogger(__name__)

# router = APIRouter()


# class FunctionsHandler:
#     def __init__(
#         self,
#         client_id: str,  # Add this parameter
#         waba_conf: WABAConfig,
#         sender_phone: str,
#         openai_handler: OpenAIHandler,
#         message_buffer_manager: MessageBufferManager,
#     ):
#         self.waba_conf = waba_conf
#         self.sender_phone = sender_phone
#         self.message_buffer_manager = message_buffer_manager
#         self.openai_handler = openai_handler
#         self.conversation_id = openai_handler.conversation_id
#         self.client_id = client_id

#     async def execute_function(
#         self,
#         name: str,
#         args: Dict[str, Any],
#     ) -> FunctionResponse:
#         try:
#             if name == "get_course_price":
#                 return await self._handle_get_course_price(args)
#             elif name == "get_course_details":
#                 return await self._handle_get_course_details(args)
#             elif name == "send_emprendemy_contact":
#                 return await self._handle_send_contact(args)
#             elif name == "send_sign_up_message":
#                 return await self._handle_send_sign_up(args)
#             elif name == "send_conversation_to_supervisor":
#                 return await self._handle_send_conversation_to_supervisor(args)
#             else:
#                 return FunctionResponse(
#                     success=False,
#                     data={},
#                     error=f"Unknown function: {name}",
#                     response_behavior=ResponseBehavior.NO_FOLLOW_UP,
#                 )
#         except Exception as e:
#             logger.error(f"Error executing function {name}: {str(e)}", exc_info=True)
#             return FunctionResponse(
#                 success=False,
#                 data={},
#                 error=f"Error executing {name}: {str(e)}",
#                 response_behavior=ResponseBehavior.NO_FOLLOW_UP,
#             )

#     async def save_function_execution_message(
#         self, function_name: str, args: Dict[str, Any]
#     ) -> None:
#         """Save function execution log to database"""
#         args_msg = "\n".join(f" - {k}: {v}" for k, v in args.items())
#         message_body = f"Funcion ejecutada: {function_name}\n{args_msg}"

#         db.save_message(
#             conversation_id=self.conversation_id,
#             message_data={
#                 "message": {
#                     "id": str(uuid.uuid4()),
#                     "text": {"body": message_body},
#                 },
#                 "type": "system",
#                 "is_response": True,
#             },
#         )

#     async def _handle_get_course_price(
#         self,
#         args: Dict[str, Any],
#     ) -> FunctionResponse:
#         try:
#             # Log function execution
#             await self.save_function_execution_message("get_course_price", args)

#             # Get country-specific pricing, default to OTHER if not found
#             country = args.get("country_code", "").upper()
#             if country not in PRICES_DATA:
#                 country = "OTHER"
#             pricing = PRICES_DATA[country]

#             # Create pricing prompt using context messages
#             conversation_messages = context.get_messages(
#                 self.waba_conf.waba_id, self.sender_phone
#             )

#             price_message_context = [
#                 {
#                     "role": "system",
#                     "content": PRICE_MESSAGE_TEMPLATE_PROMPT.substitute(
#                         symbol=pricing.symbol,
#                         price=f"{pricing.price:,.0f}",
#                         currency=pricing.currency,
#                         final_price=f"{pricing.final_price:,.0f}",
#                         messages=f"{conversation_messages}",
#                     ),
#                 }
#             ]

#             # Generate natural pricing message
#             message, _ = await self.openai_handler.get_completion(
#                 messages=price_message_context,
#                 temperature=0.1,
#                 tool_choice=ToolChoice.NONE,
#                 situation="handle_get_course_price",
#             )

#             if not message.content:
#                 return FunctionResponse(
#                     success=False,
#                     data={},
#                     error="No message content generated",
#                     response_behavior=ResponseBehavior.NO_FOLLOW_UP,
#                 )

#             # Send response and update conversation context
#             await self.openai_handler.process_response(
#                 to_send_message=message.content,
#             )

#             # Return success with follow-up context for conversation flow
#             return FunctionResponse(
#                 success=True,
#                 data={},
#                 # follow_up_instructions=FOLLOW_UP_PRICES_PARTIAL_PROMPT,
#                 follow_up_instructions="IMPORTANTE: ya has enviado los precios",
#                 response_behavior=ResponseBehavior.REQUIRES_FOLLOW_UP,
#             )

#         except Exception as e:
#             logger.error(f"Error in get_course_price: {str(e)}", exc_info=True)
#             return FunctionResponse(
#                 success=False,
#                 data={},
#                 error=str(e),
#                 response_behavior=ResponseBehavior.NO_FOLLOW_UP,
#             )

#     async def _handle_get_course_details(
#         self,
#         args: Dict[str, Any],
#     ) -> FunctionResponse:
#         try:
#             # Registrar la ejecución de la función
#             await self.save_function_execution_message("get_course_details", args)

#             # Extraer y validar parámetros básicos
#             course_id = args.get("course_id")
#             info_type = args.get("info_type", "brief")
#             specific_info = args.get("specific_info", [])
#             course_data = courses_cache.get_course(self.waba_conf.waba_id, course_id)

#             if not course_data:
#                 return FunctionResponse(
#                     success=False,
#                     data={},
#                     error="Course not found",
#                     response_behavior=ResponseBehavior.NO_FOLLOW_UP,
#                 )

#             conversation_messages = context.get_messages(
#                 self.waba_conf.waba_id, self.sender_phone
#             )

#             to_send_message = None

#             # Procesar según el tipo de información solicitada
#             if info_type == "general":
#                 # to_send_message = course_data.get("selling_description", "")

#                 # Nuevo manejo para información general
#                 instructions = [
#                     {
#                         "role": "system",
#                         "content": COURSE_GENERAL_INFO_PROMPT.substitute(
#                             course_title=course_data["title"],
#                             selling_description=course_data.get(
#                                 "selling_description", ""
#                             ),
#                             messages="\n".join(
#                                 [
#                                     f"{m['role']}: {m['content']}"
#                                     for m in conversation_messages
#                                 ]
#                             ),
#                         ),
#                     }
#                 ]

#                 response, _ = await self.openai_handler.get_completion(
#                     messages=instructions,
#                     temperature=0.3,
#                     tool_choice=ToolChoice.NONE,
#                     situation="handle_get_course_details_general",
#                 )

#                 to_send_message = response.content

#             elif info_type == "specific":
#                 # Obtener y formatear campos específicos solicitados
#                 specific_data = {k: course_data.get(k, "") for k in specific_info}

#                 # Formateo especial para el campo duration si está presente
#                 if "duration" in specific_info:
#                     duration = specific_data.get("duration")
#                     specific_data["duration"] = format_duration(duration)

#                 # Preparar datos para el prompt
#                 formatted_course_data = json.dumps(
#                     specific_data, indent=2, ensure_ascii=False
#                 )

#                 instructions_with_conversation_messages = [
#                     {
#                         "role": "system",
#                         "content": COURSE_SPECIFIC_DETAILS_PROMPT.substitute(
#                             # course_title=course_data["title"],
#                             # specific_info=", ".join(specific_info),
#                             course_data=formatted_course_data,
#                             messages=conversation_messages,
#                         ),
#                     }
#                 ]

#                 # course_specifics_prompt = [instructions_with_conversation_messages] + conversation_messages

#                 # Obtener respuesta de OpenAI
#                 response, _ = await self.openai_handler.get_completion(
#                     # messages=course_specifics_prompt,
#                     messages=instructions_with_conversation_messages,
#                     temperature=0.2,
#                     tool_choice=ToolChoice.NONE,
#                     situation="handle_get_course_details",
#                 )
#                 answer = response.content

#                 if answer:
#                     to_send_message = answer

#             elif info_type == "semantic":
#                 # Búsqueda semántica en el contenido del curso
#                 # query = args.get("query", "")
#                 searchable_fields = [
#                     "description",
#                     "units",
#                     "objectives",
#                     "requirements",
#                     "selling_description",
#                 ]
#                 # Concatenar todos los campos de búsqueda
#                 searcheable_content = " ".join(
#                     format_searchable_fields(course_data.get(field, ""))
#                     for field in searchable_fields
#                 )

#                 search_prompt = [
#                     {
#                         "role": "system",
#                         "content": COURSE_SEMANTIC_SEARCH_PROMPT.substitute(
#                             course_title=course_data["title"],
#                             course_content=searcheable_content,
#                             messages=conversation_messages,
#                             # query=query,
#                         ),
#                     }
#                 ]
#                 # + conversation_messages

#                 # Obtener respuesta de OpenAI
#                 message, _ = await self.openai_handler.get_completion(
#                     messages=search_prompt,
#                     temperature=0.3,
#                     tool_choice=ToolChoice.NONE,
#                     situation="handle_get_course_details",
#                 )

#                 answer = message.content

#                 if answer:
#                     to_send_message = answer

#             # Procesar y enviar respuesta si se generó contenido
#             if to_send_message:
#                 await self.openai_handler.process_response(
#                     to_send_message=to_send_message,
#                 )

#                 return FunctionResponse(
#                     success=True,
#                     data={},
#                     follow_up_instructions="IMPORTANTE: la consulta sobre el curso ya ha sido contestada",
#                     response_behavior=ResponseBehavior.REQUIRES_FOLLOW_UP,
#                 )

#         except Exception as e:
#             logger.error(
#                 f"Error in _handle_get_course_details: {str(e)}", exc_info=True
#             )
#             return FunctionResponse(
#                 success=False,
#                 data={},
#                 error=str(e),
#                 response_behavior=ResponseBehavior.NO_FOLLOW_UP,
#             )

#     async def _handle_send_contact(
#         self,
#         args: Dict[str, Any],
#     ) -> FunctionResponse:
#         try:
#             # Registrar la ejecución de la función
#             await self.save_function_execution_message(
#                 "enviar contacto de emprendemy", args
#             )

#             # Enviar el contacto (acción atómica)
#             await send_emprendemy_contact(self.sender_phone, self.waba_conf)

#             await self.openai_handler.process_response(
#                 to_send_message=None,
#                 to_context_message="Mensaje de Whatsapp con contacto de Emprendemy enviado.",
#                 to_context_role=MessageRole.SYSTEM,
#             )

#             return FunctionResponse(
#                 success=True,
#                 follow_up_instructions="IMPORTANTE: YA HAS ENVIADO EL CONTACTO PEDIDO.",
#                 response_behavior=ResponseBehavior.REQUIRES_FOLLOW_UP,
#             )

#         except Exception as e:
#             logger.error(f"Error in send_contact: {str(e)}", exc_info=True)
#             return FunctionResponse(
#                 success=False,
#                 data={},
#                 error=str(e),
#                 response_behavior=ResponseBehavior.NO_FOLLOW_UP,
#             )

#     async def _handle_send_sign_up(self, args: Dict[str, Any]) -> FunctionResponse:
#         try:
#             # Registrar la ejecución de la función
#             await self.save_function_execution_message("send_cta_to_signup", args)

#             # Obtener información del curso
#             course_id = args.get("course_id")
#             course_info = COURSES_INFO.get(course_id, {})

#             if not course_info:
#                 logger.error(f"Course info not found for ID: {course_id}")
#                 return FunctionResponse(
#                     success=False,
#                     data={},
#                     error="Course not found",
#                     response_behavior=ResponseBehavior.NO_FOLLOW_UP,
#                 )

#             # Enviar CTA (acción atómica)
#             await send_cta_to_signup(
#                 waba_conf=self.waba_conf,
#                 to=self.sender_phone,
#                 curso=course_info["name"],
#                 url_compra=course_info["url"],
#                 catchy_phrase=args.get("catchy_phrase", "Tremendo curso!"),
#                 descuento="55%",
#             )

#             await self.openai_handler.process_response(
#                 to_send_message=None,
#                 to_context_message=f"Se envió link de inscripción para el curso '{course_info['name']}'",
#                 to_context_role=MessageRole.SYSTEM,
#             )

#             return FunctionResponse(
#                 success=True,
#                 follow_up_instructions="IMPORTANTE: YA HAS ENVIADO EL LINK DE INSCRIPCION.",
#                 response_behavior=ResponseBehavior.REQUIRES_FOLLOW_UP,
#             )

#         except Exception as e:
#             logger.error(f"Error in send_cta: {str(e)}", exc_info=True)
#             return FunctionResponse(
#                 success=False,
#                 data={},
#                 error=str(e),
#                 response_behavior=ResponseBehavior.NO_FOLLOW_UP,
#             )

#     async def _handle_send_conversation_to_supervisor(
#         self,
#         args: Dict[str, Any],
#     ) -> FunctionResponse:
#         try:
#             # Registrar la ejecución de la función
#             await self.save_function_execution_message(
#                 "send_conversation_to_supervisor", args
#             )

#             # Validar tipo de notificación
#             notification_type = args.get("notification_type")
#             if notification_type not in SUPERVISOR_NOTIFICATION_TYPE:
#                 return FunctionResponse(
#                     success=False,
#                     data={},
#                     error=f"Invalid notification type: {notification_type}",
#                     response_behavior=ResponseBehavior.NO_FOLLOW_UP,
#                 )

#             info = SUPERVISOR_NOTIFICATION_TYPE[notification_type]

#             # Obtener mensajes de la conversación
#             conversation_messages = context.get_messages(
#                 self.waba_conf.waba_id, self.sender_phone
#             )

#             # Get client config from config manager
#             from core.config import config_manager

#             client_id = (
#                 self.openai_handler.client_id
#             )  # You'll need to add this attribute
#             client_config = config_manager.get_client_config(client_id)

#             # Generar y enviar email
#             html_content = generate_email_content(
#                 conversation_history=conversation_messages,
#                 sender_phone=self.sender_phone,
#                 notification_type=notification_type,
#                 info=info,
#                 waba_conf=self.waba_conf,
#             )

#             send_email(
#                 subject=f"{info['subject_prefix']} - Usuario {self.sender_phone[-4:]}",
#                 html_content=html_content,
#                 client_config=client_config,  # Pass client_config instead of settings
#             )

#             await self.openai_handler.process_response(
#                 to_send_message=None,
#                 to_context_message=f"Se envio mail al supervisor sobre {notification_type}",
#                 to_context_role=MessageRole.SYSTEM,
#             )

#             return FunctionResponse(
#                 success=True,
#                 follow_up_instructions="IMPORTANTE: EL MAIL SE HA ENVIADO, MENCIONALO",
#                 response_behavior=ResponseBehavior.REQUIRES_FOLLOW_UP,
#             )

#         except Exception as e:
#             logger.error(f"Error in supervisor notification: {str(e)}", exc_info=True)
#             return FunctionResponse(
#                 success=False,
#                 data={},
#                 error=str(e),
#                 response_behavior=ResponseBehavior.NO_FOLLOW_UP,
#             )
