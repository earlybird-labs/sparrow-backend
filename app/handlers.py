import logging
import json
import os
from pprint import pprint

from .llm import (
    llm_response,
    describe_vision_anthropic,
    transcribe_audio,
    create_speech,
    ollama_response,
)
from .utils import safe_say, fetch_and_format_thread_messages, is_bot_thread
from .config import SLACK_USER_TOKEN
from .workflows.forms.onboard import create_onboarding_message, create_onboarding_modal


def handle_message(ack, client, event, message, say):
    ack()

    bot_id = client.auth_test()["user_id"]

    print(event)

    ignore_list = ["message_deleted", "message_changed"]

    if event.get("subtype") not in ignore_list:
        if bot_id in message.get("text"):
            logging.info("Handling direct message")
            handle_direct_message(client, say, event, message, bot_id)
        elif message.get("thread_ts"):
            logging.info("Handling thread message")
            handle_thread_message(client, say, event, message, bot_id)


def handle_direct_message(client, say, event, message, bot_id):
    if message.get("files"):
        logging.info("Handling direct message with file")
        handle_message_with_file(client, say, event, message, bot_id)
    else:
        logging.info("Handling direct message without file")
        user_message = format_user_message(message, bot_id)
        response = llm_response([{"role": "user", "content": user_message}])
        process_response(response, False, client, say, event)


def handle_thread_message(client, say, event, message, bot_id):
    formatted_messages = fetch_and_format_thread_messages(client, message)
    pprint(formatted_messages, indent=2)
    if is_bot_thread(client, formatted_messages):
        if message.get("files"):
            logging.info("Handling thread message with file")
            handle_message_with_file(
                client, say, event, message, bot_id, formatted_messages
            )
        else:
            logging.info("Handling thread message without file")
            response = llm_response(formatted_messages)
            process_response(response, False, client, say, event)


def handle_message_with_file(
    client, say, event, message, bot_id, additional_messages=None
):
    file_data, speech_mode = process_file_upload(client, message)

    print("message", message)

    user_message = format_user_message(message, bot_id, file_data)
    print("user_message", user_message)

    all_messages = compile_messages(additional_messages, user_message)
    print("all_messages", all_messages)

    response = llm_response(all_messages)

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
