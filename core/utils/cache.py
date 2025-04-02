from cachetools import TTLCache
from apscheduler.schedulers.asyncio import AsyncIOScheduler
import asyncio
from core.services.supabase import upsert_thread, upsert_waba, save_message_to_db
import logging

# Initialize caches
wabas_cache = TTLCache(maxsize=100, ttl=0)  # Infinite TTL
threads_cache = TTLCache(maxsize=1000, ttl=0)  # Infinite TTL
messages_cache = TTLCache(maxsize=10000, ttl=0)  # Infinite TTL
thread_creation_cache = TTLCache(maxsize=1000, ttl=10)  # 10 seconds TTL
blocked_threads_cache = TTLCache(maxsize=1000, ttl=10)  # 10 seconds TTL
thread_locks = TTLCache(maxsize=1000, ttl=300)

# Initialize scheduler
scheduler = AsyncIOScheduler()

logger = logging.getLogger(__name__)


async def save_and_clear_wabas_cache():
    logger.info("Starting save_and_clear_wabas_cache function")
    wabas = list(wabas_cache.values())
    logger.info(f"WABAs to upsert: {len(wabas)}")

    if wabas:
        result = upsert_waba(wabas)
        if result.get("error"):
            logger.info("Error saving WABAs to database:", result["error"])
        else:
            logger.info("WABAs saved to database:", result.get("data"))
            wabas_cache.clear()
            logger.info("WABAs cleared from cache")
    else:
        logger.info("No WABAs to save")


async def save_and_clear_threads_cache():
    logger.info("Starting save_and_clear_threads_cache function")
    threads = list(threads_cache.values())
    logger.info(f"Threads to upsert: {len(threads)}")

    if threads:
        result = await upsert_thread(threads)
        if result.get("error"):
            logger.info("Error saving threads to database:", result["error"])
        else:
            logger.info("Threads saved to database:", result.get("data"))
            threads_cache.clear()
            logger.info("Threads cleared from cache")
    else:
        logger.info("No threads to save")


async def save_and_clear_messages_cache():
    logger.info("Starting save_and_clear_messages_cache function")
    messages = list(messages_cache.values())
    logger.info(f"Messages to insert: {len(messages)}")

    if messages:
        result = await save_message_to_db(messages)
        if result.get("error"):
            logger.info("Error saving messages to database:", result["error"])
        else:
            logger.info("Messages saved to database:", result.get("data"))
            messages_cache.clear()
            logger.info("Messages cleared from cache")
    else:
        logger.info("No messages to save")


async def save_and_clear_all_caches():
    logger.info("Running scheduled task: save_and_clear_all_caches")
    await save_and_clear_wabas_cache()
    await save_and_clear_threads_cache()
    await save_and_clear_messages_cache()


def upsert_waba_on_cache(waba_id: str, company_variables: dict):
    if not waba_id:
        logger.info("No waba id available to send to cache")
        return

    waba = {
        "id": waba_id,
        "name": company_variables.get("name"),
        "phone_number": company_variables.get("phoneNumberId"),
        "openai_assistant_id": company_variables.get("assistantId"),
        "openai_api_key": company_variables.get("openaiKey"),
        "fb_token": company_variables.get("permanent_token"),
        "updated_at": asyncio.get_event_loop().time(),
    }

    wabas_cache[waba_id] = waba


def log_wabas_cache():
    logger.info("Logging all WABA cache entries:")
    for waba_id, waba in wabas_cache.items():
        logger.info(f"WABA ID: {waba['id']}, Name: {waba['name']}")


# Start the scheduler
def start_scheduler():
    scheduler.add_job(save_and_clear_all_caches, "cron", hour=3)
    scheduler.start()


# Stop the scheduler
def stop_scheduler():
    scheduler.shutdown()
