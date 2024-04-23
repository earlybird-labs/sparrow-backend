import time
import json
import os
from pprint import pprint

from .config import SLACK_USER_TOKEN
from .llm import (
    classify_user_request,
    create_speech,
    llm_response,
    create_title_from_transcript,
    format_response_in_markdown,
    create_thread,
    create_vectorstore,
    modify_thread,
    create_run,
    run_steps,
    retrieve_message,
    add_message_to_thread,
)
from .models import RequestType, AIResponse
from .helpers import process_file_upload, format_user_message
from .services import create_db_thread, find_db_thread_by_id, find_db_thread
from .utils import (
    fetch_and_format_thread_messages,
    safe_say,
)
from .workflows.blocks.raise_issue import generate_issue_prompt_blocks
from .workflows.forms.onboard import create_onboarding_message, create_onboarding_modal
from .logger import logger

# Global dictionary to store context
ephemeral_context = {}


def get_thread_in_db(message, thread_ts, ts):
    if not thread_ts:
        thread_ts = ts

    thread_id = find_db_thread(message.get("channel"), thread_ts)
    print("OG thread_id", thread_id)
    print("type(thread_id) at OG", type(thread_id))

    if not thread_id:
        oai_thread = create_thread()
        vectorstore_id = create_vectorstore(str(thread_ts)).id
        insert_result = create_db_thread(
            message.get("channel"), thread_ts, oai_thread.id, vectorstore_id
        )
        thread_id = insert_result.inserted_id
        pprint("if not thread_id")
    else:
        thread_id.get("_id")
        pprint("else thread_id")

    print("end of get_thread_in_db", type(thread_id))
    if type(thread_id) == dict:
        thread_id = thread_id["_id"]
    return thread_id


def handle_message(ack, client, event, message, say):
    """
    Handles incoming messages by determining the type of request and responding appropriately.

    :param ack: Function to acknowledge the event.
    :param client: Slack client for API interactions.
    :param event: Event data containing message details.
    :param message: Message details from the event.
    :param say: Function to send messages to the channel.
    """
    ack()

    bot_id = client.auth_test()["user_id"]
    ignore_list = ["message_deleted", "message_changed"]

    if event.get("subtype") not in ignore_list:
        logger.info(f"event:\n{json.dumps(event, indent=4)}")
        bot_mention = bot_id in message.get("text")
        has_files = message.get("files") is not None
        request_type = RequestType.conversation
        thread_ts = message.get("thread_ts", None)
        ts = message.get("ts", None)

        if not has_files:
            request_type = classify_user_request(event["text"])
            logger.info(f"request_type: {request_type}")
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
                print("\n\nPM request\n\n")
                thread_id = get_thread_in_db(message, thread_ts, ts)
                handle_pm_request(client, say, event, message, bot_id)
            elif request_type == RequestType.ai_conversation:
                thread_id = get_thread_in_db(message, thread_ts, ts)
                handle_direct_message(client, say, event, message, bot_id)

        if bot_mention:
            logger.info("Handling direct message")
            thread_id = get_thread_in_db(message, thread_ts, ts)
            handle_direct_message(client, say, event, message, bot_id, thread_id)
        elif thread_ts is not None:
            if bot_already_in_thread(
                client, message.get("thread_ts"), message.get("channel")
            ):
                thread_id = get_thread_in_db(message, thread_ts, ts)
                print(thread_id)
                logger.info("Handling thread message")
                handle_thread_message(
                    client, say, event, message, bot_id, request_type, thread_id
                )


def handle_pm_request(client, say, event, message, bot_id):
    """
    Handles private messages that may lead to creating a Jira issue.

    :param client: Slack client for API interactions.
    :param say: Function to send messages to the channel.
    :param event: Event data containing message details.
    :param message: Message details from the event.
    :param bot_id: ID of the bot user.
    """
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
    ephemeral_context[ephemeral_id] = message_ts


def handle_create_jira_yes(ack, body, client, respond):
    """
    Handles the affirmative response to creating a Jira issue.

    :param ack: Function to acknowledge the event.
    :param body: Body of the response containing user and message details.
    :param client: Slack client for API interactions.
    :param respond: Function to send follow-up messages.
    """
    ack()

    ephemeral_id = body["container"]["message_ts"]
    user_id = body["user"]["id"]
    channel_id = body["channel"]["id"]
    original_message_ts = ephemeral_context.get(ephemeral_id)

    client.chat_postMessage(
        channel=channel_id,
        thread_ts=original_message_ts,
        text=f"<@{user_id}>, Could you describe the request in more detail?",
    )

    respond(
        text="Great, let's discuss your request in the thread above! :ebl:",
        delete_original=True,
    )


