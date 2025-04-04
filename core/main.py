# core/main.py
from clients import register_all_clients
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
from core.routers.meta_webhooks.messages import router as verification_router
from core.routers.meta_webhooks.verification import router as messages_router


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


# Caché de instancias de aplicaciones
_app_instances = {}


def create_application(client_id=None, include_webhooks=False):
    """
    Factory function que crea y configura la aplicación FastAPI
    con la configuración específica del cliente si se proporciona.
    """
    global service_container

    # Verificar si ya existe una instancia en caché
    cache_key = f"{client_id}_{include_webhooks}"
    if cache_key in _app_instances:
        logger.debug(f"Returning cached application for client: {client_id}")
        return _app_instances[cache_key]

    # Get project config
    project_config = config_manager.get_project_config()

    # Get client config if client_id is provided
    client_config = None
    if client_id:
        client_config = config_manager.get_client_config(client_id)
        if not client_config:
            logger.warning(f"No configuration found for client {client_id}")
            return None

    try:
        # Crear container de servicios con ID de cliente
        service_container = ServiceContainer(
            supabase_client=supabase, client_id=client_id
        )

        app = FastAPI(
            title=f"{project_config.PROJECT_NAME} - {client_config.name if client_config else 'Main'}",
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

        # Solo incluir webhooks si se solicita explícitamente
        if include_webhooks:
            api_v1_router.include_router(messages_router)
            api_v1_router.include_router(verification_router)

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

        # Almacenar en caché la instancia creada
        _app_instances[cache_key] = app

        # Si hay cliente, guardar referencia en su config
        if client_config:
            client_config.app_instance = app

        return app
    except Exception as e:
        logger.error(f"Error creating application for client {client_id}: {e}")
        return None


def create_main_application():
    """Crea la aplicación principal que incluirá el endpoint centralizado de webhooks"""
    # Configuración básica
    app = FastAPI(title="IAssistance Main Application")

    # Incluir el router de webhooks centralizado
    app.include_router(messages_router, prefix="/api/v1")
    app.include_router(verification_router, prefix="/api/v1")

    # Montar las aplicaciones de cliente en sus prefijos específicos
    for client_id, client_config in config_manager._clients.items():
        if not getattr(
            client_config, "enabled", True
        ):  # Verificar si está habilitado (por defecto sí)
            continue

        # Crear aplicación cliente sin webhooks
        client_app = create_application(client_id=client_id, include_webhooks=False)

        if client_app:
            # Usar base_path de la configuración o un valor predeterminado
            mount_path = client_config.base_path or f"/api/v1/{client_id}"
            app.mount(mount_path, client_app)
            # logger.info(f"Mounted client application: {client_id} at {mount_path}")

    return app


register_all_clients()

app = create_main_application()
