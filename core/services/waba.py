# core/services/waba.py
from core.models.waba import WABAConfig


async def get_waba_config(
    service_container, client_id: str, waba_id: str
) -> WABAConfig:
    """Versión actualizada que usa el contenedor de servicios"""
    return await service_container.wabas_config_cache.get_config(client_id, waba_id)