def handle_create_jira_no(ack, body, client, say, respond):
    """
    Handles the negative response to creating a Jira issue.

    :param ack: Function to acknowledge the event.
    :param body: Body of the response containing user and message details.
    :param client: Slack client for API interactions.
    :param say: Function to send messages to the channel.
    :param respond: Function to send follow-up messages.
    """
    ack()

    bot_id = client.auth_test()["user_id"]

    respond(
        text=f"No worries! If you need any help just use <@{bot_id}> for help! :ebl:",
        thread_ts=body["container"]["message_ts"],
        delete_original=True,
    )


def handle_reaction_added(ack, client, event):
    """
    Handles reactions added to messages.

    :param ack: Function to acknowledge the event.
    :param client: Slack client for API interactions.
    :param event: Event data containing reaction details.
    """
    ack()
    pprint(event)
    reaction_name = event.get("reaction")
    pprint(reaction_name)
    if reaction_name == "ebl":
        pprint("EBL reaction added")


def handle_sparrow(ack, client, respond, command):
    """
    Handles specific commands directed at the bot.

    :param ack: Function to acknowledge the command.
    :param client: Slack client for API interactions.
    :param respond: Function to send responses to the command.
    :param command: Command details.
    """
    ack()
    request = command.get("text")
    pprint(request)
    # response = agent.run(request)


def handle_direct_message(client, say, event, message, bot_id, thread_id=None):
    """
    Handles direct messages to the bot, with or without file attachments.

    :param client: Slack client for API interactions.
    :param say: Function to send messages to the channel.
    :param event: Event data containing message details.
    :param message: Message details from the event.
    :param bot_id: ID of the bot user.
    """
    if message.get("files"):
        logger.info("Handling direct message with file")
        handle_message_with_file(client, say, event, message, bot_id, thread_id)
    else:
        logger.info("Handling direct message without file")
        user_message = format_user_message(message, bot_id)
        response = llm_response([{"role": "user", "content": user_message}])
        process_response(response, False, client, say, event)


def handle_thread_message(
    client,
    say,
    event,
    message,
    bot_id,
    request_type=RequestType.bug_report,
    thread_id=None,
):
    """
    Handles messages within a thread, determining if the bot should respond based on its previous involvement.

    :param client: Slack client for API interactions.
    :param say: Function to send messages to the channel.
    :param event: Event data containing message details.
    :param message: Message details from the event.
    :param bot_id: ID of the bot user.
    :param request_type: Type of request identified in the message.
    """
    formatted_messages = fetch_and_format_thread_messages(client, message)
    if message.get("files"):
        logger.info("Handling thread message with file")
        handle_message_with_file(
            client,
            say,
            event,
            message,
            bot_id,
            formatted_messages,
            request_type,
            thread_id,
        )
    else:
        logger.info("Handling thread message without file")
        logger.info(f"request_type: {request_type}")
        response = llm_response(formatted_messages, request_type=request_type)
        process_response(response, False, client, say, event)


def handle_message_with_file(
    client,
    say,
    event,
    message,
    bot_id,
    additional_messages=None,
    request_type=RequestType.conversation,
    thread_id=None,
):
    """
    Processes messages that include file attachments, handling different types of uploads.

    :param client: Slack client for API interactions.
    :param say: Function to send messages to the channel.
    :param event: Event data containing message details.
    :param message: Message details from the event.
    :param bot_id: ID of the bot user.
    :param additional_messages: Additional messages related to the main message.
    :param request_type: Type of request identified in the message.
    """

    print("thread_id in handle_message_with_file", thread_id)
    print("type(thread_id) in handle_message_with_file", type(thread_id))
    # loaded_thread_id = json.loads(thread_id)
    # print("loaded_thread_id", loaded_thread_id)
    # print("type(loaded_thread_id)", type(loaded_thread_id))
    print("\n\n")

    file_datas, speech_mode, vectorstore = process_file_upload(
        SLACK_USER_TOKEN, client, message, thread_id
    )

    user_message = format_user_message(message, bot_id, file_datas)
    logger.info(f"user_message: {user_message}")

    if vectorstore:
        vectorstore_id = find_db_thread_by_id(thread_id).get("vectorstore_id")
        print("vectorstore_id", vectorstore_id)
        oai_thread = find_db_thread_by_id(thread_id)["oai_thread"]
        modify_thread(oai_thread, [vectorstore_id])
        print("modify_thread")

        add_message_to_thread(oai_thread, user_message, "user")
        print("add_message_to_thread")
        run_id = create_run(oai_thread).id
        print("create_run")
        completed = False
        while not completed:
            steps = run_steps(oai_thread, run_id)
            for step in steps.data:
                try:
                    if step.status == "completed":
                        msg_id = step.step_details.message_creation.message_id
                        result = retrieve_message(msg_id, oai_thread)
                        completed = True
                        break
                except Exception as e:
                    print(f"Error processing step: {e}")
                    completed = False
                time.sleep(1)
        user_message += "Document Search Results:\n" + result

    all_messages = compile_messages(additional_messages, user_message)
    logger.info(f"all_messages: {all_messages}")
    response = llm_response(all_messages, request_type=request_type)
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
    process_response(response, speech_mode, client, say, event)


