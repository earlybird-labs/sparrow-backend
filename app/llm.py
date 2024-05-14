# llm.py

import json

from typing import List, Dict, Any, Optional, Type
from app.models import AIResponse, RequestType, EntityGraph, IssueTicket
from app.prompts import (
    general,
    project_manager,
    classify_request,
    formatting_prompt,
    visualizer_prompt,
)
from app.utils import (
    get_file_data,
    save_file,
    delete_file,
    fetch_and_format_thread_messages,
)
from app.logger import logger
from app.config import OPENAI_API_KEY, ANTHROPIC_API_KEY, GROQ_API_KEY, TOGETHER_API_KEY

import instructor
from openai import OpenAI
from anthropic import Anthropic
from groq import Groq


class LLMClient:
    def __init__(self):
        self.openai_client = OpenAI(api_key=OPENAI_API_KEY)
        self.anthropic_client = Anthropic(api_key=ANTHROPIC_API_KEY)
        self.groq_client = Groq(api_key=GROQ_API_KEY)
        self.together_client = OpenAI(
            api_key=TOGETHER_API_KEY, base_url="https://api.together.xyz/v1"
        )

        self.openai_instructor = instructor.from_openai(self.openai_client)
        self.anthropic_instructor = instructor.from_anthropic(self.anthropic_client)
        self.groq_instructor = instructor.from_groq(
            self.groq_client, mode=instructor.Mode.JSON
        )
        self.together_instructor = instructor.from_openai(
            self.together_client, mode=instructor.Mode.MD_JSON
        )

        self.client_model_map = {
            "openai": {
                "instructor": self.openai_instructor,
                "chat": self.openai_client,
                "model": "gpt-4-turbo",
            },
            "anthropic": {
                "instructor": self.anthropic_instructor,
                "chat": self.anthropic_client,
                "model": "claude-3-haiku-20240307",
            },
            "groq": {
                "instructor": self.groq_instructor,
                "chat": self.groq_client,
                "model": "llama3-70b-8192",
            },
            "together": {
                "instructor": self.together_instructor,
                "chat": self.together_client,
                "model": "meta-llama/Llama-3-70b-chat-hf",
            },
        }

        self.system_prompt_map = {
            "feature_request": project_manager,
            "bug_report": project_manager,
            "conversation": general,
            "general_request": general,
            "ai_conversation": general,
            "visualizer": visualizer_prompt,
        }

    def _generate_llm_response(
        self,
        messages: List[Dict[str, str]],
        temperature: float,
        client: Any,
        model: str,
    ) -> Optional[AIResponse]:
        try:
            logger.info(f"Generating LLM response with {client}")
            # formatted_messages = fetch_and_format_thread_messages(messages)
            response = client.chat.completions.create(
                model=model,
                temperature=temperature,
                messages=messages,
            )
            logger.info(f"Response: {response}")
            return AIResponse(content=response.choices[0].message.content)
        except Exception as e:
            logger.error(f"Error generating LLM response: {e}")
            return None

    def llm_response(
        self,
        messages: List[Dict[str, str]],
        temperature: float = 0.7,
        client_name: str = "groq",
        request_type: RequestType = RequestType.conversation,
        retry_count: int = 1,
        structured: bool = False,
        response_model: Optional[Type] = None,
    ):
        model = self.client_model_map[client_name]["model"]
        request_type_value = request_type.value
        system_prompt = self.system_prompt_map[request_type_value]
        full_messages = [
            {"role": "system", "content": system_prompt},
            *messages,
        ]

        print("full_messages", json.dumps(full_messages, indent=4))

        attempt = 0

        while attempt <= retry_count:
            if structured:
                client = self.client_model_map[client_name]["instructor"]
                response = client.create(
                    model=model,
                    temperature=temperature,
                    messages=full_messages,
                    response_model=response_model,
                )
            else:
                client = self.client_model_map[client_name]["chat"]
                response = self._generate_llm_response(
                    full_messages, temperature, client, model
                )

            if response is not None:
                return response

            logger.error(f"Attempt {attempt} failed for {client_name}. Retrying...")
            if attempt < retry_count:
                client_name = "openai"  # Switch to openai for retry
                model = self.client_model_map[client_name]["model"]
            attempt += 1

        return None  # Return None if all retries fail

    def classify_user_request(
        self, message: str, client_name: str = "groq"
    ) -> Optional[RequestType]:
        try:
            client = self.client_model_map[client_name]["instructor"]
            model = self.client_model_map[client_name]["model"]
            messages = [
                {"role": "system", "content": classify_request},
                {"role": "user", "content": message},
            ]
            response = client.create(
                model=model,
                messages=messages,
                response_model=RequestType,
            )
            return response
        except Exception as e:
            logger.error(f"Error classifying user request: {e}")
            return None

    def prepare_tickets_from_thread(
        self, messages: List[Dict[str, str]], client_name: str = "together"
    ) -> Optional[List[IssueTicket]]:
        try:
            client = self.client_model_map[client_name]["instructor"]
            model = self.client_model_map[client_name]["model"]

            full_messages = [
                {
                    "role": "system",
                    "content": "Your job is to prepare a list of issue tickets from a conversation thread and return the list of tickets in JSON format.",
                },
                *messages,
            ]

            return client.create(
                model=model,
                messages=full_messages,
                temperature=0.3,
                response_model=List[IssueTicket],
            )

        except Exception as e:
            logger.error(f"Error preparing tickets from thread: {e}")
            return None

    def transcribe_audio(self, file_url: str, file_type: str) -> Optional[str]:
        try:
            audio_file_path = save_file(file_url, file_type)
            audio_file = open(audio_file_path, "rb")
            transcription = self.openai_client.audio.transcriptions.create(
                model="whisper-1", file=audio_file
            )
            delete_file(audio_file_path)
            return transcription.text
        except Exception as e:
            logger.error(f"Error processing audio file: {e}")
            return None

    def create_speech(self, text: str) -> None:
        speech_file_path = "tmp/speech.mp3"
        try:
            response = self.openai_client.audio.speech.create(
                model="tts-1", voice="alloy", input=text
            )
            with open(speech_file_path, "wb") as file:
                file.write(response.content)
        except Exception as e:
            logger.error(f"Error saving speech file: {e}")

    def describe_image(
        self,
        file_url: str,
        image_media_type: str,
        message: Optional[str] = None,
        mode: str = None,
        remote: bool = False,
        client_name: str = "anthropic",
    ) -> Optional[str]:
        if client_name == "anthropic":
            return self.describe_vision_anthropic(
                file_url, image_media_type, message, mode, remote
            )
        elif client_name == "openai":
            return self.describe_image_openai(file_url)
        return None

    def describe_vision_anthropic(
        self,
        file_url: str,
        image_media_type: str,
        message: Optional[str] = None,
        mode: str = None,
        remote: bool = False,
    ) -> Optional[str]:
        try:
            if mode:
                prompt = self.system_prompt_map[mode]
            else:
                prompt = "Describe this image in as much detail as possible. Extract as much information as possible from the image."

            if message:
                prompt += f"\nThe user also sent the following message along with the image: {message}"

            image_data = get_file_data(file_url, remote=remote)
            messages = [
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "image",
                            "source": {
                                "type": "base64",
                                "media_type": image_media_type,
                                "data": image_data,
                            },
                        },
                        {
                            "type": "text",
                            "text": prompt,
                        },
                    ],
                }
            ]
            response = self.anthropic_client.messages.create(
                model="claude-3-haiku-20240307",
                max_tokens=4000,
                messages=messages,
            )
            return response.content[0].text
        except Exception as e:
            logger.error(f"Error describing vision: {e}")
            return None

    def describe_image_openai(self, file_url: str) -> Optional[str]:
        try:
            messages = [
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": "Describe this image."},
                        {
                            "type": "image_url",
                            "image_url": {"url": file_url},
                        },
                    ],
                }
            ]
            response = self.openai_client.chat.completions.create(
                model="gpt-4-turbo",
                messages=messages,
                max_tokens=2000,
            )
            return response.choices[0].message.content
        except Exception as e:
            logger.error(f"Error describing image: {e}")
            return None
