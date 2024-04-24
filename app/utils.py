# utils.py

import os
import time
import re
import requests
import httpx
import base64
from functools import wraps

from typing import Optional

from .logger import logger


def retry(exception_to_check, tries=4, delay=3, backoff=2, logger=None):
    """
    Retry calling the decorated function using an exponential backoff.

    :param exception_to_check: the exception to check. may be a tuple of exceptions to check
    :param tries: number of times to try (not retry) before giving up
    :param delay: initial delay between retries in seconds
    :param backoff: backoff multiplier e.g. value of 2 will double the delay each retry
    :param logger: logger to use. If None, print.
    :return: Decorated function with retry capability.
    """

    def deco_retry(f):
        @wraps(f)
        def f_retry(*args, **kwargs):
            mtries, mdelay = tries, delay
            while mtries > 1:
                try:
                    return f(*args, **kwargs)
                except exception_to_check as e:
                    msg = f"{str(e)}, Retrying in {mdelay} seconds..."
                    if logger:
                        logger.warning(msg)
                    else:
                        print(msg)
                    time.sleep(mdelay)
                    mtries -= 1
                    mdelay *= backoff
            return f(*args, **kwargs)

        return f_retry

    return deco_retry


def save_file(file_url: str, file_type: str) -> str:
    """
    Fetches and saves an audio file from a URL.

    :param file_url: URL of the file to fetch.
    :param file_type: Type of the file (e.g., 'mp3', 'wav', 'pdf')
    :return: Path to the saved file.
    """
    response = httpx.get(file_url)
    filename = f"{int(time.time())}.{file_type}"
    file_path = os.path.join("tmp", filename)

    with open(file_path, "wb") as file:
        file.write(response.content)

    return file_path


def download_and_save_file(file_url: str, file_type: str) -> Optional[str]:
    try:
        response = requests.get(file_url, stream=True)
        timestamp = int(time.time())
        if response.status_code == 200:
            file_path = f"/tmp/{timestamp}.{file_type}"
            with open(file_path, "wb") as f:
                for chunk in response.iter_content(chunk_size=8192):
                    f.write(chunk)
            return file_path
        else:
            logger.error(
                f"Failed to download file: {file_url} with status code: {response.status_code}"
            )
    except Exception as e:
        logger.error(
            f"Exception occurred while downloading file: {file_url}, Error: {str(e)}"
        )
    return None


def delete_file(file_path: str) -> None:
    """
    Deletes a file from the filesystem.

    :param file_path: Path to the file to be deleted.
    """
    os.remove(file_path)


def get_file_data(file_url: str) -> str:
    """
    Fetches file data from a URL and encodes it in base64.

    :param file_url: URL of the file to fetch.
    :return: Base64 encoded string of the file data.
    """
    response = httpx.get(file_url)
    file_data = base64.b64encode(response.content).decode("utf-8")
    return file_data


def fetch_and_format_thread_messages(client, message):
    """
    Fetches all messages from a thread and formats them.

    :param client: The Slack client instance used to interact with the Slack API.
    :param message: The message event data containing details about the thread.
    :return: A list of dictionaries, each representing a formatted message.
    """
    try:
        thread_ts = message["thread_ts"]
        channel_id = message["channel"]
        bot_id = client.auth_test()["user_id"]

        thread_messages_response = client.conversations_replies(
            channel=channel_id, ts=thread_ts
        )
        thread_messages = thread_messages_response["messages"]

        formatted_messages = []
        for msg in thread_messages:
            if msg.get("text") != "":
                role = "assistant" if msg.get("user") == bot_id else "user"
                formatted_messages.append({"role": role, "content": msg["text"]})

        return formatted_messages
    except Exception as e:
        logger.error(f"Error fetching or formatting thread messages: {e}")
        return []
