import logging
import requests
import json
import os

from .llm import (
    llm_response,
    describe_vision_anthropic,
    transcribe_audio,
    create_speech,
)
from .utils import safe_say, fetch_and_format_thread_messages, is_bot_thread
from .config import SLACK_USER_TOKEN
from .blocks.index import bug_form


def handle_message_with_file(
    client, say, event, message, bot_id, additional_messages=None
):
    file_data, speech_mode = process_file_upload(client, message)

    user_message = format_user_message(message, bot_id, file_data)

    all_messages = compile_messages(additional_messages, user_message)

    process_response(llm_response(all_messages), speech_mode, client, say, event)


def handle_command(ack, say, command, client):
    # Acknowledge the command request
    ack()
    # Respond back with the text received in the command, only visible to the user
    client.chat_postEphemeral(
        channel=command["channel_id"],
        user=command["user_id"],
        text="Commands not yet implemented",
    )


def handle_message(ack, client, event, message, say):
    ack()

    bot_id = client.auth_test()["user_id"]

    print(event)

    if message.get("subtype") != "message_deleted":
        if bot_id in message.get("text"):
            process_direct_message(client, say, event, message, bot_id)
        elif message.get("thread_ts"):
            process_thread_message(client, say, event, message, bot_id)


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


def format_user_message(message, bot_id, file_data):
    user_message = message.get("text").replace(f"<@{bot_id}>", "")
    if file_data:
        user_message += " Attachments: " + json.dumps(file_data)
    return user_message


def compile_messages(additional_messages, user_message):
    all_messages = additional_messages if additional_messages else []
    all_messages.append({"role": "user", "content": user_message})
    return all_messages


def process_response(response, speech_mode, client, say, event):
    if speech_mode:
        create_speech(response.ai_response)
        handle_speak(client, event["channel"], thread_ts=event["ts"])
    else:
        safe_say(say, text=response.ai_response, thread_ts=event["ts"])


def process_direct_message(client, say, event, message, bot_id):
    if message.get("files"):
        handle_message_with_file(client, say, event, message, bot_id)
    else:
        response = llm_response([{"role": "user", "content": message.get("text")}])
        process_bug_response(response, say, event)


def process_thread_message(client, say, event, message, bot_id):
    if message.get("thread_ts"):
        formatted_messages = fetch_and_format_thread_messages(client, message)
        if is_bot_thread(client, formatted_messages):
            if message.get("files"):
                handle_message_with_file(
                    client, say, event, message, bot_id, formatted_messages
                )
            else:
                response = llm_response(formatted_messages)
                process_bug_response(response, say, event)


def process_bug_response(response, say, event):
    if response.bug:
        say(blocks=bug_form(), thread_ts=event["ts"])
    else:
        safe_say(say, text=response.ai_response, thread_ts=event["ts"])


def handle_speak(client, channel, thread_ts=None):
    try:
        file_path = "tmp/speech.mp3"
        os.makedirs(os.path.dirname(file_path), exist_ok=True)
        upload_kwargs = {
            "channels": channel,
            "file": file_path,
            "title": "Sparrow's Response",
        }
        if thread_ts:
            upload_kwargs["thread_ts"] = thread_ts

        result = client.files_upload_v2(**upload_kwargs)
        # file_id = result["file"]["id"]
        # Optionally, send a message about the uploaded file
        # client.say(text=f"Uploaded an MP3 file: <@{file_id}>", thread_ts=thread_ts)
    except Exception as e:
        print(f"Error uploading file: {str(e)}")
