# helpers.py

import re

from typing import Any, Dict, List, Optional, Tuple
from slack_sdk import WebClient
from app.logger import logger
from app.llm import LLMClient
from app.handlers.file_handler import FileHandler


def process_message_with_files(
    token: str,
    client: WebClient,
    message: Dict[str, Any],
    llm_client: LLMClient,
) -> Tuple[List[Dict[str, str]], bool]:
    file_handler = FileHandler(token, client, llm_client)
    logger.info("Processing files")
    file_data = file_handler.process_files(message)
    return file_data


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


def find_mentioned_users(text):
    """
    Searches for user mentions in a given text formatted as <@USERID> in Slack.
    """
    pattern = r"<@([A-Z0-9]+)>"
    return re.findall(pattern, text)


def get_user_real_name(client: WebClient, user_id: str, token: str) -> str:
    """
    Fetches the real name of a user given their user ID using the Slack API.
    """
    try:
        response = client.users_info(token=token, user=user_id).data
        if response["ok"]:
            return response["user"]["real_name"]
        else:
            return f"User not found: {user_id}"
    except Exception as e:
        return f"API error: {str(e)}"


def replace_mentions_with_real_names(client: WebClient, text: str, token: str) -> str:
    """
    Replaces all Slack user ID mentions in the text with their real names.
    """
    mentioned_users = find_mentioned_users(text)
    for user_id in mentioned_users:
        real_name = get_user_real_name(client, user_id, token).replace(" ", "_")
        text = re.sub(f"<@{user_id}>", f"@{real_name}", text)
    return text


def format_files_array(files):
    """
    Formats file information for easier handling, including additional metadata.
    """
    formatted_files = []
    for file in files:
        file_info = {
            "id": file["id"],
            "url": file["url_private_download"],
            "mimetype": file.get("mimetype", "unknown"),
            "filetype": file.get("filetype", "unknown"),
        }
        formatted_files.append(file_info)
    return formatted_files
