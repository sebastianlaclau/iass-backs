# clients/iass-back-emprendemy/webhook.py
import httpx
import html
import asyncio
from dataclasses import dataclass, field
import logging
import json
import smtplib
from typing import Dict, Any, List, Optional, Literal, Union, Tuple, Set
from string import Template

import uuid
from fastapi import APIRouter, Request, BackgroundTasks, Response, HTTPException
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime, timedelta, timezone
from enum import Enum
from cachetools import TTLCache
from openai.types.chat import ChatCompletionMessage
from pydantic import BaseModel
import os
import traceback
from .constants import COURSES_INFO, PRICES_DATA, SUPERVISOR_NOTIFICATION_TYPE
from .prompts import (
    CATEGORIZE_PROMPT,
    COURSE_SPECIFIC_DETAILS_PROMPT,
    PRICE_MESSAGE_TEMPLATE_PROMPT,
    COURSE_GENERAL_INFO_PROMPT,
    COURSE_SEMANTIC_SEARCH_PROMPT,
)
from .helpers import (
    generate_email_content,
    send_cta_to_signup,
    send_email,
    send_emprendemy_contact,
)

from core.services.whatsapp import (
    send_text_response_to_wa,
)

# from core.services.openai import convert_audio_to_text
# from core.services.supabase import upload_to_supabase_audio_bucket
# from core.utils.blocked_numbers import is_number_blocked
from core.utils.helpers import (
    WABAConfig,
    InstructionsStrategy,
    format_duration,
    format_searchable_fields,
)
from core.utils.supabase_client import supabase
from core.services.openai import OpenAIHandler

from core.data.prompts import BASE_INSTRUCTIONS
from core.models.enums import MessageCategory, MessageRole, ResponseBehavior, ToolChoice
from core.models.responses import FunctionResponse
from core.models.tool import ToolChoiceType
from core.storage.cache import MessageBufferManager
from core.utils.helpers import log_messages, normalize_classification_response


logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

router = APIRouter()

SMTP_PORT = 465  # Explicitly set port for SSL


db = None
message_buffer_manager = None
context = None
courses_cache = None
instructions_cache = None


# ------------------------------------------------------------------------
# MANAGES EMPRENDEMY DATA (esto es para Emprendemy exclusivamente)
# ------------------------------------------------------------------------


@router.get("/wabas/{waba_id}/settings")
async def get_settings(waba_id: str):
    try:
        response = (
            supabase.table("empre_settings")
            .select("*")
            .eq("waba_id", waba_id)
            .order("created_at", desc=True)
            .limit(1)
            .execute()
        )
        return response.data[0] if response.data else {"instructions": ""}
    except Exception as e:
        print(f"Error getting settings: {e}")
        return {"instructions": ""}


