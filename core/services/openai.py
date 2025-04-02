import json
import os
import logging
import asyncio
import httpx
import aiohttp
from typing import Dict, Any, List
from openai import OpenAI, AsyncOpenAI, NotFoundError, BadRequestError


from core.utils.helpers import get_waba_config, WABAConfig
from core.utils.cache import blocked_threads_cache

from core.services.supabase import (
    upsert_thread,
    find_thread_in_database,
    save_message_to_db,
    save_log_to_db,
)


logger = logging.getLogger(__name__)


async def generate_embedding(content: str, openai_client: OpenAI) -> List[float]:
    try:
        response = await openai_client.embeddings.create(
            model="text-embedding-3-small",
            input=content,
            encoding_format="float",
        )
        return response.data[0].embedding
    except Exception as error:
        logger.info(f"Error generating embedding: {error}")
        raise


async def create_query_embedding(query: str, openai_client: OpenAI) -> List[float]:
    response = await openai_client.embeddings.create(
        model="text-embedding-3-small", input=query, encoding_format="float"
    )
    return response.data[0].embedding


async def create_openai_file(
    data: Any, openai_client: AsyncOpenAI, purpose: str, name: str, waba: str
) -> str:
    filename = f"{name}.json"
    try:
        save_log_to_db(data, waba)
        json_string = json.dumps(data)
        save_log_to_db(json_string, waba)

        with open(filename, "w", encoding="utf-8") as f:
            json.dump(data, f)

        with open(filename, "rb") as file:
            response = await openai_client.files.create(file=file, purpose=purpose)

        logger.info(f"File created with id: {response.id}")

        os.remove(filename)
        return response.id
    except Exception as error:
        logger.info(f"Error saving data to OpenAI vector store: {error}")
        raise error


async def get_files_by_name(file_name: str, client: AsyncOpenAI) -> List[str]:
    try:
        files = await get_openai_files(client)
        ids_array = [file.id for file in files if file_name in file.filename]
        logger.info(f"Files containing {file_name} in filename: {ids_array}")
        return ids_array
    except Exception as error:
        logger.info(f"Error getting files by name: {error}")
        raise error


async def get_openai_files(openai_client: AsyncOpenAI) -> List[Dict[str, Any]]:
    try:
        response = await openai_client.files.list()
        return response.data
    except Exception as error:
        logger.info(f"Error getting files list: {error}")
        raise error


async def del_openai_files_by_id(ids_array: List[str], openai_client: AsyncOpenAI):
    try:
        for file_id in ids_array:
            await openai_client.files.delete(file_id)
    except Exception as error:
        logger.info(f"Error deleting the list of files from OpenAI: {error}")
        raise error


async def del_files_by_name(file_name: str, client: AsyncOpenAI):
    try:
        files = await get_files_by_name(file_name, client)
        await del_openai_files_by_id(files, client)
        logger.info(f"Files deleted successfully: {files}")
    except Exception as error:
        logger.info(f"Error deleting previous files: {error}")
        raise error


async def attach_file_to_vector_store(
    file_id: str, vector_id: str, openai_client: AsyncOpenAI
):
    logger.info(
        f"Trying to attach the fileId: {file_id} to the vector store: {vector_id}"
    )
    try:
        await openai_client.beta.vector_stores.files.create(vector_id, file_id=file_id)

        retry_count = 0
        max_retries = 10
        while retry_count < max_retries:
            status_check = await openai_client.beta.vector_stores.files.retrieve(
                vector_id, file_id
            )
            if status_check.status == "completed":
                logger.info("File attachment completed:", status_check)
                return status_check
            elif status_check.status == "in_progress":
                logger.info("Vector store file attachment still in progress...")
                await asyncio.sleep(5)
                retry_count += 1
            else:
                raise Exception("File attachment to vector store failed")

        raise Exception("File attachment to vector store timed out")
    except Exception as error:
        logger.info(f"Error attaching file to vector store: {error}")
        raise error


