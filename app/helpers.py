import json

from .logger import logger
from .llm import (
    transcribe_audio,
    describe_vision_anthropic,
    create_vectorstore,
    upload_file,
    add_file_to_vectorstore,
    get_vectorstore,
)
from .services import (
    add_vectorstore_id_to_thread,
    find_db_thread,
    find_db_thread_by_id,
    update_thread,
)

from .constants import text_file_types

from .utils import get_file_data, save_file


def process_file_upload(token, client, message, thread_id=None):
    """
    Processes the uploaded files and determines if any are audio files.

    :param token: Authentication token for API access.
    :param client: Client object for API interactions.
    :param message: Dictionary containing message details, including files.
    :return: Tuple containing a list of processed file data and a boolean indicating if any audio files were processed.
    """
    files = message.get("files")
    file_datas = []
    speech_mode = False
    vectorstore = False

    print("thread_id", thread_id)
    print("type(thread_id)", type(thread_id))
    # actual_thread_id = thread_id["_id"]
    # print("actual_thread_id", actual_thread_id)
    thread_in_db = find_db_thread_by_id(thread_id)

    for file in files:
        file_url, file_type, mimetype = share_file_and_get_url(
            token, client, file.get("id")
        )

        file_data = process_file_content(file_url, file_type, mimetype, message)

        if file_data.get("upload_type") == "text_file":
            vectorstore = True
            file_id = file_data.get("content")
            vectorstore_id = thread_in_db.get("vectorstore_id")
            update_thread(
                thread_in_db, {"num_files": thread_in_db.get("num_files", 0) + 1}
            )
            add_file_to_vectorstore(vectorstore_id, file_id)
        else:

            file_datas.append(
                process_file_content(file_url, file_type, mimetype, message)
            )
        speech_mode |= file_type in ["webm", "mp4", "mp3", "wav", "m4a"]
        revoke_file_public_access(token, client, file.get("id"))

    return file_datas, speech_mode, vectorstore


def share_file_and_get_url(token, client, file_id):
    """
    Shares a file publicly and retrieves its URL, file type, and MIME type.

    :param token: Authentication token for API access.
    :param client: Client object for API interactions.
    :param file_id: ID of the file to share.
    :return: Tuple containing the file URL, file type, and MIME type.
    """
    file_info = client.files_info(file=file_id).data.get("file")
    client.files_sharedPublicURL(token=token, file=file_id)
    return (
        construct_file_url(file_info),
        file_info.get("filetype"),
        file_info.get("mimetype"),
    )


def construct_file_url(file_info):
    """
    Constructs a public URL for a file using its private URL and public permalink.

    :param file_info: Dictionary containing file details.
    :return: Constructed public URL for the file.
    """
    public_link = file_info.get("permalink_public")
    url_private = file_info.get("url_private")
    pub_secret = public_link.split("-")[-1]
    return f"{url_private}?pub_secret={pub_secret}"


def process_file_content(file_url, file_type, mimetype, message):
    """
    Processes the content of a file based on its type.

    :param file_url: URL of the file to process.
    :param file_type: Type of the file (e.g., 'jpg', 'mp3').
    :param mimetype: MIME type of the file.
    :param message: Dictionary containing the original message details.
    :return: Dictionary with the type of upload and content description, or None if file type is unsupported.
    """
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

    elif file_type in text_file_types:
        logger.info("Processing text file")

        file_path = save_file(file_url, file_type)

        file_id = upload_file(file_path).id
        print(file_id)

        return {
            "upload_type": "text_file",
            "content": file_id,
        }
    else:
        logger.error(f"Unsupported file type: {file_type}")
        return None


def revoke_file_public_access(token, client, file_id):
    """
    Revokes public access to a file.

    :param token: Authentication token for API access.
    :param client: Client object for API interactions.
    :param file_id: ID of the file to revoke access.
    """
    client.files_revokePublicURL(token=token, file=file_id)


def format_user_message(message, bot_id, file_data=None):
    """
    Formats a user message by removing the bot mention and appending file content descriptions.

    :param message: Dictionary containing the original message details.
    :param bot_id: ID of the bot to be removed from the message.
    :param file_data: List of dictionaries containing file data to append.
    :return: Formatted user message as a string.
    """
    user_message = message.get("text").replace(f"<@{bot_id}>", "")
    if file_data:
        user_message += "\nUser uploaded file contents:\n" + "".join(
            [f"{file['upload_type']}: {file['content']}\n" for file in file_data]
        )
    return user_message


def compile_messages(additional_messages, user_message):
    """
    Compiles a list of messages including the user message.

    :param additional_messages: List of additional messages to include.
    :param user_message: The main user message to append.
    :return: List of all messages including the user message.
    """
    all_messages = additional_messages if additional_messages else []
    all_messages.append({"role": "user", "content": user_message})
    return all_messages
