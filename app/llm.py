# llm.py

from typing import List, Dict, Any, Optional
from .models import AIResponse, RequestType
from .prompts import general, project_manager, classify_request, formatting_prompt
from .utils import (
    get_file_data,
    save_file,
    delete_file,
    fetch_and_format_thread_messages,
)
from .logger import logger
from .config import OPENAI_API_KEY, ANTHROPIC_API_KEY, GROQ_API_KEY, TOGETHER_API_KEY

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
        }

    def upload_file(self, file_url: str) -> Any:
        return self.openai_client.files.create(
            file=open(file_url, "rb"), purpose="assistants"
        )

    def get_vectorstore(self, vectorstore_id: str) -> Any:
        return self.openai_client.beta.vector_stores.retrieve(vectorstore_id)

    def create_vectorstore(self, name: str, lifespan_days: int = 3) -> Any:
        return self.openai_client.beta.vector_stores.create(
            name=name,
            expires_after={"anchor": "last_active_at", "days": lifespan_days},
        )

    def add_file_to_vectorstore(self, vectorstore_id: str, file_id: str) -> Any:
        return self.openai_client.beta.vector_stores.files.create(
            vector_store_id=vectorstore_id, file_id=file_id
        )

    def delete_vectorstore(self, vectorstore_id: str) -> Any:
        return self.openai_client.beta.vector_stores.delete(vectorstore_id)

    def modify_thread(self, thread_id: str, vectorstore_ids: List[str]) -> Any:
        return self.openai_client.beta.threads.update(
            thread_id=thread_id,
            tool_resources={"file_search": {"vector_store_ids": vectorstore_ids}},
        )

    def create_thread(self) -> Any:
        return self.openai_client.beta.threads.create()

    def add_message_to_thread(
        self, thread_id: str, content: str, role: str = "user"
    ) -> Any:
        return self.openai_client.beta.threads.messages.create(
            thread_id=thread_id, role=role, content=content
        )

    def create_run(
        self, thread_id: str, assistant_id: str = "asst_2KNsZSP3VAyHcfce8HQB6e9l"
    ) -> Any:
        return self.openai_client.beta.threads.runs.create(
            thread_id=thread_id,
            assistant_id=assistant_id,
            tools=[{"type": "file_search"}],
        )

    def retrieve_message(self, message_id: str, thread_id: str) -> str:
        result = (
            self.openai_client.beta.threads.messages.retrieve(
                message_id=message_id,
                thread_id=thread_id,
            )
            .content[0]
            .text.value
        )
        print("result", result)
        return result

    def run_steps(self, thread_id: str, run_id: str) -> Any:
        return self.openai_client.beta.threads.runs.steps.list(
            thread_id=thread_id, run_id=run_id
        )

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

    def _generate_llm_response(
        self,
        messages: List[Dict[str, str]],
        temperature: float,
        client: Any,
        model: str,
    ) -> Optional[AIResponse]:
        try:
            logger.info(f"Generating LLM response with {client}")
            print(messages)
            # formatted_messages = fetch_and_format_thread_messages(messages)
            response = client.chat.completions.create(
                model=model,
                temperature=temperature,
                messages=messages,
            )
            return AIResponse(ai_response=response.choices[0].message.content)
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
    ) -> Optional[AIResponse]:
        model = self.client_model_map[client_name]["model"]
        request_type_value = request_type.value
        system_prompt = self.system_prompt_map[request_type_value]
        full_messages = [
            {"role": "system", "content": system_prompt},
            *messages,
        ]
        attempt = 0

        while attempt <= retry_count:
            if structured:
                client = self.client_model_map[client_name]["instructor"]
                response = client.create(
                    model=model,
                    temperature=temperature,
                    messages=full_messages,
                    response_model=AIResponse,
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
            attempt += 1

        return None  # Return None if all retries fail

    def format_response_in_markdown(self, response: str) -> Optional[str]:
        try:
            return self.llm_response(
                messages=[
                    {"role": "system", "content": formatting_prompt},
                    {"role": "user", "content": response},
                ],
                temperature=0.0,
                client_name="groq",
                structured=False,
            ).ai_response.strip()
        except Exception as e:
            logger.error(f"Error formatting response in markdown: {e}")
            return None

    def create_title_from_transcript(self, transcript: str) -> Optional[str]:
        try:
            return self.llm_response(
                messages=[
                    {
                        "role": "system",
                        "content": "Your job is to create a single phrase title for a voice memo.",
                    },
                    {"role": "user", "content": transcript},
                ],
                client_name="groq",
                structured=False,
            ).ai_response
        except Exception as e:
            logger.error(f"Error creating title from transcript: {e}")
            return None

    def _process_audio_file(self, file_url: str, file_type: str) -> Optional[str]:
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

    def transcribe_audio(self, file_url: str, file_type: str) -> Optional[str]:
        return self._process_audio_file(file_url, file_type)

    def _save_speech_file(self, text: str, file_path: str) -> None:
        try:
            response = self.openai_client.audio.speech.create(
                model="tts-1", voice="alloy", input=text
            )
            with open(file_path, "wb") as file:
                file.write(response.content)
        except Exception as e:
            logger.error(f"Error saving speech file: {e}")

    def create_speech(self, text: str) -> None:
        speech_file_path = "tmp/speech.mp3"
        self._save_speech_file(text, speech_file_path)

    def describe_vision_anthropic(
        self, file_url: str, image_media_type: str, message: Optional[str] = None
    ) -> Optional[str]:
        try:
            if message:
                prompt = f"The user's request is {message}. Your job is to describe this image in as much detail as possible as it relates to the user's request to be used in your response."
            else:
                prompt = "Describe this image in as much detail as possible. Extract as much information as possible from the image."
            image_data = get_file_data(file_url)
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

    def describe_image(self, file_url: str) -> Optional[str]:
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
