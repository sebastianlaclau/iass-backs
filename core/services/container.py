# core/services/container.py
import logging
from core.storage.cache import (
    ConversationContext,
    MessageBufferManager,
)
from core.storage.db import DBStorage
from core.services.cache import WABAConfigCache
from core.config import config_manager

logger = logging.getLogger(__name__)


def get_client_settings(client_id):
    """Obtiene configuración específica de cliente"""
    return config_manager.get_client_config(client_id)


class ServiceContainer:
    def __init__(self, supabase_client, client_id=None):
        # Store client_id for context
        self.client_id = client_id

        self.supabase_client = supabase_client
        self.db = DBStorage(supabase_client)
        self.message_buffer_manager = MessageBufferManager()
        self.context = ConversationContext()
        self.wabas_config_cache = WABAConfigCache(supabase_client)
        # self.courses_cache = CoursesCache()
        # self.instructions_cache = InstructionsCache()

        # Get client configuration
        self.client_config = get_client_settings(client_id) if client_id else None

        # Set handlers to None initially - they'll be created on demand
        self._openai_handler_class = None
        self._functions_handler_class = None

        # Load handler classes based on client_id
        if client_id:
            self._load_handler_classes()

        # Extender el contenedor con servicios específicos del cliente
        if client_id:
            self._extend_with_client_services(client_id)

    def _check_module_path(self, module_path):
        """Debug helper to check if a module path exists"""
        import importlib.util

        logger.debug(f"Checking if module exists: {module_path}")

        # Check if module exists
        spec = importlib.util.find_spec(module_path)
        if spec is not None:
            logger.debug(f"✓ Module path exists: {module_path}")
            return True
        else:
            logger.debug(f"✗ Module path does not exist: {module_path}")

            # Try to find similar modules for debugging
            parts = module_path.split(".")
            if len(parts) > 1:
                parent_module = ".".join(parts[:-1])
                try:
                    parent = __import__(parent_module, fromlist=["*"])
                    logger.debug(
                        f"Parent module '{parent_module}' contents: {dir(parent)}"
                    )
                except ImportError:
                    logger.debug(
                        f"Parent module '{parent_module}' could not be imported"
                    )

            return False

    def _load_handler_classes(self):
        """Load appropriate handler classes for this client"""
        try:
            # Try to import client-specific handlers
            module_name = f"clients.iass_back_{self.client_id}.services"

            # Import OpenAIHandler
            try:
                import importlib

                # Import openai_handler submodule
                openai_handler_module = importlib.import_module(
                    f"{module_name}.openai_handler"
                )

                # Check if OpenAIHandler class exists
                if hasattr(openai_handler_module, "OpenAIHandler"):
                    self._openai_handler_class = openai_handler_module.OpenAIHandler

                else:
                    logger.error(
                        f"No OpenAIHandler class found in {module_name}.openai_handler"
                    )
                    from core.services.openai_handler import OpenAIHandler

                    self._openai_handler_class = OpenAIHandler

            except Exception as e:
                logger.error(f"Error loading OpenAIHandler: {str(e)}", exc_info=True)
                from core.services.openai_handler import OpenAIHandler

                self._openai_handler_class = OpenAIHandler

            # Import FunctionsHandler
            try:
                import importlib

                # Import functions_handler submodule
                functions_handler_module = importlib.import_module(
                    f"{module_name}.functions_handler"
                )

                # Check if FunctionsHandler class exists
                if hasattr(functions_handler_module, "FunctionsHandler"):
                    self._functions_handler_class = (
                        functions_handler_module.FunctionsHandler
                    )

                else:
                    logger.error(
                        f"No FunctionsHandler class found in {module_name}.functions_handler"
                    )
                    from core.services.functions_handler import FunctionsHandler

                    self._functions_handler_class = FunctionsHandler

            except Exception as e:
                logger.error(f"Error loading FunctionsHandler: {str(e)}", exc_info=True)
                from core.services.functions_handler import FunctionsHandler

                self._functions_handler_class = FunctionsHandler

        except Exception as e:
            logger.error(
                f"Error loading handler classes for client {self.client_id}: {str(e)}",
                exc_info=True,
            )
            # Use base handlers as fallback
            from core.services.openai_handler import OpenAIHandler
            from core.services.functions_handler import FunctionsHandler

            self._openai_handler_class = OpenAIHandler
            self._functions_handler_class = FunctionsHandler

    def create_openai_handler(
        self, waba_conf, sender, conversation_id, current_processing_ids
    ):
        """Factory method to create appropriate OpenAIHandler for this client"""
        handler_class = self._openai_handler_class

        handler = handler_class(
            client_id=self.client_id,
            waba_conf=waba_conf,
            sender_phone=sender,
            conversation_id=conversation_id,
            current_processing_ids=current_processing_ids,
            service_container=self,
        )

        return handler

    def _extend_with_client_services(self, client_id):
        """Extiende el contenedor con servicios específicos del cliente"""
        try:
            import importlib

            extension_module = None

            try:
                # Intentar importar módulo de extensión del cliente
                extension_module = importlib.import_module(
                    f"clients.iass_back_{client_id}.services.extensions"
                )
            except ImportError:
                logger.debug(f"No service extensions found for client {client_id}")
                return

            # Buscar clase de extensión
            for attr_name in dir(extension_module):
                if attr_name.endswith("ServiceExtension"):
                    extension_class = getattr(extension_module, attr_name)
                    extension = extension_class()
                    extension.extend_container(self)
                    logger.info(f"Extended service container with {attr_name}")
                    break

        except Exception as e:
            logger.error(f"Error extending container for client {client_id}: {str(e)}")
