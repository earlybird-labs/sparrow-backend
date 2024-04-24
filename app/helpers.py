# helpers.py

from typing import Any, Dict, List, Optional, Tuple
from slack_sdk import WebClient
from .logger import logger
from .llm import LLMClient
from .database import Database
from .constants import text_file_types
from .utils import get_file_data, save_file, download_and_save_file


def process_file_upload(
    token: str,
    client: WebClient,
    message: Dict[str, Any],
    database: Database,
    thread_id: Optional[str] = None,
) -> Tuple[List[Dict[str, str]], bool, bool]:
    files = message.get("files")
    file_datas = []
    speech_mode = False
    vectorstore = False

    logger.debug(f"thread_id: {thread_id}, type(thread_id): {type(thread_id)}")
    thread_in_db = database.find_db_thread_by_id(thread_id)

    if not thread_in_db:
        thread_in_db = database.find_db_thread(
            message.get("channel"), message.get("ts")
        )

    for file in files:
        file_url, file_type, mimetype = share_file_and_get_url(
            token, client, file.get("id")
        )

        logger.debug(
            f"file_url: {file_url}, file_type: {file_type}, mimetype: {mimetype}"
        )

        file_data = process_file_content(file_url, file_type, mimetype, message)

        if file_data.get("upload_type") == "text_file":
            vectorstore = True
            file_id = file_data.get("content")
            vectorstore_id = thread_in_db.get("vectorstore_id")
            database.update_thread(
                thread_in_db, {"num_files": thread_in_db.get("num_files", 0) + 1}
            )
            LLMClient.add_file_to_vectorstore(vectorstore_id, file_id)
        else:
            file_datas.append(file_data)

        speech_mode |= file_type in ["webm", "mp4", "mp3", "wav", "m4a"]
        revoke_file_public_access(token, client, file.get("id"))

    return file_datas, speech_mode, vectorstore


def share_file_and_get_url(
    token: str, client: WebClient, file_id: str
) -> Tuple[str, str, str]:
    file_info = client.files_info(file=file_id).data.get("file")
    client.files_sharedPublicURL(token=token, file=file_id)
    return (
        construct_file_url(file_info),
        file_info.get("filetype"),
        file_info.get("mimetype"),
    )


def construct_file_url(file_info: Dict[str, Any]) -> str:
    public_link = file_info.get("permalink_public")
    url_private = file_info.get("url_private")
    pub_secret = public_link.split("-")[-1]
    return f"{url_private}?pub_secret={pub_secret}"


def process_file_content(
    file_url: str, file_type: str, mimetype: str, message: Dict[str, Any]
) -> Optional[Dict[str, str]]:
    llm_client = LLMClient()

    if file_type in ["jpg", "jpeg", "png", "webp", "gif"]:
        return {
            "upload_type": "image",
            "content": llm_client.describe_vision_anthropic(
                file_url, mimetype, message.get("text")
            ),
        }
    elif file_type in ["webm", "mp4", "mp3", "wav", "m4a"]:
        logger.info("Transcribing audio")
        return {
            "upload_type": "audio",
            "content": llm_client.transcribe_audio(file_url, file_type),
        }
    elif file_type in text_file_types:
        logger.info("Processing text file")
        file_path = download_and_save_file(file_url, file_type)
        if file_path:
            upload_response = llm_client.upload_file(file_path)
            if upload_response and hasattr(upload_response, "id"):
                file_id = upload_response.id
                logger.debug(f"Uploaded file ID: {file_id}")
                return {
                    "upload_type": "text_file",
                    "content": file_id,
                }
            else:
                logger.error("Failed to upload file or invalid upload response")
        else:
            logger.error("File download failed or file path is None")
    else:
        logger.error(f"Unsupported file type: {file_type}")

    return None


def revoke_file_public_access(token: str, client: WebClient, file_id: str) -> None:
    client.files_revokePublicURL(token=token, file=file_id)


def format_user_message(
    message: Dict[str, Any],
    bot_id: str,
    file_data: Optional[List[Dict[str, str]]] = None,
) -> str:
    user_message = message.get("text", "").replace(f"<@{bot_id}>", "")
    if file_data:
        user_message += "\nUser uploaded file contents:\n" + "".join(
            [f"{file['upload_type']}: {file['content']}\n" for file in file_data]
        )
    return user_message


def compile_messages(
    additional_messages: Optional[List[Dict[str, str]]], user_message: str
) -> List[Dict[str, str]]:
    all_messages = additional_messages if additional_messages else []
    all_messages.append({"role": "user", "content": user_message})
    return all_messages
