# slack_api.py

from typing import Any, Dict, List
from slack_sdk.errors import SlackApiError
from .logger import logger


class SlackClient:
    def __init__(self, client):
        self.client = client

    def say(self, client, channel, text, thread_ts=None):
        try:
            client.chat_postMessage(channel=channel, text=text, thread_ts=thread_ts)
        except SlackApiError as e:
            logger.error(f"Slack API Error: {e}")

    def upload_file(self, channel, file_path, title, initial_comment, thread_ts=None):
        try:
            self.client.files_upload(
                channels=channel,
                file=file_path,
                title=title,
                initial_comment=initial_comment,
                thread_ts=thread_ts,
            )
        except SlackApiError as e:
            logger.error(f"Error uploading file: {str(e)}")

    def is_bot_thread(self, messages: List[Dict[str, Any]]) -> bool:
        bot_id = (self.client.auth_test())["user_id"]
        return any(f"<@{bot_id}>" in msg["content"] for msg in messages)

    def fetch_and_format_thread_messages(
        self, message: Dict[str, Any]
    ) -> List[Dict[str, str]]:
        try:
            thread_ts = message["thread_ts"]
            channel_id = message["channel"]
            bot_id = (self.client.auth_test())["user_id"]

            thread_messages_response = self.client.conversations_replies(
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
