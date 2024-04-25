# file_handlers.py

import json
import requests
from typing import Any, Dict, List, Optional, Tuple
from slack_sdk import WebClient
from llama_index.core import SimpleDirectoryReader

from ..logger import logger
from ..llm import LLMClient
from ..constants import text_file_types
from ..utils import download_and_save_file, delete_file


class FileHandler:
    def __init__(self, client: WebClient, llm_client: LLMClient):
        self.client = client
        self.llm_client = llm_client

    def process_files(self, message: Dict[str, Any]) -> List[Dict[str, str]]:
        try:
            files = message.get("files", [])
            file_data = []

            for file in files:
                file_url, file_type, mimetype = (
                    file["url_private"],
                    file["filetype"],
                    file["mimetype"],
                )
                file_content = self._process_file_content(
                    file_url, file_type, mimetype, message
                )
                if file_content:
                    file_data.append(file_content)
                    # speech_mode |= file_type in ["webm", "mp4", "mp3", "wav", "m4a"]

            return file_data
        except Exception as e:
            logger.error(f"Failed to process files: {e}")
            return []

    def _construct_file_url(self, file_info: Dict[str, Any]) -> str:
        public_link = file_info["permalink_public"]
        url_private = file_info["url_private"]
        pub_secret = public_link.split("-")[-1]
        return f"{url_private}?pub_secret={pub_secret}"

    def _process_file_content(
        self, file_url: str, file_type: str, mimetype: str, message: Dict[str, Any]
    ) -> Optional[Dict[str, str]]:
        headers = {"Authorization": f"Bearer {self.token}"}
        try:
            file_path = download_and_save_file(file_url, file_type, headers)
            if file_path:
                if file_type in ["jpg", "jpeg", "png", "webp", "gif"]:
                    logger.info("Processing image")
                    file_content = self.llm_client.describe_vision_anthropic(
                        file_path, mimetype, message.get("text")
                    )
                    upload_type = "image"
                elif file_type in ["webm", "mp4", "mp3", "wav", "m4a"]:
                    logger.info("Processing audio")
                    file_content = self.llm_client.transcribe_audio(file_url, file_type)
                    upload_type = "audio"
                elif file_type in text_file_types:
                    logger.info("Processing text file")
                    file_content = self._extract_text_from_file(file_path)
                    upload_type = "text_file"
                else:
                    logger.warning(f"Unsupported file type: {file_type}")
                    file_content = "Unsupported file type"
                    upload_type = "unsupported"

                delete_file(file_path)

            else:
                logger.error(f"Failed to download file: {file_url}")

            return {
                "upload_type": upload_type,
                "content": file_content,
            }
        except Exception as e:
            logger.error(f"Failed to process file: {e}")
            file_content = "Failed to process file with error: " + str(e)
            upload_type = "failed"

            return {
                "upload_type": upload_type,
                "content": file_content,
            }

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