@router.post("/wabas/{waba_id}/settings")
async def update_waba_settings(waba_id: str, settings: dict) -> dict:
    try:
        data = {"waba_id": waba_id, "instructions": settings.get("instructions", "")}
        response = supabase.table("empre_settings").insert(data).execute()
        await instructions_cache.update_instructions(
            waba_id, settings.get("instructions", "")
        )
        return {"status": "success", "data": response.data[0]}
    except Exception as e:
        print(f"Error updating settings: {str(e)}")
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/wabas/{waba_id}/courses")
async def get_courses(waba_id: str):
    try:
        cached_courses = courses_cache.get_courses(waba_id)
        if cached_courses:
            # Ensure consistent format when returning from cache
            return [
                {
                    "course_id": cid,
                    "title": data.get("title"),
                    "instructor": data.get("instructor"),
                }
                for cid, data in cached_courses.items()
            ]

        response = (
            supabase.table("empre_courses")
            .select("course_id, title, instructor")
            .eq("waba_id", waba_id)
            .execute()
        )
        return response.data
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/wabas/{waba_id}/courses")
async def create_course(waba_id: str, course_data: dict):
    try:
        if "course_id" not in course_data:
            course_id = str(uuid.uuid4())[:8]
            course_data["course_id"] = course_id

        course_data["waba_id"] = waba_id

        duration = course_data.get("duration")
        if duration is not None:
            try:
                duration = int(duration)
                if duration > 2147483647:
                    duration = 2147483647
                elif duration < -2147483648:
                    duration = -2147483648
            except (ValueError, TypeError):
                duration = None

        clean_data = {
            "course_id": course_data["course_id"],
            "waba_id": waba_id,
            "title": str(course_data.get("title", "")),
            "brief": str(course_data.get("brief", "")),
            "preview": str(course_data.get("preview", "")),
            "duration": course_data.get("duration"),
            "instructor": str(course_data.get("instructor", "")),
            "instructor_bio": str(course_data.get("instructor_bio", "")),
            "description": str(course_data.get("description", "")),
            "selling_description": str(course_data.get("selling_description", "")),
            "requirements": str(course_data.get("requirements", "")),
            "learning_objectives": json.dumps(
                course_data.get("learning_objectives", [])
            ),
            "reviews": json.dumps(course_data.get("reviews", [])),
            "units": json.dumps(course_data.get("units", [])),
        }

        print("Cleaned data:", clean_data)

        response = supabase.table("empre_courses").insert(clean_data).execute()
        print("Supabase response:", response)

        courses_cache.update_course(waba_id, clean_data["course_id"], clean_data)

        return response.data[0]
    except Exception as e:
        print(f"Error creating course: {str(e)}")
        print(f"Error type: {type(e)}")
        traceback.print_exc()
        raise HTTPException(
            status_code=500, detail=f"Failed to create course: {str(e)}"
        )


@router.get("/wabas/{waba_id}/courses/{course_id}")
async def get_course(waba_id: str, course_id: str):
    try:
        # Validate inputs
        if not waba_id or not course_id or course_id == "undefined":
            raise HTTPException(status_code=400, detail="Invalid waba_id or course_id")

        response = (
            supabase.table("empre_courses")
            .select("*")
            .eq("waba_id", waba_id)
            .eq("course_id", course_id)
            .single()
            .execute()
        )

        if not response.data:
            raise HTTPException(status_code=404, detail="Course not found")

        return response.data
    except Exception as e:
        print(f"Error getting course: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/wabas/{waba_id}/courses/{course_id}")
async def update_course(waba_id: str, course_id: str, course_data: dict):
    try:
        update_data = {
            "title": course_data.get("title"),
            "brief": course_data.get("brief"),
            "preview": course_data.get("preview"),
            "duration": course_data.get("duration"),
            "instructor": course_data.get("instructor"),
            "instructor_bio": course_data.get("instructor_bio"),
            "description": course_data.get("description"),
            "selling_description": course_data.get("selling_description"),
            "requirements": course_data.get("requirements"),
            "learning_objectives": course_data.get("learning_objectives"),
            "reviews": course_data.get("reviews"),
            "units": course_data.get("units"),
            "waba_id": waba_id,
        }

        clean_data = {k: v for k, v in update_data.items() if v is not None}

        response = (
            supabase.table("empre_courses")
            .update(clean_data)
            .eq("waba_id", waba_id)
            .eq("course_id", course_id)
            .execute()
        )

        courses_cache.update_course(waba_id, course_id, clean_data)

        return response.data[0]
    except Exception as e:
        print(f"Error updating course: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/wabas/{waba_id}/courses/{course_id}")
