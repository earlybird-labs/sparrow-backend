# file_handlers.py

from typing import Any, Dict, List, Optional, Tuple
from slack_sdk import WebClient
from llama_index.core import SimpleDirectoryReader

from ..logger import logger
from ..llm import LLMClient
from ..constants import text_file_types
from ..utils import download_and_save_file, delete_file


class FileHandler:
    def __init__(self, token: str, client: WebClient, llm_client: LLMClient):
        self.token = token
        self.client = client
        self.llm_client = llm_client

    def process_files(
        self, message: Dict[str, Any]
    ) -> Tuple[List[Dict[str, str]], bool]:
        files = message.get("files", [])
        file_data = []
        speech_mode = False

        for file in files:
            file_url, file_type, mimetype = self._share_file_and_get_url(file["id"])
            file_content = self._process_file_content(
                file_url, file_type, mimetype, message
            )
            if file_content:
                file_data.append(file_content)
                speech_mode |= file_type in ["webm", "mp4", "mp3", "wav", "m4a"]

            self._revoke_file_public_access(file["id"])

        return file_data, speech_mode

    def _share_file_and_get_url(self, file_id: str) -> Tuple[str, str, str]:
        file_info = self.client.files_info(file=file_id).data["file"]
        try:
            self.client.files_sharedPublicURL(token=self.token, file=file_id)
        except:
            logger.warning(f"Failed to share file {file_id}")
        return (
            self._construct_file_url(file_info),
            file_info["filetype"],
            file_info["mimetype"],
        )

    def _construct_file_url(self, file_info: Dict[str, Any]) -> str:
        public_link = file_info["permalink_public"]
        url_private = file_info["url_private"]
        pub_secret = public_link.split("-")[-1]
        return f"{url_private}?pub_secret={pub_secret}"

    def _process_file_content(
        self, file_url: str, file_type: str, mimetype: str, message: Dict[str, Any]
    ) -> Optional[Dict[str, str]]:
        if file_type in ["jpg", "jpeg", "png", "webp", "gif"]:
            logger.info("Processing image")
            return {
                "upload_type": "image",
                "content": self.llm_client.describe_vision_anthropic(
                    file_url, mimetype, message.get("text")
                ),
            }
        elif file_type in ["webm", "mp4", "mp3", "wav", "m4a"]:
            return {
                "upload_type": "audio",
                "content": self.llm_client.transcribe_audio(file_url, file_type),
            }
        elif file_type in text_file_types:
            file_path = download_and_save_file(file_url, file_type)
            if file_path:
                text_content = self._extract_text_from_file(file_path)
                delete_file(file_path)
                return {
                    "upload_type": "text_file",
                    "content": text_content,
                }
        else:
            logger.warning(f"Unsupported file type: {file_type}")
        return None

    def _extract_text_from_file(self, file_path: str) -> str:
        reader = SimpleDirectoryReader(input_files=[file_path])
        documents = reader.load_data()
        text = []
        current_file = None
        for doc in documents:
            file_name = doc.metadata.get("file_name", "")
            if current_file != file_name:
                text.append(f"\n\nFile: {file_name}\n")
                current_file = file_name
            text.append(doc.text)

        text_str = "\n".join(text)
        return text_str.strip()

    def _revoke_file_public_access(self, file_id: str) -> None:
        self.client.files_revokePublicURL(token=self.token, file=file_id)