async def create_and_attach_new_file(
    data: Any,
    client: AsyncOpenAI,
    purpose: str,
    file_name: str,
    vector_store_id: str,
    waba: str,
):
    try:
        file_id = await create_openai_file(data, client, purpose, file_name, waba)
        result = await attach_file_to_vector_store(file_id, vector_store_id, client)
        logger.info(f"Attached file {file_id} to vector id: {vector_store_id}")
        return result
    except Exception as error:
        logger.info(f"Error creating and attaching new file: {error}")
        raise error


async def update_json_file_by_waba(data: Any, filename: str, waba: str):
    company_vars = get_waba_config(waba)
    openai_client = company_vars["openai_client"]
    try:
        await del_files_by_name(filename, openai_client)
        result = await create_openai_file(
            data, openai_client, "assistants", filename, waba
        )
        return result
    except Exception as error:
        logger.info(f"Error updating json file: {error}")
        raise error


async def update_store_json_file_by_waba(data: Any, filename: str, waba: str):
    company_vars = get_waba_config(waba)
    openai_client = company_vars["openai_client"]
    vector_store = company_vars["vector_store"]
    try:
        await del_files_by_name(filename, openai_client)
        result = await create_and_attach_new_file(
            data, openai_client, "assistants", filename, vector_store, waba
        )
        return result
    except Exception as error:
        logger.info(f"Error updating json file: {error}")
        raise error


async def get_assistant_openai_res(
    openai_client: AsyncOpenAI,
    assistant_id: str,
    tools: List[Dict[str, Any]],
    waba: str,
    from_: str,
    message_content: str,
    type_: str,
    phone_number_id: str,
    fb_permanent_token: str,
    # service: str,
    pinecone_client: Any,
    custom_instructions: str,
    temperature: float,
) -> Dict[str, str]:
    try:
        thread_id = await creates_thread_if_not_exist(
            openai_client, assistant_id, from_, waba
        )

        await handle_new_user_message(openai_client, thread_id, message_content, type_)

        run_config = creates_run_config(
            assistant_id, tools, custom_instructions, temperature
        )

        run_response = await openai_client.beta.threads.runs.create(
            thread_id=thread_id,
            **run_config,
        )

        logger.info(
            f"Run {run_response.id} created, and now we wait for its completion"
        )

        try:
            return

        except Exception as error:
            logger.info(f"Error waiting for run completion: {error}")
            raise error

        logger.info(f"Fetching messages from thread {thread_id}")

        response_msg = await get_threads_assistant_last_message(
            openai_client, thread_id
        )

        save_message_to_db(thread_id, response_msg, "outbound", "text")

        return response_msg
    except Exception as error:
        logger.info(f"Error in get_assistant_openai_res: {error}")
        raise error


async def block_thread(from_: str, waba: str):
    local_thread_key = f"{from_}_{waba}"
    blocked_key = f"{local_thread_key}_blocked"

    if blocked_threads_cache.get(blocked_key):
        logger.info(
            f"Thread with localThreadKey {local_thread_key} blocked. Waiting..."
        )
        await asyncio.sleep(1)
        return await block_thread(from_, waba)

    blocked_threads_cache.set(blocked_key, True)
    logger.info(f"Thread {blocked_key} blocked.")


def release_thread_block(from_: str, waba: str):
    local_thread_key = f"{from_}_{waba}"
    blocked_key = f"{local_thread_key}_blocked"

    blocked_threads_cache.delete(blocked_key)
    logger.info(f"ThreadBlock {blocked_key} released")


