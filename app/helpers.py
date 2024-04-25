# helpers.py

from typing import Any, Dict, List, Optional, Tuple
from slack_sdk import WebClient
from .logger import logger
from .llm import LLMClient
from .database import Database, db
from .constants import text_file_types
from .utils import get_file_data, save_file, download_and_save_file
from .handlers.file_handler import FileHandler


def process_message_with_files(
    client: WebClient,
    message: Dict[str, Any],
    llm_client: LLMClient,
) -> Tuple[List[Dict[str, str]], bool]:
    file_handler = FileHandler(client, llm_client)
    logger.info("Processing files")
    file_data = file_handler.process_files(message)
    return file_data


def check_for_user_scope(user_id: str, user_scope: str) -> bool:
    return user_scope.split(",").contains(user_id)


def format_user_message(message: Dict[str, Any], bot_id: str) -> str:
    user_message = message.get("text", "").replace(f"<@{bot_id}>", "")
    return user_message


def add_file_data_to_messages(messages, file_data):
    if file_data:
        logger.info(f"File data: {file_data}")
        file_content = "User uploaded file contents:\n" + "".join(
            [f"{file['upload_type']}: {file['content']}\n" for file in file_data]
        )
        messages.append({"role": "user", "content": file_content})
    return messages


def compile_messages(
    additional_messages: Optional[List[Dict[str, str]]], user_message: str
) -> List[Dict[str, str]]:
    all_messages = additional_messages if additional_messages else []
    all_messages.append({"role": "user", "content": user_message})
    return all_messages
