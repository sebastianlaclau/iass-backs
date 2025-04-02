# core/services/cache.py
import logging

# from core.config import Settings
from core.data.tools_definition import TOOLS_DEFINITION
from core.models.waba import WABAConfig, InstructionsStrategy

from core.config import config_manager

logger = logging.getLogger(__name__)


class WABAConfigCache:
    def __init__(self, supabase_client):
        self._cache = {}
        self.supabase_client = supabase_client
        self.project_config = config_manager.get_project_config()

    async def get_config(self, client_id: str, waba_id: str) -> WABAConfig:
        """Obtiene configuración con soporte para múltiples clientes"""
        cache_key = f"{client_id}:{waba_id}"

        logger.debug(f"Getting config for client {client_id}, WABA {waba_id}")

        if cache_key in self._cache:
            return self._cache[cache_key]

        # Cargar de base de datos con identificación de cliente
        config = await self._load_from_db(client_id, waba_id)
        self._cache[cache_key] = config
        return config

    async def invalidate(self, client_id: str, waba_id: str):
        cache_key = f"{client_id}:{waba_id}"
        if cache_key in self._cache:
            del self._cache[cache_key]

    async def _load_from_db(self, client_id: str, waba_id: str) -> WABAConfig:
        try:
            # Ajustar query para filtrar por cliente_id también
            waba_data = (
                await self.supabase_client.from_("wabas")
                .select("*")
                .eq("waba_id", waba_id)
                .eq("client_id", client_id)
                .single()
            )

            # Get client configuration
            client_config = config_manager.get_client_config(client_id)
            if not client_config:
                raise ValueError(f"No configuration found for client {client_id}")

            # Get default values from project config for email settings
            project_config = self.project_config

            # Construir configuración con datos de cliente específicos
            config = WABAConfig(
                name=waba_data["name"],
                phone_number=waba_data["phone_number"],
                phone_number_id=waba_data["phone_number_id"],
                permanent_token=waba_data["permanent_token"],
                # Get values from client config or use project defaults
                assistant_id=client_config.waba_config.openai_assist_id,
                openai_key=client_config.waba_config.openai_api_key,
                model=project_config.OPENAI_MODEL_DEFAULT,
                tools=TOOLS_DEFINITION,
                instructions_strategy=InstructionsStrategy.SINGLE,
                pinecone_key=project_config.PINECONE_KEY_DEFAULT,
                temperature=0.3,
                vector_store="",
                waba_id=waba_id,
                smtp_server=project_config.SMTP_SERVER,
                smtp_port=project_config.SMTP_PORT,
                sender_email=project_config.SENDER_EMAIL,
                admin_email=project_config.ADMIN_EMAIL,
                email_password=project_config.EMAIL_PASSWORD,
            )

            return config

        except Exception as e:
            logger.error(f"Failed to load WABA config: {str(e)}")
            raise
