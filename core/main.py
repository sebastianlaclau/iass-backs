# core/main.py
import logging
from fastapi import FastAPI, APIRouter, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.templating import Jinja2Templates
from contextlib import asynccontextmanager

from core.services.container import ServiceContainer
from core.utils.logging import setup_logging
from core.utils.supabase_client import supabase

from core.services.sync_service import SyncService
from core.config import config_manager


setup_logging()
logger = logging.getLogger(__name__)

# Creamos el contenedor de servicios fuera de la función para mantenerlo en un ámbito más amplio
service_container = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Gestor del ciclo de vida de la aplicación"""
    global service_container

    logger.info("Iniciando aplicación...")

    project_config = config_manager.get_project_config()

    # Si la sincronización está activada y estamos en desarrollo
    if project_config.should_sync_conversations:
        sync_service = SyncService(service_container)
        await sync_service.sync_development_conversations()

    yield

    # Limpieza al terminar
    logger.info("Cerrando aplicación...")


def create_application(client_id=None):
    """
    Factory function que crea y configura la aplicación FastAPI
    con la configuración específica del cliente si se proporciona.
    """
    global service_container

    # Get project config
    project_config = config_manager.get_project_config()

    # Get client config if client_id is provided
    client_config = None
    if client_id:
        client_config = config_manager.get_client_config(client_id)
        if not client_config:
            logger.warning(f"No configuration found for client {client_id}")

    # Crear container de servicios con ID de cliente
    service_container = ServiceContainer(supabase_client=supabase, client_id=client_id)

    app = FastAPI(
        title=project_config.PROJECT_NAME,
        version=project_config.PROJECT_VERSION,
        lifespan=lifespan,
    )

    # CORS middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=project_config.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=project_config.cors_headers,
        expose_headers=["*"],
        max_age=86400,
    )

    # Templates - usar directorio relativo o configurable
    templates_dir = (
        client_config.settings.get("TEMPLATES_DIR", "templates")
        if client_config
        else "templates"
    )
    templates = Jinja2Templates(directory=templates_dir)

    # Configuración base de rutas
    api_v1_router = APIRouter(prefix=project_config.API_V1_STR)

    # Si hay configuración específica de cliente, cargar rutas adicionales
    if client_config:
        # Cargar rutas específicas del cliente
        if hasattr(client_config, "routers"):
            for router in client_config.routers:
                api_v1_router.include_router(router)
    else:
        # Cargar rutas por defecto
        from core.webhooks.webhook import webhook

        api_v1_router.include_router(webhook.router)

    # Incluir el router versionado en la app principal
    app.include_router(api_v1_router)

    # Agregar el contenedor de servicios a la aplicación para que sea accesible
    app.state.services = service_container

    # Definir la ruta principal
    @app.get("/")
    async def read_root(request: Request):
        return templates.TemplateResponse(
            "home.html",
            {
                "request": request,
                "client": client_config.name if client_config else "Default",
            },
        )

    return app
