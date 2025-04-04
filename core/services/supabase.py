import json
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional
import httpx
from core.utils.supabase_client import supabase
import logging

logger = logging.getLogger(__name__)


async def upload_to_supabase_audio_bucket(
    meta_audio_url: str, access_token: str
) -> str:
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(
                meta_audio_url,
                headers={"Authorization": f"Bearer {access_token}"},
            )
            response.raise_for_status()
            file_buffer = response.content

        file_name = f"{datetime.now(datetime.timezone.utc).timestamp()}.ogg"
        file_path = f"audio/{file_name}"

        result = supabase.storage.from_("audios_bucket").upload(
            file_path, file_buffer, file_options={"content-type": "audio/ogg"}
        )

        if isinstance(result, Dict) and "error" in result:
            raise Exception(result["error"])

        public_url = supabase.storage.from_("audios_bucket").get_public_url(file_path)

        logger.info(f"Audio file uploaded to {public_url}")
        return public_url

    except Exception as error:
        logger.info(f"Error moving the file from facebook to supabase: {error}")
        raise


async def delete_all_records():
    try:
        logger.info("Deleting all records from messages table")
        result = supabase.table("messages").delete().neq("id", 0).execute()
        if result.get("error"):
            logger.info(
                f"Error deleting records from messages table: {result['error']}"
            )
        else:
            logger.info("All records deleted from messages table")

        logger.info("Deleting all records from threads table")
        result = supabase.table("threads").delete().neq("id", 0).execute()
        if result.get("error"):
            logger.info(f"Error deleting records from threads table: {result['error']}")
        else:
            logger.info("All records deleted from threads table")

        logger.info("Deleting all records from wabas table")
        result = supabase.table("wabas").delete().neq("id", 0).execute()
        if result.get("error"):
            logger.info(f"Error deleting records from wabas table: {result['error']}")
        else:
            logger.info("All records deleted from wabas table")

    except Exception as error:
        logger.info(f"Unexpected error: {error}")


async def upsert_waba(id: str, name: str, phone_number_id: str) -> Dict[str, Any]:
    try:
        result = (
            supabase.table("wabas")
            .upsert(
                {
                    "id": id,
                    "name": name,
                    "phone_number_id": phone_number_id,
                    "updated_at": datetime.now(datetime.timezone.utc).isoformat(),
                },
                on_conflict=["id"],
            )
            .execute()
        )

        if result.get("error"):
            raise Exception(f"Failed to upsert WABA: {result['error']}")

        return result.get("data", [{}])[0]
    except Exception as error:
        logger.info(f"Failed to upsert WABA: {error}")
        raise


def upsert_thread(
    waba_id: int,
    user_phone_number: str,
    openai_thread_id: str,
    local_thread_id: Optional[str] = None,
) -> Dict[str, Any]:
    try:
        result = (
            supabase.table("threads")
            .upsert(
                {
                    "waba_id": waba_id,
                    "user_phone_number": user_phone_number,
                    "openai_thread_id": openai_thread_id,
                    "local_thread_id": local_thread_id,
                    "updated_at": datetime.now(datetime.timezone.utc).isoformat(),
                },
                on_conflict=["openai_thread_id"],
            )
            .execute()
        )

        if isinstance(result, dict) and result.get("error"):
            raise Exception(result["error"])

        return result.data[0] if hasattr(result, "data") and result.data else {}
    except Exception as error:
        logger.error(f"Failed to upsert thread: {error}")
        raise


def save_message_to_db(
    thread_id: str, message_content: str, message_direction: str, content_type: str
) -> str:
    try:
        result = (
            supabase.table("messages")
            .insert(
                {
                    "thread_id": thread_id,
                    "message_content": message_content,
                    "message_direction": message_direction,
                    "content_type": content_type,
                    "created_at": datetime.now(datetime.timezone.utc).isoformat(),
                }
            )
            .execute()
        )

        if hasattr(result, "error") and result.error:
            raise Exception(result.error)

        return result.data[0]["message_content"] if result.data else ""
    except Exception as error:
        logger.info(f"Failed to insert message: {error}")
        raise


