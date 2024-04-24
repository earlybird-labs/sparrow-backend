# handlers.py

import json
import os
import time
from typing import Dict, Any, List, Optional

from .config import SLACK_USER_TOKEN
from .llm import LLMClient
from .models import RequestType, AIResponse
from .helpers import process_file_upload, format_user_message
from .database import Database
from .utils import fetch_and_format_thread_messages
from .logger import logger
from .slack_api import SlackClient
from .workflows.blocks.raise_issue import generate_issue_prompt_blocks
from .workflows.forms.onboard import create_onboarding_message, create_onboarding_modal


class MessageHandler:
    def __init__(
        self, slack_client: SlackClient, llm_client: LLMClient, database: Database
    ):
        self.slack_client = slack_client
        self.llm_client = llm_client
        self.database = database
        self.ephemeral_context = {}

    def handle_message(self, ack, client, event, message, say):
        ack()  # Correctly await the ack() coroutine

        # Await the auth_test() coroutine and then access its result
        auth_test_result = client.auth_test()
        bot_id = auth_test_result["user_id"]

        ignore_list = ["message_deleted", "message_changed"]

        if event.get("subtype") not in ignore_list:
            logger.info(f"event:\n{json.dumps(event, indent=4)}")
            self._process_message(client, say, event, message, bot_id)

    def _process_message(self, client, say, event, message, bot_id):
        bot_mention = bot_id in message.get("text", "")
        has_files = message.get("files") is not None
        thread_ts = message.get("thread_ts")
        ts = message.get("ts")

        if not has_files:
            self._handle_text_message(
                client, say, event, message, bot_id, bot_mention, thread_ts
            )
        else:
            self._handle_file_message(
                client, say, event, message, bot_id, bot_mention, thread_ts, ts
            )

    def _handle_text_message(
        self, client, say, event, message, bot_id, bot_mention, thread_ts
    ):
        request_type = self._classify_request(event["text"])
        logger.info(f"request_type: {request_type}")
        self._handle_request(
            request_type, bot_mention, thread_ts, client, say, event, message, bot_id
        )

    def _handle_file_message(
        self, client, say, event, message, bot_id, bot_mention, thread_ts, ts
    ):
        if bot_mention:
            logger.info("Handling direct message")
            thread_id = self._get_or_create_thread(message, thread_ts, ts)
            self._handle_direct_message(client, say, event, message, bot_id, thread_id)
        elif thread_ts is not None:
            if self._bot_already_in_thread(thread_ts, message.get("channel")):
                thread_id = self._get_or_create_thread(message, thread_ts, ts)
                logger.info("Handling thread message")
                self._handle_thread_message(
                    client, say, event, message, bot_id, thread_id
                )

    def _classify_request(self, text: str) -> RequestType:
        request_type = self.llm_client.classify_user_request(text)
        return request_type

    def _handle_request(
        self, request_type, bot_mention, thread_ts, client, say, event, message, bot_id
    ):
        request_detected = (
            request_type
            in (
                RequestType.feature_request,
                RequestType.bug_report,
                RequestType.general_request,
            )
            and not bot_mention
            and thread_ts is None
        )

        if request_detected:
            logger.info("PM request detected")
            thread_id = self._get_or_create_thread(
                message, thread_ts, message.get("ts")
            )
            self._handle_pm_request(client, say, event, message, bot_id)
        elif request_type == RequestType.ai_conversation:
            thread_id = self._get_or_create_thread(
                message, thread_ts, message.get("ts")
            )
            self._handle_direct_message(client, say, event, message, bot_id, thread_id)

    def _get_or_create_thread(self, message, thread_ts, ts):
        thread_ts = thread_ts or ts
        thread_id = self.database.find_db_thread(message.get("channel"), thread_ts)
        logger.debug(f"OG thread_id: {thread_id}, type: {type(thread_id)}")
        logger.debug(f"OG ts: {ts}, OG thread_ts: {thread_ts}")

        if not thread_id:
            oai_thread = self.llm_client.create_thread()
            vectorstore_id = self.llm_client.create_vectorstore(str(thread_ts)).id
            insert_result = self.database.create_db_thread(
                message.get("channel"), thread_ts, oai_thread.id, vectorstore_id
            )
            thread_id = insert_result.inserted_id
            logger.debug("Thread not found, created new thread")
        else:
            thread_id.get("_id")
            logger.debug("Found existing thread")

        logger.debug(
            f"End of get_thread_in_db, thread_id: {thread_id}, type: {type(thread_id)}"
        )
        return thread_id["_id"] if isinstance(thread_id, dict) else thread_id

    def _handle_pm_request(self, client, say, event, message, bot_id):
        user_id = message["user"]
        channel_id = message["channel"]
        message_ts = message["ts"]
        blocks = generate_issue_prompt_blocks()

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

        bot_id = client.auth_test()["user_id"]

        respond(
            text=f"No worries! If you need any help just use <@{bot_id}> for help! :ebl:",
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

    def _handle_direct_message(
        self, client, say, event, message, bot_id, thread_id=None
    ):
        if message.get("files"):
            logger.info("Handling direct message with file")
            self._handle_message_with_file(
                client, say, event, message, bot_id, thread_id
            )
        else:
            logger.info("Handling direct message without file")
            user_message = format_user_message(message, bot_id)
            response = self.llm_client.llm_response(
                [{"role": "user", "content": user_message}]
            )
            self._process_response(response, False, client, say, event)

    def _handle_thread_message(self, client, say, event, message, bot_id, thread_id):
        formatted_messages = fetch_and_format_thread_messages(client, message)
        if message.get("files"):
            logger.info("Handling thread message with file")
            self._handle_message_with_file(
                client,
                say,
                event,
                message,
                bot_id,
                formatted_messages,
                thread_id,
            )
        else:
            logger.info("Handling thread message without file")
            user_message = formatted_messages[-1]["content"]
            oai_thread = self.database.find_db_thread_by_id(thread_id)["oai_thread"]
            self.llm_client.add_message_to_thread(oai_thread, user_message, "user")
            self._process_thread_run(oai_thread, formatted_messages, client, say, event)

    def _process_thread_run(self, oai_thread, formatted_messages, client, say, event):
        run_id = self.llm_client.create_run(oai_thread).id
        logger.info("Run created")
        completed = False
        while not completed:
            steps = self.llm_client.run_steps(oai_thread, run_id)
            for step in steps.data:
                try:
                    if step.status == "completed":
                        msg_id = step.step_details.message_creation.message_id
                        result = self.llm_client.retrieve_message(msg_id, oai_thread)
                        completed = True
                        break
                except Exception as e:
                    logger.error(f"Error processing step: {e}")
                    completed = False
                time.sleep(1)
        context_found = "Document Search Results:\n" + result
        formatted_messages.append({"role": "user", "content": context_found})
        response = self.llm_client.llm_response(formatted_messages)
        self._process_response(response, False, client, say, event)

    def _handle_message_with_file(
        self,
        client,
        say,
        event,
        message,
        bot_id,
        additional_messages=None,
        thread_id=None,
    ):
        logger.debug(
            f"Thread ID in handle_message_with_file: {thread_id}, type: {type(thread_id)}"
        )

        file_datas, speech_mode, vectorstore = process_file_upload(
            SLACK_USER_TOKEN, client, message, thread_id
        )

        user_message = format_user_message(message, bot_id, file_datas)
        logger.info(f"user_message: {user_message}")

        if vectorstore:
            db_thread = self.database.find_db_thread_by_id(thread_id)
            if not db_thread:
                db_thread = self.database.find_db_thread(
                    message.get("channel"), message.get("ts")
                )
                thread_id = db_thread.get("_id")
                vectorstore_id = db_thread.get("vectorstore_id")
            else:
                vectorstore_id = db_thread.get("vectorstore_id")
            logger.info(f"vectorstore_id: {vectorstore_id}")
            oai_thread = self.database.find_db_thread_by_id(thread_id)["oai_thread"]
            self.llm_client.modify_thread(oai_thread, [vectorstore_id])
            logger.info("Thread modified")

            self.llm_client.add_message_to_thread(oai_thread, user_message, "user")
            logger.info("Message added to thread")
            self._process_thread_run(
                oai_thread, additional_messages, client, say, event
            )
        else:
            all_messages = self._compile_messages(additional_messages, user_message)
            logger.info(f"all_messages: {all_messages}")
            response = self.llm_client.llm_response(all_messages)
            self._process_file_response(
                response, file_datas, speech_mode, client, say, event, message
            )

    def _process_file_response(
        self, response, file_datas, speech_mode, client, say, event, message
    ):
        transcription = None
        for file in file_datas:
            if file["upload_type"] == "audio":
                if transcription:
                    transcription += "\n" + file["content"]
            elif file["upload_type"] == "image":
                transcription = file["content"]
        if transcription:
            client.chat_update(
                token=SLACK_USER_TOKEN,
                channel=message["channel"],
                text=transcription,
                ts=message["ts"],
            )
        self._process_response(response, speech_mode, client, say, event)

    def _bot_already_in_thread(self, thread_ts: str, channel_id: str) -> bool:
        try:
            bot_id = self.slack_client.client.auth_test()["user_id"]
            response = self.slack_client.client.conversations_replies(
                channel=channel_id, ts=thread_ts
            )
            messages = response.get("messages", [])
            for message in messages:
                if message.get("user") == bot_id or f"<@{bot_id}>" in message.get(
                    "text", ""
                ):
                    return True
            return False
        except Exception as e:
            logger.error(f"Error checking if bot is in thread: {e}")
            return False

    def handle_onboarding_modal_open(self, ack, body, client):
        ack()
        client.views_open(
            trigger_id=body["trigger_id"],
            view=create_onboarding_modal(),
        )

    def handle_onboarding_modal_submit(self, ack, body, view):
        ack()
        logger.debug(f"Onboarding modal submitted: {body}")
        logger.debug(f"Onboarding modal view: {view}")

    def _compile_messages(
        self, additional_messages: List[Dict[str, str]], user_message: str
    ) -> List[Dict[str, str]]:
        if not isinstance(additional_messages, list):
            additional_messages = []

        all_messages = additional_messages
        all_messages.append({"role": "user", "content": user_message})
        return all_messages

    def _process_response(
        self, response: Optional[AIResponse], speech_mode: bool, client, say, event
    ):
        if response is None:
            logger.error("Failed to generate a response from the LLM")
            return

        if isinstance(response, AIResponse):
            response = response.ai_response

        if speech_mode:
            self.llm_client.create_speech(response)
            self._handle_speak(
                client, event["channel"], response, thread_ts=event["ts"]
            )
        else:
            formatted_response = self.llm_client.format_response_in_markdown(response)
            self.slack_client.say(
                client=client,
                channel=event["channel"],
                text=formatted_response,
                thread_ts=event["ts"],
            )

    def _handle_speak(
        self, channel: str, ai_response: str, thread_ts: Optional[str] = None
    ):
        try:
            file_path = "tmp/speech.mp3"
            os.makedirs(os.path.dirname(file_path), exist_ok=True)
            title = self.llm_client.create_title_from_transcript(ai_response)
            self.slack_client.upload_file(
                channel=channel,
                file_path=file_path,
                title=title,
                initial_comment=ai_response,
                thread_ts=thread_ts,
            )
        except Exception as e:
            logger.error(f"Error uploading file: {str(e)}")
