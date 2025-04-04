# clients/__init__.py
from importlib import import_module
import logging

logger = logging.getLogger(__name__)


def register_all_clients():
    """Registra automáticamente todos los clientes disponibles"""
    # Lista de clientes conocidos
    client_modules = ["iass_back_demo", "iass_back_emprendemy"]

    for client_name in client_modules:
        try:
            # Importar el módulo main del cliente
            import_module(f"clients.{client_name}.main")
            # logger.info(f"Cliente registrado: {client_name}")
        except Exception as e:
            logger.error(f"Error registrando cliente {client_name}: {e}")
