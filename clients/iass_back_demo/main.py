# clients/iass-back-demo/main.py
from core.routers.meta_webhooks import messages
from core.models.config import ClientConfig
from core.config import config_manager
from fastapi import APIRouter
from .config import DemoClientSettings

CLIENT_ID = "demo"

# Load client-specific settings
client_settings = DemoClientSettings()

# Create client router
demo_router = APIRouter(prefix="")
demo_router.include_router(messages.router)

# Create client config
client_config = ClientConfig(
    client_id=CLIENT_ID,
    name="Demo",
    base_path="/api/v1/demo",
    mount_path="/api/v1/demo",
    module_path="clients.iass_back_demo.main",
    routers=[demo_router],
    waba_config=client_settings.create_waba_config(),
    settings={
        "LABEL": client_settings.LABEL_DEMO,
        "APP_ID": client_settings.APP_ID_DEMO,
        "FB_VERIFY_TOKEN": client_settings.FB_VERIFY_TOKEN,
    },
    enabled=True,
)

# Register with config manager
config_manager.register_client(CLIENT_ID, client_config)
