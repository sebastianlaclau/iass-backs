# core/routers/wabas.py

import logging
from fastapi import APIRouter, HTTPException

logger = logging.getLogger(__name__)

router = APIRouter()


@router.post("/wabas/{waba_id}/reload-config")
async def reload_waba_config(waba_id: str):
    logger.info(f"Received reload config request for WABA {waba_id}")
    try:
        logger.debug(f"Invalidating cache for WABA {waba_id}")
        # await wabas_config_cache.invalidate(waba_id)

        logger.debug(f"Loading new config from DB for WABA {waba_id}")
        # config = await wabas_config_cache.get_config(waba_id)

        # logger.info(f"Successfully reloaded config for WABA {config.name}")
        return {
            "success": True,
            # "message": f"WABA {config.name} configuration reloaded",
        }

    except Exception as e:
        logger.error(
            f"Failed to reload config for WABA {waba_id}: {str(e)}", exc_info=True
        )
        raise HTTPException(status_code=400, detail=str(e))
