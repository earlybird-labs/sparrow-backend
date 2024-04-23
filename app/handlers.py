import json
import logging
import os
from pprint import pprint

from .config import SLACK_USER_TOKEN
from .llm import (
    classify_user_request,
    create_speech,
    describe_vision_anthropic,
    llm_response,
    transcribe_audio,
)
from .models import RequestType
from .utils import (
    fetch_and_format_thread_messages,
    is_bot_thread,
    safe_say,
)
from .workflows.blocks.raise_issue import generate_issue_prompt_blocks
from .workflows.forms.onboard import create_onboarding_message, create_onboarding_modal

# from .agent.main import agent


# At the top of the file, configure basic logging:
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)


# Global dictionary to store context
ephemeral_context = {}


def handle_message(ack, client, event, message, say):
    ack()

    bot_id = client.auth_test()["user_id"]

    ignore_list = ["message_deleted", "message_changed"]

    if event.get("subtype") not in ignore_list:

        is_thread = message.get("thread_ts") is not None
        bot_mention = bot_id in message.get("text")
        has_files = message.get("files") is not None
        request_type = RequestType.conversation

        if not has_files:

            request_type = classify_user_request(event["text"])

            # Replace print with logging:
            logging.info("request_type", request_type)

            request_detected = (
                (
                    request_type
                    in (
                        RequestType.feature_request,
                        RequestType.bug_report,
                        RequestType.general_request,
                    )
                )
                and (not bot_mention)
                and (not is_thread)
            )

            if request_detected:
                print("\n\nPM request\n\n")
                handle_pm_request(client, say, event, message, bot_id)

        if bot_mention:
            logging.info("Handling direct message")
            handle_direct_message(client, say, event, message, bot_id)
        elif is_thread:
            if bot_already_in_thread(
                client, message.get("thread_ts"), message.get("channel")
            ):
                logging.info("Handling thread message")
                handle_thread_message(client, say, event, message, bot_id, request_type)


def handle_pm_request(client, say, event, message, bot_id):
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
    ack()

    ephemeral_id = body["container"]["message_ts"]  # ID of the ephemeral message

    user_id = body["user"]["id"]
    channel_id = body["channel"]["id"]

    original_message_ts = ephemeral_context.get(ephemeral_id)

    # Respond in a thread to the message that triggered the ephemeral message

    client.chat_postMessage(
        channel=channel_id,
        thread_ts=original_message_ts,
        text=f"<@{user_id}>, Could you describe the request in more detail?",
    )

    respond(
        delete_original=True,
    )


def handle_create_jira_no(ack, body, client, say, respond):
    ack()

    pprint(body)

    user_id = body["user"]["id"]
    channel_id = body["channel"]["id"]

    respond(
        text="No worries! If you need any help just use @Sparrow for help! :ebl:",
        thread_ts=body["container"]["message_ts"],
        delete_original=True,
    )

    # client.chat_postEphemeral(
    #     channel=channel_id,
    #     user=user_id,
    #     text="No worries! If you need any help just use @Sparrow for help! :ebl:",
    # )


def handle_reaction_added(ack, client, event):
    ack()
    pprint(event)
    reaction_name = event.get("reaction")
    pprint(reaction_name)
    if reaction_name == "ebl":
        pprint("EBL reaction added")


def handle_sparrow(ack, client, respond, command):
    ack()
    request = command.get("text")
    pprint(request)
    # response = agent.run(request)

    # response_full = f"\nRequest:\n{request}\n\nResponse:\n{response}\n\n"

    # client.chat_postMessage(channel=command.get("channel_id"), text=response_full)


def handle_direct_message(client, say, event, message, bot_id):
    if message.get("files"):
        logging.info("Handling direct message with file")
        handle_message_with_file(client, say, event, message, bot_id)
    else:
        logging.info("Handling direct message without file")
        user_message = format_user_message(message, bot_id)
        response = llm_response([{"role": "user", "content": user_message}])
        process_response(response, False, client, say, event)


def handle_thread_message(
    client, say, event, message, bot_id, request_type=RequestType.bug_report
):
    formatted_messages = fetch_and_format_thread_messages(client, message)
    pprint(formatted_messages, indent=2)
    # if is_bot_thread(client, formatted_messages):
    if message.get("files"):
        logging.info("Handling thread message with file")
        handle_message_with_file(
            client, say, event, message, bot_id, formatted_messages, request_type
        )
    else:
        logging.info("Handling thread message without file")
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
):
    file_data, speech_mode = process_file_upload(client, message)

    print("message", message)

    user_message = format_user_message(message, bot_id, file_data)
    print("user_message", user_message)

    all_messages = compile_messages(additional_messages, user_message)
    print("all_messages", all_messages)

    response = llm_response(all_messages, request_type=request_type)

    transcription = None

    for file in file_data:
        if file["upload_type"] == "audio":
            if transcription:
                transcription += "\n" + file["content"]
            else:
                transcription = file["content"]

    if transcription:

        client.chat_update(
            token=SLACK_USER_TOKEN,
            channel=message["channel"],
            text=transcription,
            ts=message["ts"],
            # metadata={"transcription": transcription},
        )

    process_response(response, speech_mode, client, say, event)


