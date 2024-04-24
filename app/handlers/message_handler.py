# handlers.py

import json

from ..config import SLACK_USER_TOKEN
from ..llm import LLMClient
from ..models import RequestType
from ..helpers import process_message, format_user_message, add_file_data_to_messages
from ..database import Database
from ..utils import add_user_message_to_messages, fetch_thread_messages
from ..logger import logger
from ..slack_api import SlackClient
from ..workflows.blocks.raise_issue import generate_issue_prompt_blocks


class MessageHandler:
    def __init__(
        self, slack_client: SlackClient, llm_client: LLMClient, database: Database
    ):
        self.slack_client = slack_client
        self.slack_web_client = slack_client.client.client
        self.bot_id = self.slack_web_client.auth_test()["user_id"]
        self.llm_client = llm_client
        self.database = database
        self.ephemeral_context = {}

    def handle_message(self, ack, client, event, message, say):
        ack()  # Correctly await the ack() coroutine

        ignore_list = ["message_deleted", "message_changed"]

        if event.get("subtype") not in ignore_list:
            logger.info(f"event:\n{json.dumps(event, indent=4)}")
            self._process_message(client, say, event, message, self.bot_id)

    def _process_message(self, client, say, event, message, bot_id):
        bot_mention = bot_id in message.get("text", "")
        thread_ts = message.get("thread_ts")
        ts = message.get("ts")

        thread_id = self._get_or_create_thread(message, thread_ts, ts)

        messages = []
        if message.get("files"):
            file_data, speech_mode = process_message(
                SLACK_USER_TOKEN, client, message, self.llm_client
            )
            messages = add_file_data_to_messages(messages, file_data)

        user_message = format_user_message(message, bot_id)
        messages = add_user_message_to_messages(messages, user_message)

        if bot_mention:
            logger.info("Handling direct message")
            self._handle_direct_message(client, say, event, messages)
        elif thread_ts is not None:
            if self._bot_already_in_thread(thread_ts, message.get("channel")):
                logger.info("Handling thread message")
                self._handle_thread_message(client, say, event, messages)
        else:
            request_type = self._classify_request(event["text"])
            logger.info(f"request_type: {request_type}")
            self._handle_request(request_type, client, say, event, message, bot_id)

    def _handle_direct_message(self, client, say, event, messages):
        response = self.llm_client.llm_response(messages)
        logger.info(f"Direct Message Response:\n{json.dumps(response, indent=4)}")
        self._send_response(response, client, say, event)

    def _handle_thread_message(self, client, say, event, messages):
        thread_messages = fetch_thread_messages(client, event)
        messages = thread_messages + messages
        logger.info(f"Thread Messages:\n{json.dumps(messages, indent=4)}")
        response = self.llm_client.llm_response(messages)
        self._send_response(response, client, say, event)

    def _classify_request(self, text: str) -> RequestType:
        request_type = self.llm_client.classify_user_request(text)
        return request_type

    def _handle_request(self, request_type, client, say, event, message, bot_id):
        if request_type in (
            RequestType.feature_request,
            RequestType.bug_report,
            RequestType.general_request,
        ):
            logger.info("PM request detected")
            self._handle_pm_request(client, say, event, message, bot_id)

    def _get_or_create_thread(self, message, thread_ts, ts):
        thread_ts = thread_ts or ts
        thread_id = self.database.find_db_thread(message.get("channel"), thread_ts)

        if not thread_id:
            insert_result = self.database.create_db_thread(
                message.get("channel"), thread_ts
            )
            thread_id = insert_result.inserted_id
            logger.debug("Thread not found, created new thread")
        else:
            thread_id = thread_id.get("_id")
            logger.debug("Found existing thread")

        return thread_id

    def _handle_pm_request(self, client, say, event, message, bot_id):
        user_id = message["user"]
        channel_id = message["channel"]
        message_ts = message["ts"]
        blocks = generate_issue_prompt_blocks()
        self.ephemeral_context[message_ts] = message_ts

        response = client.chat_postEphemeral(
            channel=channel_id,
            user=user_id,
            blocks=blocks,
            text="Do you want help creating a Jira issue?",
        )

        ephemeral_id = response["message_ts"]
        self.ephemeral_context[ephemeral_id] = message_ts

    def handle_create_jira_yes(self, ack, body, client, respond):
        ack()

        ephemeral_id = body["container"]["message_ts"]
        user_id = body["user"]["id"]
        channel_id = body["channel"]["id"]
        original_message_ts = self.ephemeral_context.get(ephemeral_id)

        client.chat_postMessage(
            channel=channel_id,
            thread_ts=original_message_ts,
            text=f"<@{user_id}>, Could you describe the request in more detail?",
        )

        respond(
            text="Great, let's discuss your request in the thread above! :ebl:",
            delete_original=True,
        )

    def handle_create_jira_no(self, ack, body, client, say, respond):
        ack()

        respond(
            text=f"No worries! If you need any help just use <@{self.bot_id}> for help! :ebl:",
            thread_ts=body["container"]["message_ts"],
            delete_original=True,
        )

    def handle_reaction_added(self, ack, client, event):
        ack()
        logger.debug(f"Reaction added event: {event}")
        reaction_name = event.get("reaction")
        logger.debug(f"Reaction name: {reaction_name}")
        if reaction_name == "ebl":
            logger.info("EBL reaction added")

    def handle_sparrow(self, ack, client, respond, command):
        ack()
        request = command.get("text")
        logger.debug(f"Sparrow request: {request}")
        # response = agent.run(request)

    def _send_response(self, ai_response, client, say, event):
        thread_ts = event.get("thread_ts") or event.get("ts")
        say(
            text=ai_response.content,
            thread_ts=thread_ts,
        )

    def _bot_already_in_thread(self, thread_ts, channel):
        replies = self.slack_web_client.conversations_replies(
            channel=channel, ts=thread_ts
        )
        for message in replies["messages"]:
            if message.get("user") == self.bot_id:
                return True
        return False