def find_thread_in_database(local_thread_key: str) -> Optional[Dict]:
    try:
        response = (
            supabase.table("threads")
            .select("*")
            .eq("local_thread_id", local_thread_key)
            .order("created_at", desc=True)
            .limit(1)
            .execute()
        )

        # logger.info(f"Thread found in database: {response.data}")
        if response.data:
            return response.data[0]
        else:
            return None

    except Exception as error:
        logger.error(f"Error finding thread in database: {error}")
        raise


async def get_wabas_list() -> List[Dict[str, Any]]:
    result = supabase.table("wabas").select("id,name,phone_number_id").execute()

    if result.get("error"):
        logger.info(f"Error fetching WABAs: {result['error']}")
        return []

    return result.get("data", [])


async def get_threads_by_waba(waba_id: str) -> List[Dict[str, Any]]:
    result = (
        supabase.table("threads")
        .select(
            "waba_id,user_phone_number,created_at,updated_at,local_thread_id,openai_thread_id"
        )
        .eq("waba_id", waba_id)
        .execute()
    )

    if result.get("error"):
        logger.info(f"Error fetching threads for WABA: {result['error']}")
        return []

    return result.get("data", [])


async def get_messages_by_thread(thread_id: str) -> List[Dict[str, Any]]:
    result = (
        supabase.table("messages")
        .select(
            "id,thread_id,message_content,message_direction,content_type,created_at"
        )
        .eq("thread_id", thread_id)
        .execute()
    )

    if result.get("error"):
        logger.info(f"Error fetching messages for thread: {result['error']}")
        return []

    return result.get("data", [])


async def save_log_to_db(message: Any, waba: Optional[str] = None) -> Optional[str]:
    if isinstance(message, dict):
        try:
            message_string = json.dumps(message)
        except:
            message_string = json.dumps(
                {
                    "message": str(message.get("message", "Unknown error")),
                    "code": message.get("code"),
                    "details": message.get("response", {})
                    .get("data", {})
                    .get("error", {})
                    .get("error_data", {})
                    .get("details"),
                }
            )
    else:
        message_string = str(message)

    max_length = 65535
    if len(message_string) > max_length:
        message_string = message_string[:max_length]

    result = (
        supabase.table("logs")
        .insert(
            {
                "message": message_string,
                "created_at": datetime.now(datetime.timezone.utc).isoformat(),
                "waba": waba or "undefined",
            }
        )
        .execute()
    )

    if result.get("error"):
        logger.info(f"Error logging message: {result['error']}")
        return None

    return result.get("data", [{}])[0].get("message")


async def get_logs() -> List[Dict[str, Any]]:
    result = supabase.table("logs").select("*").order("created_at", desc=True).execute()

    if result.get("error"):
        logger.info(f"Error fetching logs: {result['error']}")
        return []

    return result.get("data", [])


async def get_logs_by_waba(waba: str) -> List[Dict[str, Any]]:
    result = (
        supabase.table("logs")
        .select("*")
        .eq("waba", waba)
        .order("created_at", desc=True)
        .execute()
    )

    if result.get("error"):
        logger.info(f"Error fetching logs: {result['error']}")
        return []

    return result.get("data", [])


async def get_relevant_files(company: str) -> Dict[str, Any]:
    try:
        result = (
            supabase.table("jellinek_files")
            .select("file_name,download_url,file_id")
            .ilike("file_name", f"%{company}%")
            .execute()
        )

        if result.get("error"):
            raise Exception(result["error"])

        data = result.get("data", [])

        if not data:
            return {
                "success": False,
                "message": f'No files found for the brand "{company}".',
            }

        return {
            "success": True,
            "company": company,
            "files": [
                {
                    "filename": file["file_name"],
                    "url": file["download_url"],
                    "id": file["file_id"],
                }
                for file in data
            ],
        }

    except Exception as error:
        logger.info(f"Error querying Supabase: {error}")
        return {
            "success": False,
            "message": f'An error occurred while searching for files related to "{company}".',
            "error": str(error),
        }


# Add any other necessary functions here