def handle_onboard(ack, client, respond, command):
    ack()

    channel_id = command.get("channel_id")

    onboarding_message = create_onboarding_message()
    pprint(onboarding_message)
    # respond(onboarding_message)
    client.chat_postMessage(channel=channel_id, blocks=onboarding_message["blocks"])


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
        # Fetch the history of messages in the thread using conversations.replies
        response = client.conversations_replies(channel=channel_id, ts=thread_ts)
        messages = response.get("messages", [])

        # Iterate through the messages to check if the bot has been mentioned or has sent a message
        for message in messages:
            # Check if the bot has sent this message
            if message.get("user") == bot_id:
                return True
            # Check if the bot has been mentioned in the message text
            if f"<@{bot_id}>" in message.get("text", ""):
                return True

        return False
    except Exception as e:
        print(f"Error checking if bot is in thread: {e}")
        return False


def handle_onboarding_modal_open(ack, body, client):
    ack()
    # Call views_open with the built-in client
    client.views_open(
        trigger_id=body["trigger_id"],
        # Pass the view payload
        view=create_onboarding_modal(),
    )


def handle_onboarding_modal_submit(ack, body, view):
    ack()
    pprint(body)
    pprint(view)


def process_file_upload(client, message):
    files = message.get("files")
    file_data = []
    speech_mode = False

    for file in files:
        file_url, file_type, mimetype = share_file_and_get_url(client, file.get("id"))
        file_data.append(process_file_content(file_url, file_type, mimetype, message))
        speech_mode |= file_type in ["webm", "mp4", "mp3", "wav", "m4a"]
        revoke_file_public_access(client, file.get("id"))

    return file_data, speech_mode


def share_file_and_get_url(client, file_id):
    file_info = client.files_info(file=file_id).data.get("file")
    client.files_sharedPublicURL(token=SLACK_USER_TOKEN, file=file_id)
    return (
        construct_file_url(file_info),
        file_info.get("filetype"),
        file_info.get("mimetype"),
    )


def construct_file_url(file_info):
    public_link = file_info.get("permalink_public")
    url_private = file_info.get("url_private")
    pub_secret = public_link.split("-")[-1]
    return f"{url_private}?pub_secret={pub_secret}"


def process_file_content(file_url, file_type, mimetype, message):
    if file_type in ["jpg", "jpeg", "png", "webp", "gif"]:
        return {
            "upload_type": "image",
            "content": describe_vision_anthropic(
                file_url, mimetype, message.get("text")
            ),
        }
    elif file_type in ["webm", "mp4", "mp3", "wav", "m4a"]:
        logging.info("Transcribing audio")
        return {
            "upload_type": "audio",
            "content": transcribe_audio(file_url, file_type),
        }
    else:
        logging.error(f"Unsupported file type: {file_type}")
        return None


def revoke_file_public_access(client, file_id):
    client.files_revokePublicURL(token=SLACK_USER_TOKEN, file=file_id)


def format_user_message(message, bot_id, file_data=None):
    user_message = message.get("text").replace(f"<@{bot_id}>", "")
    if file_data:
        user_message += "\nUser uploaded file contents:\n" + json.dumps(file_data)
    return user_message


def compile_messages(additional_messages, user_message):
    all_messages = additional_messages if additional_messages else []
    all_messages.append({"role": "user", "content": user_message})
    return all_messages


def process_response(response, speech_mode, client, say, event):
    if speech_mode:
        create_speech(response.ai_response)
        handle_speak(
            client, event["channel"], response.ai_response, thread_ts=event["ts"]
        )
    else:
        safe_say(say, text=response.ai_response, thread_ts=event["ts"])


def handle_speak(client, channel, ai_response, thread_ts=None):
    try:
        file_path = "tmp/speech.mp3"
        os.makedirs(os.path.dirname(file_path), exist_ok=True)
        upload_kwargs = {
            "channels": channel,
            "file": file_path,
            "title": "Sparrow's Response",
            "initial_comment": ai_response,
        }
        if thread_ts:
            upload_kwargs["thread_ts"] = thread_ts

        result = client.files_upload_v2(**upload_kwargs)
    except Exception as e:
        logging.error(f"Error uploading file: {str(e)}")


def handle_url_verification(event_data):
    return event_data["challenge"]
