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
from .prompts import general, project_manager, classify_request, formatting_prompt
from .utils import get_file_data, save_file, delete_file
from .logger import logger

import time

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


def upload_file(file_url):
    response = openai_client.files.create(
        file=open(file_url, "rb"), purpose="assistants"
    )
    time.sleep(10)
    return response


def get_vectorstore(vectorstore_id):
    return openai_client.beta.vector_stores.retrieve(vectorstore_id)


def create_vectorstore(name, lifespan_days=7):
    return openai_client.beta.vector_stores.create(
        name=name,
        expires_after={"anchor": "last_active_at", "days": lifespan_days},
    )


def add_file_to_vectorstore(vectorstore_id, file_id):
    return openai_client.beta.vector_stores.files.create(
        vector_store_id=vectorstore_id, file_id=file_id
    )


def delete_vectorstore(vectorstore_id):
    return openai_client.beta.vector_stores.delete(vectorstore_id)


def modify_thread(thread_id, vectorstore_ids):
    return openai_client.beta.threads.update(
        thread_id=thread_id,
        tool_resources={"file_search": {"vector_store_ids": vectorstore_ids}},
    )


def create_thread():

    # Create a thread and attach the file to the message
    return openai_client.beta.threads.create()


def add_message_to_thread(thread_id, content, role="user"):
    return openai_client.beta.threads.messages.create(
        thread_id=thread_id, role=role, content=content
    )


def create_run(thread_id, assistant_id="asst_2KNsZSP3VAyHcfce8HQB6e9l"):
    return openai_client.beta.threads.runs.create(
        thread_id=thread_id, assistant_id=assistant_id, tools=[{"type": "file_search"}]
    )


def retrieve_message(message_id, thread_id):
    result = (
        openai_client.beta.threads.messages.retrieve(
            message_id=message_id,
            thread_id=thread_id,
        )
        .content[0]
        .text.value
    )
    print("result", result)
    return result


def run_steps(thread_id, run_id):
    return openai_client.beta.threads.runs.steps.list(
        thread_id=thread_id, run_id=run_id
    )


def classify_user_request(message, client_name="groq"):
    """
    Classifies the user's request based on the provided message and client.

    :param message: The user's message to classify.
    :param client_name: The name of the client to use for classification.
    :return: The classified request type or None if an error occurs.
    """
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
    temperature=0.7,
    client_name="groq",
    request_type=RequestType.conversation,
    retry_count=1,
    structured=False,
):
    """
    Generates a response from a language model based on the provided parameters.

    :param messages: List of messages for the language model.
    :param temperature: The randomness of the response generation.
    :param client_name: The client to use for generating the response.
    :param request_type: The type of request to respond to.
    :param retry_count: Number of retries if the initial attempt fails.
    :param structured: Boolean indicating if the response should be structured.
    :return: An AIResponse object or None if all attempts fail.
    """
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
                    temperature=temperature,
                    messages=full_messages,
                    response_model=AIResponse,
                )

            except Exception as e:
                logger.error(
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
            temperature=temperature,
            messages=messages,
        )

        return AIResponse(ai_response=response.choices[0].message.content)


def format_response_in_markdown(response):
    """
    Formats the given response in markdown.

    :param response: The response to format.
    :return: The formatted response or None if an error occurs.
    """
    try:
        return llm_response(
            messages=[
                {
                    "role": "system",
                    "content": formatting_prompt,
                },
                {"role": "user", "content": response},
            ],
            temperature=0.0,
            client_name="groq",
            structured=False,
        ).ai_response.strip()
    except Exception as e:
        logger.error(f"Error formatting response in markdown: {e}")
        return None


def create_title_from_transcript(transcript):
    """
    Creates a title from the given transcript.

    :param transcript: The transcript to create a title from.
    :return: The created title or None if an error occurs.
    """
    try:
        return llm_response(
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


def transcribe_audio(file_url, file_type):
    """
    Transcribes audio from the given file URL and file type.

    :param file_url: The URL of the audio file.
    :param file_type: The type of the audio file.
    :return: The transcription text or None if an error occurs.
    """
    try:
        audio_file_path = save_file(file_url, file_type)
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
    """
    Creates speech from the given text.

    :param text: The text to convert to speech.
    :return: None if an error occurs.
    """
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
    """
    Describes the vision of an image using the Anthropic model.

    :param file_url: The URL of the image.
    :param image_media_type: The media type of the image.
    :param message: Optional message to include in the description.
    :return: The detailed description of the image or None if an error occurs.
    """
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
    """
    Requests a description of an image using the OpenAI GPT-4 Turbo model.

    :param file_url: The URL of the image to be described.
    :return: A string containing the description of the image or None if an error occurs.
    """
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
