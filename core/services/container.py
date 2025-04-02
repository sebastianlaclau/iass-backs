# core/services/container.py
from core.storage.cache import (
    ConversationContext,
    MessageBufferManager,
)
from core.storage.db import DBStorage
from core.services.cache import WABAConfigCache
from core.config import config_manager


def get_client_settings(client_id):
    """Obtiene configuración específica de cliente"""
    return config_manager.get_client_config(client_id)


class ServiceContainer:
    def __init__(self, supabase_client, client_id=None):
        self.supabase_client = supabase_client
        self.db = DBStorage(supabase_client)
        self.message_buffer_manager = MessageBufferManager()
        self.context = ConversationContext()
        self.wabas_config_cache = WABAConfigCache(supabase_client)
        # self.courses_cache = CoursesCache()
        # self.instructions_cache = InstructionsCache()

        # Store client_id for context
        self.client_id = client_id
        self.client_config = get_client_settings(client_id) if client_id else None
