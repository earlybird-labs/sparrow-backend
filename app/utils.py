import logging
import time
import base64
import httpx
from functools import wraps
from slack_sdk.errors import SlackApiError


import os
import time
import re


def retry(exception_to_check, tries=4, delay=3, backoff=2, logger=None):
    """
    Retry calling the decorated function using an exponential backoff.

    :param exception_to_check: the exception to check. may be a tuple of exceptions to check
    :param tries: number of times to try (not retry) before giving up
    :param delay: initial delay between retries in seconds
    :param backoff: backoff multiplier e.g. value of 2 will double the delay each retry
    :param logger: logger to use. If None, print.
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


# Apply the retry decorator to the say function
@retry(SlackApiError, tries=5, delay=2, backoff=3)
def safe_say(say, *args, **kwargs):
    # Check if 'text' is in kwargs or if it's empty
    if "text" not in kwargs or not kwargs["text"]:
        # Provide a default text message or raise an error
        kwargs["text"] = "Sparrow is facing an issue, can you resend the message?"
    # Proceed to call the original say function with the updated kwargs
    try:
        say(*args, **kwargs)
    except SlackApiError as e:
        # Handle the SlackApiError
        print(f"Slack API Error: {e}")


def format_markdown_to_slack_markdown(text):
    """
    Converts markdown syntax in a string to Slack's markdown syntax using regex.
    It handles both italic and bold markdown syntax conversions.

    :param text: The string containing markdown syntax for bold and italic.
    :return: A string with markdown syntax converted to Slack's markdown format.
    """
    # Convert markdown italic syntax (*) to Slack's underscore italic (_)
    text = re.sub(r"\*(.*?)\*", r"_\1_", text)

    # Convert markdown bold syntax (**) to Slack's asterisk bold (*)
    formatted_text = re.sub(r"\*\*(.*?)\*\*", r"*\1*", text)

    return formatted_text


def is_bot_thread(client, messages):
    bot_id = client.auth_test()["user_id"]
    return any(f"<@{bot_id}>" in msg["content"] for msg in messages)


def fetch_and_format_thread_messages(client, message):
    """
    Fetches all messages from a thread and formats them.

    Parameters:
    - client: The Slack client instance used to interact with the Slack API.
    - message: The message event data containing details about the thread.

    Returns:
    A list of dictionaries, each representing a formatted message.
    """
    try:
        thread_ts = message["thread_ts"]
        channel_id = message["channel"]
        bot_id = client.auth_test()["user_id"]

        # Fetch all messages from the thread
        thread_messages_response = client.conversations_replies(
            channel=channel_id, ts=thread_ts
        )
        thread_messages = thread_messages_response["messages"]

        # Format messages
        formatted_messages = []
        for msg in thread_messages:
            # Determine the role based on the user who sent the message
            role = "assistant" if msg.get("user") == bot_id else "user"
            formatted_messages.append({"role": role, "content": msg["text"]})

        return formatted_messages
    except Exception as e:
        logging.error(f"Error fetching or formatting thread messages: {e}")
        return []


def save_audio_file(file_url, file_type):
    # Fetch the audio file content from the URL
    response = httpx.get(file_url)

    # Generate a filename with the current timestamp and the provided file type
    filename = f"{int(time.time())}.{file_type}"

    # Define the path where the file will be saved (ensure the app/tmp directory exists)
    file_path = os.path.join("tmp", filename)

    # Save the file content to the specified path
    with open(file_path, "wb") as file:
        file.write(response.content)

    # Return the path to the saved file
    return file_path


def delete_file(file_path):
    os.remove(file_path)


def get_file_data(file_url):
    response = httpx.get(file_url)
    file_data = base64.b64encode(response.content).decode("utf-8")
    return file_data
