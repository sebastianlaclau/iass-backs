# clients/iass-back-emprendemy/main.py
from core.config import config_manager
from core.main import create_application
from core.models.config import ClientConfig
from core.webhooks import webhook, webhook_verification
from fastapi import APIRouter
from config import EmprendemyClientSettings


# Client ID - use a consistent identifier
CLIENT_ID = "emprendemy"

# Instanciar la configuración específica del cliente
client_settings = EmprendemyClientSettings()

# Crea un router específico para este cliente
emprendemy_router = APIRouter(prefix="/emprendemy")  # Prefijo para todas las rutas
emprendemy_router.include_router(webhook.router)
emprendemy_router.include_router(webhook_verification.router)

client_config = ClientConfig(
    name="Emprendemy",
    base_path="/emprendemy",
    routers=[emprendemy_router],
    waba_config=client_settings.get_waba_config(),
    settings={
        "LABEL": client_settings.LABEL_EMPRENDEMY,
        "APP_ID": client_settings.APP_ID_EMPRENDEMY,
        "FB_VERIFY_TOKEN": client_settings.FB_VERIFY_TOKEN,
    },
)

# Register with config manager
config_manager.register_client(CLIENT_ID, client_config)

# Crear aplicación con configuración de cliente
app = create_application(CLIENT_ID)

if __name__ == "__main__":
    import uvicorn
    import os

    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=int(os.getenv("PORT", 8001)),
        reload=os.getenv("DEBUG", "False").lower() == "true",
    )