async def delete_course(waba_id: str, course_id: str):
    try:
        print(f"Deleting course {course_id} from WABA {waba_id}")

        response = (
            supabase.table("empre_courses")
            .delete()
            .eq("waba_id", waba_id)
            .eq("course_id", course_id)
            .execute()
        )

        # Also remove from cache
        courses_cache.delete_course(waba_id, course_id)

        return {"status": "success", "message": f"Course {course_id} deleted"}
    except Exception as e:
        print(f"Error deleting course: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


class InstructionsCache:
    def __init__(self):
        self._cache = {}  # waba_id -> instructions mapping
        self.initialize_cache()

    def initialize_cache(self):
        """Load all WABA instructions when server starts"""
        try:
            response = supabase.table("empre_settings").select("*").execute()
            for record in response.data:
                self._cache[record["waba_id"]] = record["instructions"]
            logger.info(f"Initialized instructions cache for {len(self._cache)} WABAs")
        except Exception as e:
            logger.error(f"Error initializing instructions cache: {e}")

    def get_instructions(self, waba_id: str) -> str:
        """Get cached instructions for a WABA"""
        return self._cache.get(waba_id, "")

    async def update_instructions(self, waba_id: str, instructions: str):
        """Update cache when instructions are updated in DB"""
        self._cache[waba_id] = instructions
        logger.info(f"Updated cache for WABA {waba_id}")


class CoursesCache:
    def __init__(self):
        self._cache = {}  # waba_id -> {course_id -> content} mapping
        self.initialize_cache()

    def initialize_cache(self):
        """Load all courses grouped by waba_id"""
        try:
            response = supabase.table("empre_courses").select("*").execute()
            for record in response.data:
                waba_id = record["waba_id"]
                course_id = record["course_id"]

                # Initialize waba_id dict if not exists
                if waba_id not in self._cache:
                    self._cache[waba_id] = {}

                self._cache[waba_id][course_id] = {
                    "id": course_id,
                    "title": record["title"],
                    "brief": record["brief"],
                    "preview": record["preview"],
                    "duration": record["duration"],
                    "instructor": record["instructor"],
                    "instructor_bio": record["instructor_bio"],
                    "description": record["description"],
                    "requirements": record["requirements"],
                    "learning_objectives": record["learning_objectives"],
                    "reviews": record["reviews"],
                    "units": record["units"],
                    "selling_description": record[
                        "selling_description"
                    ],  # Agregar este campo
                }
            logger.info(f"Initialized courses cache for {len(self._cache)} WABAs")
        except Exception as e:
            logger.error(f"Error initializing courses cache: {e}")

    def refresh_cache(self):
        """Reload all cache data from DB"""
        self._cache = {}
        self.initialize_cache()

    def get_courses(self, waba_id: str, force_refresh: bool = False) -> dict:
        """Get all cached courses for a WABA"""
        if force_refresh:
            self.refresh_cache()
        return self._cache.get(waba_id, {})

    def get_course(
        self, waba_id: str, course_id: str, force_refresh: bool = False
    ) -> dict:
        """Get specific course from cache"""
        if force_refresh:
            self.refresh_cache()
        return self._cache.get(waba_id, {}).get(course_id, {})

    def update_course(self, waba_id: str, course_id: str, content: dict):
        """Update cache when course is updated"""
        if waba_id not in self._cache:
            self._cache[waba_id] = {}
        self._cache[waba_id][course_id] = content
        logger.info(f"Updated cache for course {course_id} in WABA {waba_id}")

    def delete_course(self, waba_id: str, course_id: str):
        """Remove course from cache"""
        if waba_id in self._cache and course_id in self._cache[waba_id]:
            del self._cache[waba_id][course_id]
            logger.info(f"Deleted course {course_id} from WABA {waba_id} cache")


class FunctionsHandler:
    def __init__(
        self,
        client_id: str,  # Add this parameter
        waba_conf: WABAConfig,
        sender_phone: str,
        openai_handler: OpenAIHandler,
        message_buffer_manager: MessageBufferManager,
    ):
        self.waba_conf = waba_conf
        self.sender_phone = sender_phone
        self.message_buffer_manager = message_buffer_manager
        self.openai_handler = openai_handler
        self.conversation_id = openai_handler.conversation_id
        self.client_id = client_id

    async def execute_function(
        self,
        name: str,
        args: Dict[str, Any],
    ) -> FunctionResponse:
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
                return FunctionResponse(
                    success=False,
                    data={},
                    error=f"Unknown function: {name}",
                    response_behavior=ResponseBehavior.NO_FOLLOW_UP,
                )
        except Exception as e:
            logger.error(f"Error executing function {name}: {str(e)}", exc_info=True)
            return FunctionResponse(
                success=False,
                data={},
                error=f"Error executing {name}: {str(e)}",
                response_behavior=ResponseBehavior.NO_FOLLOW_UP,
            )

    async def save_function_execution_message(
        self, function_name: str, args: Dict[str, Any]
    ) -> None:
        """Save function execution log to database"""
        args_msg = "\n".join(f" - {k}: {v}" for k, v in args.items())
        message_body = f"Funcion ejecutada: {function_name}\n{args_msg}"

        db.save_message(
            conversation_id=self.conversation_id,
            message_data={
                "message": {
                    "id": str(uuid.uuid4()),
                    "text": {"body": message_body},
                },
                "type": "system",
                "is_response": True,
            },
        )

    async def _handle_get_course_price(
        self,
        args: Dict[str, Any],
    ) -> FunctionResponse:
        try:
            # Log function execution
            await self.save_function_execution_message("get_course_price", args)

            # Get country-specific pricing, default to OTHER if not found
            country = args.get("country_code", "").upper()
            if country not in PRICES_DATA:
                country = "OTHER"
            pricing = PRICES_DATA[country]

            # Create pricing prompt using context messages
            conversation_messages = context.get_messages(
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
                # follow_up_instructions=FOLLOW_UP_PRICES_PARTIAL_PROMPT,
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
        self,
        args: Dict[str, Any],
    ) -> FunctionResponse:
        try:
            # Registrar la ejecución de la función
            await self.save_function_execution_message("get_course_details", args)

            # Extraer y validar parámetros básicos
            course_id = args.get("course_id")
            info_type = args.get("info_type", "brief")
            specific_info = args.get("specific_info", [])
            course_data = courses_cache.get_course(self.waba_conf.waba_id, course_id)

            if not course_data:
                return FunctionResponse(
                    success=False,
                    data={},
                    error="Course not found",
                    response_behavior=ResponseBehavior.NO_FOLLOW_UP,
                )

            conversation_messages = context.get_messages(
                self.waba_conf.waba_id, self.sender_phone
            )

            to_send_message = None

            # Procesar según el tipo de información solicitada
            if info_type == "general":
                # to_send_message = course_data.get("selling_description", "")

                # Nuevo manejo para información general
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
                # Obtener y formatear campos específicos solicitados
                specific_data = {k: course_data.get(k, "") for k in specific_info}

                # Formateo especial para el campo duration si está presente
                if "duration" in specific_info:
                    duration = specific_data.get("duration")
                    specific_data["duration"] = format_duration(duration)

                # Preparar datos para el prompt
                formatted_course_data = json.dumps(
                    specific_data, indent=2, ensure_ascii=False
                )

                instructions_with_conversation_messages = [
                    {
                        "role": "system",
                        "content": COURSE_SPECIFIC_DETAILS_PROMPT.substitute(
                            # course_title=course_data["title"],
                            # specific_info=", ".join(specific_info),
                            course_data=formatted_course_data,
                            messages=conversation_messages,
                        ),
                    }
                ]

                # course_specifics_prompt = [instructions_with_conversation_messages] + conversation_messages

                # Obtener respuesta de OpenAI
                response, _ = await self.openai_handler.get_completion(
                    # messages=course_specifics_prompt,
                    messages=instructions_with_conversation_messages,
                    temperature=0.2,
                    tool_choice=ToolChoice.NONE,
                    situation="handle_get_course_details",
                )
                answer = response.content

                if answer:
                    to_send_message = answer

            elif info_type == "semantic":
                # Búsqueda semántica en el contenido del curso
                # query = args.get("query", "")
                searchable_fields = [
                    "description",
                    "units",
                    "objectives",
                    "requirements",
                    "selling_description",
                ]
                # Concatenar todos los campos de búsqueda
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
                            # query=query,
                        ),
                    }
                ]
                # + conversation_messages

                # Obtener respuesta de OpenAI
                message, _ = await self.openai_handler.get_completion(
                    messages=search_prompt,
                    temperature=0.3,
                    tool_choice=ToolChoice.NONE,
                    situation="handle_get_course_details",
                )

                answer = message.content

                if answer:
                    to_send_message = answer

            # Procesar y enviar respuesta si se generó contenido
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

    async def _handle_send_contact(
        self,
        args: Dict[str, Any],
    ) -> FunctionResponse:
        try:
            # Registrar la ejecución de la función
            await self.save_function_execution_message(
                "enviar contacto de emprendemy", args
            )

            # Enviar el contacto (acción atómica)
            await send_emprendemy_contact(self.sender_phone, self.waba_conf)

            await self.openai_handler.process_response(
                to_send_message=None,
                to_context_message="Mensaje de Whatsapp con contacto de Emprendemy enviado.",
                to_context_role=MessageRole.SYSTEM,
            )

            return FunctionResponse(
                success=True,
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
            # Registrar la ejecución de la función
            await self.save_function_execution_message("send_cta_to_signup", args)

            # Obtener información del curso
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

            # Enviar CTA (acción atómica)
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
        self,
        args: Dict[str, Any],
    ) -> FunctionResponse:
        try:
            # Registrar la ejecución de la función
            await self.save_function_execution_message(
                "send_conversation_to_supervisor", args
            )

            # Validar tipo de notificación
            notification_type = args.get("notification_type")
            if notification_type not in SUPERVISOR_NOTIFICATION_TYPE:
                return FunctionResponse(
                    success=False,
                    data={},
                    error=f"Invalid notification type: {notification_type}",
                    response_behavior=ResponseBehavior.NO_FOLLOW_UP,
                )

            info = SUPERVISOR_NOTIFICATION_TYPE[notification_type]

            # Obtener mensajes de la conversación
            conversation_messages = context.get_messages(
                self.waba_conf.waba_id, self.sender_phone
            )

            # Get client config from config manager
            from core.config import config_manager

            client_id = (
                self.openai_handler.client_id
            )  # You'll need to add this attribute
            client_config = config_manager.get_client_config(client_id)

            # Generar y enviar email
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
                client_config=client_config,  # Pass client_config instead of settings
            )

            await self.openai_handler.process_response(
                to_send_message=None,
                to_context_message=f"Se envio mail al supervisor sobre {notification_type}",
                to_context_role=MessageRole.SYSTEM,
            )

            return FunctionResponse(
                success=True,
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


class OpenAIHandler:
    def __init__(
        self,
        client_id: str,  # Add this parameter
        conversation_id: str,
        waba_conf: WABAConfig,
        sender_phone: str,
        current_processing_ids: List[str],
        service_container,
    ):
        self.waba_conf = waba_conf
        self.sender_phone = sender_phone
        self.conversation_id = conversation_id
        self.buffer_key = f"{sender_phone}_{waba_conf.waba_id}"
        self.current_processing_ids = current_processing_ids
        self.message_buffer_manager = service_container.message_buffer_manager
        self.context = service_container.context
        self.db = service_container.db
        self.service_container = service_container
        self.client_id = client_id

        self.functions_handler = FunctionsHandler(
            waba_conf=waba_conf,
            sender_phone=sender_phone,
            message_buffer_manager=message_buffer_manager,
            openai_handler=self,
            service_container=service_container,
        )

    async def handle_openai_process(self) -> None:
        try:
            # Get conversation context
            context_messages = context.get_messages(
                self.waba_conf.waba_id, self.sender_phone
            )

            # Get last 6 messages (or all if less than 6) for categorization
            # last_messages = (
            #     context_messages[-6:]
            #     if len(context_messages) >= 6
            #     else context_messages
            # )

            # Perform categorization if there's enough context
            category_info = None
            if self.waba_conf.instructions_strategy == InstructionsStrategy.CLASSIFIED:
                # if last_messages:
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
                        await db.update_message_metadata(
                            self.conversation_id,
                            message_id,
                            {"categories": categories_data},
                        )

            # Get instructions based on categories and strategy
            if self.waba_conf.instructions_strategy == InstructionsStrategy.CLASSIFIED:
                if category_info:
                    categories = [cat for cat, _ in category_info]
                    instructions = self.waba_conf.get_instructions("base", *categories)
                    context.set_prefix_instructions(
                        self.waba_conf.waba_id, self.sender_phone, instructions
                    )

            else:
                # For other strategies, just get base instructions
                instructions = self.waba_conf.get_instructions("base")
                context.set_prefix_instructions(
                    self.waba_conf.waba_id, self.sender_phone, instructions
                )

            # Get full context for completion
            context_for_completion = context.get_full_context(
                self.waba_conf.waba_id, self.sender_phone
            )

            # Get completion and process response
            response, _ = await self.get_completion(
                context_for_completion,
                tool_choice=ToolChoice.AUTO,
                situation="handle_openai_process",
            )

            answer = response.content

            if not response.tool_calls:
                if answer:
                    await self.process_response(
                        to_send_message=answer,
                        to_db_message=answer,
                        to_context_message=answer,
                        to_db_role=MessageRole.ASSISTANT,
                        to_context_role=MessageRole.ASSISTANT,
                    )
                return

            # Caso con tool_calls
            await self._process_tool_calls(
                response.tool_calls,
            )

        except Exception as e:
            logger.error(f"Error in handle_openai_process: {str(e)}", exc_info=True)
            if not hasattr(self, "_response_sent"):
                await self.process_response(
                    "Lo siento, hubo un error procesando tu solicitud. ¿Podrías repetirla?"
                )

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
    ) -> ChatCompletionMessage:
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

    async def _process_tool_calls(
        self,
        tool_calls: List,
    ) -> Tuple[bool, List[Dict]]:
        needs_follow_up = False
        follow_up_instructions = []

        # Mapa de prioridades basado en el flujo lógico de la conversación
        priority_map = {
            "get_course_details": 1,  # Primero info del curso
            "get_course_price": 2,  # Luego el precio
            "send_emprendemy_contact": 3,  # Después datos de contacto
            "send_sign_up_message": 4,  # Luego link de inscripción
            "send_conversation_to_supervisor": 5,  # Al final notificaciones a supervisor
        }

        # Ordenar tool_calls basado en prioridades
        sorted_calls = sorted(
            tool_calls,
            key=lambda x: priority_map.get(
                x.function.name, 99
            ),  # Funciones sin prioridad definida van al final
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

    async def _handle_follow_up(self, follow_up_instructions: List[str]) -> str:
        try:
            new_instructions = "\n\n".join(follow_up_instructions)

            combined_instructions = {
                "role": "system",
                "content": "Dale continuidad a la conversacion"
                + BASE_INSTRUCTIONS
                + new_instructions,
            }

            messages = context.get_messages(self.waba_conf.waba_id, self.sender_phone)
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

    async def process_response(
        self,
        to_send_message: Union[str, None],
        to_db_message: Union[str, None] = None,
        to_db_role: MessageRole = MessageRole.ASSISTANT,
        to_context_message: Union[str, None] = None,
        to_context_role: MessageRole = MessageRole.ASSISTANT,
    ) -> None:
        if await message_buffer_manager.has_new_pending_messages(
            self.buffer_key, self.current_processing_ids
        ):
            logger.info(
                f"Canceling response processing due to new pending messages for {self.sender_phone}"
            )
            return

        # Send message to WhatsApp if provided
        if to_send_message is not None:
            await send_text_response_to_wa(
                to_send_message, self.sender_phone, self.waba_conf
            )

        # Save to DB if there's a message (either specific DB message or fallback to send message)
        db_message = to_db_message if to_db_message is not None else to_send_message
        if db_message is not None:
            db.save_message(
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

        context.add_message(
            self.waba_conf.waba_id,
            self.sender_phone,
            to_context_role,
            context_message,
        )

    async def categorize_messages(
        self,
        messages: List[Dict[str, Any]],
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
