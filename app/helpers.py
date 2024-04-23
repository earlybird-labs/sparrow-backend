import json

from .logger import logger
from .llm import transcribe_audio, describe_vision_anthropic


def process_file_upload(token, client, message):
    files = message.get("files")
    file_data = []
    speech_mode = False

    for file in files:
        file_url, file_type, mimetype = share_file_and_get_url(
            token, client, file.get("id")
        )
        file_data.append(process_file_content(file_url, file_type, mimetype, message))
        speech_mode |= file_type in ["webm", "mp4", "mp3", "wav", "m4a"]
        revoke_file_public_access(token, client, file.get("id"))

    return file_data, speech_mode


def share_file_and_get_url(token, client, file_id):
    file_info = client.files_info(file=file_id).data.get("file")
    client.files_sharedPublicURL(token=token, file=file_id)
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
        logger.info("Transcribing audio")
        return {
            "upload_type": "audio",
            "content": transcribe_audio(file_url, file_type),
        }
    else:
        logger.error(f"Unsupported file type: {file_type}")
        return None


def revoke_file_public_access(token, client, file_id):
    client.files_revokePublicURL(token=token, file=file_id)


def format_user_message(message, bot_id, file_data=None):
    user_message = message.get("text").replace(f"<@{bot_id}>", "")
    if file_data:
        user_message += "\nUser uploaded file contents:\n" + "".join(
            [f"{file['upload_type']}: {file['content']}\n" for file in file_data]
        )
    return user_message


def compile_messages(additional_messages, user_message):
    all_messages = additional_messages if additional_messages else []
    all_messages.append({"role": "user", "content": user_message})
    return all_messages