async def creates_thread_if_not_exist(
    openai_client: AsyncOpenAI, assistant_id: str, from_: str, waba: str
) -> str:
    local_thread_key = f"{assistant_id}_{from_}_{waba}"

    try:
        db_thread = find_thread_in_database(local_thread_key)

        # logger.info(f"Thread found in DB: {db_thread}")

        if db_thread and db_thread.get("openai_thread_id"):
            openai_thread_id = db_thread["openai_thread_id"]
            logger.info(f"Corresponding OpenAI thread found in DB: {openai_thread_id}")

            try:
                logger.info(f"Retrieving OpenAI thread: {openai_thread_id}")
                await openai_client.beta.threads.retrieve(openai_thread_id)
                logger.info(f"Successfully retrieved OpenAI thread: {openai_thread_id}")
                return openai_thread_id
            except Exception as error:
                logger.warning(
                    f"Failed to retrieve OpenAI thread: {openai_thread_id}. Error: {str(error)}"
                )
                logger.info("Creating a new thread instead.")
                new_thread = await handle_new_thread(
                    openai_client, waba, from_, local_thread_key
                )
                return new_thread["openai_thread_id"]
        else:
            logger.info(
                f"No existing thread found in DB with localThreadKey: {local_thread_key}. Creating new thread."
            )
            new_thread = await handle_new_thread(
                openai_client, waba, from_, local_thread_key
            )
            return new_thread["openai_thread_id"]

    except Exception as error:
        logger.exception(f"Error in creates_thread_if_not_exist: {error}")
        # Instead of re-raising, return a new thread
        logger.info("Creating a new thread due to error.")
        new_thread = await handle_new_thread(
            openai_client, waba, from_, local_thread_key
        )
        return new_thread["openai_thread_id"]


async def handle_new_thread(
    openai_client: AsyncOpenAI, waba: str, from_: str, local_thread_key: str
) -> Dict[str, Any]:
    new_openai_thread_id = await create_new_openai_thread(openai_client)
    logger.info(
        f"Inserting/updating thread into database with OpenAI thread ID: {new_openai_thread_id}"
    )

    thread_data = upsert_thread(
        waba,
        from_,
        new_openai_thread_id,
        local_thread_key,
    )
    # logger.info(f"Thread upserted in database: {thread_data}")
    return thread_data


async def create_new_openai_thread(openai_client: AsyncOpenAI) -> str:
    logger.info("Creating new OpenAI thread.")
    try:
        thread_response = await openai_client.beta.threads.create()

        if not thread_response or not thread_response.id:
            raise ValueError("Failed to create thread: Invalid response")

        logger.info(f"New OpenAI thread created with ID: {thread_response.id}")
        return thread_response.id
    except Exception as error:
        logger.exception(f"Error creating new OpenAI thread: {error}")
        raise


async def delete_thread_manually(waba: str, phone_number: str) -> dict:
    company_vars = get_waba_config(waba)
    openai_client: AsyncOpenAI = company_vars["openai_client"]
    assistant_id = company_vars["assistant_id"]
    local_thread_key = f"{assistant_id}_{phone_number}_{waba}"

    try:
        thread = find_thread_in_database(local_thread_key)
        if not thread or not thread.get("openai_thread_id"):
            return {
                "message": f"No thread found in DB for the given key: {local_thread_key}"
            }

        openai_thread_id = thread["openai_thread_id"]

        try:
            retrieved_thread = await openai_client.beta.threads.retrieve(
                openai_thread_id
            )
            logger.info(
                f"🚀 ~ delete_thread_manually ~ retrieved_thread: {retrieved_thread}"
            )

            await openai_client.beta.threads.delete(openai_thread_id)
            logger.info(f"OpenAI threadId {openai_thread_id} deleted")

            return {
                "message": f"Saved to DB threadId: {openai_thread_id}\n"
                f"OpenAI thread ID: {openai_thread_id} found active and deleted"
            }
        except NotFoundError as openai_error:
            if openai_error.status_code == 404:
                return {
                    "message": f"OpenAI thread {openai_thread_id} not found or already deleted."
                }
            raise openai_error  # Re-throw if it's not a 404 error
    except Exception as error:
        logger.info(f"Error in delete_thread_manually: {error}")
        return {"message": f"Error occurred while deleting thread: {str(error)}"}