def bot_already_in_thread(client, thread_ts, channel_id):
    """
    Checks if the bot has already been mentioned in the thread or has sent a message in the thread.

    :param client: The Slack client to interact with the Slack API.
    :param thread_ts: The timestamp of the thread's parent message.
    :param channel_id: The ID of the channel where the thread exists.
    :return: Boolean indicating if the bot is already in the thread.
    """
    try:
        bot_id = client.auth_test()["user_id"]
        response = client.conversations_replies(channel=channel_id, ts=thread_ts)
        messages = response.get("messages", [])
        for message in messages:
            if message.get("user") == bot_id:
                return True
            if f"<@{bot_id}>" in message.get("text", ""):
                return True
        return False
    except Exception as e:
        print(f"Error checking if bot is in thread: {e}")
        return False


def handle_onboarding_modal_open(ack, body, client):
    """
    Opens an onboarding modal when triggered by a user action.

    :param ack: Function to acknowledge the action.
    :param body: Body of the request containing trigger details.
    :param client: Slack client for API interactions.
    """
    ack()
    client.views_open(
        trigger_id=body["trigger_id"],
        view=create_onboarding_modal(),
    )


def handle_onboarding_modal_submit(ack, body, view):
    """
    Handles the submission of data from the onboarding modal.

    :param ack: Function to acknowledge the submission.
    :param body: Body of the submission containing user and form details.
    :param view: View details from the modal submission.
    """
    ack()
    pprint(body)
    pprint(view)


def compile_messages(additional_messages, user_message):
    """
    Compiles messages into a structured format for processing.

    :param additional_messages: Additional messages related to the main message.
    :param user_message: The primary user message.
    :return: List of structured messages.
    """
    all_messages = additional_messages if additional_messages else []
    all_messages.append({"role": "user", "content": user_message})
    return all_messages


def process_response(response, speech_mode, client, say, event):
    """
    Processes the response from the language model and sends it to the user.

    :param response: The response from the language model.
    :param speech_mode: Boolean indicating if the response should be spoken.
    :param client: Slack client for API interactions.
    :param say: Function to send messages to the channel.
    :param event: Event data containing message details.
    """
    if isinstance(response, AIResponse):
        response = response.ai_response
    if speech_mode:
        create_speech(response)
        handle_speak(client, event["channel"], response, thread_ts=event["ts"])
    else:
        formatted_response = format_response_in_markdown(response)
        safe_say(say, text=formatted_response, thread_ts=event["ts"])


def handle_speak(client, channel, ai_response, thread_ts=None):
    """
    Handles the speaking of responses, converting text to speech and sending as an audio file.

    :param client: Slack client for API interactions.
    :param channel: Channel to send the audio file.
    :param ai_response: The response text to be spoken.
    :param thread_ts: Optional thread timestamp to send the response in a thread.
    """
    try:
        file_path = "tmp/speech.mp3"
        os.makedirs(os.path.dirname(file_path), exist_ok=True)
        title = create_title_from_transcript(ai_response)
        upload_kwargs = {
            "channels": channel,
            "file": file_path,
            "title": title,
            "initial_comment": ai_response,
        }
        if thread_ts:
            upload_kwargs["thread_ts"] = thread_ts
        pprint(upload_kwargs)
        result = client.files_upload_v2(**upload_kwargs)
    except Exception as e:
        logger.error(f"Error uploading file: {str(e)}")


def handle_url_verification(event_data):
    """
    Verifies the URL during the Slack Event API setup.

    :param event_data: Event data containing the verification challenge.
    :return: Challenge answer for verification.
    """
    return event_data["challenge"]
