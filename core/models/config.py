# core/models/config.py
from typing import Dict, Any, Optional, List, Type
from pydantic import BaseModel, Field
from pydantic_settings import BaseSettings
from fastapi import APIRouter
import os

from core.models.enums import InstructionsStrategy


class ProjectConfig(BaseSettings):
    """Base configuration all others inherit from"""

    # Core application settings
    PROJECT_NAME: str = "IAssistance Backends"
    PROJECT_VERSION: str = "1.0"
    API_V1_STR: str = "/api/v1"
    ENVIRONMENT: str = "development"
    PORT: int = int(os.getenv("PORT", 8000))

    # CORS Settings
    ALLOWED_ORIGINS: List[str] = ["http://localhost:3000"]
    CORS_HEADERS: List[str] = ["*"]

    # Common settings all clients need
    SUPABASE_URL: str
    SUPABASE_SERVICE_ROLE_KEY: str

    # Sync Settings
    SYNC_DEV_CONVERSATIONS: bool = False
    DEV_SYNC_ENABLED_PHONES: str = ""

    # OpenAI defaults
    OPENAI_MODEL_DEFAULT: str = "gpt-4-0613"
    PINECONE_KEY_DEFAULT: str = ""

    # Email configuration
    SMTP_SERVER: str = "smtp.gmail.com"
    SMTP_PORT: int = 587
    SENDER_EMAIL: str = ""
    ADMIN_EMAIL: str = ""
    EMAIL_PASSWORD: str = ""

    FB_VERIFY_TOKEN: str = "prasath"

    # Estas propiedades y métodos existen en la clase Settings porque son operaciones relacionadas directamente con la configuración, no con la lógica general de la aplicación

    # ==================== Properties ====================
    # Propiedades calculadas en tiempo de acceso (como cors_origins que procesa ALLOWED_ORIGINS)

    @property
    def cors_origins(self) -> List[str]:
        """Get CORS origins"""
        return self.ALLOWED_ORIGINS

    @property
    def cors_headers(self) -> List[str]:
        """Get CORS headers"""
        return self.CORS_HEADERS

    @property
    def should_sync_conversations(self) -> bool:
        """Determine if conversations should be synced"""
        return self.ENVIRONMENT == "development" and self.SYNC_DEV_CONVERSATIONS

    @property
    def sync_enabled_phones(self) -> List[str]:
        """Convierte el string de teléfonos en una lista"""
        if not self.DEV_SYNC_ENABLED_PHONES:
            return []
        return [
            phone.strip()
            for phone in self.DEV_SYNC_ENABLED_PHONES.split(",")
            if phone.strip()
        ]

    # ==================== Methods ====================
    # Funciones que requieren parámetros adicionales
    def should_sync_conversation_for_phone(self, phone: str) -> bool:
        """
        Determina si se debe sincronizar una conversación específica.
        Si DEV_SYNC_ENABLED_PHONES está vacío, sincroniza todos.
        """
        if not self.sync_enabled_phones:
            return True
        return phone in self.sync_enabled_phones

    class Config:
        env_file = "core/.env"
        env_file_encoding = "utf-8"
        extra = "allow"


class WABAConfig(BaseModel):
    """WhatsApp Business API configuration"""

    phone_number: str
    waba_id: str
    permanent_token: str
    phone_number_id: str
    verification_token: str = "prasath"

    openai_assist_id: Optional[str] = None
    openai_api_key: Optional[str] = None

    # Add instructions_strategy with default value
    instructions_strategy: InstructionsStrategy = InstructionsStrategy.SINGLE


class ClientConfig(BaseModel):
    """Client-specific configuration"""

    # Campos existentes
    name: str
    base_path: str
    settings: Dict[str, Any] = Field(default_factory=dict)
    waba_config: WABAConfig
    routers: List[APIRouter] = []
    config_class: Optional[Type[BaseSettings]] = None

    # Nuevos campos para registro y fábrica
    client_id: str  # Identificador único del cliente
    module_path: (
        str  # Ruta al módulo principal del cliente (ej: "clients.iass_back_demo.main")
    )
    mount_path: str  # Ruta donde montar la aplicación (ej: "/api/v1/demo")
    enabled: bool = True  # Permite activar/desactivar clientes
    app_instance: Optional[Any] = (
        None  # Para almacenar la instancia de aplicación (cache)
    )

    def get_full_config(self) -> BaseSettings:
        """Get client-specific configuration instance"""
        if self.config_class:
            return self.config_class()
        return ProjectConfig()

    class Config:
        arbitrary_types_allowed = True  # To allow APIRouter objects
