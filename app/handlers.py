import logging
import requests
import json

from .llm import (
    llm_response,
    describe_vision_anthropic,
    transcribe_audio,
    create_speech,
)
from .utils import safe_say, fetch_and_format_thread_messages, is_bot_thread
from .config import SLACK_USER_TOKEN
from .blocks.index import bug_form


def handle_message_with_file(client, say, event, message, bot_id, addt_messages=None):
    file_data, speech_mode = handle_file_upload(client, message)

    print(file_data)

    file_data_json = json.dumps(file_data)

    user_message = message.get("text").replace(f"<@{bot_id}>", "")

    user_message += "Attachments: " + file_data_json

    all_messages = []

    if addt_messages:
        all_messages.extend(addt_messages)

    all_messages.append({"role": "user", "content": user_message})

    response = llm_response(all_messages)

    if speech_mode:
        create_speech(response.ai_response)
        handle_speak(client, message)
    else:
        safe_say(say, text=response.ai_response, thread_ts=event["ts"])


def handle_message(ack, client, event, message, say):
    ack()

    bot_id = client.auth_test()["user_id"]

    if message.get("subtype") != "message_deleted":

        if bot_id in message.get("text"):

            if message.get("files"):
                handle_message_with_file(client, say, event, message, bot_id)
            else:
                response = llm_response(
                    [{"role": "user", "content": message.get("text")}]
                )
                if response.bug:

                    blocks = [
                        {
                            "type": "section",
                            "text": {
                                "type": "mrkdwn",
                                "text": response.ai_response,
                            },
                        }
                    ] + bug_form

                    safe_say(
                        say,
                        text=response.ai_response,
                        blocks=blocks,
                        thread_ts=event["ts"],
                    )
                else:
                    safe_say(say, text=response.ai_response, thread_ts=event["ts"])

        if message.get("thread_ts"):

            formatted_messages = fetch_and_format_thread_messages(client, message)

            if is_bot_thread(client, formatted_messages):
                if message.get("files"):
                    handle_message_with_file(
                        client, say, event, message, bot_id, formatted_messages
                    )
                else:
                    response = llm_response(formatted_messages)
                    if response.bug:

                        blocks = [
                            {
                                "type": "section",
                                "text": {
                                    "type": "mrkdwn",
                                    "text": response.ai_response,
                                },
                            }
                        ] + bug_form

                        safe_say(
                            say,
                            text=response.ai_response,
                            blocks=blocks,
                            thread_ts=event["ts"],
                        )
                    else:
                        safe_say(say, text=response.ai_response, thread_ts=event["ts"])
    else:
        print("No message")


def handle_file_upload(client, message):
    files = message.get("files")

    file_data = []

    speech_mode = False

    for file in files:
        file_id = file.get("id")
        file_url, file_type, mimetype = handle_file_sharing(client, file_id)

        if file_type in ["jpg", "jpeg", "png", "webp", "gif"]:
            image_description = describe_vision_anthropic(
                file_url=file_url,
                image_media_type=mimetype,
                message=message.get("text"),
            )
            file_data.append({"upload_type": "image", "content": image_description})
        elif file_type in ["webm", "mp4", "mp3", "wav", "m4a"]:
            print("Transcribing audio")
            transcription = transcribe_audio(file_url, file_type)
            file_data.append({"upload_type": "audio", "content": transcription})
            speech_mode = True

        else:
            logging.error(f"Unsupported file type: {file_type}")

        handle_file_revoke(client, file_id)

    return file_data, speech_mode


def handle_file_revoke(client, file_id):
    client.files_revokePublicURL(token=SLACK_USER_TOKEN, file=file_id)


def handle_file_sharing(client, file_id):
    file_info = client.files_info(file=file_id).data.get("file")
    file_type = file_info.get("filetype")
    mimetype = file_info.get("mimetype")

    client.files_sharedPublicURL(token=SLACK_USER_TOKEN, file=file_id)

    public_link = file_info.get("permalink_public")
    url_private = file_info.get("url_private")
    pub_secret = public_link.split("-")[-1]
    file_url = f"{url_private}?pub_secret={pub_secret}"

    return file_url, file_type, mimetype


def handle_speak(client, message):
    try:

        file_path = "app/tmp/speech.mp3"
        channel = message["channel"]
        result = client.files_upload(
            channels=channel,
            file=file_path,
            title="Sparrow's Voice Response",
            filetype="mp3",
        )
        # file_id = result["file"]["id"]
        # Optionally, send a message about the uploaded file
        # client.say(text=f"Uploaded an MP3 file: <@{file_id}>")
    except Exception as e:
        print(f"Error uploading file: {str(e)}")


def handle_app_mention(ack, event, say):
    ack()
    pass
    # try:
    #     response = llm_response([{"role": "user", "content": event["text"]}])
    #     safe_say(say, text=response.ai_response, thread_ts=event["ts"])
    # except Exception as e:
    #     logging.error(f"Error responding to app mention: {e}")


def handle_open_modal(ack, body, client):
    # Acknowledge the command request
    ack()
    # Call views_open with the built-in client
    client.views_open(
        # Pass a valid trigger_id within 3 seconds of receiving it
        trigger_id=body["trigger_id"],
        # View payload
        view={
            "type": "modal",
            # View identifier
            "callback_id": "view_1",
            "title": {"type": "plain_text", "text": "Sparrow"},
            "submit": {"type": "plain_text", "text": "Submit"},
            "blocks": [
                {
                    "type": "input",
                    "block_id": "input_c",
                    "label": {
                        "type": "plain_text",
                        "text": "What are your hopes and dreams?",
                    },
                    "element": {
                        "type": "plain_text_input",
                        "action_id": "dreamy_input",
                        "multiline": True,
                    },
                },
            ],
        },
    )


def generate_response(prompt):
    """
    Generates a response from the Llama2 model for a given prompt.

    Args:
        prompt (str): The input prompt to generate a response for.

    Returns:
        str: The generated response from the model.
    """
    response = requests.post(
        "http://localhost:11434/api/generate",
        json={"model": "dolphin", "prompt": prompt, "stream": False},
    )
    if response.status_code == 200:
        return response.json()["response"]
        # return "For sure"
    else:
        raise Exception(f"Failed to generate response: {response.text}")
