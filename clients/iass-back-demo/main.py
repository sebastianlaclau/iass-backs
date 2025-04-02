# clients/iass-back-demo/main.py
from core.webhooks import webhook, webhook_verification

from core.main import create_application
from core.models.config import ClientConfig
from core.config import config_manager
from fastapi import APIRouter, Request
from config import DemoClientSettings

# Client ID - use a consistent identifier
CLIENT_ID = "demo"

# Load client-specific settings
client_settings = DemoClientSettings()

# Create client router
demo_router = APIRouter(prefix="/demo")
demo_router.include_router(webhook.router)
demo_router.include_router(webhook_verification.router)

# Create client config
client_config = ClientConfig(
    name="Demo",
    base_path="/demo",
    routers=[demo_router],
    waba_config=client_settings.get_waba_config(),
    settings={
        "LABEL": client_settings.LABEL_DEMO,
        "APP_ID": client_settings.APP_ID_DEMO,
        "FB_VERIFY_TOKEN": client_settings.FB_VERIFY_TOKEN,
    },
)

# Register with config manager
config_manager.register_client(CLIENT_ID, client_config)

# Create application with client ID
app = create_application(CLIENT_ID)

if __name__ == "__main__":
    import uvicorn
    import os

    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=int(os.getenv("PORT", 8000)),
        reload=os.getenv("DEBUG", "False").lower() == "true",
    )
