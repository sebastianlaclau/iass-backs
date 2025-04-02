# core/utils/config.py
# from typing import List, Any, Optional, Dict
# from dataclasses import dataclass
# from openai import AsyncOpenAI

# from enum import Enum
# from core.config import settings
# import logging

# logger = logging.getLogger(__name__)


# class InstructionsStrategy(Enum):
#     SINGLE = "single"
#     CLASSIFIED = "classified"


# @dataclass
# class WABAConfig:
#     name: str
#     phone_number: str
#     assistant_id: str
#     phone_number_id: str
#     tools: List[Any]
#     openai_key: str
#     permanent_token: str
#     model: str
#     vector_store: str
#     pinecone_key: str
#     temperature: float
#     waba_id: str
#     sender_email: str
#     admin_email: str
#     email_password: str
#     smtp_server: str = "smtp.gmail.com"
#     smtp_port: int = 587
#     openai_client: Optional[AsyncOpenAI] = None
#     instructions_strategy: InstructionsStrategy = InstructionsStrategy.SINGLE
#     basic_instructions: str = None
#     custom_instructions: Dict[str, str] = None

#     def __post_init__(self):
#         from core.api.webhook import (
#             instructions_cache,
#             BASE_INSTRUCTIONS,
#             CUSTOM_INSTRUCTIONS,
#         )

#         """Initialize clients and validate configuration"""
#         try:
#             self.openai_client = self.create_openai_client()
#             self.validate()

#             if self.instructions_strategy == InstructionsStrategy.SINGLE:
#                 self.basic_instructions = instructions_cache.get_instructions(
#                     self.waba_id
#                 )
#                 self.custom_instructions = None

#             else:
#                 all_instructions = {"base": BASE_INSTRUCTIONS}
#                 all_instructions.update(CUSTOM_INSTRUCTIONS)
#                 self.custom_instructions = all_instructions
#                 self.basic_instructions = None

#         except Exception as e:
#             logger.error(f"Error initializing WABAConfig: {str(e)}")
#             raise

#     def validate(self) -> bool:
#         """Validate that all required fields are present and valid"""
#         required_fields = {
#             "name": self.name,
#             "phone_number": self.phone_number,
#             "phone_number_id": self.phone_number_id,
#             "permanent_token": self.permanent_token,
#             "openai_key": self.openai_key,
#             "pinecone_key": self.pinecone_key,
#             "sender_email": self.sender_email,
#             "admin_email": self.admin_email,
#             "email_password": self.email_password,
#         }

#         for field_name, value in required_fields.items():
#             if not value or not isinstance(value, str):
#                 raise ValueError(f"Invalid or missing {field_name}")

#         if not self.openai_client:
#             raise ValueError("OpenAI client failed to initialize")

#         return True

#     def create_openai_client(self) -> AsyncOpenAI:
#         """Create OpenAI client with error handling"""
#         try:
#             return AsyncOpenAI(api_key=self.openai_key)
#         except Exception as e:
#             logger.error(f"Failed to create OpenAI client: {str(e)}")
#             raise

#     def get_instructions(self, *categories: str) -> List[Dict[str, str]]:
#         # Para strategy SINGLE, retornamos las instrucciones básicas directamente
#         if self.instructions_strategy == InstructionsStrategy.SINGLE:
#             if self.basic_instructions:
#                 return [{"role": "system", "content": self.basic_instructions}]
#             return []

#         if not self.custom_instructions:
#             return []

#         # Construimos las instrucciones en secciones
#         instructions_sections = []

#         # Procesamos cada categoría solicitada en el orden que fueron pasadas
#         for category in categories:
#             if category in self.custom_instructions:
#                 # Para la categoría base no incluimos el prefijo "Instructions for"
#                 if category == "base":
#                     instructions_sections.append(
#                         f"{self.custom_instructions[category]}"
#                     )
#                 else:
#                     instructions_sections.append(
#                         f"Instructions for {category}:\n"
#                         f"{self.custom_instructions[category]}"
#                     )

#         # Si no hay instrucciones, retornamos lista vacía
#         if not instructions_sections:
#             return []

#         # Combinamos todas las secciones en un único mensaje
#         combined_instructions = "\n\n".join(instructions_sections)

#         return [{"role": "system", "content": combined_instructions}]


# def get_waba_config(waba_id: str) -> WABAConfig:
#     """Get WABA configuration based on ID"""
#     from core.api.webhook import DEMO_RUN_TOOLS_DEFINITION_EMPRENDEMY

#     configs = {
#         settings.FB_WABA_DEMO: WABAConfig(
#             name=settings.LABEL_DEMO,
#             phone_number=settings.PHONE_NUMBER_DEMO,
#             permanent_token=settings.FB_PERMANENT_TOKEN_DEMO,
#             phone_number_id=settings.PHONE_NUMBER_ID_DEMO,
#             assistant_id=settings.OPENAI_ASSIST_ID_DEMO,
#             openai_key=settings.OPENAI_API_KEY_DEMO,
#             model="gpt-4o-mini",
#             tools=DEMO_RUN_TOOLS_DEFINITION_EMPRENDEMY,
#             instructions_strategy=InstructionsStrategy.CLASSIFIED,
#             pinecone_key=settings.PINECONE_202409_BOT_LLM_WAPP,
#             temperature=0.3,
#             vector_store="",
#             waba_id=waba_id,
#             smtp_server=settings.SMTP_SERVER,
#             smtp_port=settings.SMTP_PORT,
#             sender_email=settings.SENDER_EMAIL,
#             admin_email=settings.ADMIN_EMAIL,
#             email_password=settings.EMAIL_PASSWORD,
#         ),
#         # settings.FB_WABA_EMPRENDEMY: WABAConfig(
#         #     name=settings.LABEL_EMPRENDEMY,
#         #     phone_number=settings.PHONE_NUMBER_EMPRENDEMY,
#         #     permanent_token=settings.FB_PERMANENT_TOKEN_EMPRENDEMY,
#         #     phone_number_id=settings.PHONE_NUMBER_ID_EMPRENDEMY,
#         #     assistant_id=settings.OPENAI_ASSIST_ID_EMPRENDEMY,
#         #     openai_key=settings.OPENAI_API_KEY_EMPRENDEMY,
#         #     model="gpt-4o-mini",
#         #     tools=DEMO_RUN_TOOLS_DEFINITION_EMPRENDEMY,
#         #     instructions_strategy=InstructionsStrategy.SINGLE,
#         #     pinecone_key=settings.PINECONE_202409_BOT_LLM_WAPP,
#         #     temperature=0.3,
#         #     vector_store="",
#         #     waba_id=waba_id,
#         #     smtp_server=settings.SMTP_SERVER,
#         #     smtp_port=settings.SMTP_PORT,
#         #     sender_email=settings.SENDER_EMAIL,
#         #     admin_email=settings.ADMIN_EMAIL,
#         #     email_password=settings.EMAIL_PASSWORD,
#         # ),
#     }

#     if waba_id not in configs:
#         raise ValueError(f"Invalid WABA ID: {waba_id}")

#     return configs[waba_id]
