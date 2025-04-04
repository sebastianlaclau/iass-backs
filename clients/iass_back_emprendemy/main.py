# clients/iass_back_emprendemy/main.py
from core.config import config_manager
from core.models.config import ClientConfig
from core.routers.meta_webhooks import messages
from fastapi import APIRouter
from .config import EmprendemyClientSettings


# Client ID - use a consistent identifier
CLIENT_ID = "emprendemy"

# Instanciar la configuración específica del cliente
client_settings = EmprendemyClientSettings()

# Crea un router específico para este cliente
# emprendemy_router = APIRouter(prefix="/emprendemy")
emprendemy_router = APIRouter(prefix="")
emprendemy_router.include_router(messages.router)

# Create client config
client_config = ClientConfig(
    client_id=CLIENT_ID,
    name="Emprendemy",
    base_path="/api/v1/emprendemy",
    module_path="clients.iass_back_emprendemy.main",
    mount_path="/api/v1/emprendemy",
    routers=[emprendemy_router],
    waba_config=client_settings.create_waba_config(),
    settings={
        "LABEL": client_settings.LABEL_EMPRENDEMY,
        "APP_ID": client_settings.APP_ID_EMPRENDEMY,
        "FB_VERIFY_TOKEN": client_settings.FB_VERIFY_TOKEN,
    },
    enabled=True,
)

# Register with config manager
config_manager.register_client(CLIENT_ID, client_config)