async def handle_new_user_message(
    openai_client: AsyncOpenAI, thread_id: str, message_content: str, type_: str
):
    logger.info(f"Handling new user message for thread {thread_id}")
    retries = 0
    max_retries = 3

    while retries < max_retries:
        try:
            runs = await openai_client.beta.threads.runs.list(thread_id=thread_id)
            active_run = next(
                (
                    run
                    for run in runs.data
                    if run.status
                    in ["queued", "in_progress", "requires_action", "incomplete"]
                ),
                None,
            )

            if active_run:
                logger.info(
                    f"Active run {active_run.id} found with status: {active_run.status}"
                )

            logger.info(f"Adding new message to thread {thread_id}")
            await openai_client.beta.threads.messages.create(
                thread_id=thread_id,
                role="user",
                content=message_content,
            )

            save_message_to_db(thread_id, message_content, "inbound", type_)
            return
        except Exception as error:
            logger.info(
                f"Attempt {retries + 1} failed. Error handling new message: {error}"
            )
            if (
                isinstance(error, BadRequestError)
                and "Can't add messages to thread" in str(error)
                and retries < max_retries - 1
            ):
                retries += 1
                await asyncio.sleep(1)
            else:
                logger.info(f"Final error handling new message: {error}")
                raise ValueError("Failed to handle message after multiple attempts")

    logger.info(f"Failed to add message after {max_retries} attempts")
    raise ValueError("Operation failed after maximum retries")


async def get_threads_assistant_last_message(
    openai_client: AsyncOpenAI, thread_id: str
) -> str:
    try:
        thread_messages = await openai_client.beta.threads.messages.list(
            thread_id=thread_id,
            order="desc",  # Get messages in descending order (newest first)
        )

        assistant_messages = []
        async for msg in thread_messages:
            if msg.role == "assistant":
                assistant_messages.append(msg)
                break  # Stop after finding the first (most recent) assistant message

        if not assistant_messages:
            logger.info("No assistant messages found in the thread.")
            return ""

        last_assistant_message = assistant_messages[0]
        content = last_assistant_message.content[0].text.value
        return content
    except Exception as error:
        logger.info(f"Error in get_threads_assistant_last_message: {error}")
        raise error


def creates_run_config(
    assistant_id: str,
    tools: List[Dict[str, Any]],
    custom_instructions: str,
    temperature: float,
) -> Dict[str, Any]:
    run_config = {
        "assistant_id": assistant_id,
        "tools": tools,
    }

    if custom_instructions:
        run_config["instructions"] = custom_instructions

    if temperature:
        run_config["temperature"] = temperature

    return run_config


async def convert_audio_to_text(audio_url: str, waba_conf: WABAConfig) -> str:
    # TODO revisar esta linea que cambie de donde vienen las variables ahora
    # openai_key = get_waba_config(waba)["openai_key"]
    logger.info(f"Attempting to convert audio from URL: {audio_url}")

    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(audio_url)
            response.raise_for_status()

        logger.info(f"Fetched audio file with status: {response.status_code}")

        form_data = aiohttp.FormData()
        form_data.add_field("file", response.content, filename="audio.ogg")
        form_data.add_field("model", "whisper-1")

        async with aiohttp.ClientSession() as session:
            async with session.post(
                "https://api.openai.com/v1/audio/transcriptions",
                data=form_data,
                headers={"Authorization": f"Bearer {waba_conf.openai_key}"},
            ) as transcribe_response:
                transcribe_data = await transcribe_response.json()

        return transcribe_data["text"]
    except Exception as error:
        logger.info(f"There was an error converting audio to text: {error}")
        raise error


async def convert_text_to_speech(text: str, to: str, waba: str) -> bytes:
    openai_key = get_waba_config(waba)["openai_key"]

    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                "https://api.openai.com/v1/audio/speech",
                json={
                    "model": "tts-1",
                    "voice": "alloy",
                    "input": text,
                    "response_format": "mp3",
                    "speed": 1.0,
                },
                headers={
                    "Authorization": f"Bearer {openai_key}",
                    "Content-Type": "application/json",
                },
            )
            response.raise_for_status()

        logger.info("Audio content received from OpenAI")

        return response.content
    except Exception as error:
        logger.info(f"Error converting text to speech: {error}")
        raise error
