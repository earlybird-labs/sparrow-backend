import instructor
from instructor import Mode
from openai import OpenAI
from anthropic import Anthropic
from groq import Groq

from .config import (
    TOGETHER_API_KEY,
    OPENAI_API_KEY,
    ANTHROPIC_API_KEY,
    GROQ_API_KEY,
)
from .models import AIResponse, RequestType
from .prompts import general, project_manager, classify_request
from .utils import get_file_data, save_audio_file, delete_file
from .logger import logger

groq_client = Groq(api_key=GROQ_API_KEY)
openai_client = OpenAI(api_key=OPENAI_API_KEY)
anthropic_client = Anthropic(api_key=ANTHROPIC_API_KEY)
together_client = OpenAI(
    api_key=TOGETHER_API_KEY, base_url="https://api.together.xyz/v1"
)

groq_instructor = instructor.from_groq(groq_client, mode=Mode.JSON)
openai_instructor = instructor.from_openai(openai_client)
anthropic_instructor = instructor.from_anthropic(anthropic_client)
together_instructor = instructor.from_openai(together_client, mode=Mode.MD_JSON)

client_model_map = {
    "openai": {
        "instructor": openai_instructor,
        "chat": openai_client,
        "model": "gpt-4-turbo",
    },
    "anthropic": {
        "instructor": anthropic_instructor,
        "chat": anthropic_client,
        "model": "claude-3-haiku-20240307",
    },
    "groq": {
        "instructor": groq_instructor,
        "chat": groq_client,
        "model": "llama3-70b-8192",
    },
    "together": {
        "instructor": together_instructor,
        "chat": together_client,
        "model": "meta-llama/Llama-3-70b-chat-hf",
    },
}

system_prompt_map = {
    "feature_request": project_manager,
    "bug_report": project_manager,
    "conversation": general,
    "general_request": general,
}


def classify_user_request(message, client_name="groq"):
    try:
        client = client_model_map[client_name]["instructor"]
        model = client_model_map[client_name]["model"]
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


def llm_response(
    messages,
    client_name="groq",
    request_type=RequestType.conversation,
    retry_count=1,
    structured=False,
):

    model = client_model_map[client_name]["model"]

    request_type_value = request_type.value
    system_prompt = system_prompt_map[request_type_value]

    full_messages = [
        {"role": "system", "content": system_prompt},
        *messages,
    ]

    attempt = 0

    if structured:

        client = client_model_map[client_name]["instructor"]

        while attempt <= retry_count:
            try:

                logger.info(f"Generating LLM response with {client_name}")

                return client.create(
                    model=model,
                    messages=full_messages,
                    response_model=AIResponse,
                )

            except Exception as e:
                logging.error(
                    f"Attempt {attempt} failed for {client_name} with error: {e}"
                )
                if attempt < retry_count:
                    client_name = "openai"  # Switch to openai for retry
                attempt += 1

        return None  # Return None if all retries fail

    else:

        client = client_model_map[client_name]["chat"]

        logger.info(f"Generating LLM response with {client_name}")

        response = client.chat.completions.create(
            model=model,
            messages=messages,
        )

        return AIResponse(ai_response=response.choices[0].message.content)


def transcribe_audio(file_url, file_type):
    try:
        audio_file_path = save_audio_file(file_url, file_type)
        audio_file = open(audio_file_path, "rb")
        transcription = openai_client.audio.transcriptions.create(
            model="whisper-1", file=audio_file
        )
        # delete the audio file
        delete_file(audio_file_path)
        return transcription.text
    except Exception as e:
        logger.error(f"Error transcribing audio: {e}")
        return None


def create_speech(text):
    try:
        speech_file_path = "tmp/speech.mp3"
        response = openai_client.audio.speech.create(
            model="tts-1", voice="alloy", input=text
        )

        with open(speech_file_path, "wb") as file:
            file.write(response.content)
    except Exception as e:
        logger.error(f"Error creating speech: {e}")
        return None


def describe_vision_anthropic(file_url, image_media_type, message=None):
    try:
        if message:
            prompt = f"The user's request is {message}. Your job is to describe this image in as much detail as possible as it relates to the user's request to be used in your response."
        else:
            prompt = "Describe this image in as much detail as possible. Extract as much information as possible from the image."

        image_data = get_file_data(file_url)
        message = anthropic_client.messages.create(
            model="claude-3-haiku-20240307",
            max_tokens=4000,
            messages=[
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
            ],
        )
        return message.content[0].text
    except Exception as e:
        logger.error(f"Error describing vision: {e}")
        return None


def describe_image(file_url):
    try:
        response = openai_client.chat.completions.create(
            model="gpt-4-turbo",
            messages=[
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
            ],
            max_tokens=2000,
        )

        return response.choices[0].message.content
    except Exception as e:
        logger.error(f"Error describing image: {e}")
        return None


if __name__ == "__main__":
    print(
        describe_vision_anthropic(
            file_url="https://upload.wikimedia.org/wikipedia/commons/a/a7/Camponotus_flavomarginatus_ant.jpg",
            image_media_type="image/jpeg",
        )
    )
