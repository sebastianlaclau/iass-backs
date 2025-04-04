# core/services/waba.py
import logging

logger = logging.getLogger(__name__)


async def get_waba_config(service_container, client_id, waba_id):
    """
    Get WABA configuration from cache or load it from database
    """
    try:
        cache = service_container.wabas_config_cache
        config = await cache.get_config(client_id, waba_id)
        return config
    except Exception as e:
        logger.error(f"Failed to load WABA config: {str(e)}")
        raise
